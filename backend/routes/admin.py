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

            # Story counts
            stories_result = client.table("stories").select("id", count="exact").execute()
            overview["stories"]["total"] = stories_result.count or 0

            # Generated today
            gen_today = client.table("stories").select("id", count="exact").gte(
                "created_at", f"{today}T00:00:00"
            ).eq("status", "completed").execute()
            overview["stories"]["generated_today"] = gen_today.count or 0

            # Failed today
            failed_today = client.table("stories").select("id", count="exact").gte(
                "created_at", f"{today}T00:00:00"
            ).eq("status", "failed").execute()
            overview["stories"]["failed_today"] = failed_today.count or 0

            # Scheduled stories
            scheduled_result = client.table("scheduled_stories").select("id", count="exact").eq(
                "status", "pending"
            ).execute()
            overview["scheduled"]["pending"] = scheduled_result.count or 0

            # Due in next hour
            next_hour = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
            due_soon = client.table("scheduled_stories").select("id", count="exact").eq(
                "status", "pending"
            ).lte("scheduled_for", next_hour).execute()
            overview["scheduled"]["due_soon"] = due_soon.count or 0

        except Exception as e:
            logger.error(f"Failed to fetch Supabase stats: {e}", error=str(e))
            overview["system"]["supabase_error"] = str(e)

    # Get job queue stats from SQLite
    try:
        from backend.jobs.database import StoryJobDatabase
        job_db = StoryJobDatabase()
        await job_db.connect()

        conn = job_db._conn
        if conn:
            # Pending jobs
            cursor = await conn.execute(
                "SELECT COUNT(*) FROM story_jobs WHERE status = 'pending'"
            )
            overview["jobs"]["pending"] = (await cursor.fetchone())[0]

            # Running jobs
            cursor = await conn.execute(
                "SELECT COUNT(*) FROM story_jobs WHERE status = 'running'"
            )
            overview["jobs"]["running"] = (await cursor.fetchone())[0]

            # Completed today
            cursor = await conn.execute(
                "SELECT COUNT(*) FROM story_jobs WHERE status = 'completed' AND completed_at LIKE ?",
                (f"{today}%",)
            )
            overview["jobs"]["completed_today"] = (await cursor.fetchone())[0]

            # Failed today
            cursor = await conn.execute(
                "SELECT COUNT(*) FROM story_jobs WHERE status = 'failed' AND completed_at LIKE ?",
                (f"{today}%",)
            )
            overview["jobs"]["failed_today"] = (await cursor.fetchone())[0]

        await job_db.close()
    except Exception as e:
        logger.error(f"Failed to fetch job queue stats: {e}", error=str(e))
        overview["system"]["jobs_error"] = str(e)

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


# ===== Scheduled Stories =====

@router.get("/scheduled")
async def get_scheduled_stories(
    limit: int = Query(50, ge=1, le=200),
    status: Optional[str] = Query(None, description="Filter by status (pending, running, completed, failed)")
):
    """
    Get scheduled/queued stories from the job queue.

    Note: The scheduler uses SQLite job queue, not Supabase scheduled_stories table.
    This endpoint shows pending and recent jobs from the actual job queue.
    """
    try:
        from backend.jobs.database import StoryJobDatabase
        job_db = StoryJobDatabase()
        await job_db.connect()

        conn = job_db._conn
        scheduled = []

        if conn:
            # Get jobs - default to pending/running if no status specified
            if status:
                cursor = await conn.execute("""
                    SELECT job_id, status, user_email, story_bible, settings,
                           current_step, progress_percent, error_message,
                           created_at, started_at, completed_at, retry_count
                    FROM story_jobs
                    WHERE status = ?
                    ORDER BY created_at DESC
                    LIMIT ?
                """, (status, limit))
            else:
                # Show pending and running by default
                cursor = await conn.execute("""
                    SELECT job_id, status, user_email, story_bible, settings,
                           current_step, progress_percent, error_message,
                           created_at, started_at, completed_at, retry_count
                    FROM story_jobs
                    WHERE status IN ('pending', 'running')
                    ORDER BY created_at ASC
                    LIMIT ?
                """, (limit,))

            rows = await cursor.fetchall()
            import json
            for row in rows:
                # Parse settings to get delivery info
                settings = {}
                try:
                    if row[4]:
                        settings = json.loads(row[4])
                except:
                    pass

                # Parse story_bible to get genre
                bible = {}
                try:
                    if row[3]:
                        bible = json.loads(row[3])
                except:
                    pass

                scheduled.append({
                    "id": row[0],
                    "status": row[1],
                    "user_email": row[2],
                    "genre": bible.get("genre", "unknown"),
                    "current_step": row[5],
                    "progress_percent": row[6],
                    "error_message": row[7],
                    "created_at": row[8],
                    "started_at": row[9],
                    "completed_at": row[10],
                    "attempts": row[11] or 0,
                    # Use created_at as scheduled_for since jobs are created at schedule time
                    "scheduled_for": row[8]
                })

        await job_db.close()
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
    Get job queue status from SQLite database.
    """
    try:
        from backend.jobs.database import StoryJobDatabase
        job_db = StoryJobDatabase()
        await job_db.connect()

        conn = job_db._conn
        jobs = []

        if conn:
            if status:
                cursor = await conn.execute("""
                    SELECT job_id, status, user_email, current_step, progress_percent,
                           error_message, created_at, started_at, completed_at,
                           generation_time_seconds, retry_count
                    FROM story_jobs
                    WHERE status = ?
                    ORDER BY created_at DESC
                    LIMIT ?
                """, (status, limit))
            else:
                cursor = await conn.execute("""
                    SELECT job_id, status, user_email, current_step, progress_percent,
                           error_message, created_at, started_at, completed_at,
                           generation_time_seconds, retry_count
                    FROM story_jobs
                    ORDER BY created_at DESC
                    LIMIT ?
                """, (limit,))

            rows = await cursor.fetchall()
            jobs = [
                {
                    "job_id": row[0],
                    "status": row[1],
                    "user_email": row[2],
                    "current_step": row[3],
                    "progress_percent": row[4],
                    "error_message": row[5],
                    "created_at": row[6],
                    "started_at": row[7],
                    "completed_at": row[8],
                    "generation_time_seconds": row[9],
                    "retry_count": row[10]
                }
                for row in rows
            ]

        await job_db.close()
        return {"jobs": jobs}
    except Exception as e:
        logger.error(f"Failed to fetch jobs: {e}", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/jobs/failed")
async def get_failed_jobs(limit: int = Query(50, ge=1, le=200)):
    """Get failed jobs with error details."""
    try:
        from backend.jobs.database import StoryJobDatabase
        job_db = StoryJobDatabase()
        await job_db.connect()

        conn = job_db._conn
        jobs = []

        if conn:
            cursor = await conn.execute("""
                SELECT job_id, status, user_email, current_step, error_message,
                       created_at, completed_at, retry_count
                FROM story_jobs
                WHERE status = 'failed'
                ORDER BY completed_at DESC
                LIMIT ?
            """, (limit,))

            rows = await cursor.fetchall()
            jobs = [
                {
                    "job_id": row[0],
                    "status": row[1],
                    "user_email": row[2],
                    "failed_at_step": row[3],
                    "error_message": row[4],
                    "created_at": row[5],
                    "completed_at": row[6],
                    "retry_count": row[7]
                }
                for row in rows
            ]

        await job_db.close()
        return {"failed_jobs": jobs}
    except Exception as e:
        logger.error(f"Failed to fetch failed jobs: {e}", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/jobs/stats")
async def get_job_stats():
    """Get job queue statistics."""
    try:
        from backend.jobs.database import StoryJobDatabase
        job_db = StoryJobDatabase()
        await job_db.connect()

        conn = job_db._conn
        stats = {
            "by_status": {},
            "avg_generation_time": None,
            "total_jobs": 0,
            "jobs_last_24h": 0,
            "success_rate_24h": 0
        }

        if conn:
            # Count by status
            cursor = await conn.execute("""
                SELECT status, COUNT(*) FROM story_jobs GROUP BY status
            """)
            rows = await cursor.fetchall()
            stats["by_status"] = {row[0]: row[1] for row in rows}
            stats["total_jobs"] = sum(stats["by_status"].values())

            # Average generation time for completed jobs
            cursor = await conn.execute("""
                SELECT AVG(generation_time_seconds) FROM story_jobs
                WHERE status = 'completed' AND generation_time_seconds IS NOT NULL
            """)
            avg = (await cursor.fetchone())[0]
            stats["avg_generation_time"] = round(avg, 2) if avg else None

            # Jobs in last 24 hours
            yesterday = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
            cursor = await conn.execute("""
                SELECT COUNT(*) FROM story_jobs WHERE created_at >= ?
            """, (yesterday,))
            stats["jobs_last_24h"] = (await cursor.fetchone())[0]

            # Success rate in last 24h
            cursor = await conn.execute("""
                SELECT
                    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
                    SUM(CASE WHEN status IN ('completed', 'failed') THEN 1 ELSE 0 END) as total
                FROM story_jobs
                WHERE created_at >= ?
            """, (yesterday,))
            row = await cursor.fetchone()
            if row[1] and row[1] > 0:
                stats["success_rate_24h"] = round((row[0] / row[1]) * 100, 1)

        await job_db.close()
        return stats
    except Exception as e:
        logger.error(f"Failed to fetch job stats: {e}", error=str(e))
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
    import psutil

    # Basic system info
    info = {
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "environment": os.getenv("ENVIRONMENT", "development"),
        "debug_mode": config.DEBUG,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

    # Resource usage
    try:
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
    except Exception:
        pass  # psutil may not be available

    # Configuration status
    info["config"] = {
        "supabase_configured": config.supabase_configured,
        "stripe_configured": config.stripe_configured,
        "media_generation_enabled": config.ENABLE_MEDIA_GENERATION,
        "credit_system_enabled": config.ENABLE_CREDIT_SYSTEM,
        "model": config.MODEL_NAME
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
