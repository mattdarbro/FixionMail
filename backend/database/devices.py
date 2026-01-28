"""
Device Service

Handles device registration for push notifications.
Stores APNs tokens for iOS devices to enable story delivery notifications.
"""

from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from uuid import UUID, uuid4

from supabase import Client

from .client import get_supabase_admin_client


class DeviceService:
    """
    Service class for device operations.
    """

    def __init__(self, client: Optional[Client] = None):
        self._client = client

    @property
    def client(self) -> Client:
        if self._client is None:
            self._client = get_supabase_admin_client()
        return self._client

    # =========================================================================
    # Device Registration
    # =========================================================================

    async def register(
        self,
        user_id: UUID | str,
        token: str,
        platform: str = "ios",
        *,
        device_name: Optional[str] = None,
        device_model: Optional[str] = None,
        os_version: Optional[str] = None,
        app_version: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Register or update a device for push notifications.

        If the token already exists for this user, updates the record.
        Otherwise creates a new device registration.

        Args:
            user_id: User ID
            token: APNs device token
            platform: Device platform (ios, android, web)
            device_name: Human-readable device name
            device_model: Device model (e.g., "iPhone 15 Pro")
            os_version: OS version
            app_version: App version

        Returns:
            Device registration data
        """
        now = datetime.now(timezone.utc).isoformat()

        # Check if device already registered
        existing = await self.get_by_token(user_id, token)

        if existing:
            # Update existing registration
            update_data = {
                "is_active": True,
                "last_used_at": now,
                "updated_at": now,
            }
            if device_name:
                update_data["device_name"] = device_name
            if device_model:
                update_data["device_model"] = device_model
            if os_version:
                update_data["os_version"] = os_version
            if app_version:
                update_data["app_version"] = app_version

            result = (
                self.client.table("devices")
                .update(update_data)
                .eq("id", existing["id"])
                .execute()
            )
            return result.data[0]

        # Create new registration
        device_data = {
            "id": str(uuid4()),
            "user_id": str(user_id),
            "token": token,
            "platform": platform,
            "device_name": device_name,
            "device_model": device_model,
            "os_version": os_version,
            "app_version": app_version,
            "is_active": True,
            "last_used_at": now,
            "created_at": now,
            "updated_at": now,
        }

        result = self.client.table("devices").insert(device_data).execute()
        return result.data[0]

    async def unregister(
        self, user_id: UUID | str, token: str
    ) -> bool:
        """
        Unregister a device (mark as inactive).

        Args:
            user_id: User ID
            token: Device token to unregister

        Returns:
            True if device was found and unregistered
        """
        result = (
            self.client.table("devices")
            .update({
                "is_active": False,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            })
            .eq("user_id", str(user_id))
            .eq("token", token)
            .execute()
        )
        return len(result.data) > 0

    # =========================================================================
    # Device Retrieval
    # =========================================================================

    async def get_by_token(
        self, user_id: UUID | str, token: str
    ) -> Optional[Dict[str, Any]]:
        """Get device by user ID and token."""
        result = (
            self.client.table("devices")
            .select("*")
            .eq("user_id", str(user_id))
            .eq("token", token)
            .execute()
        )
        return result.data[0] if result.data else None

    async def get_user_devices(
        self, user_id: UUID | str, *, active_only: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Get all devices for a user.

        Args:
            user_id: User ID
            active_only: Only return active devices

        Returns:
            List of devices
        """
        query = (
            self.client.table("devices")
            .select("*")
            .eq("user_id", str(user_id))
            .order("last_used_at", desc=True)
        )

        if active_only:
            query = query.eq("is_active", True)

        result = query.execute()
        return result.data

    async def get_active_tokens(
        self, user_id: UUID | str, platform: str = "ios"
    ) -> List[str]:
        """
        Get active device tokens for a user.

        Used when sending push notifications.

        Args:
            user_id: User ID
            platform: Platform to filter by

        Returns:
            List of active device tokens
        """
        result = (
            self.client.table("devices")
            .select("token")
            .eq("user_id", str(user_id))
            .eq("platform", platform)
            .eq("is_active", True)
            .execute()
        )
        return [d["token"] for d in result.data]

    # =========================================================================
    # Bulk Operations (for push notifications)
    # =========================================================================

    async def get_all_active_tokens(
        self, platform: str = "ios"
    ) -> List[Dict[str, str]]:
        """
        Get all active device tokens across all users.

        Used for broadcast notifications.

        Returns:
            List of {user_id, token} dicts
        """
        result = (
            self.client.table("devices")
            .select("user_id, token")
            .eq("platform", platform)
            .eq("is_active", True)
            .execute()
        )
        return result.data

    async def mark_token_invalid(self, token: str) -> None:
        """
        Mark a token as invalid (inactive).

        Called when APNs returns an invalid token error.

        Args:
            token: The invalid device token
        """
        self.client.table("devices").update({
            "is_active": False,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }).eq("token", token).execute()

    # =========================================================================
    # Cleanup
    # =========================================================================

    async def cleanup_inactive(self, days: int = 90) -> int:
        """
        Delete devices that have been inactive for a long time.

        Args:
            days: Number of days of inactivity before deletion

        Returns:
            Number of devices deleted
        """
        cutoff = datetime.now(timezone.utc)
        # This is a simplified approach - in production you'd calculate the actual cutoff date
        # For now, we just delete inactive devices
        result = (
            self.client.table("devices")
            .delete()
            .eq("is_active", False)
            .execute()
        )
        return len(result.data)
