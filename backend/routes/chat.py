"""
Fixion Chat Routes

API endpoints for the Fixion chat interface including
onboarding, story discussions, and general chat.
"""

from typing import Optional, List
import json

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from backend.config import config
from backend.fixion import FixionService, FIXION_PERSONAS
from backend.routes.auth import get_current_user_id

router = APIRouter(prefix="/api/chat", tags=["chat"])


# =============================================================================
# Request/Response Models
# =============================================================================

class ChatRequest(BaseModel):
    """Request to send a chat message."""
    message: str
    context_type: Optional[str] = "general"  # general, onboarding, story_discussion, retell
    story_id: Optional[str] = None
    conversation_id: Optional[str] = None


class ChatResponse(BaseModel):
    """Response from Fixion."""
    message: str
    conversation_id: str
    context_type: str
    genre: Optional[str] = None


class GenreSelectionRequest(BaseModel):
    """Request to select a genre during onboarding."""
    genre: str
    conversation_id: str


class IntensitySelectionRequest(BaseModel):
    """Request to select intensity during onboarding."""
    intensity: str  # 'light', 'moderate', 'dark'
    conversation_id: str


class StoryDiscussionRequest(BaseModel):
    """Request to start discussing a story."""
    story_id: str
    message: Optional[str] = None


class RetellRequest(BaseModel):
    """Request to process a retell."""
    story_id: str
    feedback: str
    conversation_id: Optional[str] = None


class HallucinationReportRequest(BaseModel):
    """Request to report a hallucination."""
    story_id: str
    description: str
    excerpt: Optional[str] = None


class OnboardingResponse(BaseModel):
    """Response for onboarding steps."""
    message: str
    conversation_id: str
    onboarding_step: str
    genres: Optional[List[str]] = None
    genre: Optional[str] = None


# =============================================================================
# Chat Routes
# =============================================================================

@router.post("/message", response_model=ChatResponse)
async def send_message(
    request: ChatRequest,
    user_id: str = Depends(get_current_user_id)
):
    """
    Send a message to Fixion and get a response.

    This is the main chat endpoint for general conversation.
    """
    fixion = FixionService(user_id=user_id)

    try:
        result = await fixion.chat(
            user_message=request.message,
            context_type=request.context_type,
            story_id=request.story_id,
            conversation_id=request.conversation_id,
        )

        return ChatResponse(
            message=result["message"],
            conversation_id=result["conversation_id"],
            context_type=result["context_type"],
            genre=result.get("genre"),
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/message/stream")
async def send_message_stream(
    request: ChatRequest,
    user_id: str = Depends(get_current_user_id)
):
    """
    Send a message to Fixion and stream the response.

    Returns a Server-Sent Events stream for real-time display.
    """
    fixion = FixionService(user_id=user_id)

    # Get or create conversation before streaming so we have the ID
    from backend.database.conversations import ConversationService
    conv_service = ConversationService()

    if request.conversation_id:
        conversation = await conv_service.get_by_id(request.conversation_id)
        if not conversation:
            conversation = await conv_service.create(
                user_id, request.context_type or "general", request.story_id
            )
    else:
        conversation = await conv_service.get_or_create_active(
            user_id, request.context_type or "general", request.story_id
        )

    actual_conversation_id = conversation["id"]

    async def generate():
        try:
            async for chunk in fixion.chat_stream(
                user_message=request.message,
                context_type=request.context_type,
                story_id=request.story_id,
                conversation_id=actual_conversation_id,
            ):
                # Send token in JSON format expected by frontend
                token_data = json.dumps({"type": "token", "content": chunk})
                yield f"data: {token_data}\n\n"

            # Send done signal with conversation ID
            done_data = json.dumps({"type": "done", "conversation_id": actual_conversation_id})
            yield f"data: {done_data}\n\n"
        except Exception as e:
            error_data = json.dumps({"type": "error", "message": str(e)})
            yield f"data: {error_data}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


# =============================================================================
# Onboarding Routes
# =============================================================================

@router.post("/onboarding/start", response_model=OnboardingResponse)
async def start_onboarding(user_id: str = Depends(get_current_user_id)):
    """
    Start the onboarding conversation with Fixion.

    Returns Fixion's greeting and available genres.
    """
    fixion = FixionService(user_id=user_id)

    try:
        result = await fixion.start_onboarding()

        return OnboardingResponse(
            message=result["message"],
            conversation_id=result["conversation_id"],
            onboarding_step=result["onboarding_step"],
            genres=result.get("genres"),
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/onboarding/genre", response_model=OnboardingResponse)
async def select_genre(
    request: GenreSelectionRequest,
    user_id: str = Depends(get_current_user_id)
):
    """
    Select a genre during onboarding.

    Fixion will pivot to the genre-specific persona.
    """
    if request.genre.lower() not in FIXION_PERSONAS:
        available = list(FIXION_PERSONAS.keys())
        raise HTTPException(
            status_code=400,
            detail=f"Invalid genre. Available: {', '.join(available)}"
        )

    fixion = FixionService(user_id=user_id)

    try:
        result = await fixion.handle_genre_selection(
            genre=request.genre,
            conversation_id=request.conversation_id,
        )

        return OnboardingResponse(
            message=result["message"],
            conversation_id=result["conversation_id"],
            onboarding_step=result.get("onboarding_step", "intensity_selection"),
            genre=result.get("genre"),
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/onboarding/intensity", response_model=OnboardingResponse)
async def select_intensity(
    request: IntensitySelectionRequest,
    user_id: str = Depends(get_current_user_id)
):
    """
    Select intensity level during onboarding.
    """
    valid_intensities = ["light", "moderate", "dark"]
    if request.intensity.lower() not in valid_intensities:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid intensity. Options: {', '.join(valid_intensities)}"
        )

    fixion = FixionService(user_id=user_id)

    try:
        result = await fixion.handle_intensity_selection(
            intensity=request.intensity,
            conversation_id=request.conversation_id,
        )

        return OnboardingResponse(
            message=result["message"],
            conversation_id=result["conversation_id"],
            onboarding_step="protagonist",
            genre=result.get("genre"),
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/onboarding/genres")
async def get_available_genres():
    """Get list of available genres for onboarding."""
    return {
        "genres": [
            {
                "id": genre_id,
                "name": data["name"],
                "description": data.get("character_note", ""),
            }
            for genre_id, data in FIXION_PERSONAS.items()
        ]
    }


# =============================================================================
# Story Discussion Routes
# =============================================================================

@router.post("/story/discuss")
async def discuss_story(
    request: StoryDiscussionRequest,
    user_id: str = Depends(get_current_user_id)
):
    """
    Start or continue a discussion about a specific story.

    This is called when a user clicks "Talk to Fixion" from a story.
    """
    fixion = FixionService(user_id=user_id)

    try:
        result = await fixion.discuss_story(
            story_id=request.story_id,
            initial_message=request.message,
        )

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/story/retell")
async def request_retell(
    request: RetellRequest,
    user_id: str = Depends(get_current_user_id)
):
    """
    Process a retell/revision request.

    Fixion will analyze the feedback and determine revision type.
    """
    fixion = FixionService(user_id=user_id)

    try:
        result = await fixion.process_retell_request(
            story_id=request.story_id,
            feedback=request.feedback,
            conversation_id=request.conversation_id,
        )

        if "error" in result:
            raise HTTPException(
                status_code=404,
                detail="Story not found"
            )

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Hallucination Reporting
# =============================================================================

@router.post("/hallucination/report")
async def report_hallucination(
    request: HallucinationReportRequest,
    user_id: str = Depends(get_current_user_id)
):
    """
    Report a hallucination found in a story.

    User may receive a credit reward for finding it.
    """
    fixion = FixionService(user_id=user_id)

    try:
        result = await fixion.handle_hallucination_report(
            story_id=request.story_id,
            description=request.description,
        )

        # TODO: Actually save the hallucination and award credits
        # This would involve:
        # 1. Saving to hallucinations table
        # 2. Adding credits via CreditService
        # 3. Potentially generating a reward image

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Conversation History
# =============================================================================

@router.get("/conversations")
async def get_conversations(
    limit: int = 20,
    include_inactive: bool = False,
    user_id: str = Depends(get_current_user_id)
):
    """Get user's chat conversations."""
    from backend.database.conversations import ConversationService

    service = ConversationService()
    conversations = await service.get_user_conversations(
        user_id,
        limit=limit,
        include_inactive=include_inactive,
    )

    return {"conversations": conversations}


@router.get("/conversations/{conversation_id}")
async def get_conversation(
    conversation_id: str,
    user_id: str = Depends(get_current_user_id)
):
    """Get a specific conversation with messages."""
    from backend.database.conversations import ConversationService

    service = ConversationService()
    conversation = await service.get_by_id(conversation_id)

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Verify ownership
    if conversation.get("user_id") != user_id:
        raise HTTPException(status_code=403, detail="Not your conversation")

    return conversation


@router.get("/conversations/{conversation_id}/messages")
async def get_conversation_messages(
    conversation_id: str,
    limit: int = 50,
    user_id: str = Depends(get_current_user_id)
):
    """Get messages from a conversation."""
    from backend.database.conversations import ConversationService

    service = ConversationService()

    # Verify conversation exists and belongs to user
    conversation = await service.get_by_id(conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    if conversation.get("user_id") != user_id:
        raise HTTPException(status_code=403, detail="Not your conversation")

    messages = await service.get_messages(conversation_id, limit=limit)
    return {"messages": messages}


# =============================================================================
# Check-in Messages
# =============================================================================

@router.get("/checkin/{trigger}")
async def get_checkin_message(
    trigger: str,
    story_title: Optional[str] = None,
):
    """
    Get a check-in message template.

    Triggers: first_story, week_one, inactive, great_feedback
    """
    fixion = FixionService()
    message = fixion.get_checkin_message(trigger, story_title)

    return {
        "trigger": trigger,
        "message": message,
    }
