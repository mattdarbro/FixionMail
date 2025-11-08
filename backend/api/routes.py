"""
API routes for storytelling endpoints.

Handles story session creation, continuation, and retrieval.
"""

import uuid
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse
import json
import os

from backend.models.state import (
    StartStoryRequest,
    StartStoryResponse,
    ContinueStoryRequest,
    ContinueStoryResponse,
    GetSessionRequest,
    GetSessionResponse,
    ErrorResponse,
    Choice,
    create_initial_state,
    format_choice_for_api
)
from backend.storyteller.graph import create_persistent_graph, run_story_turn
from backend.email.database import EmailDatabase
from backend.email.scheduler import EmailScheduler

# Import config at module level
try:
    from backend.config import config
except Exception as e:
    # Fallback if config fails to load
    print(f"⚠️  Config loading failed: {e}")
    class DummyConfig:
        CREDITS_PER_NEW_USER = 25
        ENABLE_CREDIT_SYSTEM = False
        DEBUG = False
    config = DummyConfig()

# Create router
router = APIRouter(tags=["story"])

# Global graph instance with persistence
story_graph = None
story_graph_checkpointer = None

# Global email scheduler instance
email_db = None
email_scheduler = None

async def initialize_email_system():
    """Initialize email database and scheduler (call during app startup)."""
    global email_db, email_scheduler

    if email_db is None:
        try:
            # Use environment variable for email DB path, or default
            email_db_path = os.getenv("EMAIL_DB_PATH", "email_scheduler.db")
            print(f"📧 Initializing email system with DB: {email_db_path}")

            email_db = EmailDatabase(email_db_path)
            await email_db.connect()

            email_scheduler = EmailScheduler(email_db)
            print(f"✓ Email system initialized successfully")
        except Exception as e:
            print(f"⚠️  Error initializing email system: {e}")
            import traceback
            traceback.print_exc()
            raise

async def initialize_story_graph():
    """Initialize the story graph with async checkpointer (call during app startup)."""
    global story_graph, story_graph_checkpointer
    if story_graph is None:
        try:
            from pathlib import Path
            from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

            # Use the property that resolves to persistent storage if available
            db_path = config.checkpoint_db_path
            print(f"📝 Initializing story graph with checkpoint DB: {db_path}")

            # Ensure database directory exists with proper permissions
            db_file = Path(db_path)
            db_dir = db_file.parent
            import os

            print(f"🔍 Checking database directory: {db_dir}")
            print(f"   Directory exists: {db_dir.exists()}")

            if not db_dir.exists():
                print(f"   Creating directory: {db_dir}")
                db_dir.mkdir(parents=True, exist_ok=True)
                print(f"   ✓ Directory created")

            # Check permissions
            print(f"   Directory readable: {os.access(db_dir, os.R_OK)}")
            print(f"   Directory writable: {os.access(db_dir, os.W_OK)}")
            print(f"   Directory executable: {os.access(db_dir, os.X_OK)}")

            # Create async checkpointer - create connection directly
            from backend.storyteller.graph import create_storyteller_graph
            import aiosqlite

            db_path_str = str(db_file.absolute())
            print(f"📝 Creating checkpointer with path: {db_path_str}")

            # Create a persistent connection for the checkpointer
            conn = await aiosqlite.connect(db_path_str)
            story_graph_checkpointer = AsyncSqliteSaver(conn)

            # Create the graph with the checkpointer directly
            story_graph = create_storyteller_graph(checkpointer=story_graph_checkpointer)
            print(f"✓ Story graph initialized successfully with async checkpointer")
        except Exception as e:
            print(f"⚠️  Error creating story graph: {e}")
            print(f"   Error type: {type(e).__name__}")
            import traceback
            traceback.print_exc()
            raise

async def get_story_graph():
    """Get the story graph (initializes on first use if not already initialized)."""
    global story_graph, story_graph_checkpointer

    if story_graph is None:
        # Fallback: Try to initialize now if it wasn't done during startup
        print("⚠️  Story graph not initialized during startup. Attempting lazy initialization...")

        try:
            from pathlib import Path
            from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
            from backend.storyteller.graph import create_storyteller_graph
            import os

            # Use the property that resolves to persistent storage if available
            db_path = config.checkpoint_db_path
            print(f"📝 Lazy-initializing story graph with checkpoint DB: {db_path}")

            # Ensure database directory exists with proper permissions
            db_file = Path(db_path)
            db_dir = db_file.parent

            print(f"🔍 Checking database directory: {db_dir}")
            print(f"   Directory exists: {db_dir.exists()}")

            if not db_dir.exists():
                print(f"   Creating directory: {db_dir}")
                db_dir.mkdir(parents=True, exist_ok=True)
                print(f"   ✓ Directory created")

            # Check permissions
            print(f"   Directory readable: {os.access(db_dir, os.R_OK)}")
            print(f"   Directory writable: {os.access(db_dir, os.W_OK)}")
            print(f"   Directory executable: {os.access(db_dir, os.X_OK)}")

            # Check if database file already exists
            if db_file.exists():
                print(f"   Database file exists: {db_file}")
                print(f"   File readable: {os.access(db_file, os.R_OK)}")
                print(f"   File writable: {os.access(db_file, os.W_OK)}")
            else:
                print(f"   Database file does not exist yet (will be created)")

            # Initialize async checkpointer (we're already in async context)
            # Create connection directly - simpler and avoids context manager issues
            import aiosqlite

            db_path_str = str(db_file.absolute())
            print(f"📝 Creating checkpointer with path: {db_path_str}")

            # Create a persistent connection for the checkpointer
            conn = await aiosqlite.connect(db_path_str)
            story_graph_checkpointer = AsyncSqliteSaver(conn)

            # Create the graph with the checkpointer directly
            story_graph = create_storyteller_graph(checkpointer=story_graph_checkpointer)
            print(f"✓ Story graph lazy-initialized successfully")

        except Exception as e:
            print(f"❌ Failed to lazy-initialize story graph: {e}")
            print(f"   Error type: {type(e).__name__}")
            import traceback
            traceback.print_exc()
            raise RuntimeError(f"Story graph initialization failed: {e}") from e

    return story_graph

# In-memory session store (in production, use Redis or database)
active_sessions: dict[str, dict] = {}


# ===== List Available Worlds =====

@router.get("/worlds", response_model=list[str])
async def list_worlds():
    """List all available story worlds (based on world_template.json)."""
    try:
        from pathlib import Path

        story_worlds_dir = Path("story_worlds")
        if not story_worlds_dir.exists():
            return []

        # Find all directories with world_template.json
        worlds = []
        for world_dir in story_worlds_dir.iterdir():
            if world_dir.is_dir():
                template_path = world_dir / "world_template.json"
                if template_path.exists():
                    worlds.append(world_dir.name)

        return worlds
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error listing worlds: {str(e)}"
        )


# ===== Start New Story =====

@router.post("/story/start", response_model=StartStoryResponse)
async def start_story(request: StartStoryRequest):
    """
    Start a new story session.

    Creates a new session, initializes state, and generates the opening narrative.
    """
    try:
        # Generate session and user IDs
        session_id = str(uuid.uuid4())
        user_id = request.user_id or str(uuid.uuid4())

        # Validate world exists (check for world_template.json)
        from pathlib import Path

        world_template_path = Path("story_worlds") / request.world_id / "world_template.json"
        if not world_template_path.exists():
            raise HTTPException(
                status_code=404,
                detail=f"World '{request.world_id}' not found. Missing world_template.json at {world_template_path}"
            )

        print(f"✓ Found world template for '{request.world_id}'")

        # Create initial state
        initial_state = create_initial_state(
            user_id=user_id,
            world_id=request.world_id,
            credits=config.CREDITS_PER_NEW_USER,
            total_chapters=config.TOTAL_CHAPTERS
        )

        # Run first turn (opening narrative)
        final_state, outputs = await run_story_turn(
            graph=await get_story_graph(),
            user_input="Begin the story",
            session_id=session_id,
            current_state=initial_state
        )

        # Store session
        active_sessions[session_id] = {
            "user_id": user_id,
            "world_id": request.world_id,
            "email": request.email,  # Store email for later use
            "created_at": datetime.utcnow().isoformat(),
            "last_access": datetime.utcnow().isoformat()
        }

        # Store user email in database if provided
        if request.email and email_db:
            await email_db.store_user(
                user_id=user_id,
                email=request.email,
                session_id=session_id,
                world_id=request.world_id
            )
            print(f"📧 Stored email for user {user_id}: {request.email}")

            # Send welcome email (optional - can be enabled/disabled via env var)
            if os.getenv("SEND_WELCOME_EMAIL", "false").lower() == "true" and email_scheduler:
                # Schedule first chapter for tomorrow at 8 AM
                tomorrow_8am = (datetime.utcnow() + timedelta(days=1)).replace(hour=8, minute=0, second=0, microsecond=0)
                try:
                    await email_scheduler.send_welcome_email(
                        user_email=request.email,
                        first_chapter_time=tomorrow_8am
                    )
                    print(f"✅ Sent welcome email to {request.email}")
                except Exception as e:
                    print(f"⚠️  Failed to send welcome email: {e}")

        # Build response
        response = StartStoryResponse(
            session_id=session_id,
            user_id=user_id,
            world_id=request.world_id,
            current_beat=outputs["current_beat"],
            narrative=outputs["narrative"],
            choices=[format_choice_for_api(c) for c in outputs["choices"]],
            image_url=outputs.get("image_url"),
            audio_url=outputs.get("audio_url"),
            credits_remaining=outputs["credits_remaining"]
        )

        return response

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error starting story: {str(e)}"
        )


# ===== Continue Story =====

@router.post("/story/continue", response_model=ContinueStoryResponse)
async def continue_story(request: ContinueStoryRequest):
    """
    Continue the story with a player choice.

    Processes the selected choice and generates the next story segment.
    """
    try:
        # Load previous state from checkpoint (source of truth)
        graph = await get_story_graph()
        config_dict = {"configurable": {"thread_id": request.session_id}}

        checkpoint = None
        if hasattr(graph, 'checkpointer') and graph.checkpointer:
            checkpoint = await graph.checkpointer.aget(config_dict)

        if not checkpoint:
            raise HTTPException(
                status_code=404,
                detail=f"Session not found: {request.session_id}. The session may have expired or the server was restarted."
            )

        # If checkpoint exists but active_sessions doesn't have it, restore it
        # (This can happen after Railway redeploys)
        if request.session_id not in active_sessions:
            print(f"⚠️  Restoring session {request.session_id} from checkpoint (was missing from active_sessions)")
            previous_state = checkpoint["channel_values"]
            active_sessions[request.session_id] = {
                "user_id": previous_state.get("user_id", "unknown"),
                "world_id": previous_state.get("world_id", "unknown"),
                "created_at": previous_state.get("session_start", datetime.utcnow().isoformat()),
                "last_access": datetime.utcnow().isoformat()
            }

        # Update last access
        active_sessions[request.session_id]["last_access"] = datetime.utcnow().isoformat()

        previous_state = checkpoint["channel_values"]

        # Find the selected choice and extract its continuation text
        previous_choices = previous_state.get("choices", [])
        selected_choice = None

        # Debug logging
        print(f"\n{'='*70}")
        print(f"DEBUG: CONTINUE STORY REQUEST")
        print(f"{'='*70}")
        print(f"🔍 Session ID: {request.session_id}")
        print(f"🔍 Requested choice_id: {request.choice_id} (type: {type(request.choice_id).__name__})")
        print(f"🔍 Previous choices count: {len(previous_choices)}")
        print(f"\nPrevious choices in state:")
        for i, choice in enumerate(previous_choices):
            choice_id = choice.get('id')
            choice_text = choice.get('text', '')[:50]
            print(f"  [{i}] id={choice_id} (type: {type(choice_id).__name__})")
            print(f"      text='{choice_text}...'")
            print(f"      Match? {choice_id == request.choice_id} (strict), {str(choice_id) == str(request.choice_id)} (as strings)")

        # Try to find the choice
        for choice in previous_choices:
            if choice.get("id") == request.choice_id:
                selected_choice = choice
                break

        if not selected_choice:
            print(f"\n❌ DEBUG: Could not find choice with id={request.choice_id}")
            print(f"Available IDs: {[c.get('id') for c in previous_choices]}")
            raise HTTPException(
                status_code=400,
                detail=f"Invalid choice ID: {request.choice_id}. Available: {[c.get('id') for c in previous_choices]}"
            )

        print(f"\n✓ DEBUG: Found selected choice:")
        print(f"  ID: {selected_choice.get('id')}")
        print(f"  Text: {selected_choice.get('text', '')[:100]}...")
        print(f"{'='*70}\n")

        # Extract the continuation text
        choice_continuation = selected_choice.get("text", "")

        # Update state with the continuation text before running the turn
        previous_state["last_choice_continuation"] = choice_continuation

        # Format choice as user input (for message history)
        user_input = f"Choice {request.choice_id}: {choice_continuation[:100]}..."

        # Run story turn with updated state
        final_state, outputs = await run_story_turn(
            graph=graph,
            user_input=user_input,
            session_id=request.session_id,
            current_state=previous_state  # Pass updated state
        )

        # Check for errors
        if outputs.get("error"):
            raise HTTPException(
                status_code=500,
                detail=outputs["error"]
            )

        # Check credits
        if config.ENABLE_CREDIT_SYSTEM and outputs["credits_remaining"] <= 0:
            return JSONResponse(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                content={
                    "error": "Insufficient credits",
                    "credits_remaining": 0,
                    "message": "You've run out of story credits. Please purchase more to continue."
                }
            )

        # Schedule next chapter email if user has email stored
        session_info = active_sessions.get(request.session_id, {})
        user_email = session_info.get("email")

        if user_email and email_scheduler and outputs.get("audio_url"):
            # Determine send time: immediate (dev mode) or scheduled (tomorrow 8am)
            dev_mode = os.getenv("EMAIL_DEV_MODE", "false").lower() == "true"

            if dev_mode:
                # Dev mode: send immediately
                print(f"📧 [DEV MODE] Sending chapter {outputs['current_beat']} immediately to {user_email}")
                try:
                    await email_scheduler.send_immediate(
                        user_email=user_email,
                        session_id=request.session_id,
                        chapter_number=outputs["current_beat"],
                        audio_url=outputs["audio_url"],
                        image_url=outputs.get("image_url"),
                        choices=outputs["choices"]
                    )
                except Exception as e:
                    print(f"⚠️  Failed to send immediate email: {e}")
            else:
                # Production mode: schedule for tomorrow at 8 AM
                tomorrow_8am = (datetime.utcnow() + timedelta(days=1)).replace(
                    hour=8, minute=0, second=0, microsecond=0
                )
                print(f"📧 Scheduling chapter {outputs['current_beat']} for {user_email} at {tomorrow_8am}")
                try:
                    await email_scheduler.schedule_chapter(
                        user_email=user_email,
                        session_id=request.session_id,
                        chapter_number=outputs["current_beat"],
                        audio_url=outputs["audio_url"],
                        image_url=outputs.get("image_url"),
                        choices=outputs["choices"],
                        send_at=tomorrow_8am
                    )
                except Exception as e:
                    print(f"⚠️  Failed to schedule email: {e}")

        # Build response
        response = ContinueStoryResponse(
            session_id=request.session_id,
            current_beat=outputs["current_beat"],
            beat_complete=outputs["beat_complete"],
            narrative=outputs["narrative"],
            choices=[format_choice_for_api(c) for c in outputs["choices"]],
            image_url=outputs.get("image_url"),
            audio_url=outputs.get("audio_url"),
            credits_remaining=outputs["credits_remaining"]
        )

        return response

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error continuing story: {str(e)}"
        )


# ===== Get Session State =====

@router.get("/story/session/{session_id}", response_model=GetSessionResponse)
async def get_session(session_id: str):
    """
    Retrieve current session state.

    Useful for resuming a session or checking progress.
    """
    try:
        # Validate session exists
        if session_id not in active_sessions:
            raise HTTPException(
                status_code=404,
                detail=f"Session not found: {session_id}"
            )

        session_info = active_sessions[session_id]

        # Load state from checkpoint
        # Note: MemorySaver stores in memory, so we need to get from the graph
        # For now, return session info (in production, use persistent checkpointer)
        config_dict = {"configurable": {"thread_id": session_id}}

        # Get latest checkpoint from graph's memory
        graph = await get_story_graph()
        checkpoint = await graph.checkpointer.aget(config_dict) if hasattr(graph, 'checkpointer') else None

        if not checkpoint:
            raise HTTPException(
                status_code=404,
                detail="No checkpoint found for session"
            )

        state = checkpoint["channel_values"]

        # Build response
        response = GetSessionResponse(
            session_id=session_id,
            user_id=session_info["user_id"],
            world_id=session_info["world_id"],
            current_beat=state.get("current_beat", 1),
            beat_progress=state.get("beat_progress", {}),
            credits_remaining=state.get("credits_remaining", 0),
            session_start=session_info["created_at"],
            last_narrative=state.get("narrative_text", ""),
            last_choices=[format_choice_for_api(c) for c in state.get("choices", [])]
        )

        return response

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving session: {str(e)}"
        )


# ===== Delete Session =====

@router.delete("/story/session/{session_id}")
async def delete_session(session_id: str):
    """
    Delete a story session.

    Removes session from memory. Checkpoint remains in database.
    """
    if session_id not in active_sessions:
        raise HTTPException(
            status_code=404,
            detail=f"Session not found: {session_id}"
        )

    del active_sessions[session_id]

    return {"message": f"Session {session_id} deleted", "session_id": session_id}


# ===== Get Active Sessions (Debug Only) =====

@router.get("/sessions")
async def list_sessions():
    """List all active sessions (debug endpoint)."""
    if not config.DEBUG:
        raise HTTPException(
            status_code=403,
            detail="Debug endpoints disabled in production"
        )

    return {
        "active_sessions": len(active_sessions),
        "sessions": [
            {
                "session_id": sid,
                "user_id": info["user_id"],
                "world_id": info["world_id"],
                "created_at": info["created_at"],
                "last_access": info["last_access"]
            }
            for sid, info in active_sessions.items()
        ]
    }


# ===== Streaming Endpoints (REMOVED) =====
# Streaming is not needed for async email delivery.
# Images and audio will be generated server-side and sent via email.
