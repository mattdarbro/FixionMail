"""
User Management Routes

Handles user profile updates, preferences, story bible management,
and account information.
"""

from typing import Optional, Dict, Any, List

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from backend.config import config
from backend.database.users import UserService, UserNotFoundError
from backend.database.stories import StoryService
from backend.database.credits import CreditService
from backend.routes.auth import get_current_user, get_current_user_id

router = APIRouter(prefix="/api/users", tags=["users"])


# =============================================================================
# Request/Response Models
# =============================================================================

class UpdatePreferencesRequest(BaseModel):
    """Request to update user preferences."""
    story_length: Optional[str] = None  # 'short', 'medium', 'long'
    delivery_time: Optional[str] = None  # HH:MM format
    timezone: Optional[str] = None
    voice_id: Optional[str] = None
    model_preference: Optional[str] = None  # 'sonnet', 'opus'


class UpdateStoryBibleRequest(BaseModel):
    """Request to update story bible (usually from Fixion onboarding)."""
    story_bible: Dict[str, Any]


class SetGenreRequest(BaseModel):
    """Request to set current genre."""
    genre: str
    protagonist: Optional[Dict[str, Any]] = None


class UpdateOnboardingRequest(BaseModel):
    """Request to update onboarding step."""
    step: str
    completed: bool = False


class UserProfileResponse(BaseModel):
    """Full user profile response."""
    id: str
    email: str
    credits: int
    subscription_status: str
    subscription_tier: Optional[str]
    current_period_end: Optional[str]
    onboarding_completed: bool
    onboarding_step: Optional[str]
    current_genre: Optional[str]
    preferences: Dict[str, Any]
    story_bible: Dict[str, Any]
    created_at: str


class CreditBalanceResponse(BaseModel):
    """Credit balance response."""
    credits: int
    subscription_status: str
    subscription_tier: Optional[str]


class UserStatsResponse(BaseModel):
    """User statistics response."""
    total_stories: int
    original_stories: int
    retells: int
    genres: Dict[str, int]
    total_words: int
    average_rating: float


class CreditTransactionResponse(BaseModel):
    """Credit transaction response."""
    id: str
    amount: int
    balance_after: int
    transaction_type: str
    description: Optional[str]
    created_at: str


# =============================================================================
# Profile Routes
# =============================================================================

@router.get("/me", response_model=UserProfileResponse)
async def get_profile(user: dict = Depends(get_current_user)):
    """Get current user's full profile."""
    return UserProfileResponse(
        id=user["id"],
        email=user["email"],
        credits=user["credits"],
        subscription_status=user["subscription_status"],
        subscription_tier=user.get("subscription_tier"),
        current_period_end=user.get("current_period_end"),
        onboarding_completed=user["onboarding_completed"],
        onboarding_step=user.get("onboarding_step"),
        current_genre=user.get("current_genre"),
        preferences=user.get("preferences", {}),
        story_bible=user.get("story_bible", {}),
        created_at=user["created_at"],
    )


@router.put("/preferences")
async def update_preferences(
    request: UpdatePreferencesRequest,
    user_id: str = Depends(get_current_user_id)
):
    """Update user's delivery and generation preferences."""
    user_service = UserService()

    updates = {}
    if request.story_length:
        updates["story_length"] = request.story_length
    if request.delivery_time:
        updates["delivery_time"] = request.delivery_time
    if request.timezone:
        updates["timezone"] = request.timezone
    if request.voice_id:
        updates["voice_id"] = request.voice_id
    if request.model_preference:
        updates["model_preference"] = request.model_preference

    if not updates:
        raise HTTPException(
            status_code=400,
            detail="No preferences provided to update"
        )

    try:
        updated = await user_service.update_preferences(user_id, updates)
        return {"status": "success", "preferences": updated.get("preferences", {})}
    except UserNotFoundError:
        raise HTTPException(status_code=404, detail="User not found")


@router.put("/story-bible")
async def update_story_bible(
    request: UpdateStoryBibleRequest,
    user_id: str = Depends(get_current_user_id)
):
    """
    Update user's story bible.

    This is typically called after Fixion finishes onboarding.
    """
    user_service = UserService()

    try:
        updated = await user_service.update_story_bible(user_id, request.story_bible)
        return {"status": "success", "story_bible": updated.get("story_bible", {})}
    except UserNotFoundError:
        raise HTTPException(status_code=404, detail="User not found")


@router.put("/genre")
async def set_genre(
    request: SetGenreRequest,
    user_id: str = Depends(get_current_user_id)
):
    """
    Set user's current genre and optionally protagonist.

    For genres that require character continuity (romance, etc.),
    the protagonist is stored for use in future stories.
    """
    user_service = UserService()

    try:
        updated = await user_service.set_current_genre(
            user_id,
            request.genre,
            request.protagonist
        )
        return {
            "status": "success",
            "genre": updated.get("current_genre"),
            "protagonist": updated.get("current_protagonist"),
        }
    except UserNotFoundError:
        raise HTTPException(status_code=404, detail="User not found")


# =============================================================================
# Onboarding Routes
# =============================================================================

@router.put("/onboarding")
async def update_onboarding(
    request: UpdateOnboardingRequest,
    user_id: str = Depends(get_current_user_id)
):
    """Update onboarding progress."""
    user_service = UserService()

    try:
        if request.completed:
            updated = await user_service.complete_onboarding(user_id)
        else:
            updated = await user_service.update_onboarding_step(user_id, request.step)

        return {
            "status": "success",
            "onboarding_step": updated.get("onboarding_step"),
            "onboarding_completed": updated.get("onboarding_completed"),
        }
    except UserNotFoundError:
        raise HTTPException(status_code=404, detail="User not found")


@router.post("/onboarding/complete")
async def complete_onboarding(user_id: str = Depends(get_current_user_id)):
    """Mark onboarding as complete."""
    user_service = UserService()

    try:
        updated = await user_service.complete_onboarding(user_id)
        return {
            "status": "success",
            "message": "Onboarding complete! Your first story will arrive soon.",
        }
    except UserNotFoundError:
        raise HTTPException(status_code=404, detail="User not found")


# =============================================================================
# Credits Routes
# =============================================================================

@router.get("/credits", response_model=CreditBalanceResponse)
async def get_credits(user: dict = Depends(get_current_user)):
    """Get current credit balance and subscription status."""
    return CreditBalanceResponse(
        credits=user["credits"],
        subscription_status=user["subscription_status"],
        subscription_tier=user.get("subscription_tier"),
    )


@router.get("/credits/transactions", response_model=List[CreditTransactionResponse])
async def get_credit_transactions(
    limit: int = 50,
    offset: int = 0,
    user_id: str = Depends(get_current_user_id)
):
    """Get credit transaction history."""
    credit_service = CreditService()

    transactions = await credit_service.get_transactions(
        user_id,
        limit=limit,
        offset=offset,
    )

    return [
        CreditTransactionResponse(
            id=t["id"],
            amount=t["amount"],
            balance_after=t["balance_after"],
            transaction_type=t["transaction_type"],
            description=t.get("description"),
            created_at=t["created_at"],
        )
        for t in transactions
    ]


@router.get("/credits/usage")
async def get_credit_usage(
    days: int = 30,
    user_id: str = Depends(get_current_user_id)
):
    """Get credit usage summary for a period."""
    credit_service = CreditService()

    summary = await credit_service.get_usage_summary(user_id, days=days)
    return summary


# =============================================================================
# Statistics Routes
# =============================================================================

@router.get("/stats", response_model=UserStatsResponse)
async def get_user_stats(user_id: str = Depends(get_current_user_id)):
    """Get user's story statistics."""
    story_service = StoryService()

    stats = await story_service.get_user_stats(user_id)
    return UserStatsResponse(**stats)


# =============================================================================
# Account Routes
# =============================================================================

@router.get("/subscription")
async def get_subscription(user: dict = Depends(get_current_user)):
    """Get subscription details."""
    return {
        "status": user["subscription_status"],
        "tier": user.get("subscription_tier"),
        "current_period_end": user.get("current_period_end"),
        "cancel_at_period_end": user.get("cancel_at_period_end", False),
        "stripe_customer_id": user.get("stripe_customer_id"),
    }


@router.delete("/account")
async def delete_account(user_id: str = Depends(get_current_user_id)):
    """
    Delete user account.

    This will:
    - Cancel any active subscription
    - Delete all stories
    - Delete user data

    This action is irreversible.
    """
    # Note: In a real implementation, you'd want:
    # 1. Confirmation step
    # 2. Cancel Stripe subscription
    # 3. Delete data from all tables
    # 4. Delete auth user from Supabase

    raise HTTPException(
        status_code=501,
        detail="Account deletion not yet implemented. Please contact support."
    )
