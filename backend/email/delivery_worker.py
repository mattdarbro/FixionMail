"""
Delivery Worker

Lightweight worker that sends emails at scheduled times.
Runs every minute, checks for due deliveries, and sends via Resend API.

This is decoupled from story generation - stories are pre-generated
and waiting, this worker just handles the email timing.
"""

import os
import asyncio
import resend
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from backend.database.deliveries import DeliveryService, DeliveryStatus
from backend.database.stories import StoryService
from backend.utils.logging import get_logger

logger = get_logger("delivery_worker")

# Initialize Resend
resend.api_key = os.getenv("RESEND_API_KEY")


class DeliveryWorker:
    """
    Background worker that sends emails at scheduled delivery times.

    - Runs every minute
    - Checks for pending deliveries where deliver_at <= now
    - Sends email via Resend API
    - Marks delivery as sent/failed
    """

    def __init__(self, check_interval_seconds: int = 60):
        self.check_interval = check_interval_seconds
        self.scheduler = AsyncIOScheduler()
        self.delivery_service: Optional[DeliveryService] = None
        self.story_service: Optional[StoryService] = None
        self._is_processing = False

    async def initialize(self):
        """Initialize services."""
        self.delivery_service = DeliveryService()
        self.story_service = StoryService()
        logger.info("Delivery worker initialized", check_interval=self.check_interval)

    async def process_deliveries(self):
        """
        Main processing loop - check for due deliveries and send.
        Called every minute by scheduler.
        """
        if self._is_processing:
            return

        self._is_processing = True

        try:
            # Get deliveries that are due
            due_deliveries = await self.delivery_service.get_due_deliveries(limit=20)

            if not due_deliveries:
                return

            logger.info(f"Processing due deliveries", count=len(due_deliveries))

            for i, delivery in enumerate(due_deliveries):
                await self._send_delivery(delivery)
                # Rate limit: Resend allows max 2 requests/second
                # Add 0.6s delay between sends to stay safely under limit
                if i < len(due_deliveries) - 1:
                    await asyncio.sleep(0.6)

        except Exception as e:
            logger.error(f"Delivery worker error: {e}", error=str(e))
        finally:
            self._is_processing = False

    async def _send_delivery(self, delivery: Dict[str, Any]):
        """Send a single delivery."""
        delivery_id = delivery["id"]
        user_email = delivery["user_email"]
        email_sent = False  # Track if email was successfully sent

        try:
            # Check if already sent (prevents duplicate sends on retry)
            if delivery.get("status") == "sent":
                logger.info(f"Delivery already sent, skipping", delivery_id=delivery_id)
                return

            # Mark as sending (prevents duplicate sends)
            await self.delivery_service.mark_sending(delivery_id)

            # Get story data (should be joined from query)
            story = delivery.get("story")
            if not story:
                raise Exception("Story not found for delivery")

            # Build and send email
            html = self._render_story_email(
                story_title=story["title"],
                story_narrative=story["narrative"],
                audio_url=story.get("audio_url"),
                image_url=story.get("image_url"),
                genre=story["genre"],
                word_count=story.get("word_count", 0)
            )

            from_address = os.getenv("EMAIL_FROM_ADDRESS", "onboarding@resend.dev")

            params = {
                "from": from_address,
                "to": [user_email],
                "subject": f"📖 Today's Story: {story['title']}",
                "html": html,
            }

            response = resend.Emails.send(params)
            resend_id = response.get("id") if isinstance(response, dict) else getattr(response, "id", None)
            email_sent = True  # Email was successfully sent

            # Try to mark as sent - if this fails, we should NOT retry sending
            try:
                await self.delivery_service.mark_sent(delivery_id, resend_email_id=resend_id)
            except Exception as mark_error:
                # Email was sent but we couldn't update the database
                # Log the error but don't retry to prevent duplicate emails
                logger.error(
                    f"Email sent but mark_sent failed - DO NOT RETRY",
                    delivery_id=delivery_id,
                    resend_id=resend_id,
                    error=str(mark_error)
                )
                return  # Don't continue - email was sent

            # Also update story as delivered
            try:
                await self.story_service.mark_delivered(story["id"])
            except Exception as mark_error:
                # Non-critical - email was sent, story delivery update failed
                logger.warning(
                    f"Could not mark story as delivered",
                    story_id=story["id"],
                    error=str(mark_error)
                )

            logger.info(
                f"Delivery sent",
                delivery_id=delivery_id,
                email=user_email,
                story_title=story["title"],
                resend_id=resend_id
            )

        except Exception as e:
            error_msg = str(e)
            logger.error(
                f"Delivery failed",
                delivery_id=delivery_id,
                email=user_email,
                error=error_msg
            )

            # Only retry if email was NOT sent
            # If email was sent but something else failed, don't retry to prevent duplicates
            if email_sent:
                should_retry = False
            else:
                # Determine if retryable based on error type
                should_retry = any(x in error_msg.lower() for x in [
                    "timeout", "rate limit", "429", "503", "502", "connection"
                ])

            try:
                await self.delivery_service.mark_failed(
                    delivery_id,
                    error_message=error_msg,
                    should_retry=should_retry
                )
            except Exception as mark_error:
                logger.error(f"Failed to mark delivery as failed: {mark_error}", delivery_id=delivery_id)

    def _render_story_email(
        self,
        story_title: str,
        story_narrative: str,
        audio_url: Optional[str],
        image_url: Optional[str],
        genre: str,
        word_count: int
    ) -> str:
        """Generate HTML for story email."""
        base_url = os.getenv("APP_BASE_URL", "http://localhost:8000").rstrip('/')

        # Image section
        image_section = ""
        if image_url:
            full_image_url = image_url if image_url.startswith('http') else f"{base_url}/{image_url.lstrip('/')}"
            image_section = f'''
            <div style="margin: 30px 0; text-align: center;">
              <img src="{full_image_url}" alt="{story_title}"
                   style="width: 100%; max-width: 600px; height: auto; border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.15);">
            </div>
            '''

        # Audio section
        audio_section = ""
        if audio_url:
            full_audio_url = audio_url if audio_url.startswith('http') else f"{base_url}/{audio_url.lstrip('/')}"
            audio_section = f'''
            <div style="margin: 30px 0; padding: 30px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 16px;">
              <div style="text-align: center; margin-bottom: 20px;">
                <h3 style="color: white; margin: 0 0 8px 0; font-size: 20px;">🎧 Listen to Your Story</h3>
                <p style="margin: 0; font-size: 14px; color: rgba(255,255,255,0.9);">Professional narration</p>
              </div>
              <div style="text-align: center; margin-bottom: 20px;">
                <a href="{full_audio_url}" target="_blank"
                   style="display: inline-block; background: white; color: #667eea; padding: 16px 40px; border-radius: 50px; text-decoration: none; font-weight: 700; font-size: 16px;">
                  ▶️ Play Audio
                </a>
              </div>
              <div style="background: rgba(255,255,255,0.15); border-radius: 12px; padding: 20px;">
                <audio controls style="width: 100%; height: 40px;">
                  <source src="{full_audio_url}" type="audio/mpeg">
                </audio>
              </div>
            </div>
            '''

        # Format story
        paragraphs = story_narrative.split('\n\n')
        formatted_story = ''.join([
            f'<p style="margin: 0 0 24px 0; font-size: 18px; line-height: 1.8; color: #2d2d2d;">{p.strip()}</p>'
            for p in paragraphs if p.strip()
        ])

        reading_time = max(1, round(word_count / 200))

        return f'''
        <!DOCTYPE html>
        <html>
        <head>
          <meta charset="utf-8">
          <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="margin: 0; padding: 0; font-family: Georgia, serif; background: #f8f9fa;">
          <div style="max-width: 700px; margin: 0 auto; padding: 40px 20px;">
            <!-- Header -->
            <div style="text-align: center; margin-bottom: 40px;">
              <div style="display: inline-block; background: white; padding: 12px 24px; border-radius: 30px; margin-bottom: 20px;">
                <p style="margin: 0; font-size: 13px; color: #6c757d; text-transform: uppercase; letter-spacing: 2px; font-weight: 600;">
                  {genre.upper()}
                </p>
              </div>
              <h1 style="color: #1a1a1a; margin: 0 0 12px 0; font-size: 42px; font-weight: 700;">
                {story_title}
              </h1>
              <p style="margin: 0; font-size: 15px; color: #6c757d;">
                {word_count:,} words • {reading_time} min read
              </p>
            </div>

            {image_section}
            {audio_section}

            <!-- Story Content -->
            <div style="background: white; border-radius: 16px; padding: 60px 50px; margin: 30px 0;">
              {formatted_story}
            </div>

            <!-- Footer -->
            <div style="text-align: center; margin-top: 50px; padding: 40px 30px; background: white; border-radius: 16px;">
              <p style="margin: 0 0 12px 0; font-size: 18px; color: #1a1a1a; font-weight: 600;">
                ✨ Enjoyed this story?
              </p>
              <p style="margin: 0 0 20px 0; font-size: 15px; color: #6c757d;">
                You'll receive a new story tomorrow.
              </p>
              <div style="display: inline-block; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 12px 32px; border-radius: 25px;">
                <p style="margin: 0; font-size: 13px; color: white; font-weight: 600;">📬 FIXION MAIL</p>
              </div>
            </div>

            <p style="text-align: center; color: #adb5bd; font-size: 12px; margin-top: 30px;">
              FixionMail • Daily Stories Delivered to Your Inbox
            </p>
          </div>
        </body>
        </html>
        '''

    def start(self):
        """Start the delivery worker."""
        self.scheduler.add_job(
            self.process_deliveries,
            trigger=IntervalTrigger(seconds=self.check_interval),
            id="delivery_worker",
            name="Send scheduled email deliveries",
            replace_existing=True,
            max_instances=1
        )
        self.scheduler.start()
        logger.info("Delivery worker started", check_interval=self.check_interval)

    def shutdown(self):
        """Shutdown the worker."""
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)
        logger.info("Delivery worker stopped")


# Global instance
_delivery_worker: Optional[DeliveryWorker] = None


async def start_delivery_worker(check_interval: int = 60):
    """Start the delivery worker. Call during FastAPI startup."""
    global _delivery_worker

    if _delivery_worker is None:
        _delivery_worker = DeliveryWorker(check_interval_seconds=check_interval)
        await _delivery_worker.initialize()
        _delivery_worker.start()


def stop_delivery_worker():
    """Stop the delivery worker. Call during FastAPI shutdown."""
    global _delivery_worker

    if _delivery_worker is not None:
        _delivery_worker.shutdown()
        _delivery_worker = None


def get_delivery_worker() -> Optional[DeliveryWorker]:
    """Get the current worker instance."""
    return _delivery_worker
