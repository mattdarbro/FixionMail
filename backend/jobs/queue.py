"""
Story job queue manager.
Provides high-level interface for creating and managing story generation jobs.
"""

import uuid
from typing import Dict, Any, Optional
from backend.database.jobs import JobQueueService, JobStatus


class StoryJobQueue:
    """
    High-level interface for the story job queue.

    Uses Supabase for persistence via JobQueueService.

    Usage:
        queue = StoryJobQueue()
        await queue.initialize()

        # Queue a story
        job_id = await queue.enqueue(story_bible, email, settings)

        # Check status
        status = await queue.get_status(job_id)
    """

    def __init__(self):
        self.job_service = JobQueueService()
        self._initialized = True  # Supabase client is lazy-loaded

    async def initialize(self):
        """Initialize the service (no-op for Supabase, kept for API compatibility)"""
        self._initialized = True

    async def enqueue(
        self,
        story_bible: Dict[str, Any],
        user_email: str,
        settings: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None
    ) -> str:
        """
        Queue a new story generation job.

        Args:
            story_bible: The story bible/configuration
            user_email: Email to send the completed story to
            settings: Optional settings (models, tier, etc.)
            user_id: Optional user ID if known

        Returns:
            job_id: Unique identifier for tracking the job
        """
        job_id = f"story_{uuid.uuid4().hex[:12]}"

        await self.job_service.create_job(
            job_id=job_id,
            story_bible=story_bible,
            user_email=user_email,
            settings=settings,
            user_id=user_id
        )

        return job_id

    async def get_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the current status of a job.

        Returns:
            Dict with status info or None if job not found
        """
        job = await self.job_service.get_job_by_id(job_id)
        if not job:
            return None

        return {
            "job_id": job["job_id"],
            "status": job["status"],
            "current_step": job.get("current_step"),
            "progress_percent": job.get("progress_percent", 0),
            "error_message": job.get("error_message"),
            "created_at": job["created_at"],
            "started_at": job.get("started_at"),
            "completed_at": job.get("completed_at"),
            "generation_time_seconds": job.get("generation_time_seconds")
        }

    async def get_result(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the full result of a completed job.

        Returns:
            Full job data including result, or None if not found
        """
        return await self.job_service.get_job_by_id(job_id)

    async def get_pending_count(self) -> int:
        """Get the number of pending jobs in the queue"""
        jobs = await self.job_service.get_pending_jobs(limit=1000)
        return len(jobs)

    async def get_recent_jobs(
        self,
        email: Optional[str] = None,
        limit: int = 20
    ) -> list:
        """Get recent jobs for display"""
        return await self.job_service.get_recent_jobs(email=email, limit=limit)

    async def close(self):
        """Close the connection (no-op for Supabase, kept for API compatibility)"""
        self._initialized = False


# Global queue instance (initialized on first use)
_queue_instance: Optional[StoryJobQueue] = None


async def get_queue() -> StoryJobQueue:
    """
    Get or create the global queue instance.

    This ensures we reuse the same instance across the app.
    """
    global _queue_instance

    if _queue_instance is None:
        _queue_instance = StoryJobQueue()
        await _queue_instance.initialize()

    return _queue_instance


async def close_queue():
    """Close the global queue instance"""
    global _queue_instance

    if _queue_instance is not None:
        await _queue_instance.close()
        _queue_instance = None
