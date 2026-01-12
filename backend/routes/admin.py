"""
Admin Dashboard API Routes

Provides endpoints for the admin dashboard to view:
- Users
- Stories
- Scheduled stories
- Job queue status
- Error logs
- System statistics
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone, timedelta
import os

from backend.config import config
from backend.utils.logging import get_log_buffer, get_logger

router = APIRouter(prefix="/api/admin", tags=["admin"])
logger = get_logger("admin")


# ===== Dashboard Overview =====

@router.get("/overview")
async def get_dashboard_overview():
    """
    Get a high-level overview for the admin dashboard.

    Returns counts and recent activity across all systems.
    """
    logger.info("Fetching dashboard overview")

    overview = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "users": {"total": 0, "active_today": 0, "new_today": 0},
        "stories": {"total": 0, "generated_today": 0, "failed_today": 0},
        "scheduled": {"pending": 0, "due_soon": 0},
        "jobs": {"pending": 0, "running": 0, "completed_today": 0, "failed_today": 0},
        "deliveries": {"pending": 0, "sent_today": 0, "upcoming_1h": 0, "failed": 0},
        "logs": {"errors": 0, "warnings": 0, "total": 0},
        "system": {"status": "operational"}
    }

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Get Supabase stats if configured
    if config.supabase_configured:
        try:
            from backend.database.client import get_supabase_admin_client
            client = get_supabase_admin_client()

            # User counts
            users_result = client.table("users").select("id", count="exact").execute()
            overview["users"]["total"] = users_result.count or 0

            # Active today (last_login_at or updated_at today)
            active_result = client.table("users").select("id", count="exact").gte(
                "last_login_at", f"{today}T00:00:00"
            ).execute()
            overview["users"]["active_today"] = active_result.count or 0

            # New today
            new_result = client.table("users").select("id", count="exact").gte(
                "created_at", f"{today}T00:00:00"
            ).execute()
            overview["users"]["new_today"] = new_result.count or 0

            # Story counts (from stories table)
            stories_result = client.table("stories").select("id", count="exact").execute()
            overview["stories"]["total"] = stories_result.count or 0

            # Generated today
            gen_today = client.table("stories").select("id", count="exact").gte(
                "created_at", f"{today}T00:00:00"
            ).eq("status", "completed").execute()
            overview["stories"]["generated_today"] = gen_today.count or 0

            # Failed stories today
            failed_today = client.table("stories").select("id", count="exact").gte(
                "created_at", f"{today}T00:00:00"
            ).eq("status", "failed").execute()
            overview["stories"]["failed_today"] = failed_today.count or 0

            # Job queue stats (from story_jobs table)
            pending_jobs = client.table("story_jobs").select("id", count="exact").eq(
                "status", "pending"
            ).execute()
            overview["jobs"]["pending"] = pending_jobs.count or 0
            overview["scheduled"]["pending"] = pending_jobs.count or 0

            running_jobs = client.table("story_jobs").select("id", count="exact").eq(
                "status", "running"
            ).execute()
            overview["jobs"]["running"] = running_jobs.count or 0

            # Jobs completed today
            completed_today = client.table("story_jobs").select("id", count="exact").eq(
                "status", "completed"
            ).gte("completed_at", f"{today}T00:00:00").execute()
            overview["jobs"]["completed_today"] = completed_today.count or 0

            # Jobs failed today
            failed_jobs_today = client.table("story_jobs").select("id", count="exact").eq(
                "status", "failed"
            ).gte("completed_at", f"{today}T00:00:00").execute()
            overview["jobs"]["failed_today"] = failed_jobs_today.count or 0

            # Due soon (pending jobs created in last hour = imminent)
            next_hour = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
            due_soon = client.table("story_jobs").select("id", count="exact").eq(
                "status", "pending"
            ).execute()
            overview["scheduled"]["due_soon"] = due_soon.count or 0

            # Delivery stats (email delivery queue)
            try:
                from backend.database.deliveries import DeliveryService
                delivery_service = DeliveryService()
                del_stats = await delivery_service.get_delivery_stats()
                overview["deliveries"]["pending"] = del_stats.get("pending", 0)
                overview["deliveries"]["sent_today"] = del_stats.get("sent_today", 0)
                overview["deliveries"]["upcoming_1h"] = del_stats.get("upcoming_1h", 0)
                overview["deliveries"]["failed"] = del_stats.get("failed", 0)
            except Exception as del_e:
                logger.warning(f"Failed to fetch delivery stats: {del_e}")

        except Exception as e:
            logger.error(f"Failed to fetch Supabase stats: {e}", error=str(e))
            overview["system"]["supabase_error"] = str(e)

    # Get log buffer stats
    log_buffer = get_log_buffer()
    log_stats = log_buffer.get_stats()
    overview["logs"]["errors"] = log_stats.get("error_count", 0)
    overview["logs"]["warnings"] = log_stats.get("warning_count", 0)
    overview["logs"]["total"] = log_stats.get("total", 0)

    return overview


# ===== Users =====

@router.get("/users")
async def get_users(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    status: Optional[str] = Query(None, description="Filter by subscription_status")
):
    """
    Get list of users with their subscription status and activity.
    """
    if not config.supabase_configured:
        raise HTTPException(status_code=503, detail="Supabase not configured")

    try:
        from backend.database.client import get_supabase_admin_client
        client = get_supabase_admin_client()

        query = client.table("users").select(
            "id, email, subscription_status, subscription_tier, credits, "
            "credits_used_total, trial_credits_remaining, onboarding_completed, "
            "created_at, last_login_at, last_story_at, current_genre"
        ).order("created_at", desc=True).range(offset, offset + limit - 1)

        if status:
            query = query.eq("subscription_status", status)

        result = query.execute()

        # Get total count
        count_query = client.table("users").select("id", count="exact")
        if status:
            count_query = count_query.eq("subscription_status", status)
        count_result = count_query.execute()

        return {
            "users": result.data,
            "total": count_result.count or len(result.data),
            "limit": limit,
            "offset": offset
        }
    except Exception as e:
        logger.error(f"Failed to fetch users: {e}", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/users/{user_id}")
async def get_user_detail(user_id: str):
    """Get detailed information about a specific user."""
    if not config.supabase_configured:
        raise HTTPException(status_code=503, detail="Supabase not configured")

    try:
        from backend.database.client import get_supabase_admin_client
        client = get_supabase_admin_client()

        # Get user
        user_result = client.table("users").select("*").eq("id", user_id).single().execute()
        if not user_result.data:
            raise HTTPException(status_code=404, detail="User not found")

        # Get user's story count
        stories = client.table("stories").select("id", count="exact").eq("user_id", user_id).execute()

        # Get recent credit transactions
        transactions = client.table("credit_transactions").select(
            "id, amount, balance_after, transaction_type, description, created_at"
        ).eq("user_id", user_id).order("created_at", desc=True).limit(10).execute()

        return {
            "user": user_result.data,
            "story_count": stories.count or 0,
            "recent_transactions": transactions.data
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch user detail: {e}", user_id=user_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/users/{user_id}")
async def delete_user(user_id: str):
    """
    Delete a user and all their associated data.
    This is a destructive operation - use with caution!
    """
    if not config.supabase_configured:
        raise HTTPException(status_code=503, detail="Supabase not configured")

    try:
        from backend.database.client import get_supabase_admin_client
        client = get_supabase_admin_client()

        # First verify the user exists
        user_result = client.table("users").select("id, email").eq("id", user_id).single().execute()
        if not user_result.data:
            raise HTTPException(status_code=404, detail="User not found")

        user_email = user_result.data.get("email", "unknown")
        logger.info(f"Deleting user", user_id=user_id, email=user_email)

        deleted_counts = {}

        # Delete scheduled deliveries first (references stories)
        try:
            deliveries = client.table("scheduled_deliveries").delete().eq("user_id", user_id).execute()
            deleted_counts["deliveries"] = len(deliveries.data) if deliveries.data else 0
        except Exception as e:
            logger.warning(f"Error deleting deliveries: {e}")
            deleted_counts["deliveries"] = 0

        # Delete stories
        try:
            stories = client.table("stories").delete().eq("user_id", user_id).execute()
            deleted_counts["stories"] = len(stories.data) if stories.data else 0
        except Exception as e:
            logger.warning(f"Error deleting stories: {e}")
            deleted_counts["stories"] = 0

        # Delete credit transactions
        try:
            transactions = client.table("credit_transactions").delete().eq("user_id", user_id).execute()
            deleted_counts["transactions"] = len(transactions.data) if transactions.data else 0
        except Exception as e:
            logger.warning(f"Error deleting transactions: {e}")
            deleted_counts["transactions"] = 0

        # Delete story jobs (if any)
        try:
            jobs = client.table("story_jobs").delete().eq("user_email", user_email).execute()
            deleted_counts["jobs"] = len(jobs.data) if jobs.data else 0
        except Exception as e:
            logger.warning(f"Error deleting jobs: {e}")
            deleted_counts["jobs"] = 0

        # Finally delete the user
        client.table("users").delete().eq("id", user_id).execute()

        logger.info(
            f"User deleted successfully",
            user_id=user_id,
            email=user_email,
            deleted=deleted_counts
        )

        return {
            "success": True,
            "message": f"User {user_email} deleted successfully",
            "deleted": deleted_counts
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete user: {e}", user_id=user_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# ===== Stories =====

@router.get("/stories")
async def get_stories(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    status: Optional[str] = Query(None, description="Filter by status"),
    user_id: Optional[str] = Query(None, description="Filter by user_id")
):
    """
    Get list of stories with generation details.
    """
    if not config.supabase_configured:
        raise HTTPException(status_code=503, detail="Supabase not configured")

    try:
        from backend.database.client import get_supabase_admin_client
        client = get_supabase_admin_client()

        query = client.table("stories").select(
            "id, user_id, title, genre, word_count, status, model_used, "
            "is_retell, rating, email_sent, credits_used, created_at, delivered_at"
        ).order("created_at", desc=True).range(offset, offset + limit - 1)

        if status:
            query = query.eq("status", status)
        if user_id:
            query = query.eq("user_id", user_id)

        result = query.execute()

        # Get total count
        count_query = client.table("stories").select("id", count="exact")
        if status:
            count_query = count_query.eq("status", status)
        if user_id:
            count_query = count_query.eq("user_id", user_id)
        count_result = count_query.execute()

        return {
            "stories": result.data,
            "total": count_result.count or len(result.data),
            "limit": limit,
            "offset": offset
        }
    except Exception as e:
        logger.error(f"Failed to fetch stories: {e}", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stories/failed")
async def get_failed_stories(
    limit: int = Query(50, ge=1, le=200),
    days: int = Query(7, ge=1, le=30, description="Look back N days")
):
    """Get recently failed story generations."""
    if not config.supabase_configured:
        raise HTTPException(status_code=503, detail="Supabase not configured")

    try:
        from backend.database.client import get_supabase_admin_client
        client = get_supabase_admin_client()

        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

        result = client.table("stories").select(
            "id, user_id, title, genre, status, model_used, created_at"
        ).eq("status", "failed").gte("created_at", cutoff).order(
            "created_at", desc=True
        ).limit(limit).execute()

        return {"failed_stories": result.data, "days": days}
    except Exception as e:
        logger.error(f"Failed to fetch failed stories: {e}", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# ===== Scheduled Stories / Job Queue =====

@router.get("/scheduled")
async def get_scheduled_stories(
    limit: int = Query(50, ge=1, le=200),
    status: Optional[str] = Query(None, description="Filter by status (pending, running, completed, failed)")
):
    """
    Get scheduled/queued stories from the job queue (Supabase).

    Shows pending and recent jobs from the story_jobs table.
    """
    if not config.supabase_configured:
        raise HTTPException(status_code=503, detail="Supabase not configured")

    try:
        from backend.database.client import get_supabase_admin_client
        client = get_supabase_admin_client()

        if status:
            query = client.table("story_jobs").select(
                "job_id, status, user_email, story_bible, settings, "
                "current_step, progress_percent, error_message, "
                "created_at, started_at, completed_at, retry_count"
            ).eq("status", status).order("created_at", desc=True).limit(limit)
        else:
            # Show pending and running by default
            query = client.table("story_jobs").select(
                "job_id, status, user_email, story_bible, settings, "
                "current_step, progress_percent, error_message, "
                "created_at, started_at, completed_at, retry_count"
            ).in_("status", ["pending", "running"]).order("created_at").limit(limit)

        result = query.execute()

        scheduled = []
        for row in result.data:
            bible = row.get("story_bible") or {}
            scheduled.append({
                "id": row["job_id"],
                "status": row["status"],
                "user_email": row["user_email"],
                "genre": bible.get("genre", "unknown"),
                "current_step": row.get("current_step"),
                "progress_percent": row.get("progress_percent", 0),
                "error_message": row.get("error_message"),
                "created_at": row["created_at"],
                "started_at": row.get("started_at"),
                "completed_at": row.get("completed_at"),
                "attempts": row.get("retry_count", 0),
                "scheduled_for": row["created_at"]
            })

        return {"scheduled_stories": scheduled}
    except Exception as e:
        logger.error(f"Failed to fetch scheduled stories: {e}", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# ===== Job Queue =====

@router.get("/jobs")
async def get_jobs(
    limit: int = Query(50, ge=1, le=200),
    status: Optional[str] = Query(None, description="Filter by status (pending, running, completed, failed)")
):
    """
    Get job queue status from Supabase.
    """
    if not config.supabase_configured:
        raise HTTPException(status_code=503, detail="Supabase not configured")

    try:
        from backend.database.client import get_supabase_admin_client
        client = get_supabase_admin_client()

        query = client.table("story_jobs").select(
            "job_id, status, user_email, current_step, progress_percent, "
            "error_message, created_at, started_at, completed_at, "
            "generation_time_seconds, retry_count"
        ).order("created_at", desc=True).limit(limit)

        if status:
            query = query.eq("status", status)

        result = query.execute()

        jobs = [
            {
                "job_id": row["job_id"],
                "status": row["status"],
                "user_email": row["user_email"],
                "current_step": row.get("current_step"),
                "progress_percent": row.get("progress_percent", 0),
                "error_message": row.get("error_message"),
                "created_at": row["created_at"],
                "started_at": row.get("started_at"),
                "completed_at": row.get("completed_at"),
                "generation_time_seconds": row.get("generation_time_seconds"),
                "retry_count": row.get("retry_count", 0)
            }
            for row in result.data
        ]

        return {"jobs": jobs}
    except Exception as e:
        logger.error(f"Failed to fetch jobs: {e}", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/jobs/{job_id}/abort")
async def abort_job(job_id: str):
    """
    Abort a pending or running job.

    Useful for cancelling stuck jobs or unwanted story generations.
    Only pending and running jobs can be aborted.
    """
    if not config.supabase_configured:
        raise HTTPException(status_code=503, detail="Supabase not configured")

    try:
        from backend.database.jobs import JobQueueService
        job_service = JobQueueService()

        result = await job_service.abort_job(
            job_id=job_id,
            reason="Aborted by admin"
        )

        if result is None:
            raise HTTPException(
                status_code=400,
                detail="Job not found or cannot be aborted (already completed/failed)"
            )

        logger.info("Admin aborted job", job_id=job_id)

        return {
            "status": "aborted",
            "message": f"Job {job_id} has been aborted",
            "job_id": job_id
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to abort job: {e}", job_id=job_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/jobs/failed")
async def get_failed_jobs(limit: int = Query(50, ge=1, le=200)):
    """Get failed jobs with error details."""
    if not config.supabase_configured:
        raise HTTPException(status_code=503, detail="Supabase not configured")

    try:
        from backend.database.jobs import JobQueueService, JobStatus
        job_service = JobQueueService()
        failed_jobs = await job_service.get_failed_jobs(limit=limit)

        jobs = [
            {
                "job_id": row["job_id"],
                "status": "failed",
                "user_email": row["user_email"],
                "failed_at_step": row.get("story_bible", {}).get("current_step"),
                "error_message": row.get("error_message"),
                "created_at": row["created_at"],
                "completed_at": row.get("completed_at"),
                "retry_count": row.get("retry_count", 0)
            }
            for row in failed_jobs
        ]

        return {"failed_jobs": jobs}
    except Exception as e:
        logger.error(f"Failed to fetch failed jobs: {e}", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/jobs/stats")
async def get_job_stats():
    """Get job queue statistics."""
    if not config.supabase_configured:
        raise HTTPException(status_code=503, detail="Supabase not configured")

    try:
        from backend.database.client import get_supabase_admin_client
        client = get_supabase_admin_client()

        stats = {
            "by_status": {},
            "avg_generation_time": None,
            "total_jobs": 0,
            "jobs_last_24h": 0,
            "success_rate_24h": 0
        }

        # Count by status
        for status in ["pending", "running", "completed", "failed"]:
            result = client.table("story_jobs").select("id", count="exact").eq("status", status).execute()
            stats["by_status"][status] = result.count or 0

        stats["total_jobs"] = sum(stats["by_status"].values())

        # Average generation time for completed jobs
        completed_jobs = client.table("story_jobs").select(
            "generation_time_seconds"
        ).eq("status", "completed").not_.is_("generation_time_seconds", "null").limit(100).execute()

        if completed_jobs.data:
            times = [j["generation_time_seconds"] for j in completed_jobs.data if j.get("generation_time_seconds")]
            if times:
                stats["avg_generation_time"] = round(sum(times) / len(times), 2)

        # Jobs in last 24 hours
        yesterday = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
        jobs_24h = client.table("story_jobs").select("id", count="exact").gte("created_at", yesterday).execute()
        stats["jobs_last_24h"] = jobs_24h.count or 0

        # Success rate in last 24h
        completed_24h = client.table("story_jobs").select("id", count="exact").eq(
            "status", "completed"
        ).gte("created_at", yesterday).execute()

        failed_24h = client.table("story_jobs").select("id", count="exact").eq(
            "status", "failed"
        ).gte("created_at", yesterday).execute()

        total_finished = (completed_24h.count or 0) + (failed_24h.count or 0)
        if total_finished > 0:
            stats["success_rate_24h"] = round(((completed_24h.count or 0) / total_finished) * 100, 1)

        return stats
    except Exception as e:
        logger.error(f"Failed to fetch job stats: {e}", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# ===== Deliveries =====

@router.get("/deliveries")
async def get_deliveries(
    limit: int = Query(50, ge=1, le=200),
    status: Optional[str] = Query(None, description="Filter by status (pending, sending, sent, failed)")
):
    """
    Get scheduled email deliveries.

    Shows the email delivery queue - stories waiting to be sent at scheduled times.
    """
    if not config.supabase_configured:
        raise HTTPException(status_code=503, detail="Supabase not configured")

    try:
        from backend.database.deliveries import DeliveryService
        delivery_service = DeliveryService()
        deliveries = await delivery_service.get_delivery_schedule(status=status, limit=limit)

        result = []
        for d in deliveries:
            story = d.get("stories") or {}
            result.append({
                "id": d["id"],
                "user_email": d["user_email"],
                "story_title": story.get("title", "Untitled"),
                "story_genre": story.get("genre", "unknown"),
                "word_count": story.get("word_count", 0),
                "deliver_at": d["deliver_at"],
                "timezone": d.get("timezone", "UTC"),
                "status": d["status"],
                "sent_at": d.get("sent_at"),
                "error_message": d.get("error_message"),
                "retry_count": d.get("retry_count", 0),
                "created_at": d["created_at"]
            })

        return {"deliveries": result}
    except Exception as e:
        logger.error(f"Failed to fetch deliveries: {e}", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/deliveries/stats")
async def get_delivery_stats():
    """Get email delivery statistics."""
    if not config.supabase_configured:
        raise HTTPException(status_code=503, detail="Supabase not configured")

    try:
        from backend.database.deliveries import DeliveryService
        delivery_service = DeliveryService()
        stats = await delivery_service.get_delivery_stats()
        return stats
    except Exception as e:
        logger.error(f"Failed to fetch delivery stats: {e}", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/deliveries/upcoming")
async def get_upcoming_deliveries(
    hours: int = Query(24, ge=1, le=168, description="Hours to look ahead")
):
    """Get upcoming deliveries within the next N hours."""
    if not config.supabase_configured:
        raise HTTPException(status_code=503, detail="Supabase not configured")

    try:
        from backend.database.deliveries import DeliveryService
        delivery_service = DeliveryService()
        deliveries = await delivery_service.get_upcoming_deliveries(hours_ahead=hours)

        result = []
        for d in deliveries:
            story = d.get("stories") or {}
            result.append({
                "id": d["id"],
                "user_email": d["user_email"],
                "story_title": story.get("title", "Untitled"),
                "story_genre": story.get("genre", "unknown"),
                "deliver_at": d["deliver_at"],
                "timezone": d.get("timezone", "UTC"),
                "status": d["status"]
            })

        return {"upcoming": result, "hours_ahead": hours}
    except Exception as e:
        logger.error(f"Failed to fetch upcoming deliveries: {e}", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/deliveries/failed")
async def get_failed_deliveries(limit: int = Query(50, ge=1, le=200)):
    """Get failed email deliveries."""
    if not config.supabase_configured:
        raise HTTPException(status_code=503, detail="Supabase not configured")

    try:
        from backend.database.deliveries import DeliveryService
        delivery_service = DeliveryService()
        failed = await delivery_service.get_failed_deliveries(limit=limit)

        result = []
        for d in failed:
            story = d.get("stories") or {}
            result.append({
                "id": d["id"],
                "user_email": d["user_email"],
                "story_title": story.get("title", "Untitled"),
                "deliver_at": d.get("deliver_at"),
                "error_message": d.get("error_message"),
                "retry_count": d.get("retry_count", 0),
                "updated_at": d.get("updated_at")
            })

        return {"failed_deliveries": result}
    except Exception as e:
        logger.error(f"Failed to fetch failed deliveries: {e}", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# ===== Logs =====

@router.get("/logs")
async def get_logs(
    limit: int = Query(100, ge=1, le=500),
    level: Optional[str] = Query(None, description="Filter by level (debug, info, warning, error, critical)"),
    source: Optional[str] = Query(None, description="Filter by source")
):
    """Get recent log entries from the in-memory buffer."""
    from backend.utils.logging import LogLevel

    log_buffer = get_log_buffer()

    level_filter = None
    if level:
        try:
            level_filter = LogLevel(level.lower())
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid log level: {level}")

    logs = log_buffer.get_recent(limit=limit, level=level_filter, source=source)
    stats = log_buffer.get_stats()

    return {
        "logs": logs,
        "stats": stats
    }


@router.get("/logs/errors")
async def get_error_logs(limit: int = Query(50, ge=1, le=200)):
    """Get recent error and critical log entries."""
    log_buffer = get_log_buffer()
    errors = log_buffer.get_errors(limit=limit)

    return {"errors": errors}


@router.get("/logs/warnings")
async def get_warning_logs(limit: int = Query(50, ge=1, le=200)):
    """Get recent warning log entries."""
    log_buffer = get_log_buffer()
    warnings = log_buffer.get_warnings(limit=limit)

    return {"warnings": warnings}


# ===== System =====

@router.get("/system")
async def get_system_info():
    """Get system information and health status."""
    import platform

    # Basic system info
    info = {
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "environment": os.getenv("ENVIRONMENT", "development"),
        "debug_mode": config.DEBUG,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

    # Resource usage (psutil is optional - may not be installed in production)
    try:
        import psutil
        info["cpu_percent"] = psutil.cpu_percent()
        info["memory"] = {
            "total_gb": round(psutil.virtual_memory().total / (1024**3), 2),
            "used_gb": round(psutil.virtual_memory().used / (1024**3), 2),
            "percent": psutil.virtual_memory().percent
        }
        info["disk"] = {
            "total_gb": round(psutil.disk_usage('/').total / (1024**3), 2),
            "used_gb": round(psutil.disk_usage('/').used / (1024**3), 2),
            "percent": psutil.disk_usage('/').percent
        }
    except ImportError:
        # psutil not installed - skip resource metrics
        pass
    except Exception:
        pass  # Other errors (permissions, etc.)

    # Configuration status
    info["config"] = {
        "supabase_configured": config.supabase_configured,
        "stripe_configured": config.stripe_configured,
        "media_generation_enabled": config.ENABLE_MEDIA_GENERATION,
        "credit_system_enabled": config.ENABLE_CREDIT_SYSTEM,
        "model": config.MODEL_NAME,
        "job_queue": "supabase"  # Indicate we're now using Supabase
    }

    # Check API keys (without exposing them)
    info["api_keys"] = {
        "anthropic": bool(os.getenv("ANTHROPIC_API_KEY")),
        "openai": bool(os.getenv("OPENAI_API_KEY")),
        "replicate": bool(os.getenv("REPLICATE_API_TOKEN")),
        "resend": bool(os.getenv("RESEND_API_KEY"))
    }

    return info


@router.post("/logs/clear")
async def clear_logs():
    """Clear the in-memory log buffer."""
    log_buffer = get_log_buffer()
    log_buffer.clear()
    logger.info("Log buffer cleared by admin")
    return {"status": "cleared"}


# ===== Scheduler Status =====

@router.get("/scheduler/status")
async def get_scheduler_status():
    """
    Get the status of the daily story scheduler.

    Shows scheduler health, next check time, and upcoming user deliveries.
    """
    from backend.jobs.daily_scheduler import get_daily_scheduler
    from zoneinfo import ZoneInfo

    status = {
        "scheduler_running": False,
        "check_interval_seconds": 60,
        "generation_lead_minutes": 30,
        "next_deliveries": [],
        "recent_failures": {
            "jobs": 0,
            "deliveries": 0
        },
        "alerts": []
    }

    # Check if scheduler is running
    scheduler = get_daily_scheduler()
    if scheduler:
        status["scheduler_running"] = scheduler.scheduler.running if scheduler.scheduler else False
        status["check_interval_seconds"] = scheduler.check_interval
        status["generation_lead_minutes"] = scheduler.generation_lead

    # Get upcoming user deliveries based on their preferences
    if config.supabase_configured:
        try:
            from backend.database.client import get_supabase_admin_client
            client = get_supabase_admin_client()

            # Get active users with their delivery preferences
            users_result = client.table("users").select(
                "id, email, preferences, current_genre, credits, last_story_at"
            ).eq("onboarding_completed", True).gt("credits", 0).limit(50).execute()

            now_utc = datetime.now(timezone.utc)
            upcoming = []

            for user in users_result.data or []:
                prefs = user.get("preferences", {})
                delivery_time = prefs.get("delivery_time", "08:00")
                user_tz_str = prefs.get("timezone", "UTC")

                try:
                    user_tz = ZoneInfo(user_tz_str)
                except Exception:
                    user_tz = ZoneInfo("UTC")

                # Parse delivery time
                try:
                    hour, minute = map(int, delivery_time.split(":"))
                except (ValueError, AttributeError):
                    hour, minute = 8, 0

                # Calculate next delivery time in user's timezone
                user_now = now_utc.astimezone(user_tz)
                next_delivery = user_now.replace(hour=hour, minute=minute, second=0, microsecond=0)

                # If already passed today, it's tomorrow
                if next_delivery <= user_now:
                    next_delivery = next_delivery + timedelta(days=1)

                # Convert back to UTC for display
                next_delivery_utc = next_delivery.astimezone(timezone.utc)

                # Check if already got story today
                last_story = user.get("last_story_at")
                got_story_today = False
                if last_story:
                    try:
                        if isinstance(last_story, str):
                            last_story_dt = datetime.fromisoformat(last_story.replace("Z", "+00:00"))
                        else:
                            last_story_dt = last_story
                        last_story_user_tz = last_story_dt.astimezone(user_tz)
                        got_story_today = last_story_user_tz.date() == user_now.date()
                    except Exception:
                        pass

                upcoming.append({
                    "email": user["email"],
                    "delivery_time": delivery_time,
                    "timezone": user_tz_str,
                    "next_delivery_utc": next_delivery_utc.isoformat(),
                    "hours_until": round((next_delivery_utc - now_utc).total_seconds() / 3600, 1),
                    "genre": user.get("current_genre", "mystery"),
                    "credits": user.get("credits", 0),
                    "got_story_today": got_story_today
                })

            # Sort by next delivery time
            upcoming.sort(key=lambda x: x["next_delivery_utc"])
            status["next_deliveries"] = upcoming[:20]  # Top 20

            # Get recent failure counts (last 24 hours)
            yesterday = (now_utc - timedelta(hours=24)).isoformat()

            failed_jobs = client.table("story_jobs").select("id", count="exact").eq(
                "status", "failed"
            ).gte("completed_at", yesterday).execute()
            status["recent_failures"]["jobs"] = failed_jobs.count or 0

            # Failed deliveries
            from backend.database.deliveries import DeliveryService
            delivery_service = DeliveryService()
            failed_deliveries = await delivery_service.get_failed_deliveries(limit=100)
            status["recent_failures"]["deliveries"] = len(failed_deliveries)

            # Generate alerts
            if status["recent_failures"]["jobs"] > 0:
                status["alerts"].append({
                    "level": "error",
                    "message": f"{status['recent_failures']['jobs']} story generation(s) failed in the last 24 hours"
                })

            if status["recent_failures"]["deliveries"] > 0:
                status["alerts"].append({
                    "level": "error",
                    "message": f"{status['recent_failures']['deliveries']} email delivery(ies) have failed"
                })

            if not status["scheduler_running"]:
                status["alerts"].append({
                    "level": "warning",
                    "message": "Daily scheduler is not running! Stories will not be generated automatically."
                })

        except Exception as e:
            logger.error(f"Failed to fetch scheduler status: {e}", error=str(e))
            status["alerts"].append({
                "level": "error",
                "message": f"Error fetching scheduler data: {str(e)}"
            })

    return status


# ===== Manual Story Generation =====

@router.post("/users/{user_id}/generate-story")
async def generate_story_for_user(user_id: str):
    """
    Manually trigger story generation for a user.

    Useful for recovering from failed scheduled deliveries or
    testing story generation for specific users.
    """
    if not config.supabase_configured:
        raise HTTPException(status_code=503, detail="Supabase not configured")

    try:
        from backend.database.client import get_supabase_admin_client
        from backend.database.users import UserService

        client = get_supabase_admin_client()

        # Get user details
        user_result = client.table("users").select("*").eq("id", user_id).single().execute()
        if not user_result.data:
            raise HTTPException(status_code=404, detail="User not found")

        user = user_result.data

        # Check if user has credits (if credit system is enabled)
        if config.ENABLE_CREDIT_SYSTEM:
            credits = user.get("story_credits", 0)
            tier = user.get("subscription_tier", "free")
            if tier == "free" and credits < 1:
                raise HTTPException(
                    status_code=400,
                    detail=f"User has insufficient credits ({credits}). Add credits first."
                )

        # Check if user has a story bible
        story_bible = user.get("story_bible") or {}
        if not story_bible:
            raise HTTPException(
                status_code=400,
                detail="User has no story bible configured. Set up a story bible first."
            )

        # Use Redis Queue system if enabled, otherwise fall back to legacy system
        redis_queue_enabled = getattr(config, 'redis_configured', False)

        if redis_queue_enabled and config.REDIS_URL:
            # Use Redis Queue system
            import uuid
            from backend.database.jobs import JobQueueService
            from backend.queue.tasks import enqueue_story_job

            job_service = JobQueueService()

            # Check if user already has an active job
            existing_job = await job_service.get_active_job_for_user(user["email"])
            if existing_job:
                raise HTTPException(
                    status_code=409,
                    detail=f"User already has an active job: {existing_job.get('id')}"
                )

            # Build job settings
            settings = user.get("settings") or {}
            tier = user.get("subscription_tier", "free")

            job_id = str(uuid.uuid4())
            job_settings = {
                "delivery_time": settings.get("delivery_time", "08:00"),
                "timezone": settings.get("timezone", "UTC"),
                "user_tier": tier,
                "writer_model": "sonnet",
                "structure_model": "sonnet",
                "editor_model": "opus" if tier in ["monthly", "annual"] else "sonnet",
                "tts_provider": settings.get("tts_provider", "openai"),
                "tts_voice": settings.get("tts_voice"),
                "is_daily": False,  # Manual trigger, not daily scheduled
                "immediate_delivery": True,  # Send email as soon as generated
            }

            # Create job record in database
            await job_service.create_job(
                job_id=job_id,
                story_bible=story_bible,
                user_email=user["email"],
                settings=job_settings
            )

            # Enqueue to Redis
            rq_job = enqueue_story_job(
                job_id=job_id,
                story_bible=story_bible,
                user_email=user["email"],
                settings=job_settings
            )

            logger.info(
                "Admin triggered manual story generation via Redis Queue",
                user_id=user_id,
                email=user.get("email"),
                job_id=job_id,
                rq_job_id=rq_job.id
            )

            return {
                "status": "queued",
                "message": f"Story generation queued for {user.get('email')} via Redis Queue - will be emailed immediately upon completion",
                "user_id": user_id,
                "job_id": job_id,
                "queue": "redis"
            }

        else:
            # Fall back to legacy APScheduler system
            from backend.jobs.daily_scheduler import get_daily_scheduler, DailyStoryScheduler

            scheduler = get_daily_scheduler()
            if not scheduler:
                scheduler = DailyStoryScheduler()
                await scheduler.initialize()

            await scheduler._queue_story_for_user(user, immediate_delivery=True)

            logger.info(
                "Admin triggered manual story generation via legacy scheduler",
                user_id=user_id,
                email=user.get("email")
            )

            return {
                "status": "queued",
                "message": f"Story generation queued for {user.get('email')} - will be emailed immediately upon completion",
                "user_id": user_id,
                "queue": "legacy"
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to trigger manual story generation: {e}", user_id=user_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
