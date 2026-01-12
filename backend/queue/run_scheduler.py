#!/usr/bin/env python3
"""
Daily Story Scheduler for FixionMail (Redis Queue version).

This script runs the scheduler that checks which users need stories
and enqueues generation jobs to Redis.

Usage:
    python -m backend.queue.run_scheduler
"""

import asyncio
import sys
import os
import signal
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from backend.config import config
from backend.utils.logging import job_logger as logger


class RedisQueueScheduler:
    """
    Scheduler that enqueues story generation jobs to Redis.

    Checks every minute for users who should have stories generated
    and enqueues jobs to the Redis queue for processing by workers.
    """

    def __init__(
        self,
        check_interval_seconds: int = 60,
        generation_lead_minutes: int = 30
    ):
        self.check_interval = check_interval_seconds
        self.generation_lead = generation_lead_minutes

        self.scheduler = AsyncIOScheduler()
        self._is_checking = False
        self._running = False

    async def start(self):
        """Start the scheduler."""
        if not config.REDIS_URL:
            logger.error("REDIS_URL not configured - scheduler cannot start")
            return

        # Add job to check users periodically
        self.scheduler.add_job(
            self._check_and_enqueue,
            trigger=IntervalTrigger(seconds=self.check_interval),
            id="daily_story_check",
            name="Check for users needing stories",
            replace_existing=True,
            max_instances=1
        )

        self.scheduler.start()
        self._running = True
        logger.info(
            "Redis Queue Scheduler started",
            check_interval=self.check_interval,
            generation_lead=self.generation_lead
        )

    async def stop(self):
        """Stop the scheduler gracefully."""
        self._running = False
        if self.scheduler.running:
            self.scheduler.shutdown(wait=True)
        logger.info("Scheduler stopped")

    async def _check_and_enqueue(self):
        """Check for users needing stories and enqueue jobs."""
        if self._is_checking:
            return

        self._is_checking = True

        try:
            from backend.database.users import UserService
            from backend.database.jobs import JobQueueService
            from backend.queue.tasks import enqueue_story_job
            import uuid

            user_service = UserService()
            job_service = JobQueueService()

            # Get active subscribed users
            users = await user_service.get_active_subscribers()

            enqueued_count = 0

            for user in users:
                try:
                    # Check if this user should have a story generated now
                    if not await self._should_generate_for_user(user, user_service):
                        continue

                    # Check if user already has a pending/running job
                    active_jobs = await job_service.get_user_active_jobs(user["id"], limit=1)
                    if active_jobs:
                        continue

                    # Get user's story bible
                    story_bible = user.get("story_bible") or {}
                    if not story_bible:
                        logger.warning(f"User has no story bible", email=user["email"])
                        continue

                    # Generate job ID and settings
                    job_id = str(uuid.uuid4())
                    settings = self._build_job_settings(user)

                    # Create job record in database (for tracking)
                    await job_service.create_job(
                        job_id=job_id,
                        story_bible=story_bible,
                        user_email=user["email"],
                        settings=settings
                    )

                    # Enqueue to Redis
                    rq_job = enqueue_story_job(
                        job_id=job_id,
                        story_bible=story_bible,
                        user_email=user["email"],
                        settings=settings
                    )

                    logger.info(
                        f"Enqueued story job to Redis",
                        job_id=job_id,
                        rq_job_id=rq_job.id,
                        email=user["email"]
                    )
                    enqueued_count += 1

                except Exception as user_error:
                    logger.error(
                        f"Error processing user: {user_error}",
                        email=user.get("email"),
                        error=str(user_error)
                    )

            if enqueued_count > 0:
                logger.info(f"Enqueued {enqueued_count} story job(s)")

        except Exception as e:
            logger.error(f"Scheduler check error: {e}", error=str(e))
        finally:
            self._is_checking = False

    async def _should_generate_for_user(self, user: dict, user_service) -> bool:
        """Check if we should generate a story for this user now."""
        try:
            # Get user's timezone and delivery time preferences
            settings = user.get("settings") or {}
            user_tz_str = settings.get("timezone", "UTC")
            delivery_time = settings.get("delivery_time", "08:00")

            try:
                user_tz = ZoneInfo(user_tz_str)
            except Exception:
                user_tz = ZoneInfo("UTC")

            # Parse delivery time
            try:
                target_hour, target_minute = map(int, delivery_time.split(":"))
            except Exception:
                target_hour, target_minute = 8, 0

            # Get current time in user's timezone
            user_now = datetime.now(user_tz)

            # Calculate generation window
            # We want to generate {generation_lead} minutes BEFORE delivery time
            delivery_datetime = user_now.replace(
                hour=target_hour,
                minute=target_minute,
                second=0,
                microsecond=0
            )

            # If delivery time has passed today, check for tomorrow
            if delivery_datetime < user_now:
                # Already past delivery time today
                return False

            generation_start = delivery_datetime - timedelta(minutes=self.generation_lead)
            generation_end = delivery_datetime

            # Check if we're in the generation window
            if not (generation_start <= user_now <= generation_end):
                return False

            # Check if user already got a story today
            last_story_at = user.get("last_story_at")
            if last_story_at:
                if isinstance(last_story_at, str):
                    last_story_at = datetime.fromisoformat(last_story_at.replace("Z", "+00:00"))

                last_story_local = last_story_at.astimezone(user_tz)
                if last_story_local.date() == user_now.date():
                    return False

            # Check credits if applicable
            if config.ENABLE_CREDIT_SYSTEM:
                tier = user.get("subscription_tier", "free")
                if tier == "free":
                    credits = user.get("story_credits", 0)
                    if credits <= 0:
                        return False

            return True

        except Exception as e:
            logger.error(f"Error checking user eligibility: {e}", email=user.get("email"))
            return False

    def _build_job_settings(self, user: dict) -> dict:
        """Build job settings from user preferences."""
        settings = user.get("settings") or {}
        tier = user.get("subscription_tier", "free")
        subscription_status = user.get("subscription_status", "")
        is_premium = subscription_status == "active" or tier in ["monthly", "annual", "premium"]

        return {
            "delivery_time": settings.get("delivery_time", "08:00"),
            "timezone": settings.get("timezone", "UTC"),
            "user_tier": "premium" if is_premium else tier,
            "writer_model": "sonnet",
            "structure_model": "sonnet",
            "editor_model": "opus" if is_premium else "sonnet",
            "tts_provider": settings.get("tts_provider", "openai"),
            "tts_voice": settings.get("tts_voice"),
            "is_daily": True,
            "immediate_delivery": False,
        }


async def main():
    """Run the scheduler."""
    print("=" * 50)
    print("FixionMail Daily Story Scheduler (Redis Queue)")
    print("=" * 50)

    if not config.REDIS_URL:
        print("❌ ERROR: REDIS_URL environment variable is required")
        sys.exit(1)

    scheduler = RedisQueueScheduler()

    # Handle shutdown signals
    loop = asyncio.get_event_loop()

    def shutdown_handler():
        print("\n👋 Shutting down scheduler...")
        asyncio.create_task(scheduler.stop())

    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, shutdown_handler)

    await scheduler.start()

    print("✅ Scheduler running. Press Ctrl+C to stop.")

    # Keep running
    try:
        while scheduler._running:
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        pass

    print("Scheduler stopped.")


if __name__ == "__main__":
    asyncio.run(main())
