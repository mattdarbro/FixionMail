"""
API routes for storytelling endpoints.

Handles story session creation, continuation, and retrieval.
"""

import uuid
from datetime import datetime
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse, StreamingResponse
import asyncio
import json

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

# Global graph instance with persistence (lazy-loaded)
story_graph = None

def get_story_graph():
    """Get or create the story graph (lazy initialization)."""
    global story_graph
    if story_graph is None:
        try:
            # Use the property that resolves to persistent storage if available
            db_path = config.checkpoint_db_path
            print(f"📝 Initializing story graph with checkpoint DB: {db_path}")
            story_graph = create_persistent_graph(db_path=db_path)
        except Exception as e:
            print(f"⚠️  Error creating story graph: {e}")
            import traceback
            traceback.print_exc()
            raise
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
            credits=config.CREDITS_PER_NEW_USER
        )

        # Run first turn (opening narrative)
        final_state, outputs = await run_story_turn(
            graph=get_story_graph(),
            user_input="Begin the story",
            session_id=session_id,
            current_state=initial_state
        )

        # Store session
        active_sessions[session_id] = {
            "user_id": user_id,
            "world_id": request.world_id,
            "created_at": datetime.utcnow().isoformat(),
            "last_access": datetime.utcnow().isoformat()
        }

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
        graph = get_story_graph()
        config_dict = {"configurable": {"thread_id": request.session_id}}

        checkpoint = None
        if hasattr(graph, 'checkpointer') and graph.checkpointer:
            checkpoint = graph.checkpointer.get(config_dict)

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
        graph = get_story_graph()
        checkpoint = graph.checkpointer.get(config_dict) if hasattr(graph, 'checkpointer') else None

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


# ===== Streaming Endpoints =====

@router.post("/story/continue/stream")
async def continue_story_stream(request: ContinueStoryRequest):
    """
    Continue the story with streaming response.
    
    Streams narrative text, choices, and media URLs as they become available.
    """
    async def generate_stream():
        try:
            # Validate session exists
            if request.session_id not in active_sessions:
                yield f"data: {json.dumps({'type': 'error', 'message': 'Session not found'})}\n\n"
                return

            # Get story graph
            graph = get_story_graph()
            
            # Get current state
            current_state = await graph.aget_state(request.session_id)
            if not current_state:
                yield f"data: {json.dumps({'type': 'error', 'message': 'Session state not found'})}\n\n"
                return

            # Stream initial loading state
            yield f"data: {json.dumps({'type': 'loading', 'message': 'Processing your choice...'})}\n\n"
            await asyncio.sleep(0.1)

            # Run story turn
            final_state, outputs = await run_story_turn(
                graph=graph,
                user_input=request.choice_text,
                session_id=request.session_id,
                current_state=current_state
            )

            # Stream narrative text (simulate word-by-word)
            narrative = outputs["narrative"]
            words = narrative.split()
            current_text = ""
            
            for i, word in enumerate(words):
                current_text += word + " "
                yield f"data: {json.dumps({'type': 'narrative', 'text': current_text.strip()})}\n\n"
                await asyncio.sleep(0.05)  # 50ms delay between words

            # Stream choices when ready
            choices = [format_choice_for_api(c) for c in outputs["choices"]]
            yield f"data: {json.dumps({'type': 'choices', 'choices': choices})}\n\n"

            # Stream image URL if available
            if outputs.get("image_url"):
                yield f"data: {json.dumps({'type': 'image', 'url': outputs['image_url']})}\n\n"

            # Stream audio URL if available
            if outputs.get("audio_url"):
                yield f"data: {json.dumps({'type': 'audio', 'url': outputs['audio_url']})}\n\n"

            # Stream final state
            yield f"data: {json.dumps({'type': 'complete', 'beat': outputs['current_beat'], 'credits': outputs['credits_remaining']})}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        generate_stream(),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "*",
        }
    )
