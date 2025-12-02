"""
Story job queue manager.
Provides high-level interface for creating and managing story generation jobs.
"""

import uuid
from typing import Dict, Any, Optional
from backend.jobs.database import StoryJobDatabase, JobStatus


class StoryJobQueue:
    """
    High-level interface for the story job queue.

    Usage:
        queue = StoryJobQueue()
        await queue.initialize()

        # Queue a story
        job_id = await queue.enqueue(story_bible, email, settings)

        # Check status
        status = await queue.get_status(job_id)
    """

    def __init__(self, db_path: str = "story_jobs.db"):
        self.db = StoryJobDatabase(db_path)
        self._initialized = False

    async def initialize(self):
        """Initialize the database connection"""
        if not self._initialized:
            await self.db.connect()
            self._initialized = True

    async def enqueue(
        self,
        story_bible: Dict[str, Any],
        user_email: str,
        settings: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Queue a new story generation job.

        Args:
            story_bible: The story bible/configuration
            user_email: Email to send the completed story to
            settings: Optional settings (models, tier, etc.)

        Returns:
            job_id: Unique identifier for tracking the job
        """
        if not self._initialized:
            await self.initialize()

        job_id = f"story_{uuid.uuid4().hex[:12]}"

        await self.db.create_job(
            job_id=job_id,
            story_bible=story_bible,
            user_email=user_email,
            settings=settings
        )

        return job_id

    async def get_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the current status of a job.

        Returns:
            Dict with status info or None if job not found
        """
        if not self._initialized:
            await self.initialize()

        job = await self.db.get_job_by_id(job_id)
        if not job:
            return None

        return {
            "job_id": job["job_id"],
            "status": job["status"],
            "current_step": job["current_step"],
            "progress_percent": job["progress_percent"],
            "error_message": job["error_message"],
            "created_at": job["created_at"],
            "started_at": job["started_at"],
            "completed_at": job["completed_at"],
            "generation_time_seconds": job["generation_time_seconds"]
        }

    async def get_result(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the full result of a completed job.

        Returns:
            Full job data including result, or None if not found
        """
        if not self._initialized:
            await self.initialize()

        return await self.db.get_job_by_id(job_id)

    async def get_pending_count(self) -> int:
        """Get the number of pending jobs in the queue"""
        if not self._initialized:
            await self.initialize()

        jobs = await self.db.get_pending_jobs(limit=1000)
        return len(jobs)

    async def get_recent_jobs(
        self,
        email: Optional[str] = None,
        limit: int = 20
    ) -> list:
        """Get recent jobs for display"""
        if not self._initialized:
            await self.initialize()

        return await self.db.get_recent_jobs(email=email, limit=limit)

    async def close(self):
        """Close the database connection"""
        if self._initialized:
            await self.db.close()
            self._initialized = False


# Global queue instance (initialized on first use)
_queue_instance: Optional[StoryJobQueue] = None


async def get_queue(db_path: str = "story_jobs.db") -> StoryJobQueue:
    """
    Get or create the global queue instance.

    This ensures we reuse the same database connection across the app.
    """
    global _queue_instance

    if _queue_instance is None:
        _queue_instance = StoryJobQueue(db_path)
        await _queue_instance.initialize()

    return _queue_instance


async def close_queue():
    """Close the global queue instance"""
    global _queue_instance

    if _queue_instance is not None:
        await _queue_instance.close()
        _queue_instance = None
