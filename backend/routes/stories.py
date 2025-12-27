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
