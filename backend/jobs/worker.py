"""
Background worker for story generation jobs.
Polls the job queue and processes stories asynchronously.
"""

import asyncio
import os
import time
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from backend.jobs.database import StoryJobDatabase, JobStatus
from backend.email.scheduler import EmailScheduler
from backend.email.database import EmailDatabase
from backend.utils.logging import job_logger as logger


class StoryWorker:
    """
    Background worker that processes story generation jobs.

    Polls the database every few seconds for pending jobs,
    runs the generation pipeline, and sends results via email.
    """

    def __init__(
        self,
        job_db_path: str = "story_jobs.db",
        email_db_path: str = "email_scheduler.db",
        poll_interval_seconds: int = 5
    ):
        self.job_db_path = job_db_path
        self.email_db_path = email_db_path
        self.poll_interval = poll_interval_seconds

        self.scheduler = AsyncIOScheduler()
        self.job_db: StoryJobDatabase | None = None
        self.email_db: EmailDatabase | None = None
        self.email_scheduler: EmailScheduler | None = None

        self._is_processing = False  # Prevent concurrent job processing
        self._current_job_id: str | None = None

    async def initialize(self):
        """Initialize database connections and recover stale jobs"""
        self.job_db = StoryJobDatabase(self.job_db_path)
        await self.job_db.connect()

        self.email_db = EmailDatabase(self.email_db_path)
        await self.email_db.connect()

        self.email_scheduler = EmailScheduler(self.email_db)

        # Recover any jobs stuck in 'running' state from previous worker crash
        recovered = await self.job_db.recover_stale_running_jobs(stale_minutes=10)
        if recovered > 0:
            logger.warning(f"Recovered {recovered} stale job(s) from previous worker crash", recovered_count=recovered)

        logger.info("Story worker initialized", db_path=self.job_db_path, poll_interval=self.poll_interval)

    async def process_jobs(self):
        """
        Main job processing loop.
        Called by scheduler every poll_interval seconds.
        """
        # Skip if already processing a job
        if self._is_processing:
            return

        try:
            # Get next pending job
            pending = await self.job_db.get_pending_jobs(limit=1)
            if not pending:
                return

            job = pending[0]
            job_id = job["job_id"]

            # Check retry limit (max 3 attempts)
            if job["retry_count"] >= 3:
                await self.job_db.mark_failed(
                    job_id,
                    error_message="Max retries exceeded",
                    should_retry=False
                )
                logger.error(f"Job failed: max retries exceeded", job_id=job_id, retries=job["retry_count"])
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
            await self.job_db.update_status(
                job_id,
                JobStatus.RUNNING,
                current_step="starting",
                progress_percent=0
            )

            # Extract job data
            story_bible = job["story_bible"]
            user_email = job["user_email"]
            settings = job.get("settings", {})

            # Get model settings (with defaults)
            writer_model = settings.get("writer_model", "sonnet")
            structure_model = settings.get("structure_model", "sonnet")
            editor_model = settings.get("editor_model", "opus")
            user_tier = settings.get("user_tier", "free")
            dev_mode = settings.get("dev_mode", False)
            tts_provider = settings.get("tts_provider", "openai")
            tts_voice = settings.get("tts_voice")
            use_structure_agent = settings.get("use_structure_agent", True)

            # Import here to avoid circular imports
            from backend.storyteller.standalone_generation import generate_standalone_story

            # Update progress: Structure phase
            await self.job_db.update_status(
                job_id,
                JobStatus.RUNNING,
                current_step="structure",
                progress_percent=10
            )

            # Run the full generation pipeline
            # The pipeline internally goes through: structure -> writer -> editor -> media
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

            # Update progress: Sending email
            await self.job_db.update_status(
                job_id,
                JobStatus.RUNNING,
                current_step="email",
                progress_percent=90
            )

            # Send the story via email
            story = result["story"]
            email_sent = await self.email_scheduler.send_story_email(
                user_email=user_email,
                story_title=story["title"],
                story_narrative=story["narrative"],
                audio_url=story.get("audio_url"),
                image_url=story.get("cover_image_url"),
                genre=story["genre"],
                word_count=story["word_count"],
                user_tier=user_tier
            )

            if not email_sent:
                logger.warning(f"Email failed to send but story was generated", job_id=job_id, email=user_email)

            # Save story to Supabase database
            story_id = None
            try:
                from backend.database.stories import StoryService
                from backend.database.users import UserService
                from backend.config import config

                if config.supabase_configured:
                    # Look up user by email
                    user_service = UserService()
                    user = await user_service.get_by_email(user_email)

                    if user:
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

                        # Mark as delivered if email sent
                        if email_sent:
                            await story_service.mark_delivered(story_id)

                        logger.info(f"Story saved to Supabase", story_id=story_id, user_id=user["id"])
                    else:
                        logger.warning(f"User not found in Supabase, story not saved", email=user_email)
                else:
                    logger.warning("Supabase not configured, story not saved to database")
            except Exception as save_error:
                logger.error(f"Failed to save story to Supabase: {save_error}", error=str(save_error))
                # Don't fail the job - story was generated and emailed successfully

            # Calculate total time
            generation_time = time.time() - start_time

            # Mark completed
            await self.job_db.mark_completed(
                job_id,
                result={
                    "story": story,
                    "story_id": story_id,
                    "metadata": result.get("metadata", {}),
                    "email_sent": email_sent
                },
                generation_time=generation_time
            )

            logger.info(f"Job completed", job_id=job_id, title=story['title'],
                       word_count=story['word_count'], time_seconds=round(generation_time, 1),
                       email_sent=email_sent, story_id=story_id)

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Job failed: {error_msg}", job_id=job_id, error=error_msg)

            # Determine if we should retry
            # Retry on transient errors (API timeouts, rate limits)
            should_retry = any(x in error_msg.lower() for x in [
                "timeout", "rate limit", "429", "503", "502", "connection"
            ])

            await self.job_db.mark_failed(
                job_id,
                error_message=error_msg,
                should_retry=should_retry
            )

    def start(self):
        """Start the background worker"""
        self.scheduler.add_job(
            self.process_jobs,
            trigger=IntervalTrigger(seconds=self.poll_interval),
            id="story_worker",
            name="Process story generation jobs",
            replace_existing=True,
            max_instances=1  # Prevent overlapping runs
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


async def start_story_worker(
    job_db_path: str = "story_jobs.db",
    email_db_path: str = "email_scheduler.db",
    poll_interval: int = 5
):
    """
    Start the background story worker.
    Call this during FastAPI startup.
    """
    global _worker_instance

    if _worker_instance is None:
        _worker_instance = StoryWorker(
            job_db_path=job_db_path,
            email_db_path=email_db_path,
            poll_interval_seconds=poll_interval
        )
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
