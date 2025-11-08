"""
Email choice handling endpoint.
When user clicks a choice button in an email, this processes it.
"""

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from datetime import datetime, timedelta
import os

from backend.api.routes import get_story_graph, active_sessions
from backend.storyteller.graph import run_story_turn
from backend.email.database import EmailDatabase
from backend.email.scheduler import EmailScheduler

router = APIRouter(tags=["email"])


@router.get("/choice", response_class=HTMLResponse)
async def handle_email_choice(request: Request, s: str, c: int):
    """
    Handle choice selection from email.

    Args:
        s: session_id
        c: choice_id

    Returns:
        HTML confirmation page
    """
    session_id = s
    choice_id = c

    try:
        # Load the story graph
        graph = await get_story_graph()

        # Get checkpoint to verify session exists
        config_dict = {"configurable": {"thread_id": session_id}}
        checkpoint = None
        if hasattr(graph, 'checkpointer') and graph.checkpointer:
            checkpoint = await graph.checkpointer.aget(config_dict)

        if not checkpoint:
            return _render_error_page(
                "Session not found",
                "This story session has expired or doesn't exist."
            )

        # Restore session if needed
        if session_id not in active_sessions:
            previous_state = checkpoint["channel_values"]
            active_sessions[session_id] = {
                "user_id": previous_state.get("user_id", "unknown"),
                "world_id": previous_state.get("world_id", "unknown"),
                "email": previous_state.get("user_email"),  # Will be None if not set
                "created_at": previous_state.get("session_start", datetime.utcnow().isoformat()),
                "last_access": datetime.utcnow().isoformat()
            }

        # Get previous state and find the choice
        previous_state = checkpoint["channel_values"]
        previous_choices = previous_state.get("choices", [])

        selected_choice = None
        for choice in previous_choices:
            if choice.get("id") == choice_id:
                selected_choice = choice
                break

        if not selected_choice:
            return _render_error_page(
                "Invalid choice",
                f"Choice {choice_id} not found for this chapter."
            )

        # Extract continuation text
        choice_continuation = selected_choice.get("text", "")
        choice_preview = choice_continuation[:100] + "..." if len(choice_continuation) > 100 else choice_continuation

        # Update state with choice
        previous_state["last_choice_continuation"] = choice_continuation

        # Format choice as user input
        user_input = f"Choice {choice_id}: {choice_continuation[:100]}..."

        # Run story turn asynchronously (generate next chapter)
        final_state, outputs = await run_story_turn(
            graph=graph,
            user_input=user_input,
            session_id=session_id,
            current_state=previous_state
        )

        # Get user email
        session_info = active_sessions.get(session_id, {})
        user_email = session_info.get("email")

        # Send/schedule next chapter email if user has email
        email_scheduled = False
        if user_email and outputs.get("audio_url"):
            try:
                # Initialize email system
                email_db_path = os.getenv("EMAIL_DB_PATH", "email_scheduler.db")
                email_db = EmailDatabase(email_db_path)
                await email_db.connect()
                email_scheduler = EmailScheduler(email_db)

                # Check dev mode
                dev_mode = os.getenv("EMAIL_DEV_MODE", "false").lower() == "true"

                if dev_mode:
                    # Send immediately
                    await email_scheduler.send_immediate(
                        user_email=user_email,
                        session_id=session_id,
                        chapter_number=outputs["current_beat"],
                        audio_url=outputs["audio_url"],
                        image_url=outputs.get("image_url"),
                        choices=outputs["choices"]
                    )
                    email_scheduled = "immediate"
                else:
                    # Schedule for tomorrow 8am
                    tomorrow_8am = (datetime.utcnow() + timedelta(days=1)).replace(
                        hour=8, minute=0, second=0, microsecond=0
                    )
                    await email_scheduler.schedule_chapter(
                        user_email=user_email,
                        session_id=session_id,
                        chapter_number=outputs["current_beat"],
                        audio_url=outputs["audio_url"],
                        image_url=outputs.get("image_url"),
                        choices=outputs["choices"],
                        send_at=tomorrow_8am
                    )
                    email_scheduled = "scheduled"

                await email_db.close()
            except Exception as e:
                print(f"⚠️  Error scheduling email: {e}")

        # Render success page
        return _render_success_page(
            choice_text=choice_preview,
            chapter_number=outputs["current_beat"],
            email_status=email_scheduled,
            has_email=bool(user_email)
        )

    except Exception as e:
        print(f"❌ Error processing email choice: {e}")
        import traceback
        traceback.print_exc()
        return _render_error_page(
            "Something went wrong",
            "We couldn't process your choice. Please try again later."
        )


def _render_success_page(
    choice_text: str,
    chapter_number: int,
    email_status: str | bool,
    has_email: bool
) -> str:
    """Render success confirmation page"""

    # Determine email message
    if email_status == "immediate":
        email_msg = f"""
        <div class="email-status sent">
            📧 <strong>Chapter {chapter_number} sent to your inbox!</strong><br>
            <span style="font-size: 14px; color: #666;">Check your email in a few seconds</span>
        </div>
        """
    elif email_status == "scheduled":
        email_msg = f"""
        <div class="email-status scheduled">
            📅 <strong>Chapter {chapter_number} scheduled for tomorrow at 8:00 AM</strong><br>
            <span style="font-size: 14px; color: #666;">We'll send it to your inbox</span>
        </div>
        """
    elif has_email:
        email_msg = """
        <div class="email-status">
            ⚠️ <strong>Email system unavailable</strong><br>
            <span style="font-size: 14px; color: #666;">Please check back later</span>
        </div>
        """
    else:
        email_msg = """
        <div class="email-status">
            💡 <strong>Want chapters via email?</strong><br>
            <span style="font-size: 14px; color: #666;">Start a new story at storykeeper.app</span>
        </div>
        """

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Choice Received - StoryKeeper</title>
        <style>
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}

            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 20px;
            }}

            .container {{
                background: white;
                border-radius: 16px;
                box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                max-width: 600px;
                width: 100%;
                padding: 48px;
                text-align: center;
                animation: slideUp 0.5s ease;
            }}

            @keyframes slideUp {{
                from {{
                    opacity: 0;
                    transform: translateY(30px);
                }}
                to {{
                    opacity: 1;
                    transform: translateY(0);
                }}
            }}

            .checkmark {{
                width: 80px;
                height: 80px;
                margin: 0 auto 24px;
                background: #10b981;
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 48px;
                animation: scaleIn 0.6s ease;
            }}

            @keyframes scaleIn {{
                from {{
                    transform: scale(0);
                }}
                to {{
                    transform: scale(1);
                }}
            }}

            h1 {{
                color: #1a1a1a;
                font-size: 32px;
                margin-bottom: 16px;
            }}

            .choice-preview {{
                background: #f8f9fa;
                border-left: 4px solid #667eea;
                padding: 20px;
                border-radius: 8px;
                margin: 24px 0;
                text-align: left;
            }}

            .choice-preview p {{
                color: #404040;
                line-height: 1.6;
                font-size: 16px;
                font-style: italic;
            }}

            .email-status {{
                background: #e0e7ff;
                border-radius: 12px;
                padding: 24px;
                margin: 32px 0;
            }}

            .email-status.sent {{
                background: #d1fae5;
            }}

            .email-status.scheduled {{
                background: #fef3c7;
            }}

            .footer {{
                margin-top: 32px;
                color: #999;
                font-size: 14px;
            }}

            .logo {{
                font-weight: 700;
                color: #667eea;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="checkmark">✓</div>

            <h1>Choice Received!</h1>

            <div class="choice-preview">
                <p>"{choice_text}"</p>
            </div>

            {email_msg}

            <div class="footer">
                <p><span class="logo">StoryKeeper</span> • Your choices, your story</p>
            </div>
        </div>
    </body>
    </html>
    """


def _render_error_page(title: str, message: str) -> str:
    """Render error page"""
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Error - StoryKeeper</title>
        <style>
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}

            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 20px;
            }}

            .container {{
                background: white;
                border-radius: 16px;
                box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                max-width: 600px;
                width: 100%;
                padding: 48px;
                text-align: center;
            }}

            .error-icon {{
                width: 80px;
                height: 80px;
                margin: 0 auto 24px;
                background: #ef4444;
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 48px;
            }}

            h1 {{
                color: #1a1a1a;
                font-size: 28px;
                margin-bottom: 16px;
            }}

            p {{
                color: #666;
                line-height: 1.6;
                font-size: 16px;
            }}

            .footer {{
                margin-top: 32px;
                color: #999;
                font-size: 14px;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="error-icon">✗</div>
            <h1>{title}</h1>
            <p>{message}</p>
            <div class="footer">
                <p>StoryKeeper</p>
            </div>
        </div>
    </body>
    </html>
    """
