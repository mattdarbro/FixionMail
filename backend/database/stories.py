"""
Story Service

Handles all story-related database operations including creation,
retrieval, updates, and revision tracking.
"""

from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from uuid import UUID, uuid4

from supabase import Client

from .client import get_supabase_admin_client


class StoryNotFoundError(Exception):
    """Raised when a story is not found in the database."""
    pass


class StoryService:
    """
    Service class for story operations.
    """

    def __init__(self, client: Optional[Client] = None):
        self._client = client

    @property
    def client(self) -> Client:
        if self._client is None:
            self._client = get_supabase_admin_client()
        return self._client

    # =========================================================================
    # Story Creation
    # =========================================================================

    async def create(
        self,
        user_id: UUID | str,
        title: str,
        narrative: str,
        genre: str,
        story_bible: Dict[str, Any],
        model_used: str,
        *,
        word_count: Optional[int] = None,
        beat_structure: Optional[str] = None,
        audio_url: Optional[str] = None,
        image_url: Optional[str] = None,
        series_id: Optional[UUID | str] = None,
        episode_number: Optional[int] = None,
        credits_used: int = 1,
        generation_cost_cents: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Create a new story.

        Args:
            user_id: Owner of the story
            title: Story title
            narrative: Full story text
            genre: Story genre
            story_bible: The bible used for generation
            model_used: 'sonnet' or 'opus'
            word_count: Calculated word count (auto-calculated if not provided)
            beat_structure: Template used (e.g., 'save_the_cat')
            audio_url: URL to generated audio
            image_url: URL to generated cover image
            series_id: Group stories in a series
            episode_number: Episode number within series
            credits_used: Credits consumed (default 1)
            generation_cost_cents: Actual API cost

        Returns:
            Created story data
        """
        if word_count is None:
            word_count = len(narrative.split())

        story_data = {
            "id": str(uuid4()),
            "user_id": str(user_id),
            "title": title,
            "narrative": narrative,
            "word_count": word_count,
            "genre": genre,
            "story_bible": story_bible,
            "model_used": model_used,
            "beat_structure": beat_structure,
            "audio_url": audio_url,
            "image_url": image_url,
            "series_id": str(series_id) if series_id else None,
            "episode_number": episode_number,
            "credits_used": credits_used,
            "generation_cost_cents": generation_cost_cents,
            "status": "completed",
            "is_retell": False,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

        result = self.client.table("stories").insert(story_data).execute()
        return result.data[0]

    async def create_retell(
        self,
        user_id: UUID | str,
        parent_story_id: UUID | str,
        title: str,
        narrative: str,
        story_bible: Dict[str, Any],
        model_used: str,
        revision_type: str,
        revision_notes: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Create a retell/revision of an existing story.

        Args:
            user_id: Owner of the story
            parent_story_id: Original story being revised
            title: Story title (may be same as original)
            narrative: Revised story text
            story_bible: Bible used for revision
            model_used: Model used for revision
            revision_type: 'surface', 'prose', or 'structure'
            revision_notes: User's feedback that led to retell
            **kwargs: Additional fields passed to create()

        Returns:
            Created retell story data
        """
        # Get parent story for metadata
        parent = await self.get_by_id(parent_story_id)
        if not parent:
            raise StoryNotFoundError(f"Parent story {parent_story_id} not found")

        story_data = {
            "id": str(uuid4()),
            "user_id": str(user_id),
            "title": title,
            "narrative": narrative,
            "word_count": len(narrative.split()),
            "genre": parent["genre"],
            "story_bible": story_bible,
            "model_used": model_used,
            "beat_structure": parent.get("beat_structure"),
            "is_retell": True,
            "parent_story_id": str(parent_story_id),
            "revision_type": revision_type,
            "revision_notes": revision_notes,
            "series_id": parent.get("series_id"),
            "episode_number": parent.get("episode_number"),
            "status": "completed",
            "credits_used": 0 if revision_type == "surface" else 1,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            **kwargs
        }

        result = self.client.table("stories").insert(story_data).execute()
        return result.data[0]

    # =========================================================================
    # Story Retrieval
    # =========================================================================

    async def get_by_id(self, story_id: UUID | str) -> Optional[Dict[str, Any]]:
        """Get story by ID."""
        result = (
            self.client.table("stories")
            .select("*")
            .eq("id", str(story_id))
            .execute()
        )
        return result.data[0] if result.data else None

    async def get_user_stories(
        self,
        user_id: UUID | str,
        *,
        limit: int = 50,
        offset: int = 0,
        genre: Optional[str] = None,
        include_retells: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Get all stories for a user.

        Args:
            user_id: User ID
            limit: Max stories to return
            offset: Pagination offset
            genre: Filter by genre
            include_retells: Include revision stories

        Returns:
            List of stories, newest first
        """
        query = (
            self.client.table("stories")
            .select("*")
            .eq("user_id", str(user_id))
            .order("created_at", desc=True)
            .limit(limit)
            .offset(offset)
        )

        if genre:
            query = query.eq("genre", genre)

        if not include_retells:
            query = query.eq("is_retell", False)

        result = query.execute()
        return result.data

    async def get_story_with_revisions(
        self, story_id: UUID | str
    ) -> Dict[str, Any]:
        """
        Get a story and all its revisions.

        Returns:
            Story data with 'revisions' list
        """
        story = await self.get_by_id(story_id)
        if not story:
            raise StoryNotFoundError(f"Story {story_id} not found")

        # Get all revisions of this story
        revisions_result = (
            self.client.table("stories")
            .select("*")
            .eq("parent_story_id", str(story_id))
            .order("created_at", desc=False)
            .execute()
        )

        story["revisions"] = revisions_result.data
        return story

    async def get_series(
        self, series_id: UUID | str
    ) -> List[Dict[str, Any]]:
        """Get all stories in a series, ordered by episode."""
        result = (
            self.client.table("stories")
            .select("*")
            .eq("series_id", str(series_id))
            .eq("is_retell", False)  # Only original stories
            .order("episode_number", desc=False)
            .execute()
        )
        return result.data

    async def get_latest_story(
        self, user_id: UUID | str
    ) -> Optional[Dict[str, Any]]:
        """Get user's most recent story."""
        result = (
            self.client.table("stories")
            .select("*")
            .eq("user_id", str(user_id))
            .eq("is_retell", False)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        return result.data[0] if result.data else None

    # =========================================================================
    # Story Updates
    # =========================================================================

    async def update(
        self, story_id: UUID | str, data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update story fields."""
        update_data = {k: v for k, v in data.items() if v is not None}
        update_data["updated_at"] = datetime.now(timezone.utc).isoformat()

        result = (
            self.client.table("stories")
            .update(update_data)
            .eq("id", str(story_id))
            .execute()
        )

        if not result.data:
            raise StoryNotFoundError(f"Story {story_id} not found")

        return result.data[0]

    async def mark_delivered(self, story_id: UUID | str) -> Dict[str, Any]:
        """Mark story as delivered via email."""
        return await self.update(story_id, {
            "status": "delivered",
            "delivered_at": datetime.now(timezone.utc).isoformat(),
            "email_sent": True,
        })

    async def add_rating(
        self,
        story_id: UUID | str,
        rating: int,
        feedback: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Add user rating to story."""
        if rating < 1 or rating > 5:
            raise ValueError("Rating must be between 1 and 5")

        return await self.update(story_id, {
            "rating": rating,
            "feedback": feedback,
        })

    async def update_media(
        self,
        story_id: UUID | str,
        audio_url: Optional[str] = None,
        image_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """Update story media URLs."""
        update_data = {}
        if audio_url is not None:
            update_data["audio_url"] = audio_url
        if image_url is not None:
            update_data["image_url"] = image_url

        return await self.update(story_id, update_data)

    # =========================================================================
    # Series Management
    # =========================================================================

    async def create_series(self) -> str:
        """Create a new series ID."""
        return str(uuid4())

    async def get_next_episode_number(
        self, series_id: UUID | str
    ) -> int:
        """Get the next episode number for a series."""
        result = (
            self.client.table("stories")
            .select("episode_number")
            .eq("series_id", str(series_id))
            .order("episode_number", desc=True)
            .limit(1)
            .execute()
        )

        if result.data and result.data[0].get("episode_number"):
            return result.data[0]["episode_number"] + 1
        return 1

    # =========================================================================
    # Statistics
    # =========================================================================

    async def get_user_stats(self, user_id: UUID | str) -> Dict[str, Any]:
        """Get story statistics for a user."""
        stories = await self.get_user_stories(user_id, limit=1000)

        total = len(stories)
        originals = [s for s in stories if not s.get("is_retell")]
        retells = [s for s in stories if s.get("is_retell")]

        genres = {}
        for story in originals:
            genre = story.get("genre", "unknown")
            genres[genre] = genres.get(genre, 0) + 1

        total_words = sum(s.get("word_count", 0) for s in stories)

        return {
            "total_stories": total,
            "original_stories": len(originals),
            "retells": len(retells),
            "genres": genres,
            "total_words": total_words,
            "average_rating": sum(
                s.get("rating", 0) for s in stories if s.get("rating")
            ) / max(len([s for s in stories if s.get("rating")]), 1),
        }
