"""
StructureAgent (SSBA): Creates story-specific beat structures.

Takes a generic beat template and story bible, outputs a detailed
story-specific beat plan that guides the WriterAgent.

For single stories: Creates a complete beat plan with scenes, emotions, arcs.
For multi-chapter (future): Creates story arc across chapters for CBA to expand.
"""

import json
import time
from typing import Dict, Any, Optional, List, Literal
from dataclasses import dataclass, field

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage

from backend.config import config


# Model configurations for StructureAgent
STRUCTURE_MODELS = {
    "haiku": {
        "model_id": "claude-3-5-haiku-20241022",
        "name": "Claude Haiku 3.5",
        "description": "Fast, cost-effective planning",
        "cost_tier": "economy"
    },
    "sonnet": {
        "model_id": "claude-sonnet-4-5-20250929",
        "name": "Claude Sonnet 4.5",
        "description": "Balanced quality and speed",
        "cost_tier": "standard"
    }
}

StructureModel = Literal["haiku", "sonnet"]


@dataclass
class StoryBeat:
    """A single story-specific beat with full context."""
    beat_number: int
    beat_name: str
    word_target: int
    # Story-specific details
    scene_description: str
    emotional_arc: str  # e.g., "curiosity → dread"
    tension_level: str  # e.g., "4 → 7" (scale 1-10)
    character_focus: str  # Who is central to this beat
    key_moment: str  # The pivotal moment/image in this beat
    purpose: str  # What this beat accomplishes narratively
    # Optional connections
    connects_to_theme: str = ""
    setup_for_next: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "beat_number": self.beat_number,
            "beat_name": self.beat_name,
            "word_target": self.word_target,
            "scene_description": self.scene_description,
            "emotional_arc": self.emotional_arc,
            "tension_level": self.tension_level,
            "character_focus": self.character_focus,
            "key_moment": self.key_moment,
            "purpose": self.purpose,
            "connects_to_theme": self.connects_to_theme,
            "setup_for_next": self.setup_for_next
        }


@dataclass
class StoryStructure:
    """Complete story-specific structure from SSBA."""
    # Story identity
    story_premise: str  # One-line hook
    central_conflict: str  # What the protagonist wants vs obstacles
    emotional_journey: str  # Protagonist's arc in brief
    thematic_core: str  # The deeper meaning

    # The beats
    beats: List[StoryBeat] = field(default_factory=list)

    # Story metadata
    genre: str = ""
    tone: str = ""
    total_words: int = 1500

    # For multi-chapter stories (future)
    is_multi_chapter: bool = False
    chapter_count: int = 1
    current_chapter: int = 1
    story_arc_position: str = ""  # e.g., "Act 1 - Setup"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "story_premise": self.story_premise,
            "central_conflict": self.central_conflict,
            "emotional_journey": self.emotional_journey,
            "thematic_core": self.thematic_core,
            "beats": [b.to_dict() for b in self.beats],
            "genre": self.genre,
            "tone": self.tone,
            "total_words": self.total_words,
            "is_multi_chapter": self.is_multi_chapter,
            "chapter_count": self.chapter_count,
            "current_chapter": self.current_chapter,
            "story_arc_position": self.story_arc_position
        }


@dataclass
class StructureResult:
    """Result from StructureAgent."""
    success: bool
    structure: Optional[StoryStructure]
    generation_time: float
    model_used: str
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "structure": self.structure.to_dict() if self.structure else None,
            "generation_time": self.generation_time,
            "model_used": self.model_used,
            "error": self.error
        }


class StructureAgent:
    """
    Story Structure Beat Agent (SSBA).

    Transforms generic beat templates into story-specific structures
    by analyzing the story bible and creating detailed scene plans.

    This agent is the "architect" - it designs the story's skeleton
    so the WriterAgent can focus purely on prose craft.
    """

    DEFAULT_MODEL = "sonnet"  # Sonnet for quality structure planning

    def __init__(
        self,
        model: StructureModel = None,
        temperature: float = 0.7
    ):
        """
        Initialize StructureAgent.

        Args:
            model: Model to use - "haiku" (fast/cheap) or "sonnet" (quality)
            temperature: Creativity level (0.6-0.8 recommended for planning)
        """
        self.model_key = model if model and model in STRUCTURE_MODELS else self.DEFAULT_MODEL
        self.model_config = STRUCTURE_MODELS[self.model_key]
        self.model_name = self.model_config["model_id"]
        self.temperature = temperature

        self.llm = ChatAnthropic(
            model=self.model_name,
            temperature=self.temperature,
            max_tokens=4000,  # Structure output is smaller than prose
            anthropic_api_key=config.ANTHROPIC_API_KEY,
            timeout=60.0,
        )

    async def create_structure(
        self,
        story_bible: Dict[str, Any],
        beat_template: Dict[str, Any],
        is_cliffhanger: bool = False,
        story_history: Optional[Dict[str, Any]] = None
    ) -> StructureResult:
        """
        Create a story-specific beat structure.

        Args:
            story_bible: Enhanced story bible with world, characters, settings
            beat_template: Generic beat template (from beat_templates.py)
            is_cliffhanger: Whether story should end on a hook
            story_history: Recent story summaries to avoid repetition

        Returns:
            StructureResult with detailed story structure
        """
        start_time = time.time()

        try:
            prompt = self._build_prompt(
                story_bible=story_bible,
                beat_template=beat_template,
                is_cliffhanger=is_cliffhanger,
                story_history=story_history
            )

            response = await self.llm.ainvoke([HumanMessage(content=prompt)])
            generation_time = time.time() - start_time

            structure = self._parse_response(
                response.content,
                beat_template,
                story_bible
            )

            return StructureResult(
                success=True,
                structure=structure,
                generation_time=generation_time,
                model_used=self.model_key
            )

        except Exception as e:
            generation_time = time.time() - start_time
            return StructureResult(
                success=False,
                structure=None,
                generation_time=generation_time,
                model_used=self.model_key,
                error=str(e)
            )

    def _build_prompt(
        self,
        story_bible: Dict[str, Any],
        beat_template: Dict[str, Any],
        is_cliffhanger: bool,
        story_history: Optional[Dict[str, Any]]
    ) -> str:
        """Build the structure planning prompt."""

        # Extract story bible components
        genre = story_bible.get("genre", "fiction")
        genre_config = story_bible.get("genre_config", {})
        setting = story_bible.get("setting", {})
        tone = story_bible.get("tone", "")
        themes = story_bible.get("themes", [])

        # Characters
        protagonist = story_bible.get("protagonist", story_bible.get("character_template", {}))
        supporting = story_bible.get("supporting_characters", [])
        main_characters = story_bible.get("main_characters", [])

        # Story settings
        story_settings = story_bible.get("story_settings", {})
        intensity = story_settings.get("intensity", 5)

        # Beat template info
        template_name = beat_template.get("name", "unknown")
        total_words = beat_template.get("total_words", 1500)
        beats = beat_template.get("beats", [])

        # Build history context
        history_context = ""
        if story_history:
            recent = story_history.get("recent_summaries", [])[-5:]
            if recent:
                history_context = f"""
## RECENT STORIES (avoid similar plots)

{chr(10).join(f'- {s}' for s in recent)}

Create something DIFFERENT from these recent stories.
"""

        # Build character context
        char_context = self._build_character_context(
            protagonist, supporting, main_characters
        )

        # Build beats to fill
        beats_to_fill = self._build_beats_template(beats)

        # Ending guidance
        ending_guidance = self._get_ending_guidance(is_cliffhanger)

        prompt = f"""You are a Story Structure Beat Agent (SSBA). Your job is to transform a generic beat template into a STORY-SPECIFIC structure.

## YOUR ROLE

You are the story's architect. You design the skeleton - specific scenes, emotional arcs, and key moments - so the prose writer can focus purely on craft.

Think of yourself as a screenwriter creating a detailed beat sheet before the novelist writes the prose.

## STORY WORLD

**Genre**: {genre_config.get('label', genre)}
**Tone**: {tone}
**Themes**: {', '.join(themes) if themes else 'To be discovered'}
**Intensity**: {intensity}/10

**Setting**: {setting.get('name', 'Unknown')}
{setting.get('description', '')}

**Atmosphere**: {setting.get('atmosphere', '')}

{char_context}
{history_context}
## BEAT TEMPLATE TO FILL

You have {len(beats)} beats totaling {total_words} words. Transform each generic beat into a specific scene.

{beats_to_fill}

{ending_guidance}

## YOUR TASK

For this specific story world and characters, create:

1. **STORY PREMISE** - A one-sentence hook that captures the story
2. **CENTRAL CONFLICT** - What does the protagonist want? What stands in their way?
3. **EMOTIONAL JOURNEY** - How does the protagonist change from start to end?
4. **THEMATIC CORE** - What deeper truth does the story explore?

Then for EACH BEAT, provide:
- **scene_description**: What specifically happens (2-3 sentences)
- **emotional_arc**: The emotional shift in this beat (e.g., "hope → doubt")
- **tension_level**: Tension at start → end of beat (1-10 scale)
- **character_focus**: Who is central to this beat
- **key_moment**: The pivotal image or moment readers will remember
- **purpose**: What this beat accomplishes for the story
- **connects_to_theme**: How this beat serves the theme (optional)
- **setup_for_next**: What this beat sets up for the next beat

## OUTPUT FORMAT

Return ONLY valid JSON:

```json
{{
  "story_premise": "One sentence hook",
  "central_conflict": "Protagonist wants X but Y stands in the way",
  "emotional_journey": "From [starting state] to [ending state]",
  "thematic_core": "This story is really about...",
  "beats": [
    {{
      "beat_number": 1,
      "beat_name": "opening_hook",
      "word_target": 400,
      "scene_description": "Specific scene description",
      "emotional_arc": "curiosity → unease",
      "tension_level": "3 → 5",
      "character_focus": "Protagonist name",
      "key_moment": "The specific image or moment",
      "purpose": "Establish world and hint at mystery",
      "connects_to_theme": "Shows protagonist's starting belief",
      "setup_for_next": "Discovery that leads to beat 2"
    }}
  ]
}}
```

## QUALITY CRITERIA

Your structure should:
- Have a CLEAR protagonist want and obstacle
- Build tension progressively (generally rising until climax)
- Give each beat a DISTINCT purpose (no redundancy)
- Create specific, vivid scenes (not generic descriptions)
- Ensure the emotional journey has an arc (change happens)
- Make the ending earn its emotional payoff

Now create the story-specific structure for this {genre} story.
"""
        return prompt

    def _build_character_context(
        self,
        protagonist: Dict[str, Any],
        supporting: List[Dict[str, Any]],
        main_characters: List[Dict[str, Any]]
    ) -> str:
        """Build character context section."""

        context = "## CHARACTERS\n\n"

        # Protagonist
        context += f"**Protagonist**: {protagonist.get('name', protagonist.get('archetype', 'TBD'))}\n"
        context += f"- Role: {protagonist.get('role', 'N/A')}\n"
        context += f"- Traits: {', '.join(protagonist.get('key_traits', []))}\n"
        context += f"- Voice: {protagonist.get('voice', 'N/A')}\n"
        if protagonist.get('defining_characteristic'):
            context += f"- Defining characteristic: {protagonist.get('defining_characteristic')}\n"
        context += "\n"

        # Main characters (must appear)
        if main_characters:
            context += "**Must Include** (recurring characters):\n"
            for char in main_characters[:3]:  # Limit to 3
                context += f"- {char.get('name', 'N/A')}: {char.get('role', 'N/A')}\n"
            context += "\n"

        # Supporting cast
        if supporting:
            context += "**Supporting Cast** (can include):\n"
            for char in supporting[:3]:  # Limit to 3
                name = char.get('name', char.get('archetype', 'N/A'))
                role = char.get('role', char.get('description', 'N/A'))
                context += f"- {name}: {role}\n"
            context += "\n"

        return context

    def _build_beats_template(self, beats: List[Dict[str, Any]]) -> str:
        """Build the beats template section."""

        template = ""
        for beat in beats:
            beat_num = beat.get("beat_number", "?")
            beat_name = beat.get("beat_name", "unknown")
            word_target = beat.get("word_target", 0)
            description = beat.get("description", "")
            guidance = beat.get("guidance", "")

            template += f"""
### Beat {beat_num}: {beat_name.upper()} ({word_target} words)

Generic template: {description}
Craft guidance: {guidance}

→ Transform this into a SPECIFIC scene for this story.
"""
        return template

    def _get_ending_guidance(self, is_cliffhanger: bool) -> str:
        """Get ending guidance based on cliffhanger setting."""

        if is_cliffhanger:
            return """
## ENDING STYLE: Curiosity Hook

The final beat should:
- RESOLVE the immediate story question
- End with a new discovery, revelation, or question
- NOT end on life-or-death peril
- Leave readers curious, not frustrated
"""
        else:
            return """
## ENDING STYLE: Complete Resolution

The final beat should:
- Resolve the central story question
- Provide emotional or thematic closure
- Show character growth or realization
- Leave readers satisfied
"""

    def _parse_response(
        self,
        response_text: str,
        beat_template: Dict[str, Any],
        story_bible: Dict[str, Any]
    ) -> StoryStructure:
        """Parse LLM response into StoryStructure."""

        text = response_text.strip()

        # Handle markdown code blocks
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()

        try:
            data = json.loads(text)
        except json.JSONDecodeError as e:
            # Try to extract JSON from the response
            import re
            json_match = re.search(r'\{[\s\S]*\}', text)
            if json_match:
                data = json.loads(json_match.group())
            else:
                raise ValueError(f"Could not parse JSON from response: {e}")

        # Build beats
        beats = []
        for beat_data in data.get("beats", []):
            beat = StoryBeat(
                beat_number=beat_data.get("beat_number", 0),
                beat_name=beat_data.get("beat_name", ""),
                word_target=beat_data.get("word_target", 0),
                scene_description=beat_data.get("scene_description", ""),
                emotional_arc=beat_data.get("emotional_arc", ""),
                tension_level=beat_data.get("tension_level", ""),
                character_focus=beat_data.get("character_focus", ""),
                key_moment=beat_data.get("key_moment", ""),
                purpose=beat_data.get("purpose", ""),
                connects_to_theme=beat_data.get("connects_to_theme", ""),
                setup_for_next=beat_data.get("setup_for_next", "")
            )
            beats.append(beat)

        # Build structure
        structure = StoryStructure(
            story_premise=data.get("story_premise", ""),
            central_conflict=data.get("central_conflict", ""),
            emotional_journey=data.get("emotional_journey", ""),
            thematic_core=data.get("thematic_core", ""),
            beats=beats,
            genre=story_bible.get("genre", ""),
            tone=story_bible.get("tone", ""),
            total_words=beat_template.get("total_words", 1500)
        )

        return structure


# Convenience function for multi-chapter story arcs (future)
async def create_multi_chapter_arc(
    story_bible: Dict[str, Any],
    chapter_count: int,
    story_structure_type: str = "save_the_cat"
) -> StructureResult:
    """
    Create a full story arc for multi-chapter stories.

    This is a placeholder for future multi-chapter support.
    Will map a story structure (Save the Cat, Hero's Journey, etc.)
    across multiple chapters.

    Args:
        story_bible: Story bible with world, characters
        chapter_count: Total number of chapters
        story_structure_type: Type of story structure to use

    Returns:
        StructureResult with story arc mapped to chapters
    """
    # TODO: Implement multi-chapter arc creation
    # This will use the prompts from prompts_v2.py:create_story_structure_prompt()
    raise NotImplementedError(
        "Multi-chapter arc creation coming in Phase 7. "
        "Use StructureAgent.create_structure() for single stories."
    )
