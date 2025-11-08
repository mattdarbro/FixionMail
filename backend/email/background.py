"""
Background task processor for email scheduling.
Uses APScheduler to process scheduled emails every minute.
"""

import asyncio
import os
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime

from backend.email.database import EmailDatabase
from backend.email.scheduler import EmailScheduler


class BackgroundEmailProcessor:
    """Background processor for scheduled emails"""

    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.db: EmailDatabase | None = None
        self.email_scheduler: EmailScheduler | None = None

    async def initialize(self):
        """Initialize database connection"""
        email_db_path = os.getenv("EMAIL_DB_PATH", "email_scheduler.db")
        self.db = EmailDatabase(email_db_path)
        await self.db.connect()
        self.email_scheduler = EmailScheduler(self.db)
        print(f"✓ Background email processor initialized")

    async def process_emails(self):
        """Process all scheduled emails that are due"""
        try:
            if self.email_scheduler:
                await self.email_scheduler.process_scheduled_emails()
            else:
                print("⚠️  Email scheduler not initialized")
        except Exception as e:
            print(f"❌ Error processing scheduled emails: {e}")
            import traceback
            traceback.print_exc()

    def start(self):
        """Start the background scheduler"""
        # Run every minute
        self.scheduler.add_job(
            self.process_emails,
            trigger=IntervalTrigger(minutes=1),
            id="email_processor",
            name="Process scheduled emails",
            replace_existing=True
        )

        self.scheduler.start()
        print(f"✓ Background email processor started (runs every minute)")

    def shutdown(self):
        """Shutdown the scheduler"""
        if self.scheduler.running:
            self.scheduler.shutdown()
        print("✓ Background email processor stopped")


# Global instance
background_processor = None


async def start_background_processor():
    """
    Start the background email processor.
    Call this during FastAPI startup.
    """
    global background_processor

    if background_processor is None:
        background_processor = BackgroundEmailProcessor()
        await background_processor.initialize()
        background_processor.start()


def stop_background_processor():
    """
    Stop the background email processor.
    Call this during FastAPI shutdown.
    """
    global background_processor

    if background_processor is not None:
        background_processor.shutdown()
        background_processor = None
