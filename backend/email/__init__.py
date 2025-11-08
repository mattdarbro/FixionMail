"""
Email module for StoryKeeper.
Handles email scheduling and delivery via Resend.
"""

from backend.email.database import EmailDatabase
from backend.email.scheduler import EmailScheduler, send_scheduled_emails
from backend.email.background import (
    BackgroundEmailProcessor,
    start_background_processor,
    stop_background_processor
)

__all__ = [
    "EmailDatabase",
    "EmailScheduler",
    "send_scheduled_emails",
    "BackgroundEmailProcessor",
    "start_background_processor",
    "stop_background_processor"
]
