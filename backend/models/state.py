"""
Story state models using TypedDict for LangGraph and Pydantic for API validation.

TypedDict is used for LangGraph state (efficient, type-checked).
Pydantic models are used for API request/response validation.
"""

from datetime import datetime
from typing import Annotated, TypedDict, Literal
from pydantic import BaseModel, Field
from langchain_core.messages import BaseMessage


# ===== LangGraph State Schema (TypedDict) =====

class StoryState(TypedDict):
    """
    Complete story session state for LangGraph workflow.

    This is the single source of truth for all story data during execution.
    All LangGraph nodes receive and return this state.
    """

    # ===== Core Narrative State =====
    messages: Annotated[list[BaseMessage], "Conversation history between user and AI"]

    # Chapter tracking (primary navigation)
    chapter_number: Annotated[int, "Current chapter number (1-30)"]
    total_chapters: Annotated[int, "Total chapters in story (default: 30)"]
    story_progress_pct: Annotated[float, "Overall story progress percentage (0-100)"]

    # Beat tracking (for pacing within chapters)
    current_beat: Annotated[int, "Current story beat (1-indexed)"]
    turns_in_beat: Annotated[int, "Number of turns completed in current beat"]
    beat_progress_score: Annotated[float, "Progress through current beat (0.0-1.0)"]
    beat_progress: Annotated[dict[int, bool], "Completion status for each beat"]

    story_summary: Annotated[list[str], "AI-generated summaries of key events (2-3 sentences each)"]

    # ===== Generated Story Bible (Dynamic) =====
    generated_story_bible: Annotated[dict, "Claude-generated story details (characters, locations, events)"]
    last_choice_continuation: Annotated[str | None, "The continuation text from last selected choice"]

    # ===== Temporary (for backwards compatibility) =====
    retrieved_context: Annotated[str, "RAG-retrieved lore from story bible (deprecated, use generated_story_bible)"]

    # ===== Generated Content =====
    narrative_text: Annotated[str, "Current story segment text"]
    choices: Annotated[list[dict], "Available player choices with continuation text"]
    image_prompt: Annotated[str | None, "Prompt for image generation"]
    image_url: Annotated[str | None, "Generated image URL"]
    audio_url: Annotated[str | None, "Generated audio URL"]

    # ===== User Management =====
    user_id: Annotated[str, "Session identifier (UUID)"]
    credits_remaining: Annotated[int, "Available story credits"]

    # ===== Metadata =====
    world_id: Annotated[str, "Current story world identifier"]
    session_start: Annotated[str, "ISO 8601 timestamp of session start"]

    # ===== Error Handling =====
    error: Annotated[str | None, "Error message if something goes wrong"]


# ===== Pydantic Models for API Validation =====

class Choice(BaseModel):
    """A single player choice option with continuation."""

    id: int = Field(..., ge=1, description="Unique choice identifier")
    text: str = Field(..., min_length=1, max_length=1000, description="Choice continuation text (starts next segment)")
    tone: str = Field(default="", max_length=50, description="Emotional tone of this choice")
    consequence_hint: str = Field(default="", max_length=200, description="Optional hint about choice outcome")


class StartStoryRequest(BaseModel):
    """Request to start a new story session."""

    world_id: str = Field(default="tfogwf", description="Story world to load")
    user_id: str | None = Field(default=None, description="Existing user ID (auto-generated if not provided)")
    email: str | None = Field(default=None, description="User email for chapter delivery")


class StartStoryResponse(BaseModel):
    """Response when starting a new story."""

    session_id: str = Field(..., description="Unique session identifier")
    user_id: str = Field(..., description="User identifier")
    world_id: str = Field(..., description="Story world being played")
    current_beat: int = Field(..., description="Current beat number")
    narrative: str = Field(..., description="Opening narrative text")
    choices: list[Choice] = Field(..., description="Available choices")
    image_url: str | None = Field(None, description="Scene image URL if available")
    audio_url: str | None = Field(None, description="Narration audio URL if available")
    credits_remaining: int = Field(..., description="Remaining credits")


class ContinueStoryRequest(BaseModel):
    """Request to continue the story with a choice."""

    session_id: str = Field(..., description="Active session identifier")
    choice_id: int = Field(..., ge=1, description="Selected choice ID")


class ContinueStoryResponse(BaseModel):
    """Response after making a choice."""

    session_id: str = Field(..., description="Session identifier")
    current_beat: int = Field(..., description="Current beat number")
    beat_complete: bool = Field(..., description="Whether current beat is completed")
    narrative: str = Field(..., description="Story segment text")
    choices: list[Choice] = Field(..., description="Available choices")
    image_url: str | None = Field(None, description="Scene image URL if available")
    audio_url: str | None = Field(None, description="Narration audio URL if available")
    credits_remaining: int = Field(..., description="Remaining credits")


class GetSessionRequest(BaseModel):
    """Request to retrieve session state."""

    session_id: str = Field(..., description="Session identifier to retrieve")


class GetSessionResponse(BaseModel):
    """Response with full session state."""

    session_id: str = Field(..., description="Session identifier")
    user_id: str = Field(..., description="User identifier")
    world_id: str = Field(..., description="Story world")
    current_beat: int = Field(..., description="Current beat number")
    beat_progress: dict[int, bool] = Field(..., description="Beat completion status")
    credits_remaining: int = Field(..., description="Remaining credits")
    session_start: str = Field(..., description="Session start timestamp (ISO 8601)")
    last_narrative: str = Field(..., description="Most recent narrative text")
    last_choices: list[Choice] = Field(..., description="Most recent choices")


class ErrorResponse(BaseModel):
    """Standard error response."""

    error: str = Field(..., description="Error message")
    detail: str | None = Field(None, description="Additional error details")
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat(), description="Error timestamp")


# ===== Beat Definition (for story bible structure) =====

class BeatDefinition(BaseModel):
    """Definition of a story beat from the story bible."""

    beat_number: int = Field(..., ge=1, description="Beat number (1-indexed)")
    title: str = Field(..., description="Beat title")
    goal: str = Field(..., description="Primary objective of this beat")
    key_revelations: list[str] = Field(default_factory=list, description="Important revelations in this beat")
    success_criteria: str = Field(..., description="How to determine if beat is complete")
    next_beat_trigger: str = Field(..., description="What triggers progression to next beat")
    tone: Literal["mysterious", "tense", "hopeful", "dark", "balanced"] = Field(
        default="balanced",
        description="Emotional tone for this beat"
    )
    character_focus: str | None = Field(None, description="Which character(s) to focus on")


class CharacterProfile(BaseModel):
    """Character definition from story bible."""

    name: str = Field(..., description="Character name")
    role: Literal["protagonist", "antagonist", "ally", "mentor", "neutral"] = Field(..., description="Story role")
    traits: list[str] = Field(..., description="Key personality traits")
    relationships: dict[str, str] = Field(default_factory=dict, description="Relationships with other characters")
    voice_profile: str | None = Field(None, description="ElevenLabs voice ID if available")


class LocationProfile(BaseModel):
    """Location definition from story bible."""

    name: str = Field(..., description="Location name")
    atmosphere: str = Field(..., description="Overall mood and feeling")
    key_elements: list[str] = Field(..., description="Notable features or objects")
    visual_style: str = Field(..., description="Visual aesthetic for image generation")


# ===== Helper Functions =====

def create_initial_state(
    user_id: str,
    world_id: str,
    credits: int = 25,
    total_chapters: int = 30
) -> StoryState:
    """
    Create initial state for a new story session.

    Args:
        user_id: Unique user identifier
        world_id: Story world to load
        credits: Starting credit amount
        total_chapters: Total chapters in story arc (default: 30)

    Returns:
        Initialized StoryState ready for LangGraph
    """
    return StoryState(
        messages=[],
        # Chapter tracking
        chapter_number=1,
        total_chapters=total_chapters,
        story_progress_pct=0.0,
        # Beat tracking
        current_beat=1,
        turns_in_beat=0,
        beat_progress_score=0.0,
        beat_progress={},
        story_summary=[],
        generated_story_bible={
            "protagonist": {},
            "love_interest": {},
            "supporting_characters": {},
            "locations": {},
            "key_events": [],
            "relationships": {}
        },
        last_choice_continuation=None,
        retrieved_context="",  # Backwards compatibility
        narrative_text="",
        choices=[],
        image_prompt=None,
        image_url=None,
        audio_url=None,
        user_id=user_id,
        credits_remaining=credits,
        world_id=world_id,
        session_start=datetime.utcnow().isoformat(),
        error=None
    )


def format_choice_for_api(choice_dict: dict) -> Choice:
    """Convert internal choice dict to API Choice model."""
    return Choice(
        id=choice_dict["id"],
        text=choice_dict["text"],
        tone=choice_dict.get("tone", ""),
        consequence_hint=choice_dict.get("consequence_hint", "")
    )
