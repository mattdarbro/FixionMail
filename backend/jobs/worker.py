"""
Background worker for story generation jobs.
Polls the Supabase job queue and processes stories asynchronously.

NOTE: This worker GENERATES stories and schedules them for delivery.
The DeliveryWorker (separate) handles sending emails at the scheduled time.
"""

import asyncio
import os
import time
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from backend.database.jobs import JobQueueService, JobStatus
from backend.utils.logging import job_logger as logger


class StoryWorker:
    """
    Background worker that processes story generation jobs.

    Polls Supabase every few seconds for pending jobs,
    runs the generation pipeline, saves the story,
    and schedules it for delivery at user's preferred time.

    Email sending is handled by the separate DeliveryWorker.
    """

    def __init__(self, poll_interval_seconds: int = 5):
        self.poll_interval = poll_interval_seconds

        self.scheduler = AsyncIOScheduler()
        self.job_service: JobQueueService | None = None

        self._is_processing = False
        self._current_job_id: str | None = None

    async def initialize(self):
        """Initialize database connections and recover stale jobs"""
        self.job_service = JobQueueService()

        # Recover any jobs stuck in 'running' state from previous worker crash
        recovered = await self.job_service.recover_stale_running_jobs(stale_minutes=10)
        if recovered > 0:
            logger.warning(f"Recovered {recovered} stale job(s)", recovered_count=recovered)

        logger.info("Story worker initialized", poll_interval=self.poll_interval)

    async def process_jobs(self):
        """
        Main job processing loop.
        Called by scheduler every poll_interval seconds.
        """
        if self._is_processing:
            return

        try:
            pending = await self.job_service.get_pending_jobs(limit=1)
            if not pending:
                return

            job = pending[0]
            job_id = job["job_id"]

            if job.get("retry_count", 0) >= 3:
                await self.job_service.mark_failed(
                    job_id,
                    error_message="Max retries exceeded",
                    should_retry=False
                )
                logger.error(f"Job failed: max retries exceeded", job_id=job_id)
                return

            self._is_processing = True
            self._current_job_id = job_id

            logger.info(f"Processing job", job_id=job_id, email=job['user_email'])

            await self._process_single_job(job)

        except Exception as e:
            logger.error(f"Worker error: {e}", error=str(e))
        finally:
            self._is_processing = False
            self._current_job_id = None

    async def _process_single_job(self, job: dict):
        """Process a single story generation job"""
        job_id = job["job_id"]
        start_time = time.time()

        try:
            # Mark as running
            await self.job_service.update_status(
                job_id,
                JobStatus.RUNNING,
                current_step="starting",
                progress_percent=0
            )

            # Extract job data
            story_bible = job["story_bible"]
            user_email = job["user_email"]
            settings = job.get("settings") or {}

            # Get model settings
            writer_model = settings.get("writer_model", "sonnet")
            structure_model = settings.get("structure_model", "sonnet")
            editor_model = settings.get("editor_model", "opus")
            user_tier = settings.get("user_tier", "free")
            dev_mode = settings.get("dev_mode", False)
            tts_provider = settings.get("tts_provider", "openai")
            tts_voice = settings.get("tts_voice")
            use_structure_agent = settings.get("use_structure_agent", True)

            # Get delivery preferences from settings (set by DailyStoryScheduler)
            delivery_time = settings.get("delivery_time", "08:00")
            user_timezone = settings.get("timezone", "UTC")
            immediate_delivery = settings.get("immediate_delivery", False)

            from backend.storyteller.standalone_generation import generate_standalone_story

            # Update progress: Structure phase
            await self.job_service.update_status(
                job_id,
                JobStatus.RUNNING,
                current_step="structure",
                progress_percent=10
            )

            # Run the full generation pipeline
            result = await generate_standalone_story(
                story_bible=story_bible,
                user_tier=user_tier,
                dev_mode=dev_mode,
                tts_provider=tts_provider,
                tts_voice=tts_voice,
                writer_model=writer_model,
                structure_model=structure_model,
                editor_model=editor_model,
                use_structure_agent=use_structure_agent
            )

            if not result.get("success"):
                raise Exception(result.get("error", "Unknown generation error"))

            story = result["story"]

            # Update progress: Saving to database
            await self.job_service.update_status(
                job_id,
                JobStatus.RUNNING,
                current_step="saving",
                progress_percent=85
            )

            # Save story and schedule delivery
            story_id = None
            delivery_scheduled = False

            try:
                from backend.database.stories import StoryService
                from backend.database.users import UserService
                from backend.database.credits import CreditService
                from backend.database.deliveries import DeliveryService
                from backend.config import config

                if config.supabase_configured:
                    user_service = UserService()
                    user = await user_service.get_by_email(user_email)

                    if user:
                        # Save story to database
                        story_service = StoryService()
                        saved_story = await story_service.create(
                            user_id=user["id"],
                            title=story["title"],
                            narrative=story["narrative"],
                            genre=story["genre"],
                            story_bible=story_bible,
                            model_used=writer_model,
                            word_count=story.get("word_count"),
                            beat_structure=story_bible.get("beat_structure"),
                            audio_url=story.get("audio_url"),
                            image_url=story.get("cover_image_url"),
                            credits_used=1 if user_tier != "free" else 0,
                        )
                        story_id = saved_story.get("id")

                        # Deduct credits if enabled
                        if config.ENABLE_CREDIT_SYSTEM and user_tier != "free":
                            try:
                                credit_service = CreditService()
                                new_balance = await credit_service.deduct_for_story(
                                    user_id=user["id"],
                                    story_id=story_id,
                                    is_retell=False
                                )
                                logger.info(f"Credits deducted", user_id=user["id"], new_balance=new_balance)
                            except Exception as credit_error:
                                logger.error(f"Failed to deduct credits: {credit_error}", error=str(credit_error))

                        # Schedule delivery at user's preferred time
                        await self.job_service.update_status(
                            job_id,
                            JobStatus.RUNNING,
                            current_step="scheduling_delivery",
                            progress_percent=95
                        )

                        # Calculate delivery time
                        if immediate_delivery:
                            # For manual admin triggers, send immediately
                            deliver_at = datetime.now(timezone.utc)
                            logger.info(
                                "Immediate delivery requested (admin trigger)",
                                story_id=story_id,
                                email=user_email
                            )
                        else:
                            # Normal flow: schedule for user's preferred time
                            deliver_at = self._calculate_delivery_time(
                                delivery_time=delivery_time,
                                user_timezone=user_timezone
                            )

                        delivery_service = DeliveryService()
                        await delivery_service.schedule_delivery(
                            story_id=story_id,
                            user_id=user["id"],
                            user_email=user_email,
                            deliver_at=deliver_at,
                            timezone_str=user_timezone
                        )
                        delivery_scheduled = True

                        logger.info(
                            f"Story saved and delivery scheduled",
                            story_id=story_id,
                            deliver_at=deliver_at.isoformat(),
                            timezone=user_timezone,
                            immediate=immediate_delivery
                        )
                    else:
                        logger.warning(f"User not found, story not saved", email=user_email)
                else:
                    logger.warning("Supabase not configured")

            except Exception as save_error:
                logger.error(f"Failed to save/schedule: {save_error}", error=str(save_error))

            # Calculate total time
            generation_time = time.time() - start_time

            # Mark completed
            await self.job_service.mark_completed(
                job_id,
                result={
                    "story": story,
                    "story_id": story_id,
                    "metadata": result.get("metadata", {}),
                    "delivery_scheduled": delivery_scheduled
                },
                generation_time=generation_time,
                story_id=story_id
            )

            logger.info(
                f"Job completed",
                job_id=job_id,
                title=story['title'],
                word_count=story['word_count'],
                time_seconds=round(generation_time, 1),
                story_id=story_id,
                delivery_scheduled=delivery_scheduled
            )

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Job failed: {error_msg}", job_id=job_id, error=error_msg)

            should_retry = any(x in error_msg.lower() for x in [
                "timeout", "rate limit", "429", "503", "502", "connection"
            ])

            await self.job_service.mark_failed(
                job_id,
                error_message=error_msg,
                should_retry=should_retry
            )

    def _calculate_delivery_time(
        self,
        delivery_time: str,
        user_timezone: str
    ) -> datetime:
        """
        Calculate the actual delivery datetime based on user preferences.

        If the delivery time has already passed today, schedule for tomorrow.
        """
        try:
            tz = ZoneInfo(user_timezone)
        except Exception:
            tz = ZoneInfo("UTC")

        # Parse delivery time (HH:MM)
        try:
            parts = delivery_time.split(":")
            target_hour = int(parts[0])
            target_minute = int(parts[1])
        except (ValueError, IndexError):
            target_hour, target_minute = 8, 0

        # Get current time in user's timezone
        now_utc = datetime.now(timezone.utc)
        now_user = now_utc.astimezone(tz)

        # Create target delivery time for today
        delivery_datetime = now_user.replace(
            hour=target_hour,
            minute=target_minute,
            second=0,
            microsecond=0
        )

        # If time has passed today, schedule for tomorrow
        if delivery_datetime <= now_user:
            delivery_datetime += timedelta(days=1)

        # Convert back to UTC for storage
        return delivery_datetime.astimezone(timezone.utc)

    def start(self):
        """Start the background worker"""
        self.scheduler.add_job(
            self.process_jobs,
            trigger=IntervalTrigger(seconds=self.poll_interval),
            id="story_worker",
            name="Process story generation jobs",
            replace_existing=True,
            max_instances=1
        )

        self.scheduler.start()
        logger.info(f"Story worker started", poll_interval=self.poll_interval)

    def shutdown(self):
        """Shutdown the worker"""
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)
        logger.info("Story worker stopped")

    @property
    def is_processing(self) -> bool:
        """Check if worker is currently processing a job"""
        return self._is_processing

    @property
    def current_job(self) -> str | None:
        """Get the ID of the currently processing job"""
        return self._current_job_id


# Global worker instance
_worker_instance: StoryWorker | None = None


async def start_story_worker(poll_interval: int = 5):
    """
    Start the background story worker.
    Call this during FastAPI startup.
    """
    global _worker_instance

    if _worker_instance is None:
        _worker_instance = StoryWorker(poll_interval_seconds=poll_interval)
        await _worker_instance.initialize()
        _worker_instance.start()


def stop_story_worker():
    """
    Stop the background story worker.
    Call this during FastAPI shutdown.
    """
    global _worker_instance

    if _worker_instance is not None:
        _worker_instance.shutdown()
        _worker_instance = None


def get_worker() -> StoryWorker | None:
    """Get the current worker instance (for status checks)"""
    return _worker_instance
