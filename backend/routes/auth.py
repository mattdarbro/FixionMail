"""
Authentication Routes

Handles Supabase Auth operations including magic link login,
email/password auth, Apple Sign-in, session management, and user profile access.

Supports:
- Magic link (passwordless) authentication
- Email/password registration and login
- Apple Sign-in (for iOS app)
- Token refresh
- Session management
"""

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, Header, Request
from pydantic import BaseModel, EmailStr, Field

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


# -----------------------------------------------------------------------------
# iOS App Authentication Models
# -----------------------------------------------------------------------------

class RegisterRequest(BaseModel):
    """Request to register a new account with email/password."""
    email: EmailStr
    password: str = Field(..., min_length=8, description="Password must be at least 8 characters")


class RegisterResponse(BaseModel):
    """Response after registration."""
    user_id: str
    email: str
    access_token: str
    refresh_token: str
    expires_at: int
    created: bool = True


class LoginRequest(BaseModel):
    """Request to login with email/password."""
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    """Response after successful login."""
    user_id: str
    email: str
    access_token: str
    refresh_token: str
    expires_at: int


class AppleSignInRequest(BaseModel):
    """Request to authenticate with Apple Sign-in."""
    identity_token: str = Field(..., description="Apple identity token (JWT)")
    authorization_code: Optional[str] = Field(None, description="Apple authorization code")
    first_name: Optional[str] = Field(None, description="User's first name (only provided on first sign-in)")
    last_name: Optional[str] = Field(None, description="User's last name (only provided on first sign-in)")


class AppleSignInResponse(BaseModel):
    """Response after Apple Sign-in."""
    user_id: str
    email: str
    access_token: str
    refresh_token: str
    expires_at: int
    created: bool  # True if new account was created


class AccountResponse(BaseModel):
    """Full account information for iOS app."""
    user_id: str
    email: str
    created_at: str
    subscription: dict
    onboarding_completed: bool
    current_genre: Optional[str] = None


class DeleteAccountRequest(BaseModel):
    """Request to delete account."""
    confirm: bool = Field(..., description="Must be true to confirm deletion")


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
    authorization: Optional[str] = Header(None, alias="Authorization")
) -> dict:
    """
    Get current user's full profile data.
    Auto-creates user profile if it doesn't exist (first login).
    """
    # Dev mode bypass
    if config.DEV_MODE and not authorization:
        user_service = UserService()
        user = await user_service.get_or_create("dev-user-id", "dev@example.com")
        return user

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
        # Verify token with Supabase and get user info
        client = get_supabase_admin_client()
        print(f"[AUTH] Verifying token: {token[:20]}...")
        user_response = client.auth.get_user(token)
        print(f"[AUTH] User response: {user_response}")

        if not user_response or not user_response.user:
            print(f"[AUTH] No user in response")
            raise HTTPException(
                status_code=401,
                detail="Invalid or expired token"
            )

        supabase_user = user_response.user
        user_id = str(supabase_user.id)
        email = supabase_user.email or ""
        print(f"[AUTH] Verified user: {user_id} ({email})")

        # Get or create user in our database (auto-creates on first login)
        user_service = UserService()
        user = await user_service.get_or_create(user_id, email)
        print(f"[AUTH] User profile loaded: {user.get('id')}")

        return user

    except SupabaseClientError as e:
        print(f"[AUTH] SupabaseClientError: {e}")
        raise HTTPException(
            status_code=503,
            detail=f"Authentication service unavailable: {str(e)}"
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"[AUTH] Exception during token verification: {type(e).__name__}: {e}")
        raise HTTPException(
            status_code=401,
            detail=f"Token verification failed: {str(e)}"
        )


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
# iOS App Authentication Routes
# =============================================================================

@router.post("/register", response_model=RegisterResponse)
async def register(request: Request):
    """
    Register a new account with email and password.

    This endpoint creates a new user account with email/password authentication.
    The user will be automatically logged in after registration.

    Request body (JSON):
    - email: Valid email address
    - password: At least 8 characters
    """
    if not config.supabase_configured:
        raise HTTPException(
            status_code=503,
            detail="Authentication service not configured"
        )

    # Parse and validate request body manually for better error messages
    try:
        body = await request.json()
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid JSON body: {str(e)}. Expected Content-Type: application/json with {{\"email\": \"...\", \"password\": \"...\"}}"
        )

    email = body.get("email")
    password = body.get("password")

    if not email:
        raise HTTPException(
            status_code=400,
            detail="Missing required field: email"
        )
    if not password:
        raise HTTPException(
            status_code=400,
            detail="Missing required field: password"
        )
    if len(password) < 8:
        raise HTTPException(
            status_code=400,
            detail="Password must be at least 8 characters"
        )

    try:
        client = get_supabase_admin_client()

        print(f"[AUTH] Attempting registration for: {email}")

        # Create new user with email/password
        # Note: For iOS apps, disable email confirmation in Supabase dashboard
        # or configure a deep link redirect URL (e.g., fixion://auth/callback)
        response = client.auth.sign_up({
            "email": email,
            "password": password,
        })

        print(f"[AUTH] Sign up response: user={response.user is not None}, session={response.session is not None}")

        if not response.user:
            raise HTTPException(
                status_code=400,
                detail="Failed to create account - no user returned from auth service"
            )

        user = response.user
        session = response.session

        # If email confirmation is required, session might be None
        if not session:
            # User created but needs to confirm email
            # For iOS apps, this means Supabase has email confirmation enabled
            # The user will receive an email with a link they need to click
            print(f"[AUTH] User created but email confirmation required: {user.id}")
            return RegisterResponse(
                user_id=str(user.id),
                email=user.email or email,
                access_token="",
                refresh_token="",
                expires_at=0,
                created=True
            )

        # Get or create user profile in our database
        user_service = UserService()
        await user_service.get_or_create(str(user.id), user.email or email)

        print(f"[AUTH] Registration successful: {user.id}")

        return RegisterResponse(
            user_id=str(user.id),
            email=user.email or email,
            access_token=session.access_token,
            refresh_token=session.refresh_token,
            expires_at=session.expires_at,
            created=True
        )

    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e).lower()
        print(f"[AUTH] Registration error: {type(e).__name__}: {e}")
        if "already registered" in error_msg or "already exists" in error_msg:
            raise HTTPException(
                status_code=409,
                detail="An account with this email already exists"
            )
        raise HTTPException(
            status_code=500,
            detail=f"Registration failed: {str(e)}"
        )


@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """
    Login with email and password.

    Returns access and refresh tokens on successful authentication.
    """
    if not config.supabase_configured:
        raise HTTPException(
            status_code=503,
            detail="Authentication service not configured"
        )

    try:
        client = get_supabase_admin_client()

        # Authenticate with email/password
        response = client.auth.sign_in_with_password({
            "email": request.email,
            "password": request.password,
        })

        if not response.session:
            raise HTTPException(
                status_code=401,
                detail="Invalid email or password"
            )

        session = response.session
        user = response.user

        # Update last login
        user_service = UserService()
        await user_service.record_login(user.id)

        return LoginResponse(
            user_id=str(user.id),
            email=user.email,
            access_token=session.access_token,
            refresh_token=session.refresh_token,
            expires_at=session.expires_at
        )

    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e).lower()
        if "invalid" in error_msg or "credentials" in error_msg:
            raise HTTPException(
                status_code=401,
                detail="Invalid email or password"
            )
        raise HTTPException(
            status_code=500,
            detail=f"Login failed: {str(e)}"
        )


@router.post("/apple", response_model=AppleSignInResponse)
async def apple_sign_in(request: AppleSignInRequest):
    """
    Authenticate with Apple Sign-in.

    Validates the Apple identity token and creates/logs in the user.
    On first sign-in, creates a new account. On subsequent sign-ins, logs in.

    The identity_token is a JWT provided by Apple Sign In on iOS.
    """
    if not config.supabase_configured:
        raise HTTPException(
            status_code=503,
            detail="Authentication service not configured"
        )

    try:
        client = get_supabase_admin_client()

        # Use Supabase's built-in Apple OAuth support
        # The identity token from iOS is used to authenticate
        response = client.auth.sign_in_with_id_token({
            "provider": "apple",
            "token": request.identity_token,
        })

        if not response.session:
            raise HTTPException(
                status_code=401,
                detail="Apple authentication failed"
            )

        session = response.session
        user = response.user

        # Check if this is a new user (created flag based on metadata)
        user_service = UserService()
        existing_user = await user_service.get_by_id(str(user.id))
        is_new = existing_user is None

        # Get or create user profile
        db_user = await user_service.get_or_create(str(user.id), user.email or "")

        # If Apple provided name info (first sign-in only), store it
        if is_new and (request.first_name or request.last_name):
            # Could store in user preferences or profile
            name = " ".join(filter(None, [request.first_name, request.last_name]))
            if name:
                current_prefs = db_user.get("preferences", {})
                current_prefs["display_name"] = name
                await user_service.update_preferences(str(user.id), current_prefs)

        # Update Apple user ID in our database for reference
        if is_new:
            # Get Apple's user identifier from the token claims
            apple_user_id = user.user_metadata.get("sub") if user.user_metadata else None
            if apple_user_id:
                await user_service.update(str(user.id), {"apple_user_id": apple_user_id})

        # Record login
        await user_service.record_login(user.id)

        return AppleSignInResponse(
            user_id=str(user.id),
            email=user.email or "",
            access_token=session.access_token,
            refresh_token=session.refresh_token,
            expires_at=session.expires_at,
            created=is_new
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"[AUTH] Apple Sign-in error: {type(e).__name__}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Apple Sign-in failed: {str(e)}"
        )


@router.get("/account", response_model=AccountResponse)
async def get_account(user: dict = Depends(get_current_user)):
    """
    Get full account information for iOS app.

    Returns user profile with subscription details.
    """
    return AccountResponse(
        user_id=user["id"],
        email=user["email"],
        created_at=user["created_at"],
        subscription={
            "tier": user.get("subscription_tier") or "free",
            "status": user.get("subscription_status", "trial"),
            "expires_at": user.get("current_period_end"),
            "stories_this_month": user.get("credits_used_total", 0),  # Approximation
            "stories_limit": None if user.get("subscription_status") == "active" else 10
        },
        onboarding_completed=user.get("onboarding_completed", False),
        current_genre=user.get("current_genre")
    )


@router.delete("/account")
async def delete_account(
    request: DeleteAccountRequest,
    user: dict = Depends(get_current_user)
):
    """
    Delete user account and all associated data.

    This action is irreversible. All stories, conversations, and settings
    will be permanently deleted.
    """
    if not request.confirm:
        raise HTTPException(
            status_code=400,
            detail="Must confirm deletion by setting confirm=true"
        )

    if not config.supabase_configured:
        raise HTTPException(
            status_code=503,
            detail="Authentication service not configured"
        )

    try:
        user_id = user["id"]
        client = get_supabase_admin_client()

        # Delete from Supabase Auth (this cascades to delete user data via FK)
        client.auth.admin.delete_user(user_id)

        return {"deleted": True, "message": "Account successfully deleted"}

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete account: {str(e)}"
        )


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
