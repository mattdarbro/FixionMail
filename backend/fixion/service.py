"""
Fixion Chat Service

Handles the core chat functionality for Fixion, including
message processing, context management, and LLM integration.
"""

from typing import Optional, Dict, Any, List, AsyncGenerator
from datetime import datetime, timezone
from uuid import UUID

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from backend.config import config
from backend.database.conversations import ConversationService
from backend.database.users import UserService
from backend.database.stories import StoryService
from .prompts import get_fixion_system_prompt, get_writers_room_response, FIXION_PERSONAS


class FixionService:
    """
    Service for Fixion chat interactions.

    Uses Claude Haiku for fast, cheap responses suitable for chat.
    """

    # Default model for chat (Haiku for speed and cost)
    DEFAULT_MODEL = "claude-3-5-haiku-20241022"

    def __init__(
        self,
        user_id: Optional[str] = None,
        conversation_service: Optional[ConversationService] = None,
        user_service: Optional[UserService] = None,
        story_service: Optional[StoryService] = None,
    ):
        """
        Initialize Fixion service.

        Args:
            user_id: Current user ID
            conversation_service: Conversation database service
            user_service: User database service
            story_service: Story database service
        """
        self.user_id = user_id
        self.conversation_service = conversation_service or ConversationService()
        self.user_service = user_service or UserService()
        self.story_service = story_service or StoryService()

        # Initialize LLM
        self.llm = ChatAnthropic(
            model=self.DEFAULT_MODEL,
            temperature=0.8,  # Slightly higher for more personality
            max_tokens=1024,  # Chat responses should be concise
            anthropic_api_key=config.ANTHROPIC_API_KEY,
        )

    # =========================================================================
    # Core Chat Methods
    # =========================================================================

    async def chat(
        self,
        user_message: str,
        context_type: str = "general",
        story_id: Optional[str] = None,
        conversation_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Process a chat message and return Fixion's response.

        Args:
            user_message: The user's message
            context_type: Type of conversation context
            story_id: Story ID if discussing a specific story
            conversation_id: Existing conversation ID to continue

        Returns:
            Response dict with message, conversation_id, and metadata
        """
        # Get or create conversation
        if conversation_id:
            conversation = await self.conversation_service.get_by_id(conversation_id)
            if not conversation:
                conversation = await self.conversation_service.create(
                    self.user_id, context_type, story_id
                )
        else:
            conversation = await self.conversation_service.get_or_create_active(
                self.user_id, context_type, story_id
            )

        conversation_id = conversation["id"]

        # Get user data for context
        user = await self.user_service.get_by_id(self.user_id) if self.user_id else None
        genre = user.get("current_genre") if user else None
        preferences = user.get("preferences", {}) if user else {}

        # Get story context if discussing a story
        story_context = None
        if story_id:
            story_context = await self.story_service.get_by_id(story_id)

        # Build system prompt
        system_prompt = get_fixion_system_prompt(
            context=context_type,
            genre=genre,
            story_context=story_context,
            user_preferences=preferences,
        )

        # Get conversation history
        history = await self.conversation_service.get_messages_for_llm(
            conversation_id, limit=20
        )

        # Build messages for LLM
        messages = [SystemMessage(content=system_prompt)]

        for msg in history:
            if msg["role"] == "user":
                messages.append(HumanMessage(content=msg["content"]))
            else:
                messages.append(AIMessage(content=msg["content"]))

        # Add current message
        messages.append(HumanMessage(content=user_message))

        # Generate response
        response = await self.llm.ainvoke(messages)
        assistant_message = response.content

        # Save messages to conversation
        await self.conversation_service.add_message(
            conversation_id, "user", user_message
        )
        await self.conversation_service.add_message(
            conversation_id, "assistant", assistant_message
        )

        return {
            "message": assistant_message,
            "conversation_id": conversation_id,
            "context_type": context_type,
            "genre": genre,
        }

    async def chat_stream(
        self,
        user_message: str,
        context_type: str = "general",
        story_id: Optional[str] = None,
        conversation_id: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:
        """
        Stream a chat response for real-time display.

        Yields:
            Chunks of the response text
        """
        # Get or create conversation
        if conversation_id:
            conversation = await self.conversation_service.get_by_id(conversation_id)
            if not conversation:
                conversation = await self.conversation_service.create(
                    self.user_id, context_type, story_id
                )
        else:
            conversation = await self.conversation_service.get_or_create_active(
                self.user_id, context_type, story_id
            )

        conversation_id = conversation["id"]

        # Get user data for context
        user = await self.user_service.get_by_id(self.user_id) if self.user_id else None
        genre = user.get("current_genre") if user else None
        preferences = user.get("preferences", {}) if user else {}

        # Get story context if discussing a story
        story_context = None
        if story_id:
            story_context = await self.story_service.get_by_id(story_id)

        # Build system prompt
        system_prompt = get_fixion_system_prompt(
            context=context_type,
            genre=genre,
            story_context=story_context,
            user_preferences=preferences,
        )

        # Get conversation history
        history = await self.conversation_service.get_messages_for_llm(
            conversation_id, limit=20
        )

        # Build messages for LLM
        messages = [SystemMessage(content=system_prompt)]

        for msg in history:
            if msg["role"] == "user":
                messages.append(HumanMessage(content=msg["content"]))
            else:
                messages.append(AIMessage(content=msg["content"]))

        messages.append(HumanMessage(content=user_message))

        # Save user message
        await self.conversation_service.add_message(
            conversation_id, "user", user_message
        )

        # Stream response
        full_response = []
        async for chunk in self.llm.astream(messages):
            if chunk.content:
                full_response.append(chunk.content)
                yield chunk.content

        # Save complete response
        assistant_message = "".join(full_response)
        await self.conversation_service.add_message(
            conversation_id, "assistant", assistant_message
        )

    # =========================================================================
    # Onboarding Methods
    # =========================================================================

    async def start_onboarding(self) -> Dict[str, Any]:
        """
        Start the onboarding conversation.

        Returns the initial Fixion greeting.
        """
        conversation = await self.conversation_service.create_onboarding_conversation(
            self.user_id
        )

        # Get the opening message
        opening = """Hey! Welcome to FixionMail. I'm Fixion — receptionist, intake specialist, and... *glances around* ...actor.

Between auditions, anyway.

So! I'll be getting you set up with your daily stories. First things first — what genre speaks to your soul?

**Choose your genre:**"""

        # Save the opening message
        await self.conversation_service.add_message(
            conversation["id"], "assistant", opening
        )

        return {
            "message": opening,
            "conversation_id": conversation["id"],
            "genres": list(FIXION_PERSONAS.keys()),
            "onboarding_step": "genre_selection",
        }

    async def handle_genre_selection(
        self, genre: str, conversation_id: str
    ) -> Dict[str, Any]:
        """
        Handle genre selection during onboarding.

        Args:
            genre: Selected genre
            conversation_id: Onboarding conversation ID

        Returns:
            Fixion's genre-specific response
        """
        genre_lower = genre.lower()

        if genre_lower not in FIXION_PERSONAS:
            return await self.chat(
                f"I picked {genre}",
                context_type="onboarding",
                conversation_id=conversation_id
            )

        persona = FIXION_PERSONAS[genre_lower]

        # Update user's current genre
        if self.user_id:
            await self.user_service.set_current_genre(self.user_id, genre_lower)
            await self.user_service.update_onboarding_step(self.user_id, "intensity")

        # Get the pivot line and continue
        pivot = persona["pivot_line"]

        intensity_question = """

How intense should we go?

**Choose intensity:**
- **Light & Cozy** — Easy reading, feel-good vibes
- **Moderate** — Some tension, stakes that matter
- **Dark & Gritty** — Mature themes, real consequences"""

        response = pivot + intensity_question

        # Save to conversation
        await self.conversation_service.add_message(
            conversation_id, "user", f"I want {genre}"
        )
        await self.conversation_service.add_message(
            conversation_id, "assistant", response
        )

        return {
            "message": response,
            "conversation_id": conversation_id,
            "genre": genre_lower,
            "onboarding_step": "intensity_selection",
        }

    async def handle_intensity_selection(
        self, intensity: str, conversation_id: str
    ) -> Dict[str, Any]:
        """
        Handle intensity selection during onboarding.

        Args:
            intensity: Selected intensity level
            conversation_id: Onboarding conversation ID

        Returns:
            Fixion's next question
        """
        # Update onboarding step
        if self.user_id:
            await self.user_service.update_onboarding_step(self.user_id, "protagonist")

        # Continue with protagonist question using the chat method
        return await self.chat(
            f"I want {intensity} intensity",
            context_type="onboarding",
            conversation_id=conversation_id
        )

    # =========================================================================
    # Story Discussion Methods
    # =========================================================================

    async def discuss_story(
        self, story_id: str, initial_message: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Start or continue a discussion about a specific story.

        Args:
            story_id: Story to discuss
            initial_message: Optional initial message from user

        Returns:
            Fixion's response
        """
        # Get or create story discussion conversation
        conversation = await self.conversation_service.start_story_discussion(
            self.user_id, story_id
        )

        story = await self.story_service.get_by_id(story_id)
        if not story:
            return {
                "message": "I can't seem to find that story. Did something go wrong?",
                "conversation_id": conversation["id"],
                "error": "story_not_found",
            }

        if initial_message:
            return await self.chat(
                initial_message,
                context_type="story_discussion",
                story_id=story_id,
                conversation_id=conversation["id"]
            )

        # Generate opening for story discussion
        opening = f"""So, "{story.get('title', 'that story')}"...

*settles in*

How'd it land? I want to hear everything."""

        await self.conversation_service.add_message(
            conversation["id"], "assistant", opening
        )

        return {
            "message": opening,
            "conversation_id": conversation["id"],
            "story": {
                "id": story["id"],
                "title": story.get("title"),
                "genre": story.get("genre"),
            },
        }

    # =========================================================================
    # Retell Methods
    # =========================================================================

    async def process_retell_request(
        self,
        story_id: str,
        feedback: str,
        conversation_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Process a request to retell/revise a story.

        Args:
            story_id: Story to revise
            feedback: User's feedback/change requests
            conversation_id: Existing conversation ID

        Returns:
            Fixion's response with revision plan
        """
        story = await self.story_service.get_by_id(story_id)
        if not story:
            return {"error": "story_not_found"}

        # Analyze the feedback to determine revision type
        revision_type = self._analyze_revision_type(feedback)

        # Get writers room response
        if revision_type == "surface":
            writers_response = get_writers_room_response("surface_fix")
            credit_message = "This is a quick fix — no credit needed."
        elif revision_type == "prose":
            writers_response = get_writers_room_response("prose_revision")
            credit_message = "This'll use one credit."
        else:  # structure
            writers_response = get_writers_room_response("structure_revision")
            credit_message = "This'll use one credit, and the story might come back pretty different."

        response = f"""Got it. {writers_response}

{credit_message}

Want me to send it through?"""

        return {
            "message": response,
            "revision_type": revision_type,
            "story_id": story_id,
            "credits_required": 0 if revision_type == "surface" else 1,
            "conversation_id": conversation_id,
        }

    def _analyze_revision_type(self, feedback: str) -> str:
        """
        Analyze feedback to determine revision type.

        This is a simple heuristic - the LLM can also help classify.
        """
        feedback_lower = feedback.lower()

        # Surface indicators
        surface_keywords = ["name", "rename", "change the name", "call them", "typo"]
        if any(kw in feedback_lower for kw in surface_keywords):
            return "surface"

        # Structure indicators
        structure_keywords = [
            "plot", "ending", "twist", "arc", "pacing", "restructure",
            "rewrite", "different direction", "whole thing"
        ]
        if any(kw in feedback_lower for kw in structure_keywords):
            return "structure"

        # Default to prose
        return "prose"

    # =========================================================================
    # Hallucination Handling
    # =========================================================================

    async def handle_hallucination_report(
        self,
        story_id: str,
        description: str,
    ) -> Dict[str, Any]:
        """
        Handle a user reporting a hallucination in a story.

        Args:
            story_id: Story with the hallucination
            description: User's description of the issue

        Returns:
            Fixion's response
        """
        # This will be expanded to actually save the hallucination
        # and potentially generate a reward image

        response = f"""*sighs deeply*

Yeah. I... yeah.

"{description}"

That's going on the board. Thank you for your service. I've added a credit to your account — you've earned it.

Gerald and I are going to have a conversation."""

        return {
            "message": response,
            "reward_given": True,
            "credits_awarded": 1,
        }

    # =========================================================================
    # Check-in Methods
    # =========================================================================

    def get_checkin_message(self, trigger: str, story_title: Optional[str] = None) -> str:
        """
        Get a check-in message for various triggers.

        Args:
            trigger: Type of check-in ('first_story', 'week_one', 'inactive', etc.)
            story_title: Story title if relevant

        Returns:
            Check-in message text
        """
        messages = {
            "first_story": f"""Hey — Fixion here.

Your first story went out this morning. I'm not nervous or anything. I just... want to know if it worked for you.

Too dark? Not dark enough? Wrong vibe entirely?

Hit reply or come chat with me. I can take it.

— Fixion""",

            "week_one": """You've been with me a week now. Five stories.

Are we vibing? Anything you want me to adjust?

Or if everything's perfect, just ignore this. I'll pretend I'm not refreshing my inbox.

— Fixion""",

            "inactive": """Hey, it's Fixion.

I've been sending stories but haven't heard from you in a bit. No pressure — just checking you're still out there.

If you want to shake things up, I'm here.

— Fixion""",

            "great_feedback": f"""Just wanted to say — I passed along your feedback about "{story_title or 'that story'}".

The writers were genuinely touched. Elena did a little happy dance. (She thinks no one saw. I saw.)

Thanks for taking the time. It means something.

— Fixion""",
        }

        return messages.get(trigger, "Hey, just checking in. — Fixion")
