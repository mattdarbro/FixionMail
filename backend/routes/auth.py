"""
Authentication Routes

Handles Supabase Auth operations including magic link login,
session management, and user profile access.
"""

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, Header, Request
from pydantic import BaseModel, EmailStr

from backend.config import config
from backend.database.client import get_supabase_admin_client, SupabaseClientError
from backend.database.users import UserService

router = APIRouter(prefix="/api/auth", tags=["authentication"])


# =============================================================================
# Request/Response Models
# =============================================================================

class MagicLinkRequest(BaseModel):
    """Request to send a magic link email."""
    email: EmailStr


class MagicLinkResponse(BaseModel):
    """Response after sending magic link."""
    message: str
    email: str


class SessionResponse(BaseModel):
    """Response with session information."""
    user_id: str
    email: str
    access_token: str
    refresh_token: str
    expires_at: int


class UserResponse(BaseModel):
    """Response with user profile data."""
    id: str
    email: str
    credits: int
    subscription_status: str
    subscription_tier: Optional[str]
    onboarding_completed: bool
    current_genre: Optional[str]
    created_at: str


class RefreshTokenRequest(BaseModel):
    """Request to refresh access token."""
    refresh_token: str


# =============================================================================
# Dependencies
# =============================================================================

async def get_current_user_id(
    authorization: Optional[str] = Header(None, alias="Authorization")
) -> str:
    """
    Extract and verify user ID from Authorization header.

    In dev mode with DEV_MODE=true, allows bypass for testing.
    """
    # Dev mode bypass
    if config.DEV_MODE and not authorization:
        # Return a test user ID for development
        return "dev-user-id"

    if not authorization:
        raise HTTPException(
            status_code=401,
            detail="Authorization header required"
        )

    # Extract token from "Bearer <token>" format
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=401,
            detail="Invalid authorization header format. Use 'Bearer <token>'"
        )

    token = parts[1]

    try:
        # Verify token with Supabase
        client = get_supabase_admin_client()
        user_response = client.auth.get_user(token)

        if not user_response or not user_response.user:
            raise HTTPException(
                status_code=401,
                detail="Invalid or expired token"
            )

        return str(user_response.user.id)

    except SupabaseClientError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Authentication service unavailable: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=401,
            detail=f"Token verification failed: {str(e)}"
        )


async def get_current_user(
    user_id: str = Depends(get_current_user_id)
) -> dict:
    """
    Get current user's full profile data.
    """
    user_service = UserService()
    user = await user_service.get_by_id(user_id)

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User profile not found"
        )

    return user


# =============================================================================
# Routes
# =============================================================================

@router.post("/magic-link", response_model=MagicLinkResponse)
async def send_magic_link(request: MagicLinkRequest):
    """
    Send a magic link email for passwordless login.

    The user will receive an email with a link to complete authentication.
    """
    if not config.supabase_configured:
        raise HTTPException(
            status_code=503,
            detail="Authentication service not configured"
        )

    try:
        client = get_supabase_admin_client()

        # Send magic link via Supabase Auth
        response = client.auth.sign_in_with_otp({
            "email": request.email,
            "options": {
                "email_redirect_to": f"{config.APP_BASE_URL}/auth/callback"
            }
        })

        return MagicLinkResponse(
            message="Magic link sent! Check your email.",
            email=request.email
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to send magic link: {str(e)}"
        )


@router.post("/verify", response_model=SessionResponse)
async def verify_otp(request: Request):
    """
    Verify OTP token from magic link and return session.

    This endpoint is called after the user clicks the magic link.
    The token_hash and type are extracted from the URL parameters.
    """
    if not config.supabase_configured:
        raise HTTPException(
            status_code=503,
            detail="Authentication service not configured"
        )

    try:
        body = await request.json()
        token_hash = body.get("token_hash")
        token_type = body.get("type", "magiclink")

        if not token_hash:
            raise HTTPException(
                status_code=400,
                detail="token_hash is required"
            )

        client = get_supabase_admin_client()

        # Verify the OTP
        response = client.auth.verify_otp({
            "token_hash": token_hash,
            "type": token_type
        })

        if not response.session:
            raise HTTPException(
                status_code=401,
                detail="Invalid or expired magic link"
            )

        session = response.session
        user = response.user

        # Update last login
        user_service = UserService()
        await user_service.record_login(user.id)

        return SessionResponse(
            user_id=str(user.id),
            email=user.email,
            access_token=session.access_token,
            refresh_token=session.refresh_token,
            expires_at=session.expires_at
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Verification failed: {str(e)}"
        )


@router.post("/refresh", response_model=SessionResponse)
async def refresh_session(request: RefreshTokenRequest):
    """
    Refresh an expired access token using a refresh token.
    """
    if not config.supabase_configured:
        raise HTTPException(
            status_code=503,
            detail="Authentication service not configured"
        )

    try:
        client = get_supabase_admin_client()

        response = client.auth.refresh_session(request.refresh_token)

        if not response.session:
            raise HTTPException(
                status_code=401,
                detail="Invalid or expired refresh token"
            )

        session = response.session
        user = response.user

        return SessionResponse(
            user_id=str(user.id),
            email=user.email,
            access_token=session.access_token,
            refresh_token=session.refresh_token,
            expires_at=session.expires_at
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=401,
            detail=f"Token refresh failed: {str(e)}"
        )


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(user: dict = Depends(get_current_user)):
    """
    Get the current authenticated user's profile.
    """
    return UserResponse(
        id=user["id"],
        email=user["email"],
        credits=user["credits"],
        subscription_status=user["subscription_status"],
        subscription_tier=user.get("subscription_tier"),
        onboarding_completed=user["onboarding_completed"],
        current_genre=user.get("current_genre"),
        created_at=user["created_at"]
    )


@router.post("/logout")
async def logout(
    authorization: Optional[str] = Header(None, alias="Authorization")
):
    """
    Log out the current user by invalidating their session.
    """
    if not authorization:
        return {"message": "Already logged out"}

    try:
        parts = authorization.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            return {"message": "Already logged out"}

        token = parts[1]
        client = get_supabase_admin_client()

        # Sign out the user
        client.auth.sign_out()

        return {"message": "Successfully logged out"}

    except Exception:
        # Even if signout fails, return success
        return {"message": "Logged out"}


# =============================================================================
# Health Check
# =============================================================================

@router.get("/health")
async def auth_health():
    """
    Check if authentication service is healthy.
    """
    return {
        "status": "healthy" if config.supabase_configured else "not_configured",
        "supabase_url": config.SUPABASE_URL[:30] + "..." if config.SUPABASE_URL else None,
    }
