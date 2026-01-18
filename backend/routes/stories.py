"""
Stories API Routes

Endpoints for retrieving user stories, managing story library,
and triggering story generation.
"""

from typing import Optional, List
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel

from backend.database.stories import StoryService
from backend.database.users import UserService
from backend.database.jobs import JobQueueService
from backend.database.deliveries import DeliveryService
from backend.jobs.daily_scheduler import get_daily_scheduler
from backend.routes.auth import get_current_user_id


router = APIRouter(prefix="/api/stories", tags=["stories"])


# =============================================================================
# Response Models
# =============================================================================

class StoryResponse(BaseModel):
    """Single story response."""
    id: str
    title: str
    narrative: str
    genre: str
    word_count: int
    audio_url: Optional[str] = None
    image_url: Optional[str] = None
    rating: Optional[int] = None
    is_retell: bool = False
    created_at: str


class StoryListResponse(BaseModel):
    """List of stories response."""
    stories: List[StoryResponse]
    total: int
    limit: int
    offset: int


class StoryStatsResponse(BaseModel):
    """User story statistics."""
    total_stories: int
    original_stories: int
    retells: int
    genres: dict
    total_words: int
    average_rating: float


class GenerateStoryRequest(BaseModel):
    """Request to generate a new story."""
    genre: Optional[str] = None  # Override user's default genre
    intensity: Optional[int] = None  # 1-5


class GenerateStoryResponse(BaseModel):
    """Response after queuing story generation."""
    job_id: str
    message: str
    status: str


class ActiveJobResponse(BaseModel):
    """A pending or running story generation job."""
    job_id: str
    status: str
    current_step: Optional[str] = None
    progress_percent: int = 0
    genre: Optional[str] = None
    created_at: str
    started_at: Optional[str] = None


class NextDeliveryResponse(BaseModel):
    """User's next scheduled email delivery."""
    delivery_id: str
    deliver_at: str
    timezone: str
    story_title: Optional[str] = None
    story_genre: Optional[str] = None


class DashboardStatusResponse(BaseModel):
    """Dashboard status including active jobs and upcoming deliveries."""
    active_jobs: List[ActiveJobResponse]
    next_delivery: Optional[NextDeliveryResponse] = None
    has_pending_story: bool


class JobActivityItem(BaseModel):
    """A single job activity log entry."""
    job_id: str
    status: str
    current_step: Optional[str] = None
    progress_percent: int = 0
    genre: Optional[str] = None
    title: Optional[str] = None
    error_message: Optional[str] = None
    is_daily: bool = False
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    generation_time_seconds: Optional[float] = None


class JobActivityResponse(BaseModel):
    """Recent job activity for the dashboard."""
    jobs: List[JobActivityItem]
    total: int


# =============================================================================
# Story List Routes
# =============================================================================

@router.get("", response_model=StoryListResponse)
async def get_stories(
    limit: int = Query(default=20, le=100),
    offset: int = Query(default=0, ge=0),
    genre: Optional[str] = None,
    user_id: str = Depends(get_current_user_id)
):
    """
    Get user's stories with pagination.

    Returns stories sorted by creation date (newest first).
    """
    story_service = StoryService()

    stories = await story_service.get_user_stories(
        user_id,
        limit=limit,
        offset=offset,
        genre=genre,
        include_retells=True,
    )

    # Get total count for pagination
    stats = await story_service.get_user_stats(user_id)
    total = stats["total_stories"]

    return StoryListResponse(
        stories=[
            StoryResponse(
                id=s["id"],
                title=s["title"],
                narrative=s["narrative"],
                genre=s["genre"],
                word_count=s["word_count"],
                audio_url=s.get("audio_url"),
                image_url=s.get("image_url"),
                rating=s.get("rating"),
                is_retell=s.get("is_retell", False),
                created_at=s["created_at"],
            )
            for s in stories
        ],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/stats", response_model=StoryStatsResponse)
async def get_story_stats(
    user_id: str = Depends(get_current_user_id)
):
    """Get user's story statistics."""
    story_service = StoryService()
    stats = await story_service.get_user_stats(user_id)

    return StoryStatsResponse(**stats)


@router.get("/status", response_model=DashboardStatusResponse)
async def get_dashboard_status(
    user_id: str = Depends(get_current_user_id)
):
    """
    Get user's story generation status for the dashboard.

    Returns:
    - Active jobs (pending/running story generation)
    - Next scheduled delivery (if any)
    - Whether user has a story being generated
    """
    job_service = JobQueueService()
    delivery_service = DeliveryService()

    # Get active jobs for this user
    active_jobs_raw = await job_service.get_user_active_jobs(user_id)

    active_jobs = [
        ActiveJobResponse(
            job_id=job["job_id"],
            status=job["status"],
            current_step=job.get("current_step"),
            progress_percent=job.get("progress_percent", 0),
            genre=job.get("story_bible", {}).get("genre"),
            created_at=job["created_at"],
            started_at=job.get("started_at"),
        )
        for job in active_jobs_raw
    ]

    # Get next delivery
    next_delivery_raw = await delivery_service.get_user_next_delivery(user_id)

    next_delivery = None
    if next_delivery_raw:
        story_info = next_delivery_raw.get("story") or {}
        next_delivery = NextDeliveryResponse(
            delivery_id=next_delivery_raw["id"],
            deliver_at=next_delivery_raw["deliver_at"],
            timezone=next_delivery_raw.get("timezone", "UTC"),
            story_title=story_info.get("title"),
            story_genre=story_info.get("genre"),
        )

    return DashboardStatusResponse(
        active_jobs=active_jobs,
        next_delivery=next_delivery,
        has_pending_story=len(active_jobs) > 0 or next_delivery is not None,
    )


@router.get("/activity", response_model=JobActivityResponse)
async def get_job_activity(
    limit: int = Query(default=20, le=50),
    user_id: str = Depends(get_current_user_id)
):
    """
    Get recent job activity for the dashboard.

    Shows all recent jobs (pending, running, completed, failed) to give
    visibility into what's happening with story generation.
    """
    job_service = JobQueueService()

    # Get recent jobs for this user
    recent_jobs = await job_service.get_recent_jobs(limit=limit)

    # Filter to only this user's jobs and build response
    jobs = []
    for job in recent_jobs:
        # Get settings to check if daily
        settings = job.get("settings") or {}
        job_user_id = settings.get("user_id")

        # Only include this user's jobs
        if job_user_id != user_id:
            continue

        # Try to get title from result
        result = job.get("result") or {}
        story_data = result.get("story") or {}
        title = story_data.get("title")

        # Get genre from story_bible
        story_bible = job.get("story_bible") or {}
        genre = story_bible.get("genre")

        jobs.append(JobActivityItem(
            job_id=job["job_id"],
            status=job["status"],
            current_step=job.get("current_step"),
            progress_percent=job.get("progress_percent", 0),
            genre=genre,
            title=title,
            error_message=job.get("error_message"),
            is_daily=settings.get("is_daily", False),
            created_at=job["created_at"],
            started_at=job.get("started_at"),
            completed_at=job.get("completed_at"),
            generation_time_seconds=job.get("generation_time_seconds"),
        ))

    return JobActivityResponse(
        jobs=jobs,
        total=len(jobs)
    )


@router.get("/latest")
async def get_latest_story(
    user_id: str = Depends(get_current_user_id)
):
    """Get user's most recent story."""
    story_service = StoryService()
    story = await story_service.get_latest_story(user_id)

    if not story:
        return {"story": None, "message": "No stories yet"}

    return {
        "story": StoryResponse(
            id=story["id"],
            title=story["title"],
            narrative=story["narrative"],
            genre=story["genre"],
            word_count=story["word_count"],
            audio_url=story.get("audio_url"),
            image_url=story.get("image_url"),
            rating=story.get("rating"),
            is_retell=story.get("is_retell", False),
            created_at=story["created_at"],
        )
    }


# =============================================================================
# Single Story Routes
# =============================================================================

@router.get("/{story_id}")
async def get_story(
    story_id: str,
    user_id: str = Depends(get_current_user_id)
):
    """Get a single story by ID."""
    story_service = StoryService()
    story = await story_service.get_by_id(story_id)

    if not story:
        raise HTTPException(status_code=404, detail="Story not found")

    # Verify ownership
    if story.get("user_id") != user_id:
        raise HTTPException(status_code=403, detail="Not your story")

    return StoryResponse(
        id=story["id"],
        title=story["title"],
        narrative=story["narrative"],
        genre=story["genre"],
        word_count=story["word_count"],
        audio_url=story.get("audio_url"),
        image_url=story.get("image_url"),
        rating=story.get("rating"),
        is_retell=story.get("is_retell", False),
        created_at=story["created_at"],
    )


@router.post("/{story_id}/rate")
async def rate_story(
    story_id: str,
    rating: int = Query(ge=1, le=5),
    user_id: str = Depends(get_current_user_id)
):
    """Rate a story (1-5 stars)."""
    story_service = StoryService()

    # Verify story exists and belongs to user
    story = await story_service.get_by_id(story_id)
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    if story.get("user_id") != user_id:
        raise HTTPException(status_code=403, detail="Not your story")

    await story_service.add_rating(story_id, rating)

    return {"success": True, "rating": rating}


# =============================================================================
# Story Generation Routes
# =============================================================================

@router.post("/generate", response_model=GenerateStoryResponse)
async def generate_story(
    request: GenerateStoryRequest,
    user_id: str = Depends(get_current_user_id)
):
    """
    Queue a new story for generation.

    This is for on-demand story generation (uses 1 credit).
    The story will be generated asynchronously and delivered via email.
    """
    user_service = UserService()
    scheduler = get_daily_scheduler()

    if not scheduler:
        raise HTTPException(
            status_code=503,
            detail="Story generation service unavailable"
        )

    # Get user data
    user = await user_service.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Check credits
    credits = user.get("credits", 0)
    if credits < 1:
        raise HTTPException(
            status_code=402,
            detail="Insufficient credits. Please subscribe or purchase credits."
        )

    # Build story bible
    story_bible = user.get("story_bible", {})
    story_bible["genre"] = request.genre or user.get("current_genre", "mystery")

    if request.intensity:
        story_bible["intensity"] = request.intensity

    if user.get("current_protagonist"):
        story_bible["protagonist"] = user["current_protagonist"]

    # Determine settings based on subscription
    prefs = user.get("preferences", {})
    subscription_status = user.get("subscription_status", "trial")
    is_premium = subscription_status == "active"

    settings = {
        "user_tier": "premium" if is_premium else "free",
        "user_id": user_id,
        "story_length": prefs.get("story_length", "medium"),
        "writer_model": "sonnet",
        "structure_model": "sonnet",
        "editor_model": "opus" if is_premium else "sonnet",
        "tts_voice": prefs.get("voice_id", "nova"),
        "dev_mode": False,
        # Manual stories are "extras" - they don't block the next scheduled daily story
        "is_daily": False,
    }

    # Queue the story
    job_id = await scheduler.queue_story_now(
        user_id=user_id,
        user_email=user["email"],
        story_bible=story_bible,
        settings=settings
    )

    return GenerateStoryResponse(
        job_id=job_id,
        message="Story generation started! You'll receive it via email shortly.",
        status="queued"
    )


@router.get("/jobs/{job_id}")
async def get_job_status(
    job_id: str,
    user_id: str = Depends(get_current_user_id)
):
    """Get the status of a story generation job."""
    scheduler = get_daily_scheduler()

    if not scheduler or not scheduler.job_db:
        raise HTTPException(
            status_code=503,
            detail="Story generation service unavailable"
        )

    job = await scheduler.job_db.get_job_by_id(job_id)

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Verify ownership (check settings for user_id)
    job_user_id = job.get("settings", {}).get("user_id")
    if job_user_id and job_user_id != user_id:
        raise HTTPException(status_code=403, detail="Not your job")

    return {
        "job_id": job["job_id"],
        "status": job["status"],
        "current_step": job.get("current_step"),
        "progress_percent": job.get("progress_percent", 0),
        "created_at": job["created_at"],
        "completed_at": job.get("completed_at"),
        "error_message": job.get("error_message"),
    }
