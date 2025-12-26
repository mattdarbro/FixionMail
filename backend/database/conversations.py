"""
Conversation Service

Handles Fixion chat conversations including message history,
context management, and conversation lifecycle.
"""

from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from uuid import UUID, uuid4

from supabase import Client

from .client import get_supabase_admin_client


class ConversationNotFoundError(Exception):
    """Raised when a conversation is not found."""
    pass


class ConversationService:
    """
    Service class for Fixion chat conversations.
    """

    def __init__(self, client: Optional[Client] = None):
        self._client = client

    @property
    def client(self) -> Client:
        if self._client is None:
            self._client = get_supabase_admin_client()
        return self._client

    # =========================================================================
    # Conversation Management
    # =========================================================================

    async def create(
        self,
        user_id: UUID | str,
        context_type: str = "general",
        story_context_id: Optional[UUID | str] = None,
    ) -> Dict[str, Any]:
        """
        Create a new conversation.

        Args:
            user_id: User ID
            context_type: Type of conversation
                - 'onboarding': New user setup
                - 'story_discussion': Discussing a specific story
                - 'preference_update': Changing preferences
                - 'retell_request': Requesting a revision
                - 'general': General chat

            story_context_id: Story ID if discussing a specific story

        Returns:
            Created conversation data
        """
        conversation_data = {
            "id": str(uuid4()),
            "user_id": str(user_id),
            "messages": [],
            "context_type": context_type,
            "story_context_id": str(story_context_id) if story_context_id else None,
            "is_active": True,
            "message_count": 0,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

        result = self.client.table("conversations").insert(conversation_data).execute()
        return result.data[0]

    async def get_by_id(
        self, conversation_id: UUID | str
    ) -> Optional[Dict[str, Any]]:
        """Get conversation by ID."""
        result = (
            self.client.table("conversations")
            .select("*")
            .eq("id", str(conversation_id))
            .execute()
        )
        return result.data[0] if result.data else None

    async def get_active_conversation(
        self, user_id: UUID | str
    ) -> Optional[Dict[str, Any]]:
        """Get user's currently active conversation."""
        result = (
            self.client.table("conversations")
            .select("*")
            .eq("user_id", str(user_id))
            .eq("is_active", True)
            .order("updated_at", desc=True)
            .limit(1)
            .execute()
        )
        return result.data[0] if result.data else None

    async def get_or_create_active(
        self,
        user_id: UUID | str,
        context_type: str = "general",
        story_context_id: Optional[UUID | str] = None,
    ) -> Dict[str, Any]:
        """
        Get active conversation or create a new one.

        If there's an active conversation with the same context, return it.
        Otherwise, create a new conversation.
        """
        active = await self.get_active_conversation(user_id)

        # If there's an active conversation with same context, use it
        if active:
            same_context = (
                active.get("context_type") == context_type and
                active.get("story_context_id") == (str(story_context_id) if story_context_id else None)
            )
            if same_context:
                return active

            # Different context - close old one and create new
            await self.close(active["id"])

        return await self.create(user_id, context_type, story_context_id)

    async def get_user_conversations(
        self,
        user_id: UUID | str,
        *,
        limit: int = 20,
        include_inactive: bool = False,
    ) -> List[Dict[str, Any]]:
        """Get user's conversations."""
        query = (
            self.client.table("conversations")
            .select("*")
            .eq("user_id", str(user_id))
            .order("updated_at", desc=True)
            .limit(limit)
        )

        if not include_inactive:
            query = query.eq("is_active", True)

        result = query.execute()
        return result.data

    # =========================================================================
    # Message Management
    # =========================================================================

    async def add_message(
        self,
        conversation_id: UUID | str,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Add a message to a conversation.

        Args:
            conversation_id: Conversation ID
            role: 'user' or 'assistant'
            content: Message content
            metadata: Optional metadata (e.g., detected intent, entities)

        Returns:
            Updated conversation data
        """
        if role not in ("user", "assistant"):
            raise ValueError("Role must be 'user' or 'assistant'")

        # Get current conversation
        conversation = await self.get_by_id(conversation_id)
        if not conversation:
            raise ConversationNotFoundError(f"Conversation {conversation_id} not found")

        # Build new message
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        if metadata:
            message["metadata"] = metadata

        # Append to messages array
        messages = conversation.get("messages", [])
        messages.append(message)

        # Update conversation
        result = (
            self.client.table("conversations")
            .update({
                "messages": messages,
                "message_count": len(messages),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            })
            .eq("id", str(conversation_id))
            .execute()
        )

        return result.data[0]

    async def get_messages(
        self,
        conversation_id: UUID | str,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get messages from a conversation.

        Args:
            conversation_id: Conversation ID
            limit: Optional limit (returns most recent if specified)

        Returns:
            List of messages
        """
        conversation = await self.get_by_id(conversation_id)
        if not conversation:
            raise ConversationNotFoundError(f"Conversation {conversation_id} not found")

        messages = conversation.get("messages", [])

        if limit:
            return messages[-limit:]
        return messages

    async def get_messages_for_llm(
        self,
        conversation_id: UUID | str,
        limit: int = 20,
    ) -> List[Dict[str, str]]:
        """
        Get messages formatted for LLM context.

        Returns list of {role, content} dicts suitable for chat completion.
        """
        messages = await self.get_messages(conversation_id, limit=limit)
        return [
            {"role": m["role"], "content": m["content"]}
            for m in messages
        ]

    # =========================================================================
    # Conversation Lifecycle
    # =========================================================================

    async def close(self, conversation_id: UUID | str) -> Dict[str, Any]:
        """Close a conversation (mark as inactive)."""
        result = (
            self.client.table("conversations")
            .update({
                "is_active": False,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            })
            .eq("id", str(conversation_id))
            .execute()
        )

        if not result.data:
            raise ConversationNotFoundError(f"Conversation {conversation_id} not found")

        return result.data[0]

    async def set_story_context(
        self,
        conversation_id: UUID | str,
        story_id: UUID | str,
    ) -> Dict[str, Any]:
        """Set the story context for a conversation."""
        result = (
            self.client.table("conversations")
            .update({
                "story_context_id": str(story_id),
                "context_type": "story_discussion",
                "updated_at": datetime.now(timezone.utc).isoformat(),
            })
            .eq("id", str(conversation_id))
            .execute()
        )

        if not result.data:
            raise ConversationNotFoundError(f"Conversation {conversation_id} not found")

        return result.data[0]

    async def update_context_type(
        self,
        conversation_id: UUID | str,
        context_type: str,
    ) -> Dict[str, Any]:
        """Update the context type of a conversation."""
        result = (
            self.client.table("conversations")
            .update({
                "context_type": context_type,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            })
            .eq("id", str(conversation_id))
            .execute()
        )

        if not result.data:
            raise ConversationNotFoundError(f"Conversation {conversation_id} not found")

        return result.data[0]

    # =========================================================================
    # Onboarding Specific
    # =========================================================================

    async def get_onboarding_conversation(
        self, user_id: UUID | str
    ) -> Optional[Dict[str, Any]]:
        """Get user's onboarding conversation if it exists."""
        result = (
            self.client.table("conversations")
            .select("*")
            .eq("user_id", str(user_id))
            .eq("context_type", "onboarding")
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        return result.data[0] if result.data else None

    async def create_onboarding_conversation(
        self, user_id: UUID | str
    ) -> Dict[str, Any]:
        """Create or get onboarding conversation for user."""
        existing = await self.get_onboarding_conversation(user_id)
        if existing and existing.get("is_active"):
            return existing

        return await self.create(user_id, context_type="onboarding")

    # =========================================================================
    # Story Discussion Specific
    # =========================================================================

    async def get_story_discussion(
        self,
        user_id: UUID | str,
        story_id: UUID | str,
    ) -> Optional[Dict[str, Any]]:
        """Get conversation about a specific story."""
        result = (
            self.client.table("conversations")
            .select("*")
            .eq("user_id", str(user_id))
            .eq("story_context_id", str(story_id))
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        return result.data[0] if result.data else None

    async def start_story_discussion(
        self,
        user_id: UUID | str,
        story_id: UUID | str,
    ) -> Dict[str, Any]:
        """Start or continue a discussion about a specific story."""
        existing = await self.get_story_discussion(user_id, story_id)
        if existing and existing.get("is_active"):
            return existing

        return await self.create(
            user_id,
            context_type="story_discussion",
            story_context_id=story_id
        )
