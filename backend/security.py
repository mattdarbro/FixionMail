"""
Security utilities for FixionMail API.

Provides API key authentication and rate limiting with dev mode bypass.
"""

from fastapi import HTTPException, Header, Request, Depends
from functools import wraps
import time
from typing import Optional
from collections import defaultdict


# Simple in-memory rate limiter (per API key)
_rate_limit_store: dict[str, list[float]] = defaultdict(list)


def get_api_key(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    authorization: Optional[str] = Header(None)
) -> Optional[str]:
    """
    Extract API key from headers.
    Supports both X-API-Key header and Bearer token.
    """
    if x_api_key:
        return x_api_key

    if authorization and authorization.startswith("Bearer "):
        return authorization[7:]

    return None


async def verify_api_key(
    request: Request,
    api_key: Optional[str] = Depends(get_api_key)
) -> str:
    """
    Verify API key authentication.

    In dev mode with no API keys configured, authentication is bypassed.
    Returns the API key (or "dev" if bypassed).
    """
    from backend.config import config

    # Dev mode bypass: if no API keys configured and DEV_MODE is True
    if not config.auth_required:
        return "dev"

    # Auth required - validate the key
    if not api_key:
        raise HTTPException(
            status_code=401,
            detail="API key required. Provide X-API-Key header or Bearer token.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    if api_key not in config.api_keys_list:
        raise HTTPException(
            status_code=403,
            detail="Invalid API key"
        )

    # Rate limiting
    if config.RATE_LIMIT_PER_MINUTE > 0:
        now = time.time()
        window_start = now - 60

        # Clean old entries
        _rate_limit_store[api_key] = [
            t for t in _rate_limit_store[api_key] if t > window_start
        ]

        # Check limit
        if len(_rate_limit_store[api_key]) >= config.RATE_LIMIT_PER_MINUTE:
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded. Max {config.RATE_LIMIT_PER_MINUTE} requests per minute."
            )

        # Record this request
        _rate_limit_store[api_key].append(now)

    return api_key


# Convenience dependency for routes that require auth
require_auth = Depends(verify_api_key)
