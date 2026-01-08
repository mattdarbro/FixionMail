"""
WriterAgent: Generates complete stories in a single LLM call.

Replaces the 3-agent flow (CBA → CEA → PA) with a single, focused writer.
Supports model selection: Sonnet 4.5 (default) or Opus 4.5 (premium quality).
"""

import json
import time
from typing import Dict, Any, Optional, Literal
from dataclasses import dataclass

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage

from backend.config import config


# Model configurations
WRITER_MODELS = {
    "sonnet": {
        "model_id": "claude-sonnet-4-5-20250929",
        "name": "Claude Sonnet 4.5",
        "description": "Fast, high-quality writing (default)",
        "cost_tier": "standard"
    },
    "opus": {
        "model_id": "claude-opus-4-5-20251101",
        "name": "Claude Opus 4.5",
        "description": "Premium quality, deeper creativity",
        "cost_tier": "premium"
    }
}

# Type alias for model selection
WriterModel = Literal["sonnet", "opus"]


def get_available_writer_models() -> Dict[str, Any]:
    """Get available writer models with their configurations."""
    return WRITER_MODELS.copy()


@dataclass
class WriterResult:
    """Result from WriterAgent."""
    success: bool
    title: str
    narrative: str
    word_count: int
    plot_type: str
    story_premise: str
    generation_time: float
    model_used: str = "sonnet"
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "title": self.title,
            "narrative": self.narrative,
            "word_count": self.word_count,
            "plot_type": self.plot_type,
            "story_premise": self.story_premise,
            "generation_time": self.generation_time,
            "model_used": self.model_used,
            "error": self.error
        }


class WriterAgent:
    """
    Generates complete stories in a single LLM call.

    Combines beat planning and prose generation into one prompt,
    reducing API calls from 3 to 1 and improving coherence.

    Supports two models:
    - sonnet (default): Claude Sonnet 4.5 - fast, high-quality
    - opus: Claude Opus 4.5 - premium quality, deeper creativity
    """

    # Default model
    DEFAULT_MODEL = "sonnet"

    def __init__(
        self,
        model: WriterModel = None,
        model_name: str = None,  # Legacy parameter
        temperature: float = 0.8
    ):
        """
        Initialize WriterAgent.

        Args:
            model: Model to use - "sonnet" (default) or "opus" (premium)
            model_name: Legacy parameter (deprecated, use `model` instead)
            temperature: Creativity level (0.7-0.9 recommended for prose)
        """
        # Determine which model to use
        if model and model in WRITER_MODELS:
            self.model_key = model
        elif model_name:
            # Legacy: if model_name contains "opus", use opus
            self.model_key = "opus" if "opus" in model_name.lower() else "sonnet"
        else:
            self.model_key = self.DEFAULT_MODEL

        self.model_config = WRITER_MODELS[self.model_key]
        self.model_name = self.model_config["model_id"]
        self.temperature = temperature

        self.llm = ChatAnthropic(
            model=self.model_name,
            temperature=self.temperature,
            max_tokens=8000,  # Enough for ~5000 word stories
            anthropic_api_key=config.ANTHROPIC_API_KEY,
            timeout=180.0,  # 3 minutes for long stories
        )

    async def generate(
        self,
        story_bible: Dict[str, Any],
        beat_template: Dict[str, Any],
        is_cliffhanger: bool = False,
        cameo: Optional[Dict[str, Any]] = None,
        user_preferences: Optional[Dict[str, Any]] = None,
        excluded_names: Optional[Dict[str, Any]] = None,
        judge_feedback: Optional[str] = None
    ) -> WriterResult:
        """
        Generate a complete story.

        Args:
            story_bible: Enhanced story bible with world, characters, settings
            beat_template: Beat structure template
            is_cliffhanger: Whether to end on a cliffhanger (free tier)
            cameo: Optional cameo character
            user_preferences: User preferences from ratings
            excluded_names: Names to avoid (recently used)
            judge_feedback: Feedback from Judge for rewrite attempts

        Returns:
            WriterResult with complete story
        """
        start_time = time.time()

        try:
            # Build the prompt
            prompt = self._build_prompt(
                story_bible=story_bible,
                beat_template=beat_template,
                is_cliffhanger=is_cliffhanger,
                cameo=cameo,
                user_preferences=user_preferences,
                excluded_names=excluded_names,
                judge_feedback=judge_feedback
            )

            # Generate story
            response = await self.llm.ainvoke([HumanMessage(content=prompt)])

            generation_time = time.time() - start_time

            # Parse response
            result = self._parse_response(response.content, generation_time)

            return result

        except Exception as e:
            generation_time = time.time() - start_time
            return WriterResult(
                success=False,
                title="",
                narrative="",
                word_count=0,
                plot_type="",
                story_premise="",
                generation_time=generation_time,
                model_used=self.model_key,
                error=str(e)
            )

    def _build_prompt(
        self,
        story_bible: Dict[str, Any],
        beat_template: Dict[str, Any],
        is_cliffhanger: bool,
        cameo: Optional[Dict[str, Any]],
        user_preferences: Optional[Dict[str, Any]],
        excluded_names: Optional[Dict[str, Any]],
        judge_feedback: Optional[str]
    ) -> str:
        """Build the writer prompt."""

        # Extract story bible components
        genre = story_bible.get("genre", "fiction")
        setting = story_bible.get("setting", {})
        tone = story_bible.get("tone", "")
        themes = story_bible.get("themes", [])
        story_history = story_bible.get("story_history", {})
        genre_config = story_bible.get("genre_config", {})
        story_settings = story_bible.get("story_settings", {})

        # Handle characters - genre_config is the authority for whether to use recurring characters
        # This ensures genre changes take effect (e.g., switching from detective to cozy uses fresh chars)
        has_recurring_chars = genre_config.get("characters") == "user"
        protagonist = story_bible.get("protagonist", story_bible.get("character_template", {})) if has_recurring_chars else {}
        supporting = story_bible.get("supporting_characters", story_bible.get("supporting_cast_template", [])) if has_recurring_chars else []
        main_characters = story_bible.get("main_characters", []) if has_recurring_chars else []

        # Check if we have SSBA-structured beats or generic template
        is_structured = self._is_structured_beat_plan(beat_template)

        # Template details
        total_words = beat_template.get("total_words", 1500)
        beats = beat_template.get("beats", [])

        # Build context sections
        history_context = self._build_history_context(story_history)
        prefs_context = self._build_preferences_context(user_preferences)
        excluded_context = self._build_excluded_names_context(excluded_names)
        cameo_context = self._build_cameo_context(cameo)
        ending_context = self._build_ending_context(is_cliffhanger)
        intensity_context = self._build_intensity_context(story_settings)
        beats_context = self._build_beats_context(beats, is_structured=is_structured)
        feedback_context = self._build_feedback_context(judge_feedback)

        # Build SSBA planning section if structured, otherwise use THINK FIRST
        if is_structured:
            story_premise = beat_template.get("story_premise", "")
            central_conflict = beat_template.get("central_conflict", "")
            emotional_journey = beat_template.get("emotional_journey", "")
            thematic_core = beat_template.get("thematic_core", "")

            planning_section = f"""
## STORY DESIGN (from Structure Agent)

The story architecture has been designed for you. Your job is to bring it to life with vivid prose.

**Story Premise**: {story_premise}
**Central Conflict**: {central_conflict}
**Emotional Journey**: {emotional_journey}
**Thematic Core**: {thematic_core}

Execute this vision with excellent prose craft. The structure is set—focus on bringing each beat to life.
"""
            beat_instruction = "Follow this beat structure precisely. Each beat has specific SCENE details, EMOTIONAL ARC, and KEY MOMENTS to hit:"
        else:
            planning_section = """
## THINK FIRST

Before writing, mentally plan:
1. **Core Conflict**: What does the protagonist want? What stands in their way?
2. **Emotional Arc**: How does the protagonist feel at start vs end? What changes them?
3. **Central Image/Symbol**: What recurring image or motif ties the story together?
4. **The Hook**: What specific moment or question will grab the reader immediately?
5. **Genre Promise**: What does this genre owe the reader? (Mystery = puzzle solved, Romance = relationship, etc.)

Let these guide every scene. A story without clear conflict and change is just events happening.
"""
            beat_instruction = "Follow this beat structure carefully. Each beat has a PURPOSE (what happens) and CRAFT GUIDANCE (how to write it):"

        prompt = f"""You are an expert fiction writer creating a complete standalone story.

## YOUR TASK

Write a complete, polished {total_words}-word story. This should be publication-ready prose.
{feedback_context}

## STORY WORLD

**Genre**: {genre_config.get('label', genre)}
**Tone**: {tone}
**Themes**: {', '.join(themes) if themes else 'To be discovered'}

**Setting**: {setting.get('name', 'N/A')}
{setting.get('description', '')}

**Atmosphere**: {setting.get('atmosphere', '')}
{intensity_context}
## {"PROTAGONIST (recurring)" if has_recurring_chars else "CHARACTER (create fresh)"}

{"**Name**: " + protagonist.get('name', 'N/A') if has_recurring_chars else "**Archetype**: " + protagonist.get('archetype', 'To be determined')}
**Role**: {protagonist.get('role', 'N/A')}
**Traits**: {', '.join(protagonist.get('key_traits', []))}
**Defining Characteristic**: {protagonist.get('defining_characteristic', 'N/A')}
**Voice**: {protagonist.get('voice', 'thoughtful')}

{"" if has_recurring_chars else "**Create a NEW protagonist** with a unique name based on this template."}

{f'''## MAIN CHARACTERS (MUST appear)

These recurring characters MUST appear in this story:
{json.dumps(main_characters, indent=2)}
''' if main_characters else ''}
{f'''## SUPPORTING CAST
{json.dumps(supporting, indent=2)}
''' if supporting else ''}
{history_context}
{prefs_context}
{excluded_context}
{cameo_context}
{ending_context}
{planning_section}
## STORY STRUCTURE ({len(beats)} beats, {total_words} words total)

{beat_instruction}
{beats_context}

## OUTPUT FORMAT

Return your response as JSON with this structure:

```json
{{
  "title": "Your story title",
  "premise": "One-sentence story hook",
  "plot_type": "mystery/action/romance/character study/etc",
  "narrative": "YOUR COMPLETE STORY HERE - all {total_words} words of polished prose"
}}
```

## CRAFT GUIDELINES

**Opening (First 100 words)**:
- Drop readers into action or a compelling moment—no "waking up" or weather descriptions
- Establish voice immediately—how does this narrator sound?
- Plant the story question: what does the reader want answered?
- Ground us: who, where, and what's at stake

**Prose Craft**:
- **Specific beats general**: "She clutched the frayed photograph" not "She held something important"
- **Active voice**: "The door slammed" not "The door was slammed"
- **Sensory layering**: Each scene needs sight + at least one other sense (sound, smell, touch, taste)
- **Dialogue tags**: "said" is invisible. Use action beats instead of adverbs: "She slammed the cup down. 'I said no.'"
- **White space**: Break up long paragraphs. One idea per paragraph in tense scenes.

**Tension & Pacing**:
- Every scene needs conflict—even quiet scenes have undercurrent of tension
- Vary sentence length: short punchy sentences for action, longer flowing ones for reflection
- End scenes on a question, revelation, or decision—never on resolution mid-story
- Cut the throat-clearing: start scenes late, leave early

**Character Depth**:
- Characters want something concrete AND something deeper (surface goal + emotional need)
- Show contradiction: brave people have fears, kind people have limits
- Dialogue reveals character: how they deflect, what they avoid saying
- Internal thought should conflict with external action at least once

**Ending**:
- Return to the opening image or question with new meaning
- The final line should resonate—last impression matters most
- Earn the emotion: if it's triumph, we need to have felt the struggle

Write the complete story now. Target exactly {total_words} words.
"""
        return prompt

    def _build_history_context(self, story_history: Dict[str, Any]) -> str:
        """Build recent story history context."""
        recent_summaries = story_history.get("recent_summaries", [])
        recent_plots = story_history.get("recent_plot_types", [])
        recent_titles = story_history.get("recent_titles", [])

        if not recent_summaries and not recent_titles:
            return ""

        context = "\n\n## ⚠️ CRITICAL: RECENT STORIES (DO NOT REPEAT) ⚠️\n\n"

        # CRITICAL: Exclude recent titles to prevent duplicates
        if recent_titles:
            titles_text = ", ".join([f'"{t}"' for t in recent_titles[-10:]])
            context += f"**🚫 FORBIDDEN TITLES (already used - DO NOT USE)**: {titles_text}\n\n"
            context += "**HARD REQUIREMENT**: Your title MUST be completely different from ALL titles listed above.\n"
            context += "- Do NOT use ANY of these titles, even with small modifications\n"
            context += "- Do NOT use similar phrases or word patterns\n"
            context += "- Create something FRESH and ORIGINAL\n"
            context += "- If you use a forbidden title, the story will be REJECTED\n\n"

        if recent_summaries:
            history_text = "\n".join([f"  - {s}" for s in recent_summaries[-5:]])
            context += f"**Recent story summaries (avoid similar plots)**:\n{history_text}\n"

        if recent_plots:
            plots_text = ", ".join(recent_plots[-5:])
            context += f"\n**Recent plot types**: {plots_text}"

        return context

    def _build_preferences_context(self, user_preferences: Optional[Dict[str, Any]]) -> str:
        """Build user preferences context."""
        if not user_preferences:
            return ""

        pacing = user_preferences.get("pacing_preference", "medium")
        action = user_preferences.get("action_level", "medium")
        emotion = user_preferences.get("emotional_depth", "medium")

        return f"""

## USER PREFERENCES

Based on their ratings, this user prefers:
- Pacing: {pacing}
- Action level: {action}
- Emotional depth: {emotion}

Adjust the story to match these preferences.
"""

    def _build_excluded_names_context(self, excluded_names: Optional[Dict[str, Any]]) -> str:
        """Build excluded names context."""
        if not excluded_names:
            return ""

        char_names = excluded_names.get("characters", [])
        place_names = excluded_names.get("places", [])

        if not char_names and not place_names:
            return ""

        context = "\n\n## AVOID THESE NAMES (recently used)\n\n"
        if char_names:
            context += f"**Characters to AVOID**: {', '.join(char_names[:20])}\n"
        if place_names:
            context += f"**Places to AVOID**: {', '.join(place_names[:20])}\n"
        context += "\nCreate FRESH, unique names with diverse cultural backgrounds."

        return context

    def _build_cameo_context(self, cameo: Optional[Dict[str, Any]]) -> str:
        """Build cameo character context."""
        if not cameo:
            return ""

        return f"""

## CAMEO CHARACTER (optional)

Include a brief cameo if it fits naturally:
- **Name**: {cameo.get('name', 'N/A')}
- **Description**: {cameo.get('description', 'N/A')}

Brief appearance only - don't force it.
"""

    def _build_intensity_context(self, story_settings: Dict[str, Any]) -> str:
        """Build intensity guidance context."""
        intensity = story_settings.get("intensity", 5)
        intensity_label = story_settings.get("intensity_label", "Moderate")

        # Map intensity to specific craft guidance
        if intensity <= 3:
            return """
## INTENSITY: Cozy/Light

This reader wants a **gentle, comforting** experience:
- **Pacing**: Leisurely. Let scenes breathe. Savor small moments.
- **Stakes**: Personal rather than life-threatening. Emotional rather than physical danger.
- **Tone**: Warm, hopeful. Humor welcome. Avoid graphic violence or heavy darkness.
- **Conflict**: Misunderstandings, personal growth challenges, gentle mysteries.
- **Resolution**: Satisfying, heartwarming. Reader should feel comforted.

Think: cozy mystery, gentle romance, feel-good fiction.
"""
        elif intensity <= 6:
            return """
## INTENSITY: Moderate

Balanced approach with **meaningful stakes**:
- **Pacing**: Varied. Build tension but allow breathing room.
- **Stakes**: Real consequences but not overwhelming darkness.
- **Tone**: Engaging with emotional range. Can include tension and lighter moments.
- **Conflict**: Genuine obstacles requiring effort to overcome.
- **Resolution**: Earned victory or meaningful change.

Think: mainstream thriller, adventure, contemporary drama.
"""
        else:
            return """
## INTENSITY: High/Intense

Reader wants **gripping, high-stakes** storytelling:
- **Pacing**: Propulsive. Keep tension high. Short, punchy scenes in action sequences.
- **Stakes**: Life, death, devastating consequences feel possible.
- **Tone**: Dark, suspenseful, urgent. Danger feels real.
- **Conflict**: Formidable obstacles. Antagonist is genuinely threatening.
- **Resolution**: Hard-won. Scars remain. Victory costs something.

Think: thriller, dark fantasy, intense drama with real peril.
"""

    def _build_ending_context(self, is_cliffhanger: bool) -> str:
        """Build ending style context."""
        if is_cliffhanger:
            return """

## ENDING STYLE: Curiosity Hook

End on an intriguing note:
- **DO**: Resolve the immediate story question
- **DO**: End with a new discovery, revelation, or question
- **DON'T**: End on life-or-death peril
- **DON'T**: Leave the core plot unresolved

Example: "She found the answer. But it raised a bigger question—one she wasn't sure she wanted answered."
"""
        else:
            return """

## ENDING STYLE: Complete Resolution

Give a satisfying conclusion:
- Resolve the central story question
- Emotional or thematic landing
- Character growth or realization
- Sense of completion
"""

    def _build_beats_context(self, beats: list, is_structured: bool = False) -> str:
        """
        Build beat structure context.

        Args:
            beats: List of beat dictionaries
            is_structured: True if beats are from SSBA (story-specific),
                          False if from generic templates

        Returns:
            Formatted beats context for prompt
        """
        beats_text = ""

        for beat in beats:
            beat_num = beat.get("beat_number", "?")
            beat_name = beat.get("beat_name", "")
            word_target = beat.get("word_target", 0)

            beats_text += f"\n**Beat {beat_num}: {beat_name.upper()}** ({word_target} words)\n"

            if is_structured:
                # SSBA-structured beats have rich story-specific details
                scene = beat.get("scene_description", "")
                emotional_arc = beat.get("emotional_arc", "")
                tension = beat.get("tension_level", "")
                character = beat.get("character_focus", "")
                key_moment = beat.get("key_moment", "")
                purpose = beat.get("purpose", "")
                theme_connection = beat.get("connects_to_theme", "")

                beats_text += f"*Scene*: {scene}\n"
                beats_text += f"*Emotional Arc*: {emotional_arc}\n"
                beats_text += f"*Tension*: {tension}\n"
                beats_text += f"*Character Focus*: {character}\n"
                beats_text += f"*Key Moment*: {key_moment}\n"
                beats_text += f"*Purpose*: {purpose}\n"
                if theme_connection:
                    beats_text += f"*Theme Connection*: {theme_connection}\n"
            else:
                # Generic template beats have description and guidance
                description = beat.get("description", "")
                guidance = beat.get("guidance", "")

                beats_text += f"*Purpose*: {description}\n"
                if guidance:
                    beats_text += f"*Craft guidance*: {guidance}\n"

        return beats_text

    def _is_structured_beat_plan(self, beat_template: Dict[str, Any]) -> bool:
        """
        Detect if beat_template is from SSBA (structured) or generic template.

        SSBA structures have: story_premise, central_conflict, emotional_journey
        Generic templates have: name, genre, description
        """
        # Check for SSBA-specific fields
        ssba_fields = ["story_premise", "central_conflict", "emotional_journey", "thematic_core"]
        return any(field in beat_template for field in ssba_fields)

    def _build_feedback_context(self, judge_feedback: Optional[str]) -> str:
        """Build Judge feedback context for rewrites."""
        if not judge_feedback:
            return ""

        return f"""

## REWRITE REQUIRED

The previous version had issues. Address this feedback:

{judge_feedback}

Make sure to fix ALL issues mentioned above.
"""

    def _parse_response(self, response_text: str, generation_time: float) -> WriterResult:
        """Parse LLM response into WriterResult."""

        # Try to extract JSON
        text = response_text.strip()

        # Handle markdown code blocks
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()

        try:
            data = json.loads(text)

            narrative = data.get("narrative", "")
            word_count = len(narrative.split())

            return WriterResult(
                success=True,
                title=data.get("title", "Untitled"),
                narrative=narrative,
                word_count=word_count,
                plot_type=data.get("plot_type", "unknown"),
                story_premise=data.get("premise", ""),
                generation_time=generation_time,
                model_used=self.model_key
            )

        except json.JSONDecodeError:
            # If JSON parsing fails, treat entire response as narrative
            # Try to extract a title from the first line
            lines = response_text.strip().split("\n")
            title = "Untitled"
            narrative = response_text.strip()

            # Check if first line looks like a title
            if lines and len(lines[0]) < 100 and not lines[0].startswith(("The ", "A ", "I ", "She ", "He ")):
                title = lines[0].strip().strip("#").strip()
                narrative = "\n".join(lines[1:]).strip()

            word_count = len(narrative.split())

            return WriterResult(
                success=True,
                title=title,
                narrative=narrative,
                word_count=word_count,
                plot_type="unknown",
                story_premise="",
                generation_time=generation_time,
                model_used=self.model_key
            )
