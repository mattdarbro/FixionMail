"""
User Management Routes

Handles user profile updates, preferences, story bible management,
and account information.
"""

import os
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


# =============================================================================
# Upgrade Routes (Temporary - will be replaced with Stripe integration)
# =============================================================================

# =============================================================================
# iOS App Preferences
# =============================================================================

class iOSPreferencesResponse(BaseModel):
    """Full preferences response for iOS app."""
    genres: List[str]
    themes: List[str]
    length: str
    tone: str
    boundaries: Dict[str, bool]
    schedule: Dict[str, Any]
    variation: Dict[str, Any]


class UpdateScheduleRequest(BaseModel):
    """Request to update schedule preferences."""
    frequency: Optional[str] = None  # daily, every_3_days, weekly, manual
    preferred_time: Optional[str] = None  # HH:MM
    timezone: Optional[str] = None
    paused: Optional[bool] = None


class UpdateVariationRequest(BaseModel):
    """Request to update story variation settings."""
    variation_tolerance: Optional[str] = None  # low, medium, high
    xion_experiments: Optional[str] = None  # never, rare, occasional, frequent
    fifi_enabled: Optional[bool] = None


@router.get("/preferences/ios", response_model=iOSPreferencesResponse)
async def get_ios_preferences(user: dict = Depends(get_current_user)):
    """
    Get full preferences for iOS app.

    Returns all user preferences in iOS app format.
    """
    story_bible = user.get("story_bible", {})
    prefs = user.get("preferences", {})

    return iOSPreferencesResponse(
        genres=story_bible.get("genres", [user.get("current_genre", "mystery")]),
        themes=story_bible.get("themes", []),
        length=prefs.get("story_length", "medium"),
        tone=story_bible.get("tone", "thoughtful"),
        boundaries={
            "no_graphic_violence": story_bible.get("no_graphic_violence", True),
            "no_explicit_content": story_bible.get("no_explicit_content", True),
        },
        schedule={
            "frequency": prefs.get("frequency", "daily"),
            "preferred_time": prefs.get("delivery_time", "08:00"),
            "timezone": prefs.get("timezone", "UTC"),
            "paused": prefs.get("paused", False),
        },
        variation={
            "variation_tolerance": user.get("variation_tolerance", "medium"),
            "xion_experiments": user.get("xion_experiments", "occasional"),
            "fifi_enabled": user.get("fifi_enabled", True),
        },
    )


@router.put("/preferences/ios")
async def update_ios_preferences(
    genres: Optional[List[str]] = None,
    themes: Optional[List[str]] = None,
    length: Optional[str] = None,
    tone: Optional[str] = None,
    user_id: str = Depends(get_current_user_id)
):
    """
    Update iOS app preferences (partial update).

    For schedule and variation settings, use dedicated endpoints.
    """
    user_service = UserService()

    try:
        user = await user_service.get_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Update story bible
        story_bible = user.get("story_bible", {})
        if genres is not None:
            story_bible["genres"] = genres
        if themes is not None:
            story_bible["themes"] = themes
        if tone is not None:
            story_bible["tone"] = tone

        await user_service.update_story_bible(user_id, story_bible)

        # Update preferences
        if length is not None:
            await user_service.update_preferences(user_id, {"story_length": length})

        return {"updated": True, "message": "Preferences updated"}

    except UserNotFoundError:
        raise HTTPException(status_code=404, detail="User not found")


@router.put("/preferences/schedule")
async def update_schedule_preferences(
    request: UpdateScheduleRequest,
    user_id: str = Depends(get_current_user_id)
):
    """
    Update story delivery schedule preferences.
    """
    user_service = UserService()

    updates = {}
    if request.frequency is not None:
        updates["frequency"] = request.frequency
    if request.preferred_time is not None:
        updates["delivery_time"] = request.preferred_time
    if request.timezone is not None:
        updates["timezone"] = request.timezone
    if request.paused is not None:
        updates["paused"] = request.paused

    if not updates:
        raise HTTPException(
            status_code=400,
            detail="No schedule preferences provided"
        )

    try:
        await user_service.update_preferences(user_id, updates)
        return {"updated": True, "schedule": updates}
    except UserNotFoundError:
        raise HTTPException(status_code=404, detail="User not found")


@router.put("/preferences/variation")
async def update_variation_preferences(
    request: UpdateVariationRequest,
    user_id: str = Depends(get_current_user_id)
):
    """
    Update story variation settings.

    Controls how much variety is introduced into stories:
    - variation_tolerance: How much drift from preferences (low/medium/high)
    - xion_experiments: How often Xion's experiments appear (never/rare/occasional/frequent)
    - fifi_enabled: Whether Fifi's happy accidents can occur
    """
    user_service = UserService()

    updates = {}
    if request.variation_tolerance is not None:
        if request.variation_tolerance not in ["low", "medium", "high"]:
            raise HTTPException(
                status_code=400,
                detail="variation_tolerance must be low, medium, or high"
            )
        updates["variation_tolerance"] = request.variation_tolerance

    if request.xion_experiments is not None:
        if request.xion_experiments not in ["never", "rare", "occasional", "frequent"]:
            raise HTTPException(
                status_code=400,
                detail="xion_experiments must be never, rare, occasional, or frequent"
            )
        updates["xion_experiments"] = request.xion_experiments

    if request.fifi_enabled is not None:
        updates["fifi_enabled"] = request.fifi_enabled

    if not updates:
        raise HTTPException(
            status_code=400,
            detail="No variation preferences provided"
        )

    try:
        await user_service.update(user_id, updates)
        return {"updated": True, "variation": updates}
    except UserNotFoundError:
        raise HTTPException(status_code=404, detail="User not found")


# =============================================================================
# Upgrade Routes (Temporary - will be replaced with Stripe integration)
# =============================================================================

class UpgradeRequest(BaseModel):
    """Request to upgrade with access code."""
    access_code: str


# Temporary upgrade code - change this to something secret!
UPGRADE_ACCESS_CODE = os.getenv("UPGRADE_ACCESS_CODE", "FIXION2024")


@router.post("/upgrade-to-premium")
async def upgrade_to_premium(
    request: UpgradeRequest,
    user: dict = Depends(get_current_user),
    user_id: str = Depends(get_current_user_id)
):
    """
    Upgrade user from trial to premium with access code.

    This is a temporary endpoint for testing. In production, this will be
    replaced with proper Stripe payment integration.

    Requires a valid access code to prevent unauthorized upgrades.
    """
    # Verify access code
    if request.access_code != UPGRADE_ACCESS_CODE:
        raise HTTPException(
            status_code=403,
            detail="Invalid access code"
        )

    if user["subscription_status"] == "active":
        raise HTTPException(
            status_code=400,
            detail="You already have an active subscription"
        )

    user_service = UserService()
    credit_service = CreditService()

    # Update subscription status to active
    await user_service.update_subscription(
        user_id,
        status="active",
        tier="monthly",
    )

    # Add 30 credits for the month
    await credit_service.add_credits(
        user_id,
        amount=30,
        transaction_type="subscription",
        description="Premium subscription - 30 monthly credits"
    )

    return {
        "status": "success",
        "message": "Upgraded to premium! You now have 30 credits per month.",
        "subscription_status": "active",
        "subscription_tier": "monthly",
    }
