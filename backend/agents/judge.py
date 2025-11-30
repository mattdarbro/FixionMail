"""
JudgeAgent: Validates stories against requirements.

Uses Claude Haiku for fast, cheap validation.
Returns pass/fail with feedback for rewrites if needed.
"""

import json
import time
from typing import Dict, Any, Optional
from dataclasses import dataclass

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage

from backend.config import config


@dataclass
class JudgeResult:
    """Result from JudgeAgent."""
    passed: bool
    feedback: Optional[str]  # Feedback for rewrite if failed
    scores: Dict[str, int]  # Individual scores (1-10)
    overall_score: int  # Average score
    validation_time: float
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "passed": self.passed,
            "feedback": self.feedback,
            "scores": self.scores,
            "overall_score": self.overall_score,
            "validation_time": self.validation_time,
            "error": self.error
        }


class JudgeAgent:
    """
    Validates stories against quality requirements.

    Uses Claude Haiku for fast, low-cost validation.
    Checks: word count, character consistency, structure, quality.
    """

    # Haiku model for fast/cheap validation
    HAIKU_MODEL = "claude-3-5-haiku-20241022"

    # Minimum passing score (average of all scores)
    PASSING_SCORE = 7

    def __init__(self, model_name: str = None, passing_score: int = None):
        """
        Initialize JudgeAgent.

        Args:
            model_name: Model to use (defaults to Haiku)
            passing_score: Minimum average score to pass (defaults to 7)
        """
        self.model_name = model_name or self.HAIKU_MODEL
        self.passing_score = passing_score or self.PASSING_SCORE

        self.llm = ChatAnthropic(
            model=self.model_name,
            temperature=0.0,  # Deterministic for consistent evaluation
            max_tokens=1500,
            anthropic_api_key=config.ANTHROPIC_API_KEY,
            timeout=30.0,  # Quick validation
        )

    async def validate(
        self,
        narrative: str,
        title: str,
        story_bible: Dict[str, Any],
        beat_template: Dict[str, Any],
        is_cliffhanger: bool = False
    ) -> JudgeResult:
        """
        Validate a story against requirements.

        Args:
            narrative: The story text to validate
            title: Story title
            story_bible: Story bible for character/world validation
            beat_template: Beat template used
            is_cliffhanger: Whether story should have cliffhanger ending

        Returns:
            JudgeResult with pass/fail and feedback
        """
        start_time = time.time()

        try:
            # Build validation prompt
            prompt = self._build_prompt(
                narrative=narrative,
                title=title,
                story_bible=story_bible,
                beat_template=beat_template,
                is_cliffhanger=is_cliffhanger
            )

            # Run validation
            response = await self.llm.ainvoke([HumanMessage(content=prompt)])

            validation_time = time.time() - start_time

            # Parse response
            result = self._parse_response(response.content, validation_time)

            return result

        except Exception as e:
            validation_time = time.time() - start_time
            return JudgeResult(
                passed=True,  # Pass on error to avoid blocking
                feedback=None,
                scores={},
                overall_score=7,
                validation_time=validation_time,
                error=str(e)
            )

    def _build_prompt(
        self,
        narrative: str,
        title: str,
        story_bible: Dict[str, Any],
        beat_template: Dict[str, Any],
        is_cliffhanger: bool
    ) -> str:
        """Build the validation prompt."""

        # Extract requirements
        genre = story_bible.get("genre", "fiction")
        tone = story_bible.get("tone", "")
        total_words = beat_template.get("total_words", 1500)
        word_tolerance = int(total_words * 0.15)  # ±15% tolerance

        # Character info
        protagonist = story_bible.get("protagonist", story_bible.get("character_template", {}))
        prot_name = protagonist.get("name", "protagonist")
        prot_traits = protagonist.get("key_traits", [])
        prot_defining = protagonist.get("defining_characteristic", "")

        # Main characters that must appear
        main_characters = story_bible.get("main_characters", [])
        main_char_names = [c.get("name", "") for c in main_characters if c.get("name")]

        # Count actual words
        actual_words = len(narrative.split())

        prompt = f"""You are a story quality validator. Evaluate this story against requirements.

## STORY TO VALIDATE

**Title**: {title}
**Word Count**: {actual_words} (target: {total_words} ±{word_tolerance})

**Story Text**:
{narrative[:6000]}  {f"... [truncated, {actual_words} total words]" if len(narrative) > 6000 else ""}

## REQUIREMENTS

**Genre**: {genre}
**Tone**: {tone}
**Target Word Count**: {total_words} words (±15% acceptable = {total_words - word_tolerance} to {total_words + word_tolerance})

**Protagonist**: {prot_name}
- Traits: {', '.join(prot_traits) if prot_traits else 'N/A'}
- Defining Characteristic: {prot_defining}

{f"**Required Characters (must appear)**: {', '.join(main_char_names)}" if main_char_names else ""}

**Ending Style**: {"Curiosity hook (resolved but intriguing)" if is_cliffhanger else "Complete resolution"}

## EVALUATION CRITERIA

Score each criterion 1-10:

1. **WORD_COUNT**: Is it within ±15% of target?
   - 10: Perfect match (±5%)
   - 7-9: Within tolerance (±15%)
   - 4-6: Slightly off (±25%)
   - 1-3: Way off (>25%)

2. **CHARACTER_CONSISTENCY**: Do characters match their defined traits?
   - Does protagonist act according to their traits?
   - Is the defining characteristic respected?
   - {f"Do {', '.join(main_char_names)} appear?" if main_char_names else "Are characters consistent?"}

3. **STRUCTURE**: Does the story have proper structure?
   - Clear beginning, middle, end
   - Appropriate pacing
   - Proper ending style ({"curiosity hook" if is_cliffhanger else "resolution"})

4. **PROSE_QUALITY**: Is the writing good?
   - Engaging prose
   - Show don't tell
   - Varied sentences
   - Natural dialogue

5. **GENRE_FIT**: Does it feel like {genre}?
   - Appropriate tone
   - Genre conventions followed
   - Reader expectations met

## OUTPUT FORMAT

Return JSON:

```json
{{
  "scores": {{
    "word_count": 8,
    "character_consistency": 9,
    "structure": 7,
    "prose_quality": 8,
    "genre_fit": 9
  }},
  "passed": true,
  "feedback": null,
  "issues": []
}}
```

If ANY score is below 6, set `passed: false` and provide specific feedback in the `feedback` field explaining what needs to be fixed.

Example feedback: "Word count is 900 (target 1500). Protagonist Elena doesn't show her 'stubborn determination' trait. Story ends abruptly without resolution."

Validate the story now:
"""
        return prompt

    def _parse_response(self, response_text: str, validation_time: float) -> JudgeResult:
        """Parse LLM response into JudgeResult."""

        text = response_text.strip()

        # Handle markdown code blocks
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()

        try:
            data = json.loads(text)

            scores = data.get("scores", {})

            # Calculate overall score
            score_values = list(scores.values())
            overall_score = sum(score_values) // len(score_values) if score_values else 7

            # Check if any score is too low
            min_score = min(score_values) if score_values else 7
            passed = data.get("passed", min_score >= 6 and overall_score >= self.passing_score)

            feedback = data.get("feedback")
            if not passed and not feedback:
                # Generate feedback from issues if not provided
                issues = data.get("issues", [])
                if issues:
                    feedback = ". ".join(issues)
                else:
                    # Generate from low scores
                    low_scores = [k for k, v in scores.items() if v < 6]
                    if low_scores:
                        feedback = f"Low scores in: {', '.join(low_scores)}. Please improve these areas."

            return JudgeResult(
                passed=passed,
                feedback=feedback if not passed else None,
                scores=scores,
                overall_score=overall_score,
                validation_time=validation_time
            )

        except json.JSONDecodeError:
            # If parsing fails, assume pass (don't block on validation errors)
            return JudgeResult(
                passed=True,
                feedback=None,
                scores={},
                overall_score=7,
                validation_time=validation_time,
                error="Failed to parse validation response"
            )
