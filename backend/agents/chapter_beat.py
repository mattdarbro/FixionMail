"""
ChapterBeatAgent (CBA): Creates detailed beat structures for individual chapters.

This agent is designed for MULTI-CHAPTER stories. It takes:
- The overall story arc from SSBA (where this chapter fits in the larger story)
- SSBA's guidance for this specific chapter
- Story bible and previous chapter context

And produces a detailed 6-beat structure for a single chapter.

STATUS: Ready for Phase 7 (Multi-Chapter Stories)
Currently raises NotImplementedError - use StructureAgent for single stories.
"""

import json
import time
from typing import Dict, Any, Optional, List, Literal
from dataclasses import dataclass, field

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage

from backend.config import config


# Model configurations
CBA_MODELS = {
    "haiku": {
        "model_id": "claude-3-5-haiku-20241022",
        "name": "Claude Haiku 3.5",
        "description": "Fast chapter planning",
        "cost_tier": "economy"
    },
    "sonnet": {
        "model_id": "claude-sonnet-4-5-20250929",
        "name": "Claude Sonnet 4.5",
        "description": "Detailed chapter planning",
        "cost_tier": "standard"
    }
}

CBAModel = Literal["haiku", "sonnet"]


@dataclass
class ChapterBeat:
    """A single beat within a chapter (6-beat chapter structure)."""
    beat_number: int
    beat_name: str  # opening_hook, rising_action, midpoint_twist, etc.
    word_target: int

    # Scene details
    scene_description: str
    key_elements: List[str]
    emotional_tone: str
    character_focus: str

    # Connections
    connects_to_previous: str = ""
    setup_for_next: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "beat_number": self.beat_number,
            "beat_name": self.beat_name,
            "word_target": self.word_target,
            "scene_description": self.scene_description,
            "key_elements": self.key_elements,
            "emotional_tone": self.emotional_tone,
            "character_focus": self.character_focus,
            "connects_to_previous": self.connects_to_previous,
            "setup_for_next": self.setup_for_next
        }


@dataclass
class ChapterStructure:
    """Complete structure for a single chapter."""
    chapter_number: int
    total_chapters: int

    # Chapter identity
    chapter_goal: str  # What this chapter accomplishes
    chapter_tension: str  # What creates tension throughout
    chapter_question: str  # The question driving the reader

    # The 6 beats
    beats: List[ChapterBeat] = field(default_factory=list)

    # Story arc context
    story_beat: str = ""  # Which story beat (e.g., "Catalyst", "Midpoint")
    act: str = ""  # Which act (1, 2a, 2b, 3)
    progress_percentage: float = 0.0

    # For choices (interactive stories)
    choice_setup: Dict[str, Any] = field(default_factory=dict)

    # Word targets
    total_words: int = 2500

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chapter_number": self.chapter_number,
            "total_chapters": self.total_chapters,
            "chapter_goal": self.chapter_goal,
            "chapter_tension": self.chapter_tension,
            "chapter_question": self.chapter_question,
            "beats": [b.to_dict() for b in self.beats],
            "story_beat": self.story_beat,
            "act": self.act,
            "progress_percentage": self.progress_percentage,
            "choice_setup": self.choice_setup,
            "total_words": self.total_words
        }


@dataclass
class ChapterBeatResult:
    """Result from ChapterBeatAgent."""
    success: bool
    structure: Optional[ChapterStructure]
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


# Standard 6-beat chapter structure
CHAPTER_BEAT_TEMPLATE = [
    {
        "beat_number": 1,
        "beat_name": "opening_hook",
        "word_target": 400,
        "description": "Immediate engagement - action, mystery, emotion, or tension",
        "guidance": "Ground reader in POV, setting, immediate situation. Connect to last chapter."
    },
    {
        "beat_number": 2,
        "beat_name": "rising_action",
        "word_target": 450,
        "description": "Develop the chapter's central situation or conflict",
        "guidance": "Introduce complications or new information. Build momentum."
    },
    {
        "beat_number": 3,
        "beat_name": "midpoint_twist",
        "word_target": 450,
        "description": "Surprise, revelation, or shift in understanding",
        "guidance": "Raise stakes or change direction. False victory or setback."
    },
    {
        "beat_number": 4,
        "beat_name": "complications",
        "word_target": 450,
        "description": "Consequences unfold, pressure increases",
        "guidance": "Obstacles intensify. Character struggles with challenge."
    },
    {
        "beat_number": 5,
        "beat_name": "tension_peak",
        "word_target": 400,
        "description": "Maximum pressure or emotional intensity",
        "guidance": "Character must make difficult choice or face hard truth."
    },
    {
        "beat_number": 6,
        "beat_name": "resolution_hook",
        "word_target": 350,
        "description": "Resolve chapter question, hook for next",
        "guidance": "Show consequences. End with hook for player choices."
    }
]


class ChapterBeatAgent:
    """
    Chapter Beat Agent (CBA) for multi-chapter stories.

    Takes SSBA's story arc and chapter guidance, produces a detailed
    6-beat structure for a single chapter.

    The 6-beat chapter structure:
    1. OPENING HOOK - Immediate engagement
    2. RISING ACTION - Develop central situation
    3. MIDPOINT TWIST - Surprise or shift
    4. COMPLICATIONS - Pressure increases
    5. TENSION PEAK - Maximum intensity
    6. RESOLUTION & HOOK - Resolve and set up next

    STATUS: Designed and ready for Phase 7 (Multi-Chapter Stories)
    """

    DEFAULT_MODEL = "haiku"  # Haiku is sufficient for chapter planning

    def __init__(
        self,
        model: CBAModel = None,
        temperature: float = 0.7
    ):
        """
        Initialize ChapterBeatAgent.

        Args:
            model: Model to use - "haiku" (default) or "sonnet"
            temperature: Creativity level
        """
        self.model_key = model if model and model in CBA_MODELS else self.DEFAULT_MODEL
        self.model_config = CBA_MODELS[self.model_key]
        self.model_name = self.model_config["model_id"]
        self.temperature = temperature

        self.llm = ChatAnthropic(
            model=self.model_name,
            temperature=self.temperature,
            max_tokens=3000,
            anthropic_api_key=config.ANTHROPIC_API_KEY,
            timeout=60.0,
        )

    async def create_chapter_beats(
        self,
        story_bible: Dict[str, Any],
        story_arc: Dict[str, Any],
        chapter_number: int,
        total_chapters: int,
        ssba_guidance: Dict[str, Any],
        last_choice: Optional[str] = None,
        chapter_summaries: Optional[List[str]] = None
    ) -> ChapterBeatResult:
        """
        Create detailed 6-beat structure for a chapter.

        Args:
            story_bible: Story bible with world, characters
            story_arc: Full story arc from SSBA
            chapter_number: Current chapter (1-indexed)
            total_chapters: Total chapters in story
            ssba_guidance: SSBA's guidance for this chapter
            last_choice: Player's last choice (for interactive stories)
            chapter_summaries: Summaries of previous chapters

        Returns:
            ChapterBeatResult with detailed chapter structure

        Raises:
            NotImplementedError: Multi-chapter stories coming in Phase 7
        """
        raise NotImplementedError(
            "ChapterBeatAgent is designed for multi-chapter stories (Phase 7). "
            "For single stories, use StructureAgent directly."
        )

    def _build_prompt(
        self,
        story_bible: Dict[str, Any],
        story_arc: Dict[str, Any],
        chapter_number: int,
        total_chapters: int,
        ssba_guidance: Dict[str, Any],
        last_choice: Optional[str],
        chapter_summaries: Optional[List[str]]
    ) -> str:
        """
        Build the chapter beat planning prompt.

        This method is implemented and ready for Phase 7.
        """
        genre = story_bible.get("genre", "fiction")
        setting = story_bible.get("setting", {})
        protagonist = story_bible.get("protagonist", {})

        # Calculate progress
        progress_pct = (chapter_number / total_chapters) * 100

        # Get SSBA guidance details
        current_story_beat = ssba_guidance.get("current_story_beat", "N/A")
        act = ssba_guidance.get("act", "N/A")
        guidance_text = ssba_guidance.get("guidance_for_cba", "N/A")

        # Build context
        summaries_text = ""
        if chapter_summaries:
            recent = chapter_summaries[-3:]
            summaries_text = "\n".join([f"- {s}" for s in recent])

        last_choice_text = ""
        if last_choice:
            last_choice_text = f"\n## PLAYER'S LAST CHOICE\n\n{last_choice}\n"

        # Build beat template section
        beats_template = ""
        for beat in CHAPTER_BEAT_TEMPLATE:
            beats_template += f"""
**Beat {beat['beat_number']}: {beat['beat_name'].upper()}** ({beat['word_target']} words)
- Purpose: {beat['description']}
- Guidance: {beat['guidance']}
"""

        prompt = f"""You are a Chapter Beat Agent (CBA) creating the detailed structure for Chapter {chapter_number}.

## STORY CONTEXT

**Genre**: {genre}
**Chapter**: {chapter_number} of {total_chapters} ({progress_pct:.1f}% complete)
**Current Story Beat**: {current_story_beat}
**Act**: {act}

**Setting**: {setting.get('name', 'N/A')}
**Protagonist**: {protagonist.get('name', 'N/A')}

## SSBA GUIDANCE FOR THIS CHAPTER

{guidance_text}

## STORY ARC CONTEXT

{json.dumps(story_arc, indent=2)}

## PREVIOUS CHAPTERS

{summaries_text if summaries_text else '(This is chapter 1)'}
{last_choice_text}
## 6-BEAT CHAPTER STRUCTURE

Create detailed beats for this chapter:
{beats_template}

## YOUR TASK

Create a 6-beat structure that:
1. Follows SSBA's guidance for this chapter
2. Connects naturally from the previous chapter/choice
3. Advances the story arc appropriately
4. Creates a satisfying chapter-level experience
5. Ends with setup for player choices (if interactive)

## OUTPUT FORMAT

Return JSON:

```json
{{
  "chapter_goal": "What this chapter accomplishes",
  "chapter_tension": "What creates tension throughout",
  "chapter_question": "The question driving readers through the chapter",
  "beats": [
    {{
      "beat_number": 1,
      "beat_name": "opening_hook",
      "word_target": 400,
      "scene_description": "Specific scene description",
      "key_elements": ["element1", "element2"],
      "emotional_tone": "tense, uncertain",
      "character_focus": "Protagonist name",
      "connects_to_previous": "How this connects to last chapter",
      "setup_for_next": "What this sets up"
    }}
  ],
  "choice_setup": {{
    "situation": "The dilemma at chapter end",
    "stakes": "Why choices matter",
    "suggested_types": ["action", "relationship", "investigation"]
  }}
}}
```

Create the chapter structure now.
"""
        return prompt

    def _parse_response(
        self,
        response_text: str,
        chapter_number: int,
        total_chapters: int
    ) -> ChapterStructure:
        """Parse LLM response into ChapterStructure."""

        text = response_text.strip()

        # Handle markdown code blocks
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()

        data = json.loads(text)

        # Build beats
        beats = []
        for beat_data in data.get("beats", []):
            beat = ChapterBeat(
                beat_number=beat_data.get("beat_number", 0),
                beat_name=beat_data.get("beat_name", ""),
                word_target=beat_data.get("word_target", 0),
                scene_description=beat_data.get("scene_description", ""),
                key_elements=beat_data.get("key_elements", []),
                emotional_tone=beat_data.get("emotional_tone", ""),
                character_focus=beat_data.get("character_focus", ""),
                connects_to_previous=beat_data.get("connects_to_previous", ""),
                setup_for_next=beat_data.get("setup_for_next", "")
            )
            beats.append(beat)

        return ChapterStructure(
            chapter_number=chapter_number,
            total_chapters=total_chapters,
            chapter_goal=data.get("chapter_goal", ""),
            chapter_tension=data.get("chapter_tension", ""),
            chapter_question=data.get("chapter_question", ""),
            beats=beats,
            choice_setup=data.get("choice_setup", {}),
            total_words=sum(b.word_target for b in beats)
        )


# Convenience function for getting chapter guidance from SSBA arc
def get_chapter_guidance_from_arc(
    story_arc: Dict[str, Any],
    chapter_number: int,
    total_chapters: int
) -> Dict[str, Any]:
    """
    Extract chapter-specific guidance from SSBA's story arc.

    For multi-chapter stories, SSBA creates a full arc with guidance
    for each chapter. This function extracts the relevant guidance.

    Args:
        story_arc: Full story arc from SSBA
        chapter_number: Current chapter
        total_chapters: Total chapters

    Returns:
        Dict with chapter guidance
    """
    progress_pct = (chapter_number / total_chapters) * 100

    # Determine act
    if progress_pct < 25:
        act = "1"
        phase = "Setup"
    elif progress_pct < 50:
        act = "2a"
        phase = "Fun & Games"
    elif progress_pct < 75:
        act = "2b"
        phase = "Bad Guys Close In"
    else:
        act = "3"
        phase = "Resolution"

    # This would be enhanced to extract from actual SSBA arc structure
    return {
        "act": act,
        "phase": phase,
        "progress_percentage": progress_pct,
        "current_story_beat": "N/A",  # Would be extracted from arc
        "guidance_for_cba": f"Chapter {chapter_number} should advance the {phase} phase."
    }
