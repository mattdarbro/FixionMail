#!/usr/bin/env python3
"""
Test email delivery with a REAL story session.
This creates an actual story session, then sends the chapter email.

Usage:
    python test_email_with_session.py your@email.com
"""

import asyncio
import sys
import os
import httpx
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Check for Resend API key
if not os.getenv("RESEND_API_KEY"):
    print("❌ Error: RESEND_API_KEY not set in .env file")
    sys.exit(1)


async def create_story_session(base_url: str):
    """Create a real story session via the API"""
    async with httpx.AsyncClient(timeout=120.0) as client:
        print("📚 Creating story session...")

        response = await client.post(
            f"{base_url}/api/story/start",
            json={
                "world_id": "west_haven",
                "user_id": None  # Will auto-generate
            }
        )

        if response.status_code != 200:
            print(f"❌ Failed to create session: {response.status_code}")
            print(response.text)
            return None

        data = response.json()
        print(f"✅ Session created: {data['session_id']}")
        return data


async def test_real_email_flow(recipient_email: str):
    """Test with a real story session"""
    from backend.email.database import EmailDatabase
    from backend.email.scheduler import EmailScheduler

    base_url = os.getenv("APP_BASE_URL", "http://localhost:8000")

    print("=" * 60)
    print("Testing Email with Real Story Session")
    print("=" * 60)
    print(f"Recipient: {recipient_email}")
    print(f"Backend URL: {base_url}")
    print()

    # Create a real story session
    session_data = await create_story_session(base_url)

    if not session_data:
        print("❌ Could not create story session")
        return

    session_id = session_data["session_id"]
    narrative = session_data["narrative"]
    choices = session_data["choices"]
    audio_url = session_data.get("audio_url")
    image_url = session_data.get("image_url")
    current_beat = session_data.get("current_beat", 1)

    print(f"\n📖 Story started!")
    print(f"   Session ID: {session_id}")
    print(f"   Chapter: {current_beat}")
    print(f"   Narrative: {narrative[:100]}...")
    print(f"   Choices: {len(choices)}")
    print(f"   Audio: {audio_url}")
    print()

    # Initialize email system
    db = EmailDatabase("test_email.db")
    await db.connect()
    scheduler = EmailScheduler(db)

    # Send email with REAL session data
    print("📧 Sending chapter email...")
    success = await scheduler.send_immediate(
        user_email=recipient_email,
        session_id=session_id,
        chapter_number=current_beat,
        audio_url=audio_url or "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3",
        image_url=image_url,
        choices=choices
    )

    if success:
        print("✅ Email sent successfully!")
        print()
        print("📬 Check your inbox for:")
        print(f"   Subject: Chapter {current_beat} is ready! 🎧")
        print("   From: onboarding@resend.dev")
        print()
        print("🎯 The email contains:")
        if audio_url:
            print("   • Real chapter audio (20 min!)")
        else:
            print("   • Test audio player")
        if image_url:
            print(f"   • Chapter image")
        print(f"   • {len(choices)} choice buttons")
        print()
        print("🚀 Click a choice button to test the full flow!")
        print(f"   It will link to: {base_url}/api/choice")
        print()
        print("✨ The choice will:")
        print("   1. Show confirmation page")
        print("   2. Generate next chapter")
        print("   3. Send next email immediately (dev mode)")
    else:
        print("❌ Email failed to send")

    await db.close()
    print("=" * 60)


async def main():
    if len(sys.argv) < 2:
        print("Usage: python test_email_with_session.py <your@email.com>")
        print()
        print("This will:")
        print("  1. Create a real story session")
        print("  2. Send chapter email with real session ID")
        print("  3. Choice buttons will work!")
        sys.exit(1)

    recipient = sys.argv[1]
    await test_real_email_flow(recipient)


if __name__ == "__main__":
    asyncio.run(main())
