"""
Daily Story Delivery Scheduler

Checks for users who should receive their daily story based on their
delivery_time and timezone preferences. Queues story generation jobs
for eligible users.

TIMING STRATEGY:
Stories are generated AHEAD of the user's preferred delivery time to ensure
on-time delivery. For example, if a user wants their story at 8:00 AM:
  - Generation starts at 7:30 AM (30 min buffer by default)
  - Story is generated, audio/images created
  - Email is sent once complete (ideally by 8:00 AM)

FUTURE SCALING:
For high user counts, consider overnight batch generation:
  - Generate all stories between 2-5 AM (off-peak)
  - Store completed stories with scheduled delivery time
  - Separate email worker sends at user's preferred time
"""

import asyncio
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
from uuid import uuid4
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from backend.database.users import UserService
from backend.database.stories import StoryService
from backend.database.jobs import JobQueueService
from backend.utils.logging import get_logger

logger = get_logger("daily_scheduler")


class DailyStoryScheduler:
    """
    Scheduler that checks for users who need their daily story.

    Runs every minute (configurable) and checks:
    1. Is it time to START generating (delivery_time - lead_time)?
    2. Have they already received a story today?
    3. Do they have credits available?

    If all conditions are met, queues a story generation job.
    """

    def __init__(
        self,
        check_interval_seconds: int = 60,  # Check every minute
        generation_lead_minutes: int = 30,  # Start generating 30 min before delivery
        delivery_window_minutes: int = 60,  # 60-minute window to catch the trigger
    ):
        self.check_interval = check_interval_seconds
        self.generation_lead = generation_lead_minutes
        self.delivery_window = delivery_window_minutes

        self.scheduler = AsyncIOScheduler()
        self.job_service: Optional[JobQueueService] = None
        self.user_service: Optional[UserService] = None
        self.story_service: Optional[StoryService] = None

        self._is_checking = False

    async def initialize(self):
        """Initialize database connections."""
        self.job_service = JobQueueService()
        self.user_service = UserService()
        self.story_service = StoryService()

        logger.info(
            "Daily scheduler initialized",
            check_interval=self.check_interval,
            generation_lead=self.generation_lead,
            delivery_window=self.delivery_window
        )

    def _parse_delivery_time(self, time_str: str) -> tuple[int, int]:
        """Parse HH:MM string to (hour, minute) tuple."""
        try:
            parts = time_str.split(":")
            return int(parts[0]), int(parts[1])
        except (ValueError, IndexError):
            return 8, 0  # Default to 8:00 AM

    def _is_generation_time(
        self,
        delivery_time: str,
        user_timezone: str,
        now: Optional[datetime] = None
    ) -> bool:
        """
        Check if it's time to START generating the story.

        We trigger generation BEFORE the delivery time to ensure stories
        arrive on time. If user wants 8:00 AM delivery and lead is 30 min,
        we start generating at 7:30 AM.

        Args:
            delivery_time: "HH:MM" format (user's desired DELIVERY time)
            user_timezone: IANA timezone string (e.g., "America/New_York")
            now: Current UTC time (for testing)

        Returns:
            True if within generation window (delivery_time - lead_time)
        """
        if now is None:
            now = datetime.now(timezone.utc)

        try:
            tz = ZoneInfo(user_timezone)
        except Exception:
            tz = ZoneInfo("UTC")

        # Convert current time to user's timezone
        user_now = now.astimezone(tz)

        # Parse delivery time
        target_hour, target_minute = self._parse_delivery_time(delivery_time)

        # Create target DELIVERY datetime in user's timezone for today
        delivery_datetime = user_now.replace(
            hour=target_hour,
            minute=target_minute,
            second=0,
            microsecond=0
        )

        # Calculate when to START generation (before delivery time)
        generation_start = delivery_datetime - timedelta(minutes=self.generation_lead)
        generation_end = generation_start + timedelta(minutes=self.delivery_window)

        return generation_start <= user_now < generation_end

    def _has_story_today(self, user: Dict[str, Any]) -> bool:
        """Check if user already received a story today (in their timezone)."""
        last_story_at = user.get("last_story_at")
        if not last_story_at:
            return False

        # Parse last_story_at
        if isinstance(last_story_at, str):
            try:
                last_story_dt = datetime.fromisoformat(last_story_at.replace("Z", "+00:00"))
            except ValueError:
                return False
        else:
            last_story_dt = last_story_at

        # Get user's timezone
        user_timezone = user.get("preferences", {}).get("timezone", "UTC")
        try:
            tz = ZoneInfo(user_timezone)
        except Exception:
            tz = ZoneInfo("UTC")

        # Check if last story was today in user's timezone
        now_user_tz = datetime.now(timezone.utc).astimezone(tz)
        last_story_user_tz = last_story_dt.astimezone(tz)

        return now_user_tz.date() == last_story_user_tz.date()

    async def check_and_queue_stories(self):
        """
        Main scheduler function - checks all eligible users and queues stories.
        Called periodically by APScheduler.
        """
        if self._is_checking:
            return

        self._is_checking = True
        queued_count = 0

        try:
            # Get all users who might need stories
            users = await self.user_service.get_users_needing_story(
                before_time=datetime.now(timezone.utc)
            )

            for user in users:
                try:
                    user_id = user.get("id")

                    # Skip if no credits
                    credits = user.get("credits", 0)
                    if credits < 1:
                        continue

                    # Skip if already received story today
                    if self._has_story_today(user):
                        continue

                    # Skip if user already has a pending/running job
                    active_jobs = await self.job_service.get_user_active_jobs(user_id, limit=1)
                    if active_jobs:
                        logger.debug(
                            "Skipping user - already has active job",
                            email=user.get('email'),
                            job_id=active_jobs[0].get('job_id')
                        )
                        continue

                    # Get delivery preferences
                    prefs = user.get("preferences", {})
                    delivery_time = prefs.get("delivery_time", "08:00")
                    user_timezone = prefs.get("timezone", "UTC")

                    # Check if it's time to START generating (ahead of delivery time)
                    if not self._is_generation_time(delivery_time, user_timezone):
                        continue

                    # Queue story generation
                    await self._queue_story_for_user(user)
                    queued_count += 1

                except Exception as e:
                    logger.error(f"Error checking user", email=user.get('email'), error=str(e))
                    continue

            if queued_count > 0:
                logger.info(f"Daily scheduler: Queued story jobs", count=queued_count)

        except Exception as e:
            logger.error(f"Daily scheduler error", error=str(e))
            import traceback
            traceback.print_exc()
        finally:
            self._is_checking = False

    async def _queue_story_for_user(self, user: Dict[str, Any], immediate_delivery: bool = False):
        """
        Queue a story generation job for a user.

        Args:
            user: User data dictionary
            immediate_delivery: If True, story will be emailed immediately upon generation
                               instead of waiting for user's scheduled delivery time.
                               Used for manual admin triggers to help users who missed their story.
        """
        user_id = user["id"]
        user_email = user["email"]

        # Build story bible from user preferences
        story_bible = user.get("story_bible", {})
        story_bible["genre"] = user.get("current_genre", "mystery")

        # Add protagonist if available
        if user.get("current_protagonist"):
            story_bible["protagonist"] = user["current_protagonist"]

        # Get preferences for settings
        prefs = user.get("preferences", {})
        subscription_status = user.get("subscription_status", "trial")

        # Extract delivery preferences from user preferences
        user_delivery_time = prefs.get("delivery_time", "08:00")
        user_timezone = prefs.get("timezone", "UTC")

        # Determine user tier and model settings
        is_premium = subscription_status == "active"
        user_tier = "premium" if is_premium else "free"

        settings = {
            "user_tier": user_tier,
            "user_id": user_id,
            "story_length": prefs.get("story_length", "medium"),
            "writer_model": "sonnet",
            "structure_model": "sonnet",
            "editor_model": "opus" if is_premium else "sonnet",
            "tts_voice": prefs.get("voice_id", "nova"),
            "dev_mode": False,  # Production mode
            # Delivery preferences for scheduling email
            "delivery_time": user_delivery_time,
            "timezone": user_timezone,
            # If True, email is sent immediately after generation (for manual admin triggers)
            "immediate_delivery": immediate_delivery,
        }

        # Create job
        job_id = f"daily_{user_id}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"

        await self.job_service.create_job(
            job_id=job_id,
            story_bible=story_bible,
            user_email=user_email,
            settings=settings,
            user_id=user_id
        )

        # Update user's last_story_at to prevent duplicate deliveries
        await self.user_service.record_story_delivery(user_id)

        logger.info(f"Queued daily story", email=user_email, job_id=job_id)

    async def queue_story_now(
        self,
        user_id: str,
        user_email: str,
        story_bible: Dict[str, Any],
        settings: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Manually queue a story for immediate generation.
        Used for testing and on-demand story requests.

        Returns:
            Job ID
        """
        job_id = f"manual_{user_id}_{uuid4().hex[:8]}"

        default_settings = {
            "user_tier": "free",
            "user_id": user_id,
            "writer_model": "sonnet",
            "structure_model": "sonnet",
            "editor_model": "sonnet",
            "dev_mode": True,
        }

        if settings:
            default_settings.update(settings)

        await self.job_service.create_job(
            job_id=job_id,
            story_bible=story_bible,
            user_email=user_email,
            settings=default_settings,
            user_id=user_id
        )

        logger.info(f"Queued manual story", email=user_email, job_id=job_id)
        return job_id

    def start(self):
        """Start the daily scheduler."""
        self.scheduler.add_job(
            self.check_and_queue_stories,
            trigger=IntervalTrigger(seconds=self.check_interval),
            id="daily_story_scheduler",
            name="Check and queue daily stories",
            replace_existing=True,
            max_instances=1
        )

        self.scheduler.start()
        logger.info(f"Daily story scheduler started", check_interval=self.check_interval)

    def shutdown(self):
        """Shutdown the scheduler."""
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)
        logger.info("Daily story scheduler stopped")


# Global scheduler instance
_scheduler_instance: Optional[DailyStoryScheduler] = None


async def start_daily_scheduler(
    check_interval: int = 60,
    generation_lead: int = 30,  # Minutes before delivery to start generating
):
    """Start the daily story scheduler. Call during FastAPI startup."""
    global _scheduler_instance

    if _scheduler_instance is None:
        _scheduler_instance = DailyStoryScheduler(
            check_interval_seconds=check_interval,
            generation_lead_minutes=generation_lead,
        )
        await _scheduler_instance.initialize()
        _scheduler_instance.start()


def stop_daily_scheduler():
    """Stop the daily story scheduler. Call during FastAPI shutdown."""
    global _scheduler_instance

    if _scheduler_instance is not None:
        _scheduler_instance.shutdown()
        _scheduler_instance = None


def get_daily_scheduler() -> Optional[DailyStoryScheduler]:
    """Get the current scheduler instance."""
    return _scheduler_instance
