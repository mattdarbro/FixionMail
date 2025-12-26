"""
User Service

Handles all user-related database operations including profile management,
subscription status, and preferences.
"""

from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from uuid import UUID

from supabase import Client

from .client import get_supabase_admin_client


class UserNotFoundError(Exception):
    """Raised when a user is not found in the database."""
    pass


class UserService:
    """
    Service class for user operations.

    Uses admin client by default for server-side operations.
    For user-facing operations with RLS, pass a user-authenticated client.
    """

    def __init__(self, client: Optional[Client] = None):
        """
        Initialize UserService.

        Args:
            client: Supabase client. If None, uses admin client.
        """
        self._client = client

    @property
    def client(self) -> Client:
        """Get the Supabase client, defaulting to admin client."""
        if self._client is None:
            self._client = get_supabase_admin_client()
        return self._client

    # =========================================================================
    # User Retrieval
    # =========================================================================

    async def get_by_id(self, user_id: UUID | str) -> Optional[Dict[str, Any]]:
        """Get user by ID."""
        result = self.client.table("users").select("*").eq("id", str(user_id)).execute()
        return result.data[0] if result.data else None

    async def get_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user by email."""
        result = self.client.table("users").select("*").eq("email", email).execute()
        return result.data[0] if result.data else None

    async def get_by_stripe_customer(self, stripe_customer_id: str) -> Optional[Dict[str, Any]]:
        """Get user by Stripe customer ID."""
        result = (
            self.client.table("users")
            .select("*")
            .eq("stripe_customer_id", stripe_customer_id)
            .execute()
        )
        return result.data[0] if result.data else None

    # =========================================================================
    # User Updates
    # =========================================================================

    async def update(self, user_id: UUID | str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update user fields.

        Args:
            user_id: User ID
            data: Dictionary of fields to update

        Returns:
            Updated user data
        """
        # Filter out None values and add updated_at
        update_data = {k: v for k, v in data.items() if v is not None}
        update_data["updated_at"] = datetime.now(timezone.utc).isoformat()

        result = (
            self.client.table("users")
            .update(update_data)
            .eq("id", str(user_id))
            .execute()
        )

        if not result.data:
            raise UserNotFoundError(f"User {user_id} not found")

        return result.data[0]

    async def update_story_bible(
        self, user_id: UUID | str, story_bible: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update user's story bible (Fixion-built preferences)."""
        return await self.update(user_id, {"story_bible": story_bible})

    async def update_preferences(
        self, user_id: UUID | str, preferences: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update user's delivery preferences."""
        # Merge with existing preferences
        user = await self.get_by_id(user_id)
        if not user:
            raise UserNotFoundError(f"User {user_id} not found")

        current_prefs = user.get("preferences", {})
        merged_prefs = {**current_prefs, **preferences}

        return await self.update(user_id, {"preferences": merged_prefs})

    async def set_current_genre(
        self,
        user_id: UUID | str,
        genre: str,
        protagonist: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Set user's current genre and optionally protagonist."""
        update_data = {"current_genre": genre}
        if protagonist is not None:
            update_data["current_protagonist"] = protagonist
        return await self.update(user_id, update_data)

    async def complete_onboarding(self, user_id: UUID | str) -> Dict[str, Any]:
        """Mark user's onboarding as complete."""
        return await self.update(user_id, {
            "onboarding_completed": True,
            "onboarding_step": "complete"
        })

    async def update_onboarding_step(
        self, user_id: UUID | str, step: str
    ) -> Dict[str, Any]:
        """Update user's current onboarding step."""
        return await self.update(user_id, {"onboarding_step": step})

    # =========================================================================
    # Subscription Management
    # =========================================================================

    async def update_subscription(
        self,
        user_id: UUID | str,
        *,
        status: str,
        tier: Optional[str] = None,
        stripe_customer_id: Optional[str] = None,
        stripe_subscription_id: Optional[str] = None,
        current_period_start: Optional[datetime] = None,
        current_period_end: Optional[datetime] = None,
        cancel_at_period_end: bool = False,
    ) -> Dict[str, Any]:
        """
        Update subscription information.

        Called by Stripe webhook handlers.
        """
        update_data = {
            "subscription_status": status,
            "cancel_at_period_end": cancel_at_period_end,
        }

        if tier is not None:
            update_data["subscription_tier"] = tier
        if stripe_customer_id is not None:
            update_data["stripe_customer_id"] = stripe_customer_id
        if stripe_subscription_id is not None:
            update_data["stripe_subscription_id"] = stripe_subscription_id
        if current_period_start is not None:
            update_data["current_period_start"] = current_period_start.isoformat()
        if current_period_end is not None:
            update_data["current_period_end"] = current_period_end.isoformat()

        return await self.update(user_id, update_data)

    async def cancel_subscription(self, user_id: UUID | str) -> Dict[str, Any]:
        """Mark subscription as cancelled."""
        return await self.update(user_id, {
            "subscription_status": "cancelled",
            "cancel_at_period_end": True,
        })

    # =========================================================================
    # Credits
    # =========================================================================

    async def get_credits(self, user_id: UUID | str) -> int:
        """Get user's current credit balance."""
        user = await self.get_by_id(user_id)
        if not user:
            raise UserNotFoundError(f"User {user_id} not found")
        return user.get("credits", 0)

    async def has_credits(self, user_id: UUID | str, amount: int = 1) -> bool:
        """Check if user has sufficient credits."""
        credits = await self.get_credits(user_id)
        return credits >= amount

    # =========================================================================
    # Activity Tracking
    # =========================================================================

    async def record_story_delivery(self, user_id: UUID | str) -> Dict[str, Any]:
        """Record that a story was delivered to the user."""
        return await self.update(user_id, {
            "last_story_at": datetime.now(timezone.utc).isoformat()
        })

    async def record_login(self, user_id: UUID | str) -> Dict[str, Any]:
        """Record user login."""
        return await self.update(user_id, {
            "last_login_at": datetime.now(timezone.utc).isoformat()
        })

    # =========================================================================
    # Queries
    # =========================================================================

    async def get_active_subscribers(self) -> List[Dict[str, Any]]:
        """Get all users with active subscriptions."""
        result = (
            self.client.table("users")
            .select("*")
            .eq("subscription_status", "active")
            .execute()
        )
        return result.data

    async def get_users_needing_story(
        self, before_time: datetime
    ) -> List[Dict[str, Any]]:
        """
        Get users who should receive a story.

        Args:
            before_time: Only return users whose scheduled delivery time is before this

        Returns:
            List of users who need stories generated
        """
        # This will be used by the story scheduler
        # For now, get all active users who haven't received a story today
        result = (
            self.client.table("users")
            .select("*")
            .in_("subscription_status", ["active", "trial"])
            .eq("onboarding_completed", True)
            .execute()
        )
        return result.data

    async def get_trial_users_expiring(self, days: int = 3) -> List[Dict[str, Any]]:
        """Get trial users whose credits are running low."""
        result = (
            self.client.table("users")
            .select("*")
            .eq("subscription_status", "trial")
            .lte("credits", days)
            .execute()
        )
        return result.data
