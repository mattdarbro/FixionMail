"""
Redis connection management for RQ job queue.

Provides a singleton Redis connection and queue instances.
"""

import os
from typing import Optional
from redis import Redis
from rq import Queue

from backend.config import config

# Singleton connection
_redis_connection: Optional[Redis] = None

# Queue names
QUEUE_STORIES = "stories"
QUEUE_EMAILS = "emails"
QUEUE_DEFAULT = "default"


def get_redis_connection() -> Redis:
    """
    Get the Redis connection singleton.

    Returns:
        Redis connection instance

    Raises:
        ValueError: If REDIS_URL is not configured
    """
    global _redis_connection

    if _redis_connection is None:
        redis_url = config.REDIS_URL
        if not redis_url:
            raise ValueError(
                "REDIS_URL environment variable is required for job queue. "
                "Set up Upstash Redis or local Redis and configure REDIS_URL."
            )

        # Parse connection options
        # Upstash uses rediss:// (TLS), local Redis uses redis://
        ssl = redis_url.startswith("rediss://")

        _redis_connection = Redis.from_url(
            redis_url,
            decode_responses=False,  # RQ needs bytes
            socket_timeout=10,
            socket_connect_timeout=10,
            retry_on_timeout=True,
            health_check_interval=30,
        )

        # Test connection
        try:
            _redis_connection.ping()
            print(f"✅ Redis connected: {redis_url.split('@')[-1] if '@' in redis_url else 'localhost'}")
        except Exception as e:
            _redis_connection = None
            raise ConnectionError(f"Failed to connect to Redis: {e}")

    return _redis_connection


def get_queue(name: str = QUEUE_DEFAULT) -> Queue:
    """
    Get an RQ queue by name.

    Args:
        name: Queue name (stories, emails, or default)

    Returns:
        RQ Queue instance
    """
    conn = get_redis_connection()
    return Queue(name, connection=conn)


def get_story_queue() -> Queue:
    """Get the story generation queue."""
    return get_queue(QUEUE_STORIES)


def get_email_queue() -> Queue:
    """Get the email delivery queue."""
    return get_queue(QUEUE_EMAILS)


def close_redis_connection():
    """Close the Redis connection (for cleanup)."""
    global _redis_connection
    if _redis_connection:
        _redis_connection.close()
        _redis_connection = None


def redis_health_check() -> dict:
    """
    Check Redis connection health.

    Returns:
        Dict with health status and queue info
    """
    try:
        conn = get_redis_connection()
        conn.ping()

        # Get queue lengths
        story_queue = get_queue(QUEUE_STORIES)
        email_queue = get_queue(QUEUE_EMAILS)

        return {
            "status": "healthy",
            "connected": True,
            "queues": {
                QUEUE_STORIES: len(story_queue),
                QUEUE_EMAILS: len(email_queue),
            },
            "failed_jobs": {
                QUEUE_STORIES: story_queue.failed_job_registry.count,
                QUEUE_EMAILS: email_queue.failed_job_registry.count,
            }
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "connected": False,
            "error": str(e)
        }
