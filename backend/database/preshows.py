"""
Pre-Show Service

Handles all pre-show related database operations including creation,
retrieval, and the writing room drama that plays while stories generate.

The pre-show system creates short scenes showing the fictional "writing room"
staff (Maurice, Joan, Fifi, Xion) reacting to and preparing the user's story.
"""

from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from uuid import UUID, uuid4
import random

from supabase import Client

from .client import get_supabase_admin_client


# Character definitions for pre-show generation
WRITING_ROOM_CHARACTERS = {
    "fixion": {
        "name": "Fixion",
        "role": "Receptionist",
        "personality": "Earnest, dramatic, warm",
        "actions": [
            "hands story bible to Maurice",
            "straightens papers nervously",
            "glances at the user's preferences",
            "takes a deep breath",
        ],
    },
    "maurice": {
        "name": "Maurice",
        "role": "Head Writer",
        "personality": "Old school, particular, gruff but skilled",
        "actions": [
            "squints at the paper",
            "sighs dramatically",
            "taps pencil on desk",
            "mutters under breath",
            "pushes glasses up",
        ],
    },
    "joan": {
        "name": "Joan",
        "role": "Senior Writer",
        "personality": "Warm, experienced, peacemaker",
        "actions": [
            "looks over Maurice's shoulder",
            "nods thoughtfully",
            "suggests gently",
            "smiles encouragingly",
        ],
    },
    "fifi": {
        "name": "Fifi",
        "role": "New Hire",
        "personality": "Eager, nervous, accidentally brilliant",
        "actions": [
            "peeks over shoulder",
            "bounces excitedly",
            "accidentally knocks over coffee",
            "raises hand tentatively",
            "scribbles notes frantically",
        ],
    },
    "xion": {
        "name": "Xion",
        "role": "Mad Experimenter",
        "personality": "Brilliant, boundary-pushing, eccentric",
        "actions": [
            "wanders in uninvited",
            "strokes chin thoughtfully",
            "pulls out strange diagram",
            "grins mischievously",
        ],
    },
}


class PreshowService:
    """
    Service class for pre-show operations.
    """

    def __init__(self, client: Optional[Client] = None):
        self._client = client

    @property
    def client(self) -> Client:
        if self._client is None:
            self._client = get_supabase_admin_client()
        return self._client

    # =========================================================================
    # Pre-Show Creation
    # =========================================================================

    async def create(
        self,
        user_id: UUID | str,
        task_id: str,
        story_bible: Dict[str, Any],
        *,
        variation: str = "standard",
        story_id: Optional[UUID | str] = None,
    ) -> Dict[str, Any]:
        """
        Create a new pre-show for a story generation task.

        Args:
            user_id: Owner of the pre-show
            task_id: Job ID for the story generation
            story_bible: The story bible being used
            variation: Pre-show variation type
            story_id: Optional story ID (set after generation)

        Returns:
            Created pre-show data
        """
        # Select characters based on variation
        characters = self._select_characters(variation)

        # Generate beats
        beats = self._generate_beats(
            variation=variation,
            characters=characters,
            story_bible=story_bible,
        )

        preshow_data = {
            "id": str(uuid4()),
            "user_id": str(user_id),
            "task_id": task_id,
            "story_id": str(story_id) if story_id else None,
            "variation": variation,
            "characters": characters,
            "beats": beats,
            "conclusion": "Your story is ready!",
            "story_bible_snapshot": story_bible,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        result = self.client.table("preshows").insert(preshow_data).execute()
        return result.data[0]

    def _select_characters(self, variation: str) -> List[str]:
        """Select which characters appear in the pre-show."""
        if variation == "standard":
            return ["fixion", "maurice", "joan"]
        elif variation == "fifi_day":
            return ["fixion", "maurice", "fifi", "joan"]
        elif variation == "xion_experiment":
            return ["fixion", "maurice", "xion", "joan"]
        elif variation == "chaos_day":
            return ["fixion", "maurice", "joan", "fifi", "xion"]
        else:
            return ["fixion", "maurice"]

    def _generate_beats(
        self,
        variation: str,
        characters: List[str],
        story_bible: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """
        Generate pre-show beats based on variation and story bible.

        This is a template-based approach. For more dynamic generation,
        this could be replaced with LLM-generated content.
        """
        genre = story_bible.get("genre", "mystery")
        intensity = story_bible.get("intensity", 3)

        beats = []

        # Opening beat - Fixion hands off the story
        beats.append({
            "character": "fixion",
            "action": "hands story bible to Maurice",
            "dialogue": f"New one just came in. They want {genre}.",
            "delay_ms": 1500,
        })

        if variation == "standard":
            beats.extend(self._standard_beats(genre, intensity))
        elif variation == "fifi_day":
            beats.extend(self._fifi_day_beats(genre, intensity))
        elif variation == "xion_experiment":
            beats.extend(self._xion_experiment_beats(genre, intensity))
        elif variation == "chaos_day":
            beats.extend(self._chaos_day_beats(genre, intensity))

        return beats

    def _standard_beats(self, genre: str, intensity: int) -> List[Dict[str, Any]]:
        """Generate beats for a standard day in the writing room."""
        return [
            {
                "character": "maurice",
                "action": "squints at the paper",
                "dialogue": f"{genre.capitalize()}. Classic. I can work with this.",
                "delay_ms": 2000,
            },
            {
                "character": "joan",
                "action": "looks over his shoulder",
                "dialogue": "What about the emotional angle?",
                "delay_ms": 1500,
            },
            {
                "character": "maurice",
                "action": "taps pencil on desk",
                "dialogue": "I was getting to that, Joan.",
                "delay_ms": 1500,
            },
            {
                "character": "joan",
                "action": "smiles encouragingly",
                "dialogue": "Of course you were.",
                "delay_ms": 1500,
            },
            {
                "character": "maurice",
                "action": "starts writing",
                "dialogue": "Alright. Let's give them something good.",
                "delay_ms": 2000,
            },
        ]

    def _fifi_day_beats(self, genre: str, intensity: int) -> List[Dict[str, Any]]:
        """Generate beats for a Fifi-centric pre-show (happy accidents)."""
        return [
            {
                "character": "maurice",
                "action": "squints at the paper",
                "dialogue": f"{genre.capitalize()}... who's handling this one?",
                "delay_ms": 2000,
            },
            {
                "character": "fifi",
                "action": "raises hand tentatively",
                "dialogue": "I can do it! I've been studying!",
                "delay_ms": 1500,
            },
            {
                "character": "maurice",
                "action": "long pause",
                "dialogue": "...",
                "delay_ms": 1000,
            },
            {
                "character": "joan",
                "action": "suggests gently",
                "dialogue": "Let her try, Maurice. She's been practicing.",
                "delay_ms": 1500,
            },
            {
                "character": "maurice",
                "action": "sighs dramatically",
                "dialogue": "Fine. But I'm reviewing it.",
                "delay_ms": 1500,
            },
            {
                "character": "fifi",
                "action": "bounces excitedly",
                "dialogue": "You won't regret this! Probably!",
                "delay_ms": 2000,
            },
        ]

    def _xion_experiment_beats(self, genre: str, intensity: int) -> List[Dict[str, Any]]:
        """Generate beats for a Xion-centric pre-show (experiments)."""
        experiments = [
            "what if the protagonist could see the future",
            "a parallel timeline element",
            "unreliable narrator techniques",
            "blending in some noir elements",
            "a mystery within the mystery",
        ]
        experiment = random.choice(experiments)

        return [
            {
                "character": "maurice",
                "action": "starts reviewing",
                "dialogue": f"Standard {genre}. I'll have this ready in—",
                "delay_ms": 2000,
            },
            {
                "character": "xion",
                "action": "wanders in uninvited",
                "dialogue": "Wait. I have an idea.",
                "delay_ms": 1500,
            },
            {
                "character": "maurice",
                "action": "mutters under breath",
                "dialogue": "Here we go...",
                "delay_ms": 1000,
            },
            {
                "character": "xion",
                "action": "strokes chin thoughtfully",
                "dialogue": f"What if we added {experiment}?",
                "delay_ms": 2000,
            },
            {
                "character": "maurice",
                "action": "throws pencil",
                "dialogue": "Absolutely not.",
                "delay_ms": 1000,
            },
            {
                "character": "joan",
                "action": "considers",
                "dialogue": "Actually... that could be interesting.",
                "delay_ms": 1500,
            },
            {
                "character": "xion",
                "action": "grins mischievously",
                "dialogue": "See? Joan gets it.",
                "delay_ms": 2000,
            },
        ]

    def _chaos_day_beats(self, genre: str, intensity: int) -> List[Dict[str, Any]]:
        """Generate beats for a chaotic day (everyone involved)."""
        return [
            {
                "character": "maurice",
                "action": "sighs dramatically",
                "dialogue": f"{genre.capitalize()}. Let's keep this simple—",
                "delay_ms": 1500,
            },
            {
                "character": "xion",
                "action": "wanders in",
                "dialogue": "I heard 'simple' and I'm concerned.",
                "delay_ms": 1500,
            },
            {
                "character": "fifi",
                "action": "accidentally knocks over coffee",
                "dialogue": "Oh no! The story bible!",
                "delay_ms": 1500,
            },
            {
                "character": "joan",
                "action": "catches the paper",
                "dialogue": "I've got it. Everyone calm down.",
                "delay_ms": 1500,
            },
            {
                "character": "maurice",
                "action": "head in hands",
                "dialogue": "This is my life now.",
                "delay_ms": 1500,
            },
            {
                "character": "fifi",
                "action": "scribbles notes frantically",
                "dialogue": "I have ideas! So many ideas!",
                "delay_ms": 1500,
            },
            {
                "character": "xion",
                "action": "pulls out strange diagram",
                "dialogue": "What if we combined ALL the genres?",
                "delay_ms": 1500,
            },
            {
                "character": "maurice",
                "action": "deep breath",
                "dialogue": "...let's just write the story.",
                "delay_ms": 2000,
            },
        ]

    # =========================================================================
    # Pre-Show Retrieval
    # =========================================================================

    async def get_by_id(self, preshow_id: UUID | str) -> Optional[Dict[str, Any]]:
        """Get pre-show by ID."""
        result = (
            self.client.table("preshows")
            .select("*")
            .eq("id", str(preshow_id))
            .execute()
        )
        return result.data[0] if result.data else None

    async def get_by_task_id(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get pre-show by task/job ID."""
        result = (
            self.client.table("preshows")
            .select("*")
            .eq("task_id", task_id)
            .execute()
        )
        return result.data[0] if result.data else None

    async def get_by_story_id(self, story_id: UUID | str) -> Optional[Dict[str, Any]]:
        """Get pre-show associated with a story."""
        result = (
            self.client.table("preshows")
            .select("*")
            .eq("story_id", str(story_id))
            .execute()
        )
        return result.data[0] if result.data else None

    async def get_user_preshows(
        self,
        user_id: UUID | str,
        *,
        limit: int = 20,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """Get user's pre-shows for the library (rewatchable)."""
        result = (
            self.client.table("preshows")
            .select("*")
            .eq("user_id", str(user_id))
            .order("created_at", desc=True)
            .limit(limit)
            .offset(offset)
            .execute()
        )
        return result.data

    # =========================================================================
    # Pre-Show Updates
    # =========================================================================

    async def link_to_story(
        self, preshow_id: UUID | str, story_id: UUID | str
    ) -> Dict[str, Any]:
        """Link a pre-show to its completed story."""
        result = (
            self.client.table("preshows")
            .update({"story_id": str(story_id)})
            .eq("id", str(preshow_id))
            .execute()
        )
        return result.data[0] if result.data else {}

    # =========================================================================
    # Variation Selection
    # =========================================================================

    def select_variation(
        self,
        user_settings: Dict[str, Any],
    ) -> str:
        """
        Select pre-show variation based on user settings.

        Args:
            user_settings: User's variation settings from the database

        Returns:
            Variation type: standard, fifi_day, xion_experiment, chaos_day
        """
        variation_tolerance = user_settings.get("variation_tolerance", "medium")
        xion_experiments = user_settings.get("xion_experiments", "occasional")
        fifi_enabled = user_settings.get("fifi_enabled", True)

        # Base probabilities
        roll = random.random()

        if variation_tolerance == "low":
            # Mostly standard
            if roll < 0.85:
                return "standard"
            elif fifi_enabled and roll < 0.95:
                return "fifi_day"
            else:
                return "standard"

        elif variation_tolerance == "medium":
            # Balanced
            if roll < 0.50:
                return "standard"
            elif fifi_enabled and roll < 0.75:
                return "fifi_day"
            elif xion_experiments != "never" and roll < 0.90:
                return "xion_experiment"
            elif roll < 0.95:
                return "chaos_day"
            else:
                return "standard"

        elif variation_tolerance == "high":
            # More variety
            if roll < 0.30:
                return "standard"
            elif fifi_enabled and roll < 0.55:
                return "fifi_day"
            elif xion_experiments != "never" and roll < 0.80:
                return "xion_experiment"
            elif roll < 0.95:
                return "chaos_day"
            else:
                return "standard"

        return "standard"
