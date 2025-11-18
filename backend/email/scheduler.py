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
            # Use Resend's testing domain (works without verification)
            # For production, verify your domain and change to: story@yourdomain.com
            from_address = os.getenv("EMAIL_FROM_ADDRESS", "onboarding@resend.dev")

            params = {
                "from": from_address,
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

    async def send_story_email(
        self,
        user_email: str,
        story_title: str,
        story_narrative: str,
        audio_url: Optional[str],
        image_url: Optional[str],
        genre: str,
        word_count: int,
        user_tier: str = "free"
    ) -> bool:
        """
        Send a standalone story email (FictionMail format) with inline content.

        Args:
            user_email: Recipient email address
            story_title: Title of the story
            story_narrative: The complete story text
            audio_url: URL to the hosted MP3 file (optional)
            image_url: URL to the hosted cover image (optional)
            genre: Story genre
            word_count: Story word count
            user_tier: User's subscription tier (free/premium)

        Returns:
            True if sent successfully, False otherwise
        """
        html = self._render_story_email(
            story_title=story_title,
            story_narrative=story_narrative,
            audio_url=audio_url,
            image_url=image_url,
            user_tier=user_tier,
            genre=genre,
            word_count=word_count
        )

        try:
            from_address = os.getenv("EMAIL_FROM_ADDRESS", "onboarding@resend.dev")

            params = {
                "from": from_address,
                "to": [user_email],
                "subject": f"📖 Today's Story: {story_title}",
                "html": html,
            }

            response = resend.Emails.send(params)
            print(f"✅ Sent story '{story_title}' to {user_email}")
            print(f"   Resend email ID: {response.get('id', 'unknown')}")

            if audio_url:
                print(f"   🎧 Inline audio player: {audio_url}")
            if image_url:
                print(f"   🎨 Inline cover image: {image_url}")

            return True

        except Exception as e:
            print(f"❌ Failed to send story email: {e}")
            print(f"   Error type: {type(e).__name__}")
            import traceback
            traceback.print_exc()
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
            from_address = os.getenv("EMAIL_FROM_ADDRESS", "onboarding@resend.dev")

            params = {
                "from": from_address,
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

        # Get base URL from environment (Railway URL in production, localhost in dev)
        base_url = os.getenv("APP_BASE_URL", "http://localhost:8000")

        # Render choice buttons
        choice_buttons = '\n'.join([
            f'''
            <a href="{base_url}/api/choice?s={session_id}&c={choice['id']}"
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

    def _render_story_email(
        self,
        story_title: str,
        story_narrative: str,
        audio_url: Optional[str],
        image_url: Optional[str],
        user_tier: str,
        genre: str,
        word_count: int
    ) -> str:
        """Generate HTML for standalone story email (FictionMail) with inline content"""

        # Get base URL from environment
        base_url = os.getenv("APP_BASE_URL", "http://localhost:8000")

        # Inline cover image (shown prominently at top)
        image_section = ""
        if image_url:
            # Construct full URL
            full_image_url = f"{base_url}{image_url}" if image_url.startswith('/') else image_url
            image_section = f'''
            <div style="margin: 30px 0; text-align: center;">
              <img src="{full_image_url}"
                   alt="{story_title}"
                   style="width: 100%; max-width: 600px; height: auto; border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.15); display: block; margin: 0 auto;">
            </div>
            '''

        # Inline audio player (beautiful design with controls)
        audio_section = ""
        if audio_url:
            # Construct full URL
            full_audio_url = f"{base_url}{audio_url}" if audio_url.startswith('/') else audio_url
            audio_section = f'''
            <div style="margin: 30px 0; padding: 30px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 16px; box-shadow: 0 8px 24px rgba(102, 126, 234, 0.25);">
              <div style="text-align: center; margin-bottom: 20px;">
                <h3 style="color: white; margin: 0 0 8px 0; font-size: 20px; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; font-weight: 600;">
                  🎧 Listen to Your Story
                </h3>
                <p style="margin: 0; font-size: 14px; color: rgba(255,255,255,0.9); font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;">
                  Professional narration • Perfect for your commute
                </p>
              </div>
              <div style="background: rgba(255,255,255,0.15); border-radius: 12px; padding: 20px; backdrop-filter: blur(10px);">
                <audio controls style="width: 100%; height: 40px; border-radius: 8px;">
                  <source src="{full_audio_url}" type="audio/mpeg">
                  Your browser does not support the audio element.
                </audio>
                <p style="margin: 15px 0 0 0; font-size: 12px; color: rgba(255,255,255,0.85); text-align: center; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;">
                  <a href="{full_audio_url}" style="color: white; text-decoration: none; font-weight: 500;">📥 Download MP3</a>
                </p>
              </div>
            </div>
            '''

        # Format story narrative with beautiful typography
        paragraphs = story_narrative.split('\n\n')
        formatted_story = ''.join([
            f'<p style="margin: 0 0 24px 0; font-size: 18px; line-height: 1.8; color: #2d2d2d; font-family: Georgia, serif;">{p.strip()}</p>'
            for p in paragraphs if p.strip()
        ])

        # Estimate reading time (average 200 words per minute)
        reading_time = max(1, round(word_count / 200))

        # Premium badge for premium tier users
        tier_badge = ""
        if user_tier == "premium":
            tier_badge = '''
            <div style="display: inline-block; background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); color: white; padding: 6px 16px; border-radius: 20px; font-size: 12px; font-weight: 600; letter-spacing: 1px; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; margin-top: 10px;">
              ✨ PREMIUM
            </div>
            '''

        return f'''
        <!DOCTYPE html>
        <html>
        <head>
          <meta charset="utf-8">
          <meta name="viewport" content="width=device-width, initial-scale=1.0">
          <style>
            @media only screen and (max-width: 600px) {{
              .container {{ padding: 20px !important; }}
              .story-title {{ font-size: 28px !important; }}
              .story-content {{ padding: 30px 24px !important; }}
            }}
          </style>
        </head>
        <body style="margin: 0; padding: 0; font-family: Georgia, serif; background: linear-gradient(180deg, #f8f9fa 0%, #e9ecef 100%); min-height: 100vh;">
          <div class="container" style="max-width: 700px; margin: 0 auto; padding: 40px 20px;">

            <!-- Header -->
            <div style="text-align: center; margin-bottom: 40px;">
              <div style="display: inline-block; background: white; padding: 12px 24px; border-radius: 30px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); margin-bottom: 20px;">
                <p style="margin: 0; font-size: 13px; color: #6c757d; text-transform: uppercase; letter-spacing: 2px; font-weight: 600; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;">
                  {genre.upper()}
                </p>
              </div>
              <h1 class="story-title" style="color: #1a1a1a; margin: 0 0 12px 0; font-size: 42px; font-weight: 700; letter-spacing: -1px; line-height: 1.2;">
                {story_title}
              </h1>
              <p style="margin: 0; font-size: 15px; color: #6c757d; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;">
                {word_count:,} words • {reading_time} min read
              </p>
              {tier_badge}
            </div>

            <!-- Cover Image (inline, prominent) -->
            {image_section}

            <!-- Audio Player (inline, beautiful) -->
            {audio_section}

            <!-- Story Content -->
            <div class="story-content" style="background: white; border-radius: 16px; padding: 60px 50px; box-shadow: 0 4px 20px rgba(0,0,0,0.08); margin: 30px 0;">
              {formatted_story}
            </div>

            <!-- Footer -->
            <div style="text-align: center; margin-top: 50px; padding: 40px 30px; background: white; border-radius: 16px; box-shadow: 0 2px 12px rgba(0,0,0,0.06);">
              <p style="margin: 0 0 12px 0; font-size: 18px; color: #1a1a1a; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; font-weight: 600;">
                ✨ Enjoyed this story?
              </p>
              <p style="margin: 0 0 20px 0; font-size: 15px; color: #6c757d; line-height: 1.6; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;">
                You'll receive a new {genre} story tomorrow.<br>
                Each one is unique and tailored just for you.
              </p>
              <div style="display: inline-block; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 12px 32px; border-radius: 25px; margin-top: 10px;">
                <p style="margin: 0; font-size: 13px; color: white; font-weight: 600; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; letter-spacing: 0.5px;">
                  📬 FICTION MAIL
                </p>
              </div>
            </div>

            <!-- Branding -->
            <p style="text-align: center; color: #adb5bd; font-size: 12px; margin-top: 30px; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;">
              FictionMail • Daily Stories Delivered to Your Inbox
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
