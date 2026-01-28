"""
Pre-Show API Routes

Endpoints for the writing room drama that plays while stories generate.
Includes SSE streaming for real-time beat delivery and pre-show retrieval
for the library (rewatchable).
"""

import asyncio
import json
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from backend.database.preshows import PreshowService
from backend.database.jobs import JobQueueService
from backend.routes.auth import get_current_user_id


router = APIRouter(prefix="/api/preshow", tags=["preshow"])


# =============================================================================
# Response Models
# =============================================================================

class BeatResponse(BaseModel):
    """A single pre-show beat."""
    character: str
    action: str
    dialogue: str
    delay_ms: int = 1500


class PreshowResponse(BaseModel):
    """Full pre-show data."""
    preshow_id: str
    story_id: Optional[str] = None
    variation: str
    characters: list[str]
    beats: list[BeatResponse]
    created_at: str


class PreshowListResponse(BaseModel):
    """List of preshows for library."""
    preshows: list[PreshowResponse]
    total: int


# =============================================================================
# SSE Streaming Endpoint
# =============================================================================

@router.get("/{task_id}/stream")
async def stream_preshow(
    task_id: str,
    user_id: str = Depends(get_current_user_id)
):
    """
    Stream pre-show beats via Server-Sent Events.

    This endpoint streams the writing room drama while a story generates.
    Each beat is sent as an SSE event with timing for client-side display.

    Events:
    - beat: A pre-show beat (character, action, dialogue)
    - progress: Story generation progress update
    - complete: Story is ready (includes story_id)
    - error: Something went wrong
    """
    preshow_service = PreshowService()
    job_service = JobQueueService()

    # Get or wait for pre-show
    preshow = await preshow_service.get_by_task_id(task_id)

    async def generate():
        try:
            # If no pre-show exists yet, wait briefly and check again
            nonlocal preshow
            wait_attempts = 0
            while not preshow and wait_attempts < 10:
                await asyncio.sleep(0.5)
                preshow = await preshow_service.get_by_task_id(task_id)
                wait_attempts += 1

            if not preshow:
                # No pre-show available, just stream job status
                yield f"data: {json.dumps({'type': 'info', 'message': 'Story is being prepared...'})}\n\n"
            else:
                # Stream pre-show beats
                beats = preshow.get("beats", [])
                for i, beat in enumerate(beats):
                    beat_data = {
                        "type": "beat",
                        "character": beat.get("character"),
                        "action": beat.get("action"),
                        "dialogue": beat.get("dialogue"),
                        "beat_number": i + 1,
                        "total_beats": len(beats),
                    }
                    yield f"data: {json.dumps(beat_data)}\n\n"

                    # Wait for the beat's delay (converted from ms to seconds)
                    delay = beat.get("delay_ms", 1500) / 1000
                    await asyncio.sleep(delay)

            # Now wait for story to complete, sending progress updates
            completed = False
            check_count = 0
            max_checks = 360  # 3 minutes at 0.5s intervals

            while not completed and check_count < max_checks:
                job = await job_service.get_job_by_id(task_id)

                if not job:
                    yield f"data: {json.dumps({'type': 'error', 'message': 'Job not found'})}\n\n"
                    break

                status = job.get("status")
                progress = job.get("progress_percent", 0)
                current_step = job.get("current_step", "")

                # Send progress update
                progress_data = {
                    "type": "progress",
                    "status": status,
                    "progress_percent": progress,
                    "current_step": current_step,
                }
                yield f"data: {json.dumps(progress_data)}\n\n"

                if status == "completed":
                    # Story is ready!
                    result = job.get("result", {})
                    story_id = result.get("story", {}).get("id") or job.get("story_id")

                    complete_data = {
                        "type": "complete",
                        "story_ready": True,
                        "story_id": story_id,
                        "message": preshow.get("conclusion", "Your story is ready!") if preshow else "Your story is ready!",
                    }
                    yield f"data: {json.dumps(complete_data)}\n\n"
                    completed = True

                elif status == "failed":
                    error_data = {
                        "type": "error",
                        "message": job.get("error_message", "Story generation failed"),
                    }
                    yield f"data: {json.dumps(error_data)}\n\n"
                    break

                else:
                    # Still generating, wait and check again
                    await asyncio.sleep(0.5)
                    check_count += 1

            if not completed and check_count >= max_checks:
                yield f"data: {json.dumps({'type': 'error', 'message': 'Story generation timed out'})}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )


# =============================================================================
# Pre-Show Retrieval Endpoints
# =============================================================================

@router.get("/{preshow_id}", response_model=PreshowResponse)
async def get_preshow(
    preshow_id: str,
    user_id: str = Depends(get_current_user_id)
):
    """
    Get a pre-show by ID (for rewatch in library).
    """
    preshow_service = PreshowService()
    preshow = await preshow_service.get_by_id(preshow_id)

    if not preshow:
        raise HTTPException(status_code=404, detail="Pre-show not found")

    # Verify ownership
    if preshow.get("user_id") != user_id:
        raise HTTPException(status_code=403, detail="Not your pre-show")

    return PreshowResponse(
        preshow_id=preshow["id"],
        story_id=preshow.get("story_id"),
        variation=preshow["variation"],
        characters=preshow["characters"],
        beats=[
            BeatResponse(
                character=b["character"],
                action=b["action"],
                dialogue=b["dialogue"],
                delay_ms=b.get("delay_ms", 1500),
            )
            for b in preshow.get("beats", [])
        ],
        created_at=preshow["created_at"],
    )


@router.get("/story/{story_id}")
async def get_preshow_for_story(
    story_id: str,
    user_id: str = Depends(get_current_user_id)
):
    """
    Get the pre-show associated with a story.
    """
    preshow_service = PreshowService()
    preshow = await preshow_service.get_by_story_id(story_id)

    if not preshow:
        return {"preshow": None, "message": "No pre-show for this story"}

    # Verify ownership
    if preshow.get("user_id") != user_id:
        raise HTTPException(status_code=403, detail="Not your pre-show")

    return {
        "preshow": PreshowResponse(
            preshow_id=preshow["id"],
            story_id=preshow.get("story_id"),
            variation=preshow["variation"],
            characters=preshow["characters"],
            beats=[
                BeatResponse(
                    character=b["character"],
                    action=b["action"],
                    dialogue=b["dialogue"],
                    delay_ms=b.get("delay_ms", 1500),
                )
                for b in preshow.get("beats", [])
            ],
            created_at=preshow["created_at"],
        )
    }


@router.get("", response_model=PreshowListResponse)
async def list_preshows(
    limit: int = 20,
    offset: int = 0,
    user_id: str = Depends(get_current_user_id)
):
    """
    List user's pre-shows for the library.

    Pre-shows can be rewatched from here.
    """
    preshow_service = PreshowService()
    preshows = await preshow_service.get_user_preshows(
        user_id,
        limit=limit,
        offset=offset,
    )

    return PreshowListResponse(
        preshows=[
            PreshowResponse(
                preshow_id=p["id"],
                story_id=p.get("story_id"),
                variation=p["variation"],
                characters=p["characters"],
                beats=[
                    BeatResponse(
                        character=b["character"],
                        action=b["action"],
                        dialogue=b["dialogue"],
                        delay_ms=b.get("delay_ms", 1500),
                    )
                    for b in p.get("beats", [])
                ],
                created_at=p["created_at"],
            )
            for p in preshows
        ],
        total=len(preshows),
    )
