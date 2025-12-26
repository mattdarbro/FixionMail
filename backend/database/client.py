"""
Supabase Client Configuration

Provides both user-authenticated client and admin client for different use cases.
"""

from functools import lru_cache
from typing import Optional

from supabase import create_client, Client

from backend.config import config


class SupabaseClientError(Exception):
    """Raised when Supabase client cannot be initialized."""
    pass


@lru_cache(maxsize=1)
def get_supabase_admin_client() -> Client:
    """
    Get Supabase client with service role key (admin access).

    Use this for:
    - Webhook handlers (Stripe, email inbound)
    - Background job workers
    - Admin operations that bypass RLS

    WARNING: This client bypasses Row Level Security!
    Only use for server-side operations where the user context is not available.
    """
    if not config.SUPABASE_URL:
        raise SupabaseClientError(
            "SUPABASE_URL is not configured. "
            "Set it in your .env file or environment variables."
        )

    if not config.SUPABASE_SERVICE_KEY:
        raise SupabaseClientError(
            "SUPABASE_SERVICE_KEY is not configured. "
            "Set it in your .env file or environment variables."
        )

    return create_client(
        config.SUPABASE_URL,
        config.SUPABASE_SERVICE_KEY
    )


def get_supabase_client(access_token: Optional[str] = None) -> Client:
    """
    Get Supabase client for user operations.

    Args:
        access_token: JWT access token from authenticated user.
                     If provided, requests will use the user's context for RLS.
                     If None, uses anon key (limited access).

    Use this for:
    - User-facing API endpoints
    - Operations that should respect Row Level Security
    """
    if not config.SUPABASE_URL:
        raise SupabaseClientError(
            "SUPABASE_URL is not configured. "
            "Set it in your .env file or environment variables."
        )

    if not config.SUPABASE_ANON_KEY:
        raise SupabaseClientError(
            "SUPABASE_ANON_KEY is not configured. "
            "Set it in your .env file or environment variables."
        )

    client = create_client(
        config.SUPABASE_URL,
        config.SUPABASE_ANON_KEY
    )

    # If access token provided, set it for authenticated requests
    if access_token:
        client.auth.set_session(access_token, "")  # Refresh token not needed for API calls

    return client


def verify_supabase_connection() -> bool:
    """
    Verify that Supabase is properly configured and accessible.

    Returns:
        True if connection successful, False otherwise.
    """
    try:
        client = get_supabase_admin_client()
        # Try a simple query to verify connection
        client.table("users").select("id").limit(1).execute()
        return True
    except Exception as e:
        print(f"Supabase connection failed: {e}")
        return False
