"""
Redis Queue (RQ) integration for FixionMail job processing.

This module provides a robust, scalable job queue using Redis.
"""

from .connection import get_redis_connection, get_queue
from .tasks import enqueue_story_job, enqueue_email_delivery

__all__ = [
    "get_redis_connection",
    "get_queue",
    "enqueue_story_job",
    "enqueue_email_delivery",
]
