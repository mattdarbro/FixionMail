"""
Email scheduling system for StoryKeeper.
Sends chapter emails at scheduled times using Resend API.
"""

import resend
import os
import json
from datetime import datetime, timedelta
from typing import Optional

from backend.email.database import EmailDatabase

# Initialize Resend
resend.api_key = os.getenv("RESEND_API_KEY")


class EmailScheduler:
    """Handles scheduling and sending chapter emails"""

    def __init__(self, db: EmailDatabase):
        self.db = db

    async def schedule_chapter(
        self,
        user_email: str,
        session_id: str,
        chapter_number: int,
        audio_url: str,
        image_url: Optional[str],
        choices: list[dict],
        send_at: datetime
    ):
        """
        Schedule a chapter email to be sent later.

        Args:
            user_email: Recipient email address
            session_id: User's story session ID
            chapter_number: Which chapter to send
            audio_url: URL to the MP3 file
            image_url: URL to chapter image (optional)
            choices: List of choice options for user
            send_at: When to send the email
        """
        # Convert choices to JSON string for storage
        choices_json = json.dumps(choices)

        await self.db.schedule_email(
            session_id=session_id,
            email=user_email,
            chapter=chapter_number,
            audio_url=audio_url,
            image_url=image_url,
            choices=choices_json,
            send_at=send_at
        )

        print(f"📧 Scheduled email for {user_email} - Chapter {chapter_number} at {send_at}")

    async def send_immediate(
        self,
        user_email: str,
        session_id: str,
        chapter_number: int,
        audio_url: str,
        image_url: Optional[str],
        choices: list[dict]
    ) -> bool:
        """
        Send a chapter email immediately (for testing or instant delivery).

        Returns:
            True if sent successfully, False otherwise
        """
        html = self._render_email(
            chapter_number=chapter_number,
            audio_url=audio_url,
            image_url=image_url,
            choices=choices,
            session_id=session_id
        )

        try:
            params = {
                "from": "StoryKeeper <story@storykeeper.app>",
                "to": [user_email],
                "subject": f"Chapter {chapter_number} is ready! 🎧",
                "html": html,
            }

            resend.Emails.send(params)
            print(f"✅ Sent chapter {chapter_number} to {user_email}")
            return True

        except Exception as e:
            print(f"❌ Failed to send email: {e}")
            return False

    async def send_welcome_email(self, user_email: str, first_chapter_time: datetime) -> bool:
        """Send welcome email when user signs up"""

        time_str = first_chapter_time.strftime("%I:%M %p %Z")

        html = f'''
        <!DOCTYPE html>
        <html>
        <head>
          <meta charset="utf-8">
          <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="font-family: Georgia, serif; max-width: 600px; margin: 0 auto; padding: 20px; background: #f5f5f5;">
          <div style="background: white; border-radius: 12px; padding: 40px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
            <h1 style="color: #1a1a1a; margin-bottom: 20px;">Welcome to StoryKeeper! 👋</h1>

            <p style="font-size: 18px; color: #404040; line-height: 1.6;">
              Your personalized audio story begins tomorrow morning.
            </p>

            <h3 style="color: #1a1a1a; margin-top: 30px;">Here's what happens next:</h3>
            <ul style="font-size: 16px; color: #404040; line-height: 1.8;">
              <li>📧 Tomorrow at {time_str}: Chapter 1 arrives</li>
              <li>🎧 Listen whenever you're ready</li>
              <li>🔀 At the end, make your choice</li>
              <li>📧 Next day: Chapter 2 (based on your choice)</li>
            </ul>

            <div style="background: #f8f9fa; border-radius: 8px; padding: 20px; margin-top: 30px;">
              <p style="margin: 0; font-size: 14px; color: #666;">
                <strong style="color: #1a1a1a;">Your Story:</strong> "The Orbital Station"<br>
                A cozy sci-fi story about love and difficult choices.<br>
                4 chapters • ~8 minutes each
              </p>
            </div>

            <p style="color: #666; font-size: 14px; margin-top: 40px; text-align: center;">
              See you tomorrow!<br>
              <strong>The StoryKeeper Team</strong>
            </p>
          </div>
        </body>
        </html>
        '''

        try:
            params = {
                "from": "StoryKeeper <story@storykeeper.app>",
                "to": [user_email],
                "subject": "Welcome to StoryKeeper! Your story begins tomorrow.",
                "html": html,
            }

            resend.Emails.send(params)
            print(f"✅ Sent welcome email to {user_email}")
            return True

        except Exception as e:
            print(f"❌ Failed to send welcome email: {e}")
            return False

    async def process_scheduled_emails(self):
        """
        Process all emails that are due to be sent.
        Should be called every minute by background task.
        """
        due_emails = await self.db.get_due_emails(limit=100)

        print(f"📬 Processing {len(due_emails)} scheduled emails...")

        for email_job in due_emails:
            # Parse choices JSON
            choices = json.loads(email_job["choices"])

            success = await self.send_immediate(
                user_email=email_job["email"],
                session_id=email_job["session_id"],
                chapter_number=email_job["chapter"],
                audio_url=email_job["audio_url"],
                image_url=email_job["image_url"],
                choices=choices
            )

            if success:
                await self.db.mark_sent(email_job["id"], success=True)
            else:
                await self.db.mark_sent(
                    email_job["id"],
                    success=False,
                    error="Failed to send via Resend API"
                )

    def _render_email(
        self,
        chapter_number: int,
        audio_url: str,
        image_url: Optional[str],
        choices: list[dict],
        session_id: str
    ) -> str:
        """Generate HTML for chapter email"""

        # Render choice buttons
        choice_buttons = '\n'.join([
            f'''
            <a href="https://storykeeper.app/choice?s={session_id}&c={choice['id']}"
               style="display: block;
                      margin: 15px 0;
                      padding: 20px;
                      background: #6366f1;
                      color: white;
                      text-decoration: none;
                      border-radius: 8px;
                      text-align: center;
                      font-size: 16px;
                      font-weight: 500;
                      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;">
              → {choice['text']}
            </a>
            '''
            for choice in choices
        ])

        # Optional image section
        image_section = ""
        if image_url:
            image_section = f'''
            <div style="margin: 30px 0;">
              <img src="{image_url}"
                   alt="Chapter {chapter_number}"
                   style="width: 100%; border-radius: 8px; display: block;">
            </div>
            '''

        return f'''
        <!DOCTYPE html>
        <html>
        <head>
          <meta charset="utf-8">
          <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="font-family: Georgia, serif; max-width: 600px; margin: 0 auto; padding: 20px; background: #f5f5f5;">
          <div style="background: white; border-radius: 12px; padding: 40px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">

            <h1 style="color: #1a1a1a; margin-bottom: 20px; font-size: 32px;">Chapter {chapter_number}</h1>

            <p style="font-size: 18px; color: #404040; line-height: 1.6;">
              Your story continues... 🎧
            </p>

            {image_section}

            <div style="margin: 30px 0; padding: 20px; background: #f8f9fa; border-radius: 8px;">
              <audio controls style="width: 100%;">
                <source src="{audio_url}" type="audio/mpeg">
                Your browser does not support the audio element.
              </audio>
              <p style="margin: 10px 0 0 0; font-size: 12px; color: #666; text-align: center;">
                <a href="{audio_url}" style="color: #6366f1; text-decoration: none;">Download audio</a>
              </p>
            </div>

            <hr style="margin: 40px 0; border: none; border-top: 1px solid #e5e5e5;">

            <h3 style="color: #1a1a1a; margin-bottom: 20px; font-size: 20px;">What happens next?</h3>

            {choice_buttons}

            <p style="color: #999; font-size: 12px; margin-top: 40px; text-align: center;">
              StoryKeeper • Your choices, your story
            </p>
          </div>
        </body>
        </html>
        '''


# Cron job / Background task entry point
async def send_scheduled_emails():
    """
    Main function to be called by background task every minute.
    Processes all due emails and sends them.
    """
    db = EmailDatabase()
    await db.connect()

    scheduler = EmailScheduler(db)
    await scheduler.process_scheduled_emails()

    await db.close()
    print(f"[{datetime.now()}] Processed scheduled emails")


if __name__ == "__main__":
    import asyncio
    asyncio.run(send_scheduled_emails())
