"""
Device Registration API Routes

Endpoints for registering devices for push notifications.
Supports iOS APNs tokens for story delivery notifications.
"""

from typing import Optional, List

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

from backend.database.devices import DeviceService
from backend.routes.auth import get_current_user_id


router = APIRouter(prefix="/api/devices", tags=["devices"])


# =============================================================================
# Request/Response Models
# =============================================================================

class RegisterDeviceRequest(BaseModel):
    """Request to register a device for push notifications."""
    token: str = Field(..., description="APNs device token")
    platform: str = Field(default="ios", description="Device platform: ios, android, web")
    device_name: Optional[str] = Field(None, description="Human-readable device name")
    device_model: Optional[str] = Field(None, description="Device model (e.g., iPhone 15 Pro)")
    os_version: Optional[str] = Field(None, description="OS version")
    app_version: Optional[str] = Field(None, description="App version")


class RegisterDeviceResponse(BaseModel):
    """Response after device registration."""
    registered: bool
    device_id: str
    message: str


class DeviceResponse(BaseModel):
    """Device information."""
    id: str
    token: str
    platform: str
    device_name: Optional[str] = None
    device_model: Optional[str] = None
    os_version: Optional[str] = None
    app_version: Optional[str] = None
    is_active: bool
    last_used_at: str
    created_at: str


class DeviceListResponse(BaseModel):
    """List of registered devices."""
    devices: List[DeviceResponse]
    total: int


class UnregisterDeviceRequest(BaseModel):
    """Request to unregister a device."""
    token: str = Field(..., description="Device token to unregister")


# =============================================================================
# Device Registration Endpoints
# =============================================================================

@router.post("", response_model=RegisterDeviceResponse)
async def register_device(
    request: RegisterDeviceRequest,
    user_id: str = Depends(get_current_user_id)
):
    """
    Register a device for push notifications.

    If the device token is already registered, updates the existing record.
    This endpoint should be called on app launch and when the token changes.
    """
    device_service = DeviceService()

    device = await device_service.register(
        user_id=user_id,
        token=request.token,
        platform=request.platform,
        device_name=request.device_name,
        device_model=request.device_model,
        os_version=request.os_version,
        app_version=request.app_version,
    )

    return RegisterDeviceResponse(
        registered=True,
        device_id=device["id"],
        message="Device registered for push notifications",
    )


@router.delete("")
async def unregister_device(
    request: UnregisterDeviceRequest,
    user_id: str = Depends(get_current_user_id)
):
    """
    Unregister a device from push notifications.

    Call this when the user logs out or disables notifications.
    """
    device_service = DeviceService()

    success = await device_service.unregister(user_id, request.token)

    if not success:
        return {"success": False, "message": "Device not found"}

    return {"success": True, "message": "Device unregistered"}


@router.get("", response_model=DeviceListResponse)
async def list_devices(
    user_id: str = Depends(get_current_user_id)
):
    """
    List all registered devices for the current user.

    Shows active and inactive devices.
    """
    device_service = DeviceService()

    devices = await device_service.get_user_devices(user_id, active_only=False)

    return DeviceListResponse(
        devices=[
            DeviceResponse(
                id=d["id"],
                token=d["token"],
                platform=d["platform"],
                device_name=d.get("device_name"),
                device_model=d.get("device_model"),
                os_version=d.get("os_version"),
                app_version=d.get("app_version"),
                is_active=d["is_active"],
                last_used_at=d["last_used_at"],
                created_at=d["created_at"],
            )
            for d in devices
        ],
        total=len(devices),
    )
