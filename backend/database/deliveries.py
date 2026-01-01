"""
Delivery Service

Handles scheduled email delivery operations using Supabase.
Decouples story generation from email delivery timing.
"""

from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List
from uuid import UUID
from enum import Enum

from supabase import Client

from .client import get_supabase_admin_client


class DeliveryStatus(str, Enum):
    """Status values for scheduled deliveries"""
    PENDING = "pending"
    SENDING = "sending"
    SENT = "sent"
    FAILED = "failed"


class DeliveryService:
    """
    Service for managing scheduled email deliveries.

    Deliveries are created after story generation completes,
    with deliver_at set to user's preferred delivery time.
    A separate worker sends emails when deliver_at is reached.
    """

    def __init__(self, client: Optional[Client] = None):
        self._client = client

    @property
    def client(self) -> Client:
        if self._client is None:
            self._client = get_supabase_admin_client()
        return self._client

    # =========================================================================
    # Scheduling Deliveries
    # =========================================================================

    async def schedule_delivery(
        self,
        story_id: str | UUID,
        user_id: str | UUID,
        user_email: str,
        deliver_at: datetime,
        timezone_str: str = "UTC"
    ) -> Dict[str, Any]:
        """
        Schedule a story for email delivery at a specific time.

        Args:
            story_id: ID of the completed story
            user_id: User's ID
            user_email: Email address for delivery
            deliver_at: When to send the email (should be in UTC)
            timezone_str: User's timezone for reference

        Returns:
            Created delivery record
        """
        delivery_data = {
            "story_id": str(story_id),
            "user_id": str(user_id),
            "user_email": user_email,
            "deliver_at": deliver_at.isoformat(),
            "timezone": timezone_str,
            "status": DeliveryStatus.PENDING.value,
        }

        result = self.client.table("scheduled_deliveries").insert(delivery_data).execute()
        return result.data[0]

    # =========================================================================
    # Worker Queries
    # =========================================================================

    async def get_due_deliveries(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get deliveries that are due to be sent.

        Returns pending deliveries where deliver_at <= now.
        """
        now = datetime.now(timezone.utc).isoformat()

        result = (
            self.client.table("scheduled_deliveries")
            .select("*, stories(*)")  # Join with stories to get content
            .eq("status", DeliveryStatus.PENDING.value)
            .lte("deliver_at", now)
            .order("deliver_at")
            .limit(limit)
            .execute()
        )
        return result.data

    async def mark_sending(self, delivery_id: str | UUID) -> Dict[str, Any]:
        """Mark a delivery as currently being sent (prevents duplicate sends)."""
        result = (
            self.client.table("scheduled_deliveries")
            .update({
                "status": DeliveryStatus.SENDING.value,
                "updated_at": datetime.now(timezone.utc).isoformat()
            })
            .eq("id", str(delivery_id))
            .execute()
        )
        return result.data[0] if result.data else None

    async def mark_sent(
        self,
        delivery_id: str | UUID,
        resend_email_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Mark a delivery as successfully sent."""
        result = (
            self.client.table("scheduled_deliveries")
            .update({
                "status": DeliveryStatus.SENT.value,
                "sent_at": datetime.now(timezone.utc).isoformat(),
                "resend_email_id": resend_email_id,
                "updated_at": datetime.now(timezone.utc).isoformat()
            })
            .eq("id", str(delivery_id))
            .execute()
        )
        return result.data[0] if result.data else None

    async def mark_failed(
        self,
        delivery_id: str | UUID,
        error_message: str,
        should_retry: bool = True
    ) -> Dict[str, Any]:
        """Mark a delivery as failed."""
        # Get current retry count
        current = (
            self.client.table("scheduled_deliveries")
            .select("retry_count")
            .eq("id", str(delivery_id))
            .single()
            .execute()
        )
        retry_count = (current.data.get("retry_count", 0) if current.data else 0) + 1

        # If should retry and under limit, set back to pending
        # Otherwise mark as permanently failed
        max_retries = 3
        new_status = DeliveryStatus.PENDING.value if (should_retry and retry_count < max_retries) else DeliveryStatus.FAILED.value

        result = (
            self.client.table("scheduled_deliveries")
            .update({
                "status": new_status,
                "error_message": error_message,
                "retry_count": retry_count,
                "updated_at": datetime.now(timezone.utc).isoformat()
            })
            .eq("id", str(delivery_id))
            .execute()
        )
        return result.data[0] if result.data else None

    # =========================================================================
    # Query Methods
    # =========================================================================

    async def get_delivery_by_id(self, delivery_id: str | UUID) -> Optional[Dict[str, Any]]:
        """Get a delivery by ID with story details."""
        result = (
            self.client.table("scheduled_deliveries")
            .select("*, stories(*)")
            .eq("id", str(delivery_id))
            .single()
            .execute()
        )
        return result.data

    async def get_user_deliveries(
        self,
        user_id: str | UUID,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Get delivery history for a user."""
        result = (
            self.client.table("scheduled_deliveries")
            .select("*, stories(id, title, genre)")
            .eq("user_id", str(user_id))
            .order("deliver_at", desc=True)
            .limit(limit)
            .execute()
        )
        return result.data

    async def get_user_next_delivery(
        self,
        user_id: str | UUID
    ) -> Optional[Dict[str, Any]]:
        """
        Get the user's next pending delivery (if any).

        Returns the soonest pending delivery with story details.
        """
        result = (
            self.client.table("scheduled_deliveries")
            .select("id, deliver_at, timezone, status, stories(id, title, genre)")
            .eq("user_id", str(user_id))
            .eq("status", DeliveryStatus.PENDING.value)
            .order("deliver_at")
            .limit(1)
            .execute()
        )
        return result.data[0] if result.data else None

    async def get_upcoming_deliveries(
        self,
        hours_ahead: int = 24,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get upcoming deliveries within the next N hours (for dashboard)."""
        now = datetime.now(timezone.utc)
        future = (now + timedelta(hours=hours_ahead)).isoformat()

        result = (
            self.client.table("scheduled_deliveries")
            .select("*, stories(id, title, genre, word_count)")
            .eq("status", DeliveryStatus.PENDING.value)
            .gte("deliver_at", now.isoformat())
            .lte("deliver_at", future)
            .order("deliver_at")
            .limit(limit)
            .execute()
        )
        return result.data

    async def get_failed_deliveries(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get failed deliveries for debugging."""
        result = (
            self.client.table("scheduled_deliveries")
            .select("*, stories(id, title, genre)")
            .eq("status", DeliveryStatus.FAILED.value)
            .order("updated_at", desc=True)
            .limit(limit)
            .execute()
        )
        return result.data

    # =========================================================================
    # Dashboard/Admin Queries
    # =========================================================================

    async def get_delivery_stats(self) -> Dict[str, Any]:
        """Get delivery statistics for dashboard."""
        stats = {
            "pending": 0,
            "sending": 0,
            "sent_today": 0,
            "failed": 0,
            "upcoming_1h": 0,
            "upcoming_24h": 0,
        }

        # Count by status
        for status in [DeliveryStatus.PENDING, DeliveryStatus.SENDING, DeliveryStatus.FAILED]:
            result = (
                self.client.table("scheduled_deliveries")
                .select("id", count="exact")
                .eq("status", status.value)
                .execute()
            )
            stats[status.value] = result.count or 0

        # Sent today
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        sent_today = (
            self.client.table("scheduled_deliveries")
            .select("id", count="exact")
            .eq("status", DeliveryStatus.SENT.value)
            .gte("sent_at", f"{today}T00:00:00")
            .execute()
        )
        stats["sent_today"] = sent_today.count or 0

        # Upcoming counts
        now = datetime.now(timezone.utc)
        hour_from_now = (now + timedelta(hours=1)).isoformat()
        day_from_now = (now + timedelta(hours=24)).isoformat()

        upcoming_1h = (
            self.client.table("scheduled_deliveries")
            .select("id", count="exact")
            .eq("status", DeliveryStatus.PENDING.value)
            .lte("deliver_at", hour_from_now)
            .execute()
        )
        stats["upcoming_1h"] = upcoming_1h.count or 0

        upcoming_24h = (
            self.client.table("scheduled_deliveries")
            .select("id", count="exact")
            .eq("status", DeliveryStatus.PENDING.value)
            .lte("deliver_at", day_from_now)
            .execute()
        )
        stats["upcoming_24h"] = upcoming_24h.count or 0

        return stats

    async def get_delivery_schedule(
        self,
        status: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get delivery schedule for dashboard."""
        query = (
            self.client.table("scheduled_deliveries")
            .select("id, user_email, deliver_at, timezone, status, sent_at, error_message, retry_count, created_at, stories(id, title, genre, word_count)")
            .order("deliver_at", desc=False)
            .limit(limit)
        )

        if status:
            query = query.eq("status", status)
        else:
            # Default: show pending and recent sent/failed
            query = query.in_("status", [DeliveryStatus.PENDING.value, DeliveryStatus.SENDING.value])

        result = query.execute()
        return result.data
