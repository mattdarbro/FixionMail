"""
FixionMail Database Layer

This module provides the Supabase client and service classes for
interacting with the database.
"""

from .client import get_supabase_client, get_supabase_admin_client
from .users import UserService
from .stories import StoryService
from .conversations import ConversationService
from .credits import CreditService
from .jobs import JobQueueService, JobStatus
from .deliveries import DeliveryService, DeliveryStatus

__all__ = [
    "get_supabase_client",
    "get_supabase_admin_client",
    "UserService",
    "StoryService",
    "ConversationService",
    "CreditService",
    "JobQueueService",
    "JobStatus",
    "DeliveryService",
    "DeliveryStatus",
]
