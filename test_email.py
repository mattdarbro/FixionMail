#!/usr/bin/env python3
"""
Test script for email delivery.
Sends a test chapter email to verify Resend integration.

Usage:
    python test_email.py your@email.com
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Check for Resend API key
if not os.getenv("RESEND_API_KEY"):
    print("❌ Error: RESEND_API_KEY not set in .env file")
    print("\nAdd to .env:")
    print("RESEND_API_KEY=re_xxxxxxxxxxxxx")
    sys.exit(1)


async def test_immediate_email(recipient_email: str):
    """Test sending an email immediately"""
    from backend.email.database import EmailDatabase
    from backend.email.scheduler import EmailScheduler

    print("=" * 60)
    print("Testing Email Delivery")
    print("=" * 60)
    print(f"Recipient: {recipient_email}")
    print(f"Resend API Key: {os.getenv('RESEND_API_KEY')[:10]}...")
    print()

    # Initialize database
    db = EmailDatabase("test_email.db")
    await db.connect()
    print("✓ Database connected")

    # Create scheduler
    scheduler = EmailScheduler(db)
    print("✓ Scheduler initialized")
    print()

    # Test data
    test_audio_url = "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3"
    test_image_url = "https://picsum.photos/600/400"
    test_choices = [
        {
            "id": 1,
            "text": "Accept the mission and board the shuttle",
            "tone": "adventurous",
            "consequence_hint": "This will lead to exciting discoveries"
        },
        {
            "id": 2,
            "text": "Stay on the station and investigate the anomaly",
            "tone": "cautious",
            "consequence_hint": "Safety first, but you might miss something important"
        }
    ]

    # Send test email
    print("📧 Sending test chapter email...")
    success = await scheduler.send_immediate(
        user_email=recipient_email,
        session_id="test-session-123",
        chapter_number=1,
        audio_url=test_audio_url,
        image_url=test_image_url,
        choices=test_choices
    )

    if success:
        print("✅ Email sent successfully!")
        print()
        print("Check your inbox for:")
        print("  Subject: Chapter 1 is ready! 🎧")
        print("  From: StoryKeeper <story@storykeeper.app>")
        print()
        print("The email should contain:")
        print("  • Audio player with test audio")
        print("  • Test image")
        print("  • Two choice buttons")
    else:
        print("❌ Email failed to send")
        print("Check the error message above")

    await db.close()
    print("=" * 60)


async def test_welcome_email(recipient_email: str):
    """Test sending a welcome email"""
    from backend.email.database import EmailDatabase
    from backend.email.scheduler import EmailScheduler

    print("=" * 60)
    print("Testing Welcome Email")
    print("=" * 60)
    print(f"Recipient: {recipient_email}")
    print()

    # Initialize
    db = EmailDatabase("test_email.db")
    await db.connect()
    scheduler = EmailScheduler(db)

    # Send welcome email
    tomorrow_8am = (datetime.utcnow() + timedelta(days=1)).replace(
        hour=8, minute=0, second=0, microsecond=0
    )

    print("📧 Sending welcome email...")
    success = await scheduler.send_welcome_email(
        user_email=recipient_email,
        first_chapter_time=tomorrow_8am
    )

    if success:
        print("✅ Welcome email sent!")
        print()
        print("Check your inbox for:")
        print("  Subject: Welcome to StoryKeeper! Your story begins tomorrow.")
    else:
        print("❌ Failed to send welcome email")

    await db.close()
    print("=" * 60)


async def test_scheduled_email(recipient_email: str):
    """Test scheduling an email for later"""
    from backend.email.database import EmailDatabase
    from backend.email.scheduler import EmailScheduler

    print("=" * 60)
    print("Testing Email Scheduling")
    print("=" * 60)
    print(f"Recipient: {recipient_email}")
    print()

    # Initialize
    db = EmailDatabase("test_email.db")
    await db.connect()
    scheduler = EmailScheduler(db)

    # Schedule for 1 minute from now
    send_time = datetime.utcnow() + timedelta(minutes=1)

    print(f"📧 Scheduling email for: {send_time.isoformat()}")

    test_choices = [{"id": 1, "text": "Continue the story"}]

    await scheduler.schedule_chapter(
        user_email=recipient_email,
        session_id="test-session-456",
        chapter_number=2,
        audio_url="https://www.soundhelix.com/examples/mp3/SoundHelix-Song-2.mp3",
        image_url=None,
        choices=test_choices,
        send_at=send_time
    )

    print("✓ Email scheduled!")
    print()
    print("To send the scheduled email, run:")
    print("  python -m backend.email.scheduler")
    print()
    print("Or check the database:")
    print("  sqlite3 test_email.db 'SELECT * FROM scheduled_emails;'")

    await db.close()
    print("=" * 60)


async def main():
    if len(sys.argv) < 2:
        print("Usage: python test_email.py <your@email.com> [test_type]")
        print()
        print("Test types:")
        print("  immediate (default) - Send chapter email immediately")
        print("  welcome             - Send welcome email")
        print("  schedule            - Schedule email for later")
        print()
        print("Example:")
        print("  python test_email.py matt@example.com")
        print("  python test_email.py matt@example.com welcome")
        sys.exit(1)

    recipient = sys.argv[1]
    test_type = sys.argv[2] if len(sys.argv) > 2 else "immediate"

    if test_type == "immediate":
        await test_immediate_email(recipient)
    elif test_type == "welcome":
        await test_welcome_email(recipient)
    elif test_type == "schedule":
        await test_scheduled_email(recipient)
    else:
        print(f"❌ Unknown test type: {test_type}")
        print("Valid types: immediate, welcome, schedule")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
