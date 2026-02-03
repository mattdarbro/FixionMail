"""
Job Queue Service

Handles story generation job queue operations using Supabase.
Replaces the SQLite-based StoryJobDatabase.
"""

from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List
from uuid import UUID, uuid4
from enum import Enum

from supabase import Client

from .client import get_supabase_admin_client


class JobStatus(str, Enum):
    """Status values for story generation jobs"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class JobQueueService:
    """
    Service class for job queue operations.

    Uses Supabase for persistence, providing:
    - Atomic job claiming with row-level locking
    - Better concurrent access than SQLite
    - Unified data layer with other services
    """

    def __init__(self, client: Optional[Client] = None):
        self._client = client

    @property
    def client(self) -> Client:
        if self._client is None:
            self._client = get_supabase_admin_client()
        return self._client

    # =========================================================================
    # Job Creation
    # =========================================================================

    async def create_job(
        self,
        job_id: str,
        story_bible: Dict[str, Any],
        user_email: str,
        settings: Optional[Dict[str, Any]] = None,
        user_id: Optional[UUID | str] = None,
    ) -> Dict[str, Any]:
        """
        Create a new story generation job.

        Args:
            job_id: Unique job identifier
            story_bible: Story generation parameters
            user_email: User's email address
            settings: Model settings (writer_model, etc.)
            user_id: Optional user ID if known

        Returns:
            Created job data, or existing job if duplicate detected
        """
        user_id_str = str(user_id) if user_id else None

        # DUPLICATE PREVENTION: For daily scheduled stories, check if user already
        # has an active (pending/running) job OR received a story today
        is_daily = settings.get("is_daily", False) if settings else False
        if is_daily and user_id_str:
            # Check for active jobs
            existing_active = (
                self.client.table("story_jobs")
                .select("job_id, status, created_at")
                .eq("user_id", user_id_str)
                .in_("status", [JobStatus.PENDING.value, JobStatus.RUNNING.value])
                .execute()
            )
            if existing_active.data:
                # User already has an active job - return existing instead of creating duplicate
                return existing_active.data[0]

            # Also check for completed jobs created today (in UTC)
            # This prevents duplicate stories if last_story_at update is delayed
            today_start = datetime.now(timezone.utc).replace(
                hour=0, minute=0, second=0, microsecond=0
            ).isoformat()
            completed_today = (
                self.client.table("story_jobs")
                .select("job_id, status, created_at")
                .eq("user_id", user_id_str)
                .eq("status", JobStatus.COMPLETED.value)
                .gte("created_at", today_start)
                .limit(1)
                .execute()
            )
            if completed_today.data:
                # User already received a story today - return existing
                return completed_today.data[0]

        job_data = {
            "job_id": job_id,
            "story_bible": story_bible,
            "user_email": user_email,
            "settings": settings,
            "user_id": user_id_str,
            "status": JobStatus.PENDING.value,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        result = self.client.table("story_jobs").insert(job_data).execute()
        return result.data[0]

    # =========================================================================
    # Job Retrieval
    # =========================================================================

    async def get_job_by_id(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get a job by its job_id."""
        result = (
            self.client.table("story_jobs")
            .select("*")
            .eq("job_id", job_id)
            .execute()
        )
        return result.data[0] if result.data else None

    async def get_pending_jobs(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get pending jobs ordered by creation time (FIFO)."""
        result = (
            self.client.table("story_jobs")
            .select("*")
            .eq("status", JobStatus.PENDING.value)
            .order("created_at")
            .limit(limit)
            .execute()
        )
        return result.data

    async def get_recent_jobs(
        self,
        email: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Get recent jobs, optionally filtered by email."""
        query = (
            self.client.table("story_jobs")
            .select("job_id, status, current_step, progress_percent, created_at, started_at, completed_at, generation_time_seconds, user_email, settings, story_bible, result, error_message")
            .order("created_at", desc=True)
            .limit(limit)
        )

        if email:
            query = query.eq("user_email", email)

        result = query.execute()
        return result.data

    async def get_jobs_by_status(
        self,
        status: JobStatus,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get jobs by status."""
        result = (
            self.client.table("story_jobs")
            .select("*")
            .eq("status", status.value)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return result.data

    async def get_user_active_jobs(
        self,
        user_id: str,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Get pending/running jobs for a specific user.

        Used to show users their in-progress story generation status.
        """
        result = (
            self.client.table("story_jobs")
            .select("job_id, status, current_step, progress_percent, story_bible, created_at, started_at")
            .eq("user_id", user_id)
            .in_("status", [JobStatus.PENDING.value, JobStatus.RUNNING.value])
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return result.data

    # =========================================================================
    # Job Status Updates
    # =========================================================================

    async def update_status(
        self,
        job_id: str,
        status: JobStatus,
        current_step: Optional[str] = None,
        progress_percent: Optional[int] = None
    ) -> Dict[str, Any]:
        """Update job status and progress."""
        update_data = {"status": status.value}

        if current_step is not None:
            update_data["current_step"] = current_step

        if progress_percent is not None:
            update_data["progress_percent"] = progress_percent

        if status == JobStatus.RUNNING:
            update_data["started_at"] = datetime.now(timezone.utc).isoformat()

        result = (
            self.client.table("story_jobs")
            .update(update_data)
            .eq("job_id", job_id)
            .execute()
        )
        return result.data[0] if result.data else None

    async def mark_completed(
        self,
        job_id: str,
        result: Dict[str, Any],
        generation_time: float,
        story_id: Optional[UUID | str] = None
    ) -> Dict[str, Any]:
        """Mark a job as completed with its result."""
        update_data = {
            "status": JobStatus.COMPLETED.value,
            "result": result,
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "generation_time_seconds": generation_time,
            "progress_percent": 100,
            "current_step": "done",
        }

        if story_id:
            update_data["story_id"] = str(story_id)

        db_result = (
            self.client.table("story_jobs")
            .update(update_data)
            .eq("job_id", job_id)
            .execute()
        )
        return db_result.data[0] if db_result.data else None

    async def abort_job(
        self,
        job_id: str,
        reason: str = "Aborted by admin"
    ) -> Optional[Dict[str, Any]]:
        """
        Abort a pending or running job.

        Only pending/running jobs can be aborted.
        Returns the updated job or None if job not found or already completed/failed.
        """
        # First check if job exists and is abortable
        job = await self.get_job_by_id(job_id)
        if not job:
            return None

        if job["status"] not in [JobStatus.PENDING.value, JobStatus.RUNNING.value]:
            return None  # Can't abort completed/failed jobs

        update_data = {
            "status": JobStatus.FAILED.value,
            "error_message": reason,
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "current_step": "aborted",
        }

        result = (
            self.client.table("story_jobs")
            .update(update_data)
            .eq("job_id", job_id)
            .execute()
        )
        return result.data[0] if result.data else None

    async def mark_failed(
        self,
        job_id: str,
        error_message: str,
        should_retry: bool = False
    ) -> Dict[str, Any]:
        """Mark a job as failed."""
        if should_retry:
            # Get current retry count and increment
            job = await self.get_job_by_id(job_id)
            new_retry_count = (job.get("retry_count", 0) if job else 0) + 1

            update_data = {
                "status": JobStatus.PENDING.value,
                "error_message": error_message,
                "retry_count": new_retry_count,
                "current_step": None,
                "progress_percent": 0,
            }
        else:
            update_data = {
                "status": JobStatus.FAILED.value,
                "error_message": error_message,
                "completed_at": datetime.now(timezone.utc).isoformat(),
            }

        result = (
            self.client.table("story_jobs")
            .update(update_data)
            .eq("job_id", job_id)
            .execute()
        )
        return result.data[0] if result.data else None

    # =========================================================================
    # Job Recovery
    # =========================================================================

    async def recover_stale_running_jobs(self, stale_minutes: int = 10) -> int:
        """
        Recover jobs stuck in 'running' status (e.g., after worker crash).

        Jobs running for longer than stale_minutes are reset to 'pending'
        so they can be re-processed.

        Returns the number of recovered jobs.
        """
        cutoff = (datetime.now(timezone.utc) - timedelta(minutes=stale_minutes)).isoformat()

        # Find stale running jobs
        stale_jobs = (
            self.client.table("story_jobs")
            .select("job_id, retry_count")
            .eq("status", JobStatus.RUNNING.value)
            .lt("started_at", cutoff)
            .execute()
        )

        recovered_count = 0
        for job in stale_jobs.data:
            if job.get("retry_count", 0) < 3:
                self.client.table("story_jobs").update({
                    "status": JobStatus.PENDING.value,
                    "current_step": None,
                    "progress_percent": 0,
                    "error_message": "Recovered from stale running state (worker crash/timeout)",
                }).eq("job_id", job["job_id"]).execute()
                recovered_count += 1
            else:
                # Max retries exceeded - mark as failed
                self.client.table("story_jobs").update({
                    "status": JobStatus.FAILED.value,
                    "error_message": "Max retries exceeded after recovery attempt",
                    "completed_at": datetime.now(timezone.utc).isoformat(),
                }).eq("job_id", job["job_id"]).execute()

        return recovered_count

    # =========================================================================
    # Completed Stories Retrieval
    # =========================================================================

    async def get_completed_stories(
        self,
        email: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get completed stories with full content for the library.
        """
        query = (
            self.client.table("story_jobs")
            .select("job_id, user_email, result, story_bible, created_at, completed_at, generation_time_seconds")
            .eq("status", JobStatus.COMPLETED.value)
            .not_.is_("result", "null")
            .order("completed_at", desc=True)
            .limit(limit)
            .range(offset, offset + limit - 1)
        )

        if email:
            query = query.eq("user_email", email)

        result = query.execute()
        stories = []

        for row in result.data:
            result_data = row.get("result", {})
            story_data = result_data.get("story", {})

            # Fallback: if story_data is empty, try using result directly
            if not story_data and "narrative" in result_data:
                story_data = result_data

            bible = row.get("story_bible", {})
            narrative = story_data.get("narrative", "")

            if not narrative:
                continue

            stories.append({
                "job_id": row["job_id"],
                "user_email": row["user_email"],
                "title": story_data.get("title", "Untitled"),
                "narrative": narrative,
                "genre": story_data.get("genre") or bible.get("genre", "unknown"),
                "word_count": story_data.get("word_count", len(narrative.split())),
                "audio_url": story_data.get("audio_url"),
                "cover_image_url": story_data.get("cover_image_url"),
                "created_at": row["created_at"],
                "completed_at": row["completed_at"],
                "generation_time_seconds": row["generation_time_seconds"],
                "metadata": result_data.get("metadata", {}),
                "email_sent": result_data.get("email_sent", False),
            })

        return stories

    async def get_story_count(self, email: Optional[str] = None) -> int:
        """Get total count of completed stories."""
        query = (
            self.client.table("story_jobs")
            .select("id", count="exact")
            .eq("status", JobStatus.COMPLETED.value)
            .not_.is_("result", "null")
        )

        if email:
            query = query.eq("user_email", email)

        result = query.execute()
        return result.count if result.count else 0

    # =========================================================================
    # Admin/Dashboard Queries
    # =========================================================================

    async def get_queue_stats(self) -> Dict[str, Any]:
        """Get job queue statistics for dashboard."""
        # Get counts by status
        all_jobs = (
            self.client.table("story_jobs")
            .select("status")
            .execute()
        )

        status_counts = {
            "pending": 0,
            "running": 0,
            "completed": 0,
            "failed": 0,
        }

        for job in all_jobs.data:
            status = job.get("status")
            if status in status_counts:
                status_counts[status] += 1

        return {
            "total": len(all_jobs.data),
            **status_counts,
        }

    async def get_failed_jobs(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get failed jobs for dashboard."""
        result = (
            self.client.table("story_jobs")
            .select("job_id, user_email, error_message, created_at, completed_at, retry_count, story_bible")
            .eq("status", JobStatus.FAILED.value)
            .order("completed_at", desc=True)
            .limit(limit)
            .execute()
        )
        return result.data

    # =========================================================================
    # Cleanup
    # =========================================================================

    async def cleanup_old_jobs(self, days: int = 30) -> int:
        """Remove completed/failed jobs older than specified days."""
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

        # Get count of jobs to delete
        to_delete = (
            self.client.table("story_jobs")
            .select("id", count="exact")
            .in_("status", [JobStatus.COMPLETED.value, JobStatus.FAILED.value])
            .lt("created_at", cutoff)
            .execute()
        )

        # Delete the jobs
        self.client.table("story_jobs").delete().in_(
            "status", [JobStatus.COMPLETED.value, JobStatus.FAILED.value]
        ).lt("created_at", cutoff).execute()

        return to_delete.count if to_delete.count else 0
