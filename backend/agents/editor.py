"""
EditorAgent: Rewrites and polishes first drafts using Opus.

Takes a first draft from WriterAgent and transforms it into a polished,
publication-ready story. Also validates quality (combines editor + judge roles).

This is the final stage of the 3-agent pipeline:
  SSBA (Sonnet) → WriterAgent (Sonnet) → EditorAgent (Opus)
"""

import json
import time
from typing import Dict, Any, Optional, Literal
from dataclasses import dataclass

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage

from backend.config import config


# Model configuration - Editor uses Opus for highest quality
EDITOR_MODELS = {
    "opus": {
        "model_id": "claude-opus-4-5-20251101",
        "name": "Claude Opus 4.5",
        "description": "Premium quality editing and polish",
        "cost_tier": "premium"
    },
    "sonnet": {
        "model_id": "claude-sonnet-4-5-20250929",
        "name": "Claude Sonnet 4.5",
        "description": "Fast editing (not recommended)",
        "cost_tier": "standard"
    }
}

EditorModel = Literal["opus", "sonnet"]


@dataclass
class EditorResult:
    """Result from EditorAgent."""
    success: bool
    title: str
    narrative: str
    word_count: int
    # Quality assessment (editor also judges)
    quality_scores: Dict[str, int]  # Each score 1-10
    overall_score: float
    passed: bool  # Overall quality threshold met
    edit_notes: str  # What the editor changed/improved
    # Metadata
    generation_time: float
    model_used: str
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "title": self.title,
            "narrative": self.narrative,
            "word_count": self.word_count,
            "quality_scores": self.quality_scores,
            "overall_score": self.overall_score,
            "passed": self.passed,
            "edit_notes": self.edit_notes,
            "generation_time": self.generation_time,
            "model_used": self.model_used,
            "error": self.error
        }


class EditorAgent:
    """
    Editor Agent - Polishes first drafts into publication-ready stories.

    Uses Opus for the highest quality rewriting. Takes the first draft
    from WriterAgent and:
    1. Improves prose quality, pacing, dialogue
    2. Enhances emotional depth and tension
    3. Polishes sentence-level craft
    4. Validates quality (combines editor + judge roles)

    This is the final stage that produces the reader-facing story.
    """

    DEFAULT_MODEL = "opus"  # Always use Opus for editing
    PASSING_SCORE = 7.0  # Average score threshold to pass

    def __init__(
        self,
        model: EditorModel = None,
        temperature: float = 0.7
    ):
        """
        Initialize EditorAgent.

        Args:
            model: Model to use - "opus" (default, recommended) or "sonnet"
            temperature: Creativity level (0.6-0.8 for editing)
        """
        self.model_key = model if model and model in EDITOR_MODELS else self.DEFAULT_MODEL
        self.model_config = EDITOR_MODELS[self.model_key]
        self.model_name = self.model_config["model_id"]
        self.temperature = temperature

        self.llm = ChatAnthropic(
            model=self.model_name,
            temperature=self.temperature,
            max_tokens=10000,  # Enough for rewritten story + notes
            anthropic_api_key=config.ANTHROPIC_API_KEY,
            timeout=300.0,  # 5 minutes for thorough editing
        )

    async def edit(
        self,
        first_draft: str,
        title: str,
        beat_plan: Dict[str, Any],
        story_bible: Dict[str, Any],
        is_cliffhanger: bool = False
    ) -> EditorResult:
        """
        Edit and polish a first draft into a final story.

        Args:
            first_draft: The narrative from WriterAgent
            title: Story title from WriterAgent
            beat_plan: Beat plan (from SSBA or generic template)
            story_bible: Story bible with world, characters, settings
            is_cliffhanger: Whether story should end on a hook

        Returns:
            EditorResult with polished story and quality assessment
        """
        start_time = time.time()

        try:
            prompt = self._build_prompt(
                first_draft=first_draft,
                title=title,
                beat_plan=beat_plan,
                story_bible=story_bible,
                is_cliffhanger=is_cliffhanger
            )

            response = await self.llm.ainvoke([HumanMessage(content=prompt)])
            generation_time = time.time() - start_time

            result = self._parse_response(response.content, generation_time)
            return result

        except Exception as e:
            generation_time = time.time() - start_time
            return EditorResult(
                success=False,
                title=title,
                narrative=first_draft,  # Return original on failure
                word_count=len(first_draft.split()),
                quality_scores={},
                overall_score=0.0,
                passed=False,
                edit_notes="",
                generation_time=generation_time,
                model_used=self.model_key,
                error=str(e)
            )

    def _build_prompt(
        self,
        first_draft: str,
        title: str,
        beat_plan: Dict[str, Any],
        story_bible: Dict[str, Any],
        is_cliffhanger: bool
    ) -> str:
        """Build the editor prompt."""

        # Extract key info
        genre = story_bible.get("genre", "fiction")
        genre_config = story_bible.get("genre_config", {})
        tone = story_bible.get("tone", "")
        themes = story_bible.get("themes", [])
        total_words = beat_plan.get("total_words", 1500)

        # Check for recurring characters that must be preserved
        has_recurring_chars = genre_config.get("characters") == "user"
        main_characters = story_bible.get("main_characters", []) if has_recurring_chars else []
        protagonist = story_bible.get("protagonist", {}) if has_recurring_chars else {}

        # Get story structure info if available (from SSBA)
        story_premise = beat_plan.get("story_premise", "")
        central_conflict = beat_plan.get("central_conflict", "")
        emotional_journey = beat_plan.get("emotional_journey", "")

        # Undercurrent (Deeper Themes) info from beat plan
        moral_premise = beat_plan.get("moral_premise", "")
        undercurrent_theme = beat_plan.get("undercurrent_theme", "")
        undercurrent_crystallization = beat_plan.get("undercurrent_crystallization", "")

        # Intensity from settings
        story_settings = story_bible.get("story_settings", {})
        intensity = story_settings.get("intensity", 5)
        intensity_label = story_settings.get("intensity_label", "Moderate")

        # Undercurrent settings
        undercurrent_mode = story_settings.get("undercurrent_mode", "off")
        undercurrent_active = undercurrent_mode in ("custom", "surprise")

        # Ending style
        ending_guidance = self._get_ending_guidance(is_cliffhanger)

        # Build undercurrent section if active
        undercurrent_section = ""
        if undercurrent_active and (moral_premise or undercurrent_theme):
            undercurrent_section = f"""
## UNDERCURRENT (Deeper Themes)

This story has a deliberate thematic undercurrent that should resonate with readers:

**Moral Premise**: {moral_premise if moral_premise else 'To be expressed through character journey'}
**Theme**: {undercurrent_theme if undercurrent_theme else 'Embedded in the narrative'}
**Crystallization Point**: {undercurrent_crystallization if undercurrent_crystallization else 'Climax or resolution'}

**YOUR UNDERCURRENT MANDATE**:
As you polish, ensure the deeper theme lands powerfully but subtly:

1. **Enhance, Don't Add**: The theme is already seeded—bring it to the surface through craft
2. **Show Through Action**: Ensure the crystallization moment demonstrates the theme through what characters DO
3. **Avoid Preaching**: Cut any dialogue or narration that states the theme directly
4. **Consequences Matter**: Make sure actions aligned with/against the theme have meaningful outcomes
5. **The Last Line**: Consider whether the final sentence resonates with the undercurrent

**CRAFT THE UNDERCURRENT**:
- Sensory details that echo the theme
- Dialogue subtext that reflects the moral premise
- Internal moments where the protagonist glimpses the truth
- A climax where the theme crystallizes through choice and consequence
"""

        # Build quality criteria based on undercurrent mode
        if undercurrent_active:
            quality_criteria_section = """## QUALITY CRITERIA (score each 1-10)

**CRAFT CRITERIA**:
- **prose_craft**: Sentence-level quality, vivid language, sensory detail
- **dialogue**: Natural, distinct voices, reveals character
- **pacing**: Tension builds appropriately, no dead spots
- **emotional_depth**: Reader feels something, character interiority
- **structure**: Beats accomplished, satisfying arc, strong ending
- **genre_fit**: Delivers on genre promises, appropriate tone

**UNDERCURRENT CRITERIA** (these matter for this story):
- **thematic_resonance**: Does the deeper theme emerge naturally and powerfully?
- **moral_clarity**: Is the undercurrent truth clear without being heavy-handed?
- **lasting_impact**: Will this story stay with the reader? Does it mean something?

A score of 7+ in each category indicates publication-ready quality.
An undercurrent score of 8+ indicates a story that will resonate beyond entertainment."""

            output_format = """## OUTPUT FORMAT

Return your response as JSON:

```json
{{
  "title": "Final title (can revise if original is weak)",
  "narrative": "YOUR COMPLETE POLISHED STORY - the full rewritten narrative",
  "edit_notes": "Brief summary of major improvements made (2-3 sentences)",
  "quality_scores": {{
    "prose_craft": 8,
    "dialogue": 7,
    "pacing": 8,
    "emotional_depth": 7,
    "structure": 8,
    "genre_fit": 8,
    "thematic_resonance": 8,
    "moral_clarity": 8,
    "lasting_impact": 8
  }},
  "word_count": 1500
}}
```"""
        else:
            quality_criteria_section = """## QUALITY CRITERIA (score each 1-10)

- **prose_craft**: Sentence-level quality, vivid language, sensory detail
- **dialogue**: Natural, distinct voices, reveals character
- **pacing**: Tension builds appropriately, no dead spots
- **emotional_depth**: Reader feels something, character interiority
- **structure**: Beats accomplished, satisfying arc, strong ending
- **genre_fit**: Delivers on genre promises, appropriate tone

A score of 7+ in each category indicates publication-ready quality."""

            output_format = """## OUTPUT FORMAT

Return your response as JSON:

```json
{{
  "title": "Final title (can revise if original is weak)",
  "narrative": "YOUR COMPLETE POLISHED STORY - the full rewritten narrative",
  "edit_notes": "Brief summary of major improvements made (2-3 sentences)",
  "quality_scores": {{
    "prose_craft": 8,
    "dialogue": 7,
    "pacing": 8,
    "emotional_depth": 7,
    "structure": 8,
    "genre_fit": 8
  }},
  "word_count": 1500
}}
```"""

        prompt = f"""You are a master editor with decades of experience polishing fiction for publication. Your task is to take this first draft and transform it into a polished, publication-ready story.

## THE FIRST DRAFT

Title: {title}

{first_draft}

## STORY CONTEXT

**Genre**: {genre}
**Tone**: {tone}
**Themes**: {', '.join(themes) if themes else 'N/A'}
**Target Word Count**: {total_words} words (±15%)
**Intensity Level**: {intensity}/10 ({intensity_label})

{f'''**Story Premise**: {story_premise}
**Central Conflict**: {central_conflict}
**Emotional Journey**: {emotional_journey}
''' if story_premise else ''}

{ending_guidance}
{undercurrent_section}
{self._build_character_preservation_section(protagonist, main_characters, has_recurring_chars)}
## YOUR EDITORIAL MANDATE

You are not just proofreading—you are REWRITING to elevate this story. Make it sing.

**PROSE CRAFT** - Transform every sentence:
- Replace weak verbs with vivid ones ("walked" → "strode", "said angrily" → "snapped")
- Add sensory depth—sight + sound + smell + touch
- Vary sentence rhythm: short punchy beats for tension, flowing sentences for reflection
- Cut throat-clearing: start scenes late, leave early
- Show don't tell: replace emotion labels with physical manifestations

**DIALOGUE** - Make every line count:
- Each character should sound distinct
- Subtext > text: what's unsaid matters
- Use action beats instead of adverbs ("she said quietly" → "she lowered her voice")
- Cut pleasantries unless they reveal character

**PACING** - Control the reader's experience:
- Tension should build progressively within each beat
- Use white space strategically—short paragraphs in tense moments
- Every scene needs conflict, even quiet ones
- The ending must land with impact

**EMOTIONAL DEPTH** - Make readers feel:
- Internal conflict should create genuine tension
- Character contradictions make them human
- Vulnerability is more powerful than strength
- Earn the emotional payoff through struggle

**STRUCTURE** - Honor the beat plan:
- Each beat should accomplish its narrative purpose
- Transitions should flow naturally
- The ending must resonate (resolve for standard, hook for cliffhanger)

{output_format}

{quality_criteria_section}

## CRITICAL INSTRUCTIONS

1. REWRITE FULLY - Don't just polish; transform the prose
2. MAINTAIN STORY - Keep the plot, characters, and structure intact
3. ELEVATE EVERYTHING - Every paragraph should be better than before
4. HIT WORD COUNT - Stay within ±15% of {total_words} words
5. BE HONEST - Score the result fairly, not generously
{f"6. HONOR THE UNDERCURRENT - Ensure the deeper theme resonates powerfully" if undercurrent_active else ""}
{f"7. PRESERVE CHARACTER NAMES - Do NOT rename any characters. Keep all names EXACTLY as written in the draft." if has_recurring_chars else ""}

Now edit this story into something remarkable.
"""
        return prompt

    def _get_ending_guidance(self, is_cliffhanger: bool) -> str:
        """Get ending guidance based on cliffhanger setting."""
        if is_cliffhanger:
            return """
## ENDING STYLE: Curiosity Hook

The final paragraphs should:
- RESOLVE the immediate story question
- End with a new discovery, revelation, or question
- NOT end on life-or-death peril
- Leave readers curious, not frustrated
- The last line should haunt or intrigue
"""
        else:
            return """
## ENDING STYLE: Complete Resolution

The final paragraphs should:
- Resolve the central story question
- Provide emotional or thematic closure
- Echo the opening with new meaning
- The last line should resonate and satisfy
"""

    def _build_character_preservation_section(
        self,
        protagonist: Dict[str, Any],
        main_characters: list,
        has_recurring_chars: bool
    ) -> str:
        """Build character name preservation section for recurring character genres."""
        if not has_recurring_chars:
            return ""

        section = """
## ⚠️ CRITICAL: CHARACTER NAME PRESERVATION ⚠️

This story features RECURRING CHARACTERS with ESTABLISHED NAMES. These characters appear across multiple stories and the reader expects consistency.

**DO NOT RENAME ANY CHARACTERS.** Keep every character name EXACTLY as it appears in the draft.
"""
        if protagonist and protagonist.get("name"):
            section += f"""
**Protagonist**: {protagonist.get("name")} ← USE THIS EXACT NAME
- Do NOT substitute with a different name
- Do NOT use nicknames unless already in the draft
- Do NOT create an alias
"""

        if main_characters:
            char_names = [c.get("name", "Unknown") for c in main_characters[:5]]
            section += f"""
**Recurring Characters** (MUST keep these exact names): {", ".join(char_names)}

**Why this matters**: These are the user's characters. They've read previous stories with these names. Changing "Detective Sarah Chen" to "Detective Maya Rodriguez" would be jarring and confusing.

When editing dialogue and prose:
- Preserve character names letter-for-letter
- Keep established relationships and dynamics
- Maintain each character's voice and personality
"""
        return section

    def _parse_response(self, response_text: str, generation_time: float) -> EditorResult:
        """Parse LLM response into EditorResult."""

        text = response_text.strip()

        # Handle markdown code blocks
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()

        try:
            data = json.loads(text)

            narrative = data.get("narrative", "")
            word_count = data.get("word_count", len(narrative.split()))
            quality_scores = data.get("quality_scores", {})

            # Calculate overall score
            if quality_scores:
                overall_score = sum(quality_scores.values()) / len(quality_scores)
            else:
                overall_score = 0.0

            # Check if passed threshold
            passed = overall_score >= self.PASSING_SCORE

            return EditorResult(
                success=True,
                title=data.get("title", "Untitled"),
                narrative=narrative,
                word_count=word_count,
                quality_scores=quality_scores,
                overall_score=round(overall_score, 1),
                passed=passed,
                edit_notes=data.get("edit_notes", ""),
                generation_time=generation_time,
                model_used=self.model_key
            )

        except json.JSONDecodeError:
            # If JSON parsing fails, try to extract narrative
            # This is a fallback for when the model returns prose directly
            return EditorResult(
                success=True,
                title="Untitled",
                narrative=response_text.strip(),
                word_count=len(response_text.split()),
                quality_scores={},
                overall_score=0.0,
                passed=False,
                edit_notes="JSON parsing failed - raw output returned",
                generation_time=generation_time,
                model_used=self.model_key
            )
