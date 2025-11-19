"""
LangGraph node functions for the storytelling workflow.

Each node is a processing step that receives state, performs an operation,
and returns updated state. Nodes should be pure functions when possible.
"""

import json
import asyncio
from typing import Any
from langchain_core.messages import HumanMessage, AIMessage
from langchain_anthropic import ChatAnthropic

from backend.models.state import StoryState
from backend.storyteller.prompts_v2 import (
    load_world_template,
    create_opening_prompt,
    create_continuation_prompt
)
from backend.config import config
import re


# ===== Helper: Prune Story Bible =====

def prune_story_bible(story_bible: dict, current_chapter: int, max_events: int = 10) -> dict:
    """
    Prune story bible to prevent unbounded context growth.

    Keeps only recent and essential information to prevent the story bible
    from growing too large and slowing down generation.

    Args:
        story_bible: Current story bible dict
        current_chapter: Current chapter number
        max_events: Maximum number of key events to keep (default: 10)

    Returns:
        Pruned story bible
    """
    if not story_bible:
        return story_bible

    pruned = story_bible.copy()

    # Limit key_events list to most recent events
    if "key_events" in pruned and isinstance(pruned["key_events"], list):
        if len(pruned["key_events"]) > max_events:
            # Keep only the most recent events
            pruned["key_events"] = pruned["key_events"][-max_events:]
            print(f"   📋 Pruned key_events: {len(story_bible['key_events'])} → {len(pruned['key_events'])} events")

    # Keep protagonist info (essential, doesn't grow much)
    # Keep love_interest info (essential, doesn't grow much)

    # Limit supporting_characters to most recently mentioned
    if "supporting_characters" in pruned and isinstance(pruned["supporting_characters"], dict):
        char_count = len(pruned["supporting_characters"])
        if char_count > 5:
            # Keep only first 5 (most important tend to be added early)
            # In a more sophisticated version, we'd track "last mentioned" timestamps
            pruned_chars = dict(list(pruned["supporting_characters"].items())[:5])
            pruned["supporting_characters"] = pruned_chars
            print(f"   📋 Pruned supporting_characters: {char_count} → {len(pruned_chars)} characters")

    # Limit locations to avoid bloat
    if "locations" in pruned and isinstance(pruned["locations"], dict):
        loc_count = len(pruned["locations"])
        if loc_count > 8:
            # Keep current_location + first 7 locations
            current_loc = pruned["locations"].get("current_location")
            other_locs = {k: v for k, v in pruned["locations"].items() if k != "current_location"}
            limited_locs = dict(list(other_locs.items())[:7])
            if current_loc:
                limited_locs["current_location"] = current_loc
            pruned["locations"] = limited_locs
            print(f"   📋 Pruned locations: {loc_count} → {len(limited_locs)} locations")

    return pruned


# ===== Helper: Ensure Target Word Count =====

async def ensure_target_length(
    llm: ChatAnthropic,
    narrative_json: str,
    target_words: int = 2500,
    tolerance: int = 300,
    max_attempts: int = 1
) -> str:
    """
    Ensure generated narrative meets target word count through iterative refinement.

    LLMs are bad at counting words (they work in tokens). This function:
    1. Parses the narrative from the JSON
    2. Counts actual words
    3. If outside tolerance, asks LLM to expand/trim
    4. Repeats up to max_attempts times

    Args:
        llm: ChatAnthropic instance
        narrative_json: JSON string with narrative field
        target_words: Target word count (default 2500)
        tolerance: Acceptable deviation (default ±300 words)
        max_attempts: Maximum refinement iterations (default 1)

    Returns:
        Refined JSON with narrative at target length
    """
    import time
    refinement_start = time.time()
    current_json = narrative_json

    for attempt in range(max_attempts):
        # Parse JSON to extract narrative
        try:
            data = json.loads(current_json)
            narrative = data.get("narrative", "")

            # Strip beat markers for accurate count
            narrative_clean = re.sub(r'^---\s*BEAT\s+\d+:.*?---\s*$', '', narrative, flags=re.MULTILINE)
            narrative_clean = narrative_clean.strip()

            # Count actual words
            word_count = len(narrative_clean.split())
            min_words = target_words - tolerance
            max_words = target_words + tolerance

            print(f"\n📏 Length Check (Attempt {attempt + 1}/{max_attempts}):")
            print(f"   Current: {word_count} words")
            print(f"   Target: {target_words} words (±{tolerance})")
            print(f"   Range: {min_words}-{max_words} words")

            # Check if acceptable
            if min_words <= word_count <= max_words:
                print(f"   ✅ Length is acceptable!")
                return current_json

            # Too short - ask for expansion
            if word_count < min_words:
                deficit = target_words - word_count
                print(f"   ⚠️  Too short by {deficit} words. Requesting expansion...")

                expansion_prompt = f"""The narrative below is too brief ({word_count} words).
Expand it to approximately {target_words} words by enriching the existing content.

EXPANSION GUIDELINES:
- Add more sensory details (sights, sounds, textures, smells)
- Deepen internal character thoughts and emotions
- Expand scene descriptions with vivid imagery
- Add meaningful dialogue or character reactions
- Strengthen emotional moments

IMPORTANT RULES:
- DO NOT add new plot points or story beats
- DO NOT skip or combine the 6-beat structure
- Keep all existing beat markers: --- BEAT X: NAME ---
- Enrich what's already there, don't create new scenes
- Maintain the same JSON format

Current JSON:
{current_json}

Return the COMPLETE JSON with the expanded narrative (target {target_words} words):"""

                refinement_call_start = time.time()
                response = await llm.ainvoke([HumanMessage(content=expansion_prompt)])
                refinement_call_duration = time.time() - refinement_call_start
                print(f"   ⏱️  Expansion LLM call took {refinement_call_duration:.2f}s")
                current_json = response.content.strip()

                # Clean markdown if present
                if "```json" in current_json:
                    cleaned = current_json.split("```json")[1].split("```")[0].strip()
                    if cleaned:  # Only use cleaned version if it's not empty
                        current_json = cleaned
                    else:
                        print(f"   ⚠️  Markdown cleaning resulted in empty string, using original")
                elif "```" in current_json:
                    cleaned = current_json.split("```")[1].split("```")[0].strip()
                    if cleaned:  # Only use cleaned version if it's not empty
                        current_json = cleaned
                    else:
                        print(f"   ⚠️  Markdown cleaning resulted in empty string, using original")

            # Too long - ask for trimming
            else:
                excess = word_count - target_words
                print(f"   ⚠️  Too long by {excess} words. Requesting trimming...")

                trimming_prompt = f"""The narrative below is too long ({word_count} words).
Trim it to approximately {target_words} words while preserving all key story beats.

TRIMMING GUIDELINES:
- Remove redundant descriptions
- Tighten dialogue (fewer words, same meaning)
- Cut unnecessary details that don't advance the story
- Condense lengthy passages

IMPORTANT RULES:
- DO NOT remove plot points or story beats
- DO NOT skip or combine the 6-beat structure
- Keep all existing beat markers: --- BEAT X: NAME ---
- Preserve emotional moments and character development
- Maintain the same JSON format

Current JSON:
{current_json}

Return the COMPLETE JSON with the trimmed narrative (target {target_words} words):"""

                refinement_call_start = time.time()
                response = await llm.ainvoke([HumanMessage(content=trimming_prompt)])
                refinement_call_duration = time.time() - refinement_call_start
                print(f"   ⏱️  Trimming LLM call took {refinement_call_duration:.2f}s")
                current_json = response.content.strip()

                # Clean markdown if present
                if "```json" in current_json:
                    cleaned = current_json.split("```json")[1].split("```")[0].strip()
                    if cleaned:  # Only use cleaned version if it's not empty
                        current_json = cleaned
                    else:
                        print(f"   ⚠️  Markdown cleaning resulted in empty string, using original")
                elif "```" in current_json:
                    cleaned = current_json.split("```")[1].split("```")[0].strip()
                    if cleaned:  # Only use cleaned version if it's not empty
                        current_json = cleaned
                    else:
                        print(f"   ⚠️  Markdown cleaning resulted in empty string, using original")

        except json.JSONDecodeError as e:
            print(f"   ❌ JSON parse error during refinement: {e}")
            # Return what we have - the parse_output_node will handle it
            break
        except Exception as e:
            print(f"   ❌ Error during length refinement: {e}")
            # If refinement failed, return the original JSON instead of malformed result
            print(f"   ⚠️  Returning original narrative due to refinement error")
            current_json = narrative_json
            break

    # After max attempts, return final result
    # Wrap in try-except in case final parse fails (e.g., if refinement timed out)
    try:
        final_data = json.loads(current_json)
        final_narrative = final_data.get("narrative", "")
        final_clean = re.sub(r'^---\s*BEAT\s+\d+:.*?---\s*$', '', final_narrative, flags=re.MULTILINE).strip()
        final_word_count = len(final_clean.split())
        refinement_duration = time.time() - refinement_start
        print(f"\n📋 Final length after {max_attempts} refinement attempts: {final_word_count} words")
        print(f"⏱️  Refinement duration: {refinement_duration:.2f}s")
    except json.JSONDecodeError as e:
        print(f"\n❌ Failed to parse final JSON for stats: {e}")
        print(f"⏱️  Refinement duration: {time.time() - refinement_start:.2f}s")
        print(f"⚠️  Returning original narrative (refinement failed)")
        # If we can't parse the refined version, return the original
        return narrative_json

    return current_json


# ===== Node 1: Generate Narrative =====

async def generate_narrative_node(state: StoryState) -> dict[str, Any]:
    """
    Generate story narrative using continuation-based prompts with world template.

    Args:
        state: Current story state

    Returns:
        Updated state with narrative_text populated (raw JSON from LLM)
    """
    import time
    start_time = time.time()

    try:
        # Initialize LLM with timeout to prevent indefinite hangs
        llm = ChatAnthropic(
            model=config.MODEL_NAME,
            temperature=config.TEMPERATURE,
            max_tokens=config.MAX_TOKENS,
            anthropic_api_key=config.ANTHROPIC_API_KEY,
            timeout=120.0,  # 2 minute timeout for LLM calls
        )

        # Load world template
        world_template = load_world_template(state["world_id"])

        # Determine if this is the opening
        # Check both message count and chapter number to be safe
        is_opening = len(state["messages"]) == 0 or (len(state["messages"]) == 1 and state.get("chapter_number", 1) == 1)

        print(f"\n{'='*70}")
        print(f"DEBUG: GENERATE_NARRATIVE_NODE")
        print(f"{'='*70}")
        print(f"Is opening: {is_opening}")
        print(f"Chapter number: {state.get('chapter_number', 1)}")
        print(f"Message count: {len(state['messages'])}")
        print(f"State keys: {list(state.keys())}")

        # Select appropriate prompt
        if is_opening:
            # Opening: Claude creates protagonist, scene, and initial story bible
            print(f"✓ Using OPENING prompt for beat {state['current_beat']}")
            prompt = create_opening_prompt(world_template)
            messages = prompt.format_messages()
            print(f"✓ Generating opening narrative for beat {state['current_beat']}")

        else:
            # Continuation: Claude continues from last choice
            print(f"✓ Using CONTINUATION prompt for beat {state['current_beat']}, chapter {state.get('chapter_number', 1)}")

            # Log context size for monitoring
            story_bible = state.get("generated_story_bible", {})
            story_bible_size = len(json.dumps(story_bible))
            summary_size = len(str(state.get("story_summary", [])))
            print(f"📊 Context sizes:")
            print(f"   Story Bible: {story_bible_size:,} chars")
            print(f"   Summaries: {summary_size:,} chars (last {min(6, len(state.get('story_summary', [])))} of {len(state.get('story_summary', []))})")
            print(f"   Estimated total context: ~{(story_bible_size + summary_size + 2000):,} chars (~{int((story_bible_size + summary_size + 2000) / 4)} tokens)")

            last_choice_continuation = state.get("last_choice_continuation", "")

            print(f"Last choice continuation from state: '{last_choice_continuation[:100] if last_choice_continuation else 'EMPTY'}'")

            if not last_choice_continuation:
                # Fallback if continuation not set (shouldn't happen)
                print(f"⚠️  WARNING: last_choice_continuation is empty! Using fallback.")
                last_choice_continuation = state["messages"][-1].content if state["messages"] else "Continue the story"
                print(f"  Fallback value: '{last_choice_continuation[:100]}'")


            prompt = create_continuation_prompt(
                world_template=world_template,
                beat_number=state["current_beat"],
                turns_in_beat=state.get("turns_in_beat", 0),
                last_choice_continuation=last_choice_continuation,
                generated_story_bible=state.get("generated_story_bible", {}),
                story_summary=state.get("story_summary", []),
                chapter_number=state.get("chapter_number", 1),
                total_chapters=state.get("total_chapters", 30)
            )

            # Include message history for context (but prompt already has summary)
            messages = prompt.format_messages(
                history=state["messages"][-6:] if len(state["messages"]) > 6 else state["messages"],
                last_choice=last_choice_continuation
            )

            print(f"✓ Generating continuation for beat {state['current_beat']}, turn {state.get('turns_in_beat', 0) + 1}")

        # Generate narrative
        llm_start = time.time()
        response = await llm.ainvoke(messages)
        llm_duration = time.time() - llm_start

        # Debug: print initial response statistics
        response_text = response.content
        word_count = len(response_text.split())
        char_count = len(response_text)
        print(f"\n📊 Initial LLM Response Statistics:")
        print(f"   Characters: {char_count:,}")
        print(f"   Words (approx): {word_count:,}")
        print(f"   Target: ~2500 words")
        print(f"   LLM call duration: {llm_duration:.2f}s")
        if word_count < 2000:
            print(f"   ⚠️  WARNING: Narrative is significantly shorter than target!")
        print(f"   First 200 chars: {response_text[:200]}")

        # Iterative length refinement
        # LLMs are bad at counting words, so we verify and refine if needed
        refined_text = await ensure_target_length(
            llm=llm,
            narrative_json=response.content,
            target_words=2500,
            tolerance=300,  # Accept 2200-2800 words (wider tolerance to reduce refinement calls)
            max_attempts=1  # Single refinement attempt to prevent timeouts
        )

        elapsed_time = time.time() - start_time
        print(f"\n⏱️  Total narrative generation time: {elapsed_time:.2f} seconds")

        return {"narrative_text": refined_text}

    except Exception as e:
        print(f"Error in generate_narrative_node: {e}")
        import traceback
        traceback.print_exc()

        return {
            "narrative_text": json.dumps({
                "narrative": "Something went wrong in the weaving of this tale. The station's systems flicker momentarily...",
                "choices": [
                    {"id": 1, "text": "She took a deep breath and tried again, steadying herself as...", "tone": "cautious"},
                    {"id": 2, "text": "She pushed forward anyway, determined not to let this stop her from...", "tone": "bold"},
                    {"id": 3, "text": "She paused, taking a moment to gather her thoughts before...", "tone": "thoughtful"}
                ],
                "image_prompt": "Space station interior, flickering lights, sci-fi atmosphere",
                "story_bible_update": {},
                "beat_progress": state.get("beat_progress_score", 0.0)
            }),
            "error": str(e)
        }


# ===== Node 2: Parse LLM Output =====

def parse_output_node(state: StoryState) -> dict[str, Any]:
    """
    Parse JSON output from LLM and update generated story bible.

    Args:
        state: Current story state with narrative_text (JSON string)

    Returns:
        Updated state with parsed narrative, choices, story_bible_update, beat_progress
    """
    try:
        # Parse JSON from LLM response
        narrative_text = state["narrative_text"]

        print(f"\n{'='*70}")
        print(f"DEBUG: PARSE_OUTPUT_NODE - Chapter {state.get('chapter_number', 1)}")
        print(f"{'='*70}")
        print(f"Raw LLM output length: {len(narrative_text)} chars")
        print(f"First 300 chars: {narrative_text[:300]}")
        print(f"Last 100 chars: {narrative_text[-100:]}")

        # Check if JSON looks complete
        if narrative_text.strip().startswith('{') and not narrative_text.strip().endswith('}'):
            print(f"⚠️  WARNING: JSON appears INCOMPLETE - starts with {{ but doesn't end with }}")
            print(f"   This suggests the LLM response was TRUNCATED!")

        # Handle markdown code blocks if present
        if "```json" in narrative_text:
            narrative_text = narrative_text.split("```json")[1].split("```")[0]
            print("⚠️  Removed ```json markdown wrapper")
        elif "```" in narrative_text:
            narrative_text = narrative_text.split("```")[1].split("```")[0]
            print("⚠️  Removed ``` markdown wrapper")

        # Clean up the text
        narrative_text = narrative_text.strip()

        # Handle "extra data" after JSON by extracting only the JSON object
        # Count braces to find the complete JSON object
        if narrative_text.startswith('{'):
            brace_count = 0
            json_end = 0
            for i, char in enumerate(narrative_text):
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        json_end = i + 1
                        break

            if json_end > 0 and json_end < len(narrative_text):
                # There's extra data after the JSON
                extra_data = narrative_text[json_end:].strip()
                if extra_data:
                    print(f"⚠️  Found extra data after JSON ({len(extra_data)} chars), truncating...")
                narrative_text = narrative_text[:json_end]

        # Try to parse JSON
        try:
            data = json.loads(narrative_text)
            print(f"✓ JSON parsed successfully on first attempt")
        except json.JSONDecodeError as e:
            # If JSON has control characters, try to fix them
            print(f"❌ Initial JSON parse failed: {e}")
            print(f"   Error position: line {e.lineno}, column {e.colno}")
            print(f"   Context around error: ...{narrative_text[max(0, e.pos-50):e.pos+50]}...")
            print(f"Attempting to fix control characters...")

            # Fix common control character issues in JSON strings
            # This handles unescaped newlines, tabs, etc. within string values
            import re

            def escape_in_strings(match):
                """Escape control characters within JSON string values."""
                s = match.group(1)
                # Escape backslashes first
                s = s.replace('\\', '\\\\')
                # Escape control characters
                s = s.replace('\n', '\\n')
                s = s.replace('\r', '\\r')
                s = s.replace('\t', '\\t')
                s = s.replace('\b', '\\b')
                s = s.replace('\f', '\\f')
                return '"' + s + '"'

            # Find all string values and escape control characters
            fixed_text = re.sub(r'"([^"\\]*(?:\\.[^"\\]*)*)"', escape_in_strings, narrative_text)

            try:
                data = json.loads(fixed_text)
                print(f"✓ Successfully parsed JSON after fixing control characters")
            except json.JSONDecodeError as e2:
                # Still failed, try regex extraction
                print(f"Still failed after fix: {e2}")
                print(f"Attempting targeted narrative extraction...")

                # Use a more precise regex that stops at the closing quote followed by comma
                # This matches: "narrative": "..." where ... can contain escaped quotes
                narrative_match = re.search(r'"narrative"\s*:\s*"((?:[^"\\]|\\.)*)"\s*,', narrative_text, re.DOTALL)

                if narrative_match:
                    narrative = narrative_match.group(1)
                    # Unescape the extracted text
                    narrative = narrative.replace('\\n', '\n').replace('\\r', '\r').replace('\\t', '\t').replace('\\"', '"').replace('\\\\', '\\')
                    print(f"✓ Extracted narrative from malformed JSON (length: {len(narrative)})")

                    # Return with default continuation-style choices
                    return {
                        "narrative_text": narrative,
                        "choices": [
                            {"id": 1, "text": "She took a moment to gather her thoughts before...", "tone": "cautious"},
                            {"id": 2, "text": "She pushed forward, determined to...", "tone": "bold"},
                            {"id": 3, "text": "She paused, considering her options as...", "tone": "thoughtful"}
                        ],
                        "image_prompt": None,
                        "messages": state["messages"]
                    }
                else:
                    # Really couldn't parse - re-raise
                    print(f"✗ Could not extract narrative from malformed JSON")
                    raise

        # Extract components
        narrative = data.get("narrative", "")
        choices = data.get("choices", [])
        image_prompt = data.get("image_prompt")
        story_bible_update = data.get("story_bible_update", {})
        beat_progress_score = data.get("beat_progress", state.get("beat_progress_score", 0.0))

        # Sanitize narrative: Remove beat markers (--- BEAT X: NAME ---)
        import re
        original_length = len(narrative)
        narrative = re.sub(r'^---\s*BEAT\s+\d+:.*?---\s*$', '', narrative, flags=re.MULTILINE)
        # Clean up any excessive blank lines left behind (max 2 consecutive newlines)
        narrative = re.sub(r'\n{3,}', '\n\n', narrative)
        # Trim leading/trailing whitespace
        narrative = narrative.strip()

        # Unescape any escaped newlines that might have been added during JSON error recovery
        # This prevents literal '\n' strings from appearing in the narrative
        if '\\n' in narrative:
            print(f"⚠️  Found escaped newlines in narrative, unescaping...")
            narrative = narrative.replace('\\n', '\n')
            narrative = narrative.replace('\\r', '\r')
            narrative = narrative.replace('\\t', '\t')

        sanitized_length = len(narrative)
        if sanitized_length < original_length:
            print(f"✓ Sanitized beat markers: {original_length} → {sanitized_length} chars ({original_length - sanitized_length} removed)")

        # Calculate narrative statistics
        narrative_words = len(narrative.split()) if narrative else 0
        narrative_chars = len(narrative) if narrative else 0

        print(f"\n📊 Extracted from JSON:")
        print(f"  Narrative length: {narrative_chars:,} chars, {narrative_words:,} words")
        if narrative_words < 2000:
            print(f"  ⚠️  WARNING: Narrative has only {narrative_words} words (target: ~2500)")
        print(f"  Choices count: {len(choices) if isinstance(choices, list) else 'NOT A LIST'}")
        print(f"  Choices type: {type(choices).__name__}")
        if isinstance(choices, list):
            for i, ch in enumerate(choices):
                print(f"  Choice {i}: {ch}")

        # Validate choices
        if not choices or not isinstance(choices, list):
            print(f"❌ FALLBACK TRIGGERED: choices is empty or not a list")
            choices = [
                {"id": 1, "text": "She continued forward, stepping into...", "tone": "neutral"},
                {"id": 2, "text": "She hesitated, then carefully approached...", "tone": "cautious"},
                {"id": 3, "text": "She smiled despite herself and...", "tone": "hopeful"}
            ]

        # Validate and fix individual choice structures
        validated_choices = []
        for i, choice in enumerate(choices):
            if not isinstance(choice, dict):
                # Skip invalid choice
                print(f"⚠️  Skipping non-dict choice at index {i}")
                continue

            # Create a clean copy to avoid mutation issues
            validated_choice = {}

            # Ensure choice has proper ID (should be 1, 2, or 3)
            # Always use index-based ID to guarantee correctness
            expected_id = i + 1
            original_id = choice.get("id")

            # Convert string IDs to integers if needed
            if isinstance(original_id, str) and original_id.isdigit():
                original_id = int(original_id)

            if original_id != expected_id:
                print(f"⚠️  Fixing choice {i}: id was {repr(original_id)} (type: {type(original_id).__name__}), setting to {expected_id}")

            validated_choice["id"] = expected_id

            # Ensure choice has text
            text = choice.get("text", "").strip()
            if not text:
                print(f"⚠️  Warning: choice {expected_id} has no text, using fallback")
                text = f"She paused, considering what to do next as..."
            validated_choice["text"] = text

            # Ensure choice has tone
            tone = choice.get("tone", "").strip()
            if not tone:
                tone = "neutral"
            validated_choice["tone"] = tone

            # Copy over consequence_hint if it exists
            if choice.get("consequence_hint"):
                validated_choice["consequence_hint"] = choice["consequence_hint"]

            validated_choices.append(validated_choice)
            print(f"✓ Validated choice {expected_id}: text='{text[:50]}...', tone={tone}")

        print(f"\n📋 Validation complete: {len(validated_choices)} choices validated")

        # If we don't have exactly 3 choices, use fallback
        if len(validated_choices) != 3:
            print(f"❌ FALLBACK TRIGGERED: Expected 3 choices, got {len(validated_choices)}, using generic fallback")
            choices = [
                {"id": 1, "text": "She continued forward, stepping into...", "tone": "neutral"},
                {"id": 2, "text": "She hesitated, then carefully approached...", "tone": "cautious"},
                {"id": 3, "text": "She smiled despite herself and...", "tone": "hopeful"}
            ]
        else:
            print(f"✓ Using validated choices (no fallback needed)")
            choices = validated_choices

        # Merge story_bible_update into generated_story_bible
        generated_story_bible = state.get("generated_story_bible", {}).copy()

        # Deep merge the update (supports nested dicts and lists)
        def deep_merge(base: dict, update: dict) -> dict:
            """Recursively merge update into base."""
            result = base.copy()
            for key, value in update.items():
                if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                    result[key] = deep_merge(result[key], value)
                elif key in result and isinstance(result[key], list) and isinstance(value, list):
                    # For lists, extend rather than replace
                    result[key] = result[key] + value
                else:
                    result[key] = value
            return result

        generated_story_bible = deep_merge(generated_story_bible, story_bible_update)

        # Get current chapter number for pruning and progress calculation
        chapter_number = state.get("chapter_number", 1) + 1

        # Prune story bible to prevent unbounded growth
        generated_story_bible = prune_story_bible(generated_story_bible, chapter_number)

        # Check if beat is complete based on progress score
        beat_progress = state.get("beat_progress", {}).copy()
        if beat_progress_score >= 1.0:
            beat_progress[state["current_beat"]] = True
            print(f"✓ Beat {state['current_beat']} completed (progress: {beat_progress_score})")

        # Increment turns in beat
        turns_in_beat = state.get("turns_in_beat", 0) + 1

        # Calculate story progress percentage
        total_chapters = state.get("total_chapters", 30)
        story_progress_pct = (chapter_number / total_chapters) * 100

        print(f"✓ Chapter {chapter_number - 1} complete. Starting Chapter {chapter_number}/{total_chapters} ({int(story_progress_pct)}%)")

        # Add AI message to history
        messages = state["messages"].copy()
        messages.append(AIMessage(content=narrative))

        # Final sanity check: ensure all choices have integer IDs
        final_choices = []
        for choice in choices:
            final_choice = choice.copy()
            if not isinstance(final_choice.get("id"), int):
                print(f"❌ CRITICAL: Choice has non-integer ID: {repr(final_choice.get('id'))} (type: {type(final_choice.get('id'))})")
                final_choice["id"] = int(final_choice.get("id")) if str(final_choice.get("id")).isdigit() else 1
            final_choices.append(final_choice)

        print(f"\n📋 FINAL CHOICES BEING RETURNED:")
        for i, choice in enumerate(final_choices):
            print(f"  Choice {i}: id={choice['id']} (type: {type(choice['id']).__name__}), text='{choice['text'][:40]}...'")
        print()

        return {
            "narrative_text": narrative,  # Now just the text, not JSON
            "choices": final_choices,
            "image_prompt": image_prompt,
            "generated_story_bible": generated_story_bible,
            "beat_progress_score": beat_progress_score,
            "beat_progress": beat_progress,
            "turns_in_beat": turns_in_beat,
            "chapter_number": chapter_number,
            "story_progress_pct": story_progress_pct,
            "messages": messages
        }

    except json.JSONDecodeError as e:
        print(f"JSON parsing error: {e}")
        print(f"Raw response: {state['narrative_text'][:500]}")

        # Fallback: treat as plain narrative
        return {
            "narrative_text": state["narrative_text"],
            "choices": [
                {"id": 1, "text": "She decided to continue, moving forward as...", "tone": "determined"},
                {"id": 2, "text": "She took a different approach, carefully...", "tone": "cautious"},
                {"id": 3, "text": "She paused to think it through before...", "tone": "thoughtful"}
            ],
            "image_prompt": None,
            "error": f"Failed to parse LLM output: {str(e)}"
        }

    except Exception as e:
        print(f"Error in parse_output_node: {e}")
        import traceback
        traceback.print_exc()
        return {"error": str(e)}


# ===== Node 4: Generate Story Summary =====

async def generate_summary_node(state: StoryState) -> dict[str, Any]:
    """
    Generate a 2-3 sentence summary of what just happened for story coherence.

    This summary helps maintain narrative consistency across multiple turns
    by providing concise context about recent events.

    Args:
        state: Current story state with new narrative

    Returns:
        Updated state with appended story_summary
    """
    try:
        # Get the current narrative that was just generated
        current_narrative = state["narrative_text"]

        # Get the player's last choice (if any)
        player_choice = ""
        if len(state["messages"]) >= 2:
            # Messages should have player's choice as the last human message
            player_choice = state["messages"][-2].content if state["messages"][-2].type == "human" else ""

        # Build summary prompt
        summary_prompt = f"""Based on this story segment, create a concise 2-3 sentence summary of what just happened.
Focus on:
- Key actions taken
- Important discoveries or revelations
- Character decisions and their immediate consequences
- Changes in the situation or environment

Story segment:
{current_narrative}

Player's choice: {player_choice if player_choice else "Story opening"}

Respond with ONLY the summary, no additional text or explanation."""

        # Use Claude to generate summary
        llm = ChatAnthropic(
            model=config.MODEL_NAME,
            temperature=0.3,  # Lower temperature for more focused summaries
            max_tokens=150,   # Keep summaries concise
            anthropic_api_key=config.ANTHROPIC_API_KEY,
            timeout=30.0,  # 30 second timeout for quick summary generation
        )

        response = await llm.ainvoke([HumanMessage(content=summary_prompt)])
        summary = response.content.strip()

        # Add to story_summary list
        story_summary = state.get("story_summary", []).copy()
        story_summary.append(summary)

        # Keep only last 10 summaries to avoid token bloat
        if len(story_summary) > 10:
            story_summary = story_summary[-10:]

        print(f"✓ Generated story summary: {summary[:100]}...")

        return {"story_summary": story_summary}

    except Exception as e:
        print(f"Error in generate_summary_node: {e}")
        # Don't fail the whole flow if summary fails
        return {"story_summary": state.get("story_summary", [])}


# ===== Node 5: Generate Image (Optional) =====

async def generate_image_node(state: StoryState) -> dict[str, Any]:
    """
    Generate scene image using Replicate API with retry logic.
    Downloads and stores images locally to avoid expiration.

    Args:
        state: Current story state with image_prompt

    Returns:
        Updated state with image_url (local path)
    """
    # Check state-level override first, then config
    should_generate = state.get("generate_image")
    if should_generate is None:
        should_generate = config.ENABLE_MEDIA_GENERATION and config.can_generate_images
    elif should_generate:
        # User wants image, but check if we CAN generate
        should_generate = config.can_generate_images

    if not should_generate:
        print("⏭️  Skipping image generation (disabled)")
        return {"image_url": None}

    if not state.get("image_prompt"):
        return {"image_url": None}

    # Enhanced image prompt for consistency
    base_prompt = state["image_prompt"]
    enhanced_prompt = f"{base_prompt}, cinematic lighting, high quality, detailed, fantasy art style"

    max_retries = 3
    retry_delay = 2  # seconds

    for attempt in range(max_retries):
        try:
            import replicate
            import httpx
            import os
            from datetime import datetime

            if not config.REPLICATE_API_TOKEN:
                print("⚠️  REPLICATE_API_TOKEN not set, skipping image generation")
                return {"image_url": None}

            # Create client with API token
            client = replicate.Client(api_token=config.REPLICATE_API_TOKEN)

            # Use a valid Replicate model (try specific version if latest fails)
            model = config.IMAGE_MODEL
            if model == "stability-ai/sdxl:latest":
                # Use a specific version for better reliability
                model = "stability-ai/sdxl:39ed52f2a78e934b3ba6e2a89f5b1c712de7dfea535525255b1aa35c5555e08b"

            print(f"Generating image with model: {model}")

            # Determine parameters based on model
            input_params = {
                "prompt": enhanced_prompt,
                "width": config.IMAGE_WIDTH,
                "height": config.IMAGE_HEIGHT,
                "num_outputs": 1,
            }

            # Flux Schnell has different parameters than SDXL
            if "flux-schnell" in model.lower():
                # Flux Schnell parameters (max 4 steps)
                input_params["num_inference_steps"] = 4
            else:
                # SDXL or other models
                input_params["negative_prompt"] = "text, watermark, low quality, blurry, distorted, ugly"
                input_params["guidance_scale"] = 7.5
                input_params["num_inference_steps"] = 25

            # Run image generation
            output = await client.async_run(model, input=input_params)

            replicate_output = output[0] if output else None
            if not replicate_output:
                raise Exception("No image URL returned from Replicate")

            # Convert FileOutput to string URL
            replicate_url = str(replicate_output)
            print(f"✓ Image generated by Replicate (attempt {attempt + 1})")

            # Download and save image locally
            # Create images directory if it doesn't exist
            os.makedirs("./generated_images", exist_ok=True)

            # Generate filename with proper naming convention
            # Format: {world_id}_{session_id}_beat{beat_number}_{timestamp}.png
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            session_id = state.get("session_id", "unknown")
            filename = f"{state['world_id']}_{session_id}_beat{state['current_beat']}_{timestamp}.png"
            filepath = f"./generated_images/{filename}"

            # Download image from Replicate
            print(f"Downloading image from Replicate: {replicate_url}")
            async with httpx.AsyncClient() as http_client:
                response = await http_client.get(replicate_url)
                response.raise_for_status()

                # Save to local file
                with open(filepath, "wb") as f:
                    f.write(response.content)

            # Upload to storage backend (Supabase in prod, local in dev)
            from backend.storage import upload_image
            public_url = upload_image(filepath, filename)

            print(f"✓ Image saved locally: {filepath}")
            print(f"  Public URL: {public_url}")

            return {"image_url": public_url}

        except Exception as e:
            error_msg = str(e)
            print(f"⚠️  Image generation failed (attempt {attempt + 1}/{max_retries}): {error_msg}")
            
            # Check for authentication errors
            if "401" in error_msg or "unauthorized" in error_msg.lower() or "authentication" in error_msg.lower():
                print("⚠️  Replicate API authentication failed. Check REPLICATE_API_TOKEN.")
                return {"image_url": None}  # Don't retry auth errors
            
            # Check for invalid model errors
            if "404" in error_msg or "not found" in error_msg.lower():
                print(f"⚠️  Invalid Replicate model. Check IMAGE_MODEL setting.")
                return {"image_url": None}  # Don't retry invalid model errors
            
            if attempt < max_retries - 1:
                print(f"Retrying in {retry_delay} seconds...")
                await asyncio.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
            else:
                print(f"❌ Image generation failed after {max_retries} attempts, continuing without image")
                return {"image_url": None}  # Don't include error in state, just skip image

    return {"image_url": None, "error": "Image generation failed"}


# ===== Node 5: Generate Audio (Optional) =====

async def generate_audio_node(state: StoryState) -> dict[str, Any]:
    """
    Generate voice narration using ElevenLabs API with retry logic.

    Args:
        state: Current story state with narrative_text

    Returns:
        Updated state with audio_url
    """
    # Check state-level override first, then config
    should_generate = state.get("generate_audio")
    if should_generate is None:
        should_generate = config.ENABLE_MEDIA_GENERATION and config.can_generate_audio
    elif should_generate:
        # User wants audio, but check if we CAN generate
        should_generate = config.can_generate_audio

    if not should_generate:
        print("⏭️  Skipping audio generation (disabled)")
        return {"audio_url": None}

    if not state.get("narrative_text"):
        return {"audio_url": None}

    # Clean and prepare text for narration
    narrative_text = state["narrative_text"].strip()

    # ElevenLabs Flash v2.5 supports up to 40,000 characters
    # Our 2500-word chapters are ~15,000 chars, so set a safe limit of 20,000
    MAX_AUDIO_CHARS = 20000

    if len(narrative_text) > MAX_AUDIO_CHARS:
        print(f"⚠️  Narrative is {len(narrative_text)} chars, truncating to {MAX_AUDIO_CHARS} for audio")
        # Try to truncate at a sentence boundary
        truncated = narrative_text[:MAX_AUDIO_CHARS]
        last_period = truncated.rfind('. ')
        if last_period > MAX_AUDIO_CHARS - 500:  # If period is near the end
            narrative_text = truncated[:last_period + 1]
        else:
            narrative_text = truncated + "..."
        print(f"  Truncated to {len(narrative_text)} chars for audio")
    else:
        print(f"✓ Narrative is {len(narrative_text)} chars, within Flash v2.5 limit (max 40K)")
    
    max_retries = 3
    retry_delay = 2  # seconds
    
    for attempt in range(max_retries):
        try:
            from elevenlabs.client import ElevenLabs
            import os
            from datetime import datetime

            if not config.ELEVENLABS_API_KEY:
                print("⚠️  ELEVENLABS_API_KEY not set, skipping audio generation")
                return {"audio_url": None}

            # Create ElevenLabs client
            client = ElevenLabs(api_key=config.ELEVENLABS_API_KEY)

            # Get voice ID from state or config
            voice_id = state.get("voice_id") or config.ELEVENLABS_VOICE_ID

            # Generate audio using Flash v2.5 (supports up to 40,000 chars, faster than v1)
            # This allows us to narrate full 2500-word chapters (~15,000 chars) without truncation
            audio_generator = client.text_to_speech.convert(
                voice_id=voice_id,  # Use state override or config default
                text=narrative_text,
                model_id="eleven_flash_v2_5",  # Flash v2.5 supports 40K chars vs 10K for monolingual_v1
                voice_settings={
                    "stability": 0.5,
                    "similarity_boost": 0.75
                }
            )

            # Create audio directory if it doesn't exist
            os.makedirs("./generated_audio", exist_ok=True)

            # Generate filename with proper naming convention
            # Format: {world_id}_{session_id}_beat{beat_number}_{timestamp}.mp3
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            session_id = state.get("session_id", "unknown")
            filename = f"{state['world_id']}_{session_id}_beat{state['current_beat']}_{timestamp}.mp3"
            filepath = f"./generated_audio/{filename}"

            # Save audio bytes to file
            with open(filepath, "wb") as f:
                for chunk in audio_generator:
                    f.write(chunk)

            # Upload to storage backend (Supabase in prod, local in dev)
            from backend.storage import upload_audio
            public_url = upload_audio(filepath, filename)

            print(f"✓ Audio generated successfully (attempt {attempt + 1})")
            print(f"  Saved to: {filepath}")
            print(f"  Public URL: {public_url}")
            return {"audio_url": public_url}

        except Exception as e:
            error_msg = str(e)
            print(f"⚠️  Audio generation failed (attempt {attempt + 1}/{max_retries}): {error_msg}")

            # Check for authentication errors
            if "401" in error_msg or "unauthorized" in error_msg.lower() or "authentication" in error_msg.lower() or "invalid api key" in error_msg.lower():
                print("⚠️  ElevenLabs API authentication failed. Check ELEVENLABS_API_KEY.")
                return {"audio_url": None}  # Don't retry auth errors

            # Check for character limit errors (shouldn't happen now with pre-truncation)
            if "max_character_limit_exceeded" in error_msg.lower() or "character limit" in error_msg.lower():
                print("⚠️  ElevenLabs character limit exceeded (shouldn't happen - check truncation logic)")
                return {"audio_url": None}

            # Check for quota/rate limit errors
            if "429" in error_msg or "quota" in error_msg.lower() or "rate limit" in error_msg.lower():
                print("⚠️  ElevenLabs API quota/rate limit exceeded.")
                return {"audio_url": None}  # Don't retry quota errors
            
            if attempt < max_retries - 1:
                print(f"Retrying in {retry_delay} seconds...")
                await asyncio.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
            else:
                print(f"❌ Audio generation failed after {max_retries} attempts, continuing without audio")
                return {"audio_url": None}  # Don't include error in state, just skip audio
    
    return {"audio_url": None}  # Fallback return


# ===== Node 6: Check Beat Completion =====

def check_beat_complete_node(state: StoryState) -> dict[str, Any]:
    """
    Check if current beat is complete and advance if necessary.

    Args:
        state: Current story state

    Returns:
        Updated state with potentially incremented current_beat and reset turns_in_beat
    """
    beat_progress = state.get("beat_progress", {})
    current_beat = state["current_beat"]

    # Check if current beat is marked complete
    if beat_progress.get(current_beat, False):
        # Advance to next beat
        next_beat = current_beat + 1

        print(f"✓ Beat {current_beat} completed! Advancing to Beat {next_beat}")

        return {
            "current_beat": next_beat,
            "turns_in_beat": 0,  # Reset turns counter for new beat
            "beat_progress_score": 0.0  # Reset progress score for new beat
        }

    # Beat not complete, continue current beat
    return {}


# ===== Node 7: Deduct Credits =====

def deduct_credits_node(state: StoryState) -> dict[str, Any]:
    """
    Deduct credits for this story segment (if credit system enabled).

    Args:
        state: Current story state

    Returns:
        Updated state with decremented credits_remaining
    """
    if not config.ENABLE_CREDIT_SYSTEM:
        return {}

    credits = state.get("credits_remaining", 0)

    if credits <= 0:
        return {
            "error": "Insufficient credits",
            "credits_remaining": 0
        }

    new_credits = credits - config.CREDITS_PER_CHOICE

    return {"credits_remaining": max(0, new_credits)}


# ===== Helper Node: Add User Message =====

def add_user_message_node(state: StoryState, user_input: str) -> dict[str, Any]:
    """
    Add user's choice to message history.

    Args:
        state: Current story state
        user_input: User's input text

    Returns:
        Updated state with new message
    """
    messages = state.get("messages", []).copy()
    messages.append(HumanMessage(content=user_input))

    return {"messages": messages}


# ===== Node 8: Story Structure Beat Agent (SSBA) =====

async def story_structure_beat_node(state: StoryState) -> dict[str, Any]:
    """
    Generate full story structure for 30-chapter arc (Chapter 1 only).

    Uses "Save the Cat" beat structure to create story-level planning.

    Args:
        state: Current story state

    Returns:
        Updated state with story_structure populated
    """
    import time
    import json
    from langchain_core.messages import HumanMessage
    from langchain_anthropic import ChatAnthropic

    start_time = time.time()

    try:
        print(f"\n{'='*70}")
        print(f"SSBA: CREATING STORY STRUCTURE")
        print(f"{'='*70}")

        # Initialize LLM
        llm = ChatAnthropic(
            model=config.MODEL_NAME,
            temperature=0.7,  # Slightly creative for planning
            max_tokens=8000,  # Need space for full structure
            anthropic_api_key=config.ANTHROPIC_API_KEY,
            timeout=30.0,
        )

        # Load world template
        from backend.storyteller.prompts_v2 import load_world_template, create_story_structure_prompt

        world_template = load_world_template(state["world_id"])
        total_chapters = state.get("total_chapters", 30)

        # Create prompt
        prompt = create_story_structure_prompt(world_template, total_chapters)

        # Generate story structure
        llm_start = time.time()
        response = await llm.ainvoke([HumanMessage(content=prompt)])
        llm_duration = time.time() - llm_start

        print(f"✓ SSBA response received ({llm_duration:.2f}s)")

        # Parse JSON response
        response_text = response.content.strip()

        # Clean markdown if present
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0].strip()

        try:
            story_structure = json.loads(response_text)
            print(f"✓ Story structure parsed successfully")
            print(f"  Acts defined: {len(story_structure.get('story_structure', {}))}")
            print(f"  Character arcs: {len(story_structure.get('key_arcs', {}))}")

            elapsed = time.time() - start_time
            print(f"⏱️  SSBA total time: {elapsed:.2f}s")

            return {"story_structure": story_structure}

        except json.JSONDecodeError as e:
            print(f"❌ Failed to parse story structure JSON: {e}")
            print(f"Response preview: {response_text[:500]}")
            # Return empty structure rather than failing
            return {"story_structure": {"error": "Failed to parse structure"}}

    except Exception as e:
        print(f"Error in story_structure_beat_node: {e}")
        import traceback
        traceback.print_exc()
        return {"story_structure": {"error": str(e)}}


async def story_beat_checkin_node(state: StoryState) -> dict[str, Any]:
    """
    SSBA check-in for chapters 2-30 (lightweight guidance).

    Provides story position context based on established structure.

    Args:
        state: Current story state with story_structure

    Returns:
        Updated state with current_story_beat and guidance
    """
    import time
    import json
    from langchain_core.messages import HumanMessage
    from langchain_anthropic import ChatAnthropic

    start_time = time.time()

    try:
        chapter_number = state.get("chapter_number", 1)

        print(f"\n{'='*70}")
        print(f"SSBA: CHECK-IN FOR CHAPTER {chapter_number}")
        print(f"{'='*70}")

        # Initialize LLM
        llm = ChatAnthropic(
            model=config.MODEL_NAME,
            temperature=0.3,  # Lower temperature for consistent guidance
            max_tokens=1000,  # Lightweight response
            anthropic_api_key=config.ANTHROPIC_API_KEY,
            timeout=15.0,
        )

        # Get story context
        from backend.storyteller.prompts_v2 import create_story_beat_checkin_prompt

        story_structure = state.get("story_structure", {})
        total_chapters = state.get("total_chapters", 30)
        story_bible = state.get("generated_story_bible", {})
        summaries = state.get("story_summary", [])
        inconsistency_flags = state.get("inconsistency_flags", [])

        # Create prompt
        prompt = create_story_beat_checkin_prompt(
            story_structure=story_structure,
            chapter_number=chapter_number,
            total_chapters=total_chapters,
            story_bible=story_bible,
            summaries=summaries,
            inconsistency_flags=inconsistency_flags
        )

        # Get guidance
        llm_start = time.time()
        response = await llm.ainvoke([HumanMessage(content=prompt)])
        llm_duration = time.time() - llm_start

        print(f"✓ SSBA check-in received ({llm_duration:.2f}s)")

        # Parse JSON response
        response_text = response.content.strip()

        # Clean markdown if present
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0].strip()

        try:
            guidance = json.loads(response_text)
            print(f"✓ Guidance parsed successfully")
            print(f"  Current beat: {guidance.get('current_story_beat', 'unknown')}")
            print(f"  Act: {guidance.get('act', '?')}")
            print(f"  Progress: {guidance.get('progress_percentage', 0):.1f}%")
            print(f"  Guidance: {guidance.get('guidance_for_cba', 'N/A')[:80]}...")

            elapsed = time.time() - start_time
            print(f"⏱️  SSBA check-in time: {elapsed:.2f}s")

            return {
                "current_story_beat": guidance.get("current_story_beat"),
                "_ssba_guidance": guidance  # Temporary field for CBA to use
            }

        except json.JSONDecodeError as e:
            print(f"❌ Failed to parse check-in JSON: {e}")
            # Return minimal guidance
            return {
                "current_story_beat": "unknown",
                "_ssba_guidance": {"error": "Failed to parse"}
            }

    except Exception as e:
        print(f"Error in story_beat_checkin_node: {e}")
        import traceback
        traceback.print_exc()
        return {"current_story_beat": "unknown"}


# ===== PHASE 3: CBA (Chapter Beat Agent) =====

async def chapter_beat_agent_node(state: StoryState) -> dict[str, Any]:
    """
    CBA generates 6-beat chapter structure based on SSBA guidance.

    This creates a detailed internal structure for the chapter with 6 beats,
    each targeting ~400-450 words for a total of ~2,400-2,700 words.

    Args:
        state: Current story state with story_structure, SSBA guidance

    Returns:
        Updated state with chapter_beat_plan
    """
    import time
    import json
    from langchain_core.messages import HumanMessage
    from langchain_anthropic import ChatAnthropic

    start_time = time.time()

    try:
        chapter_number = state.get("chapter_number", 1)

        print(f"\n{'='*70}")
        print(f"CBA: PLANNING 6-BEAT STRUCTURE FOR CHAPTER {chapter_number}")
        print(f"{'='*70}")

        # Initialize LLM
        llm = ChatAnthropic(
            model=config.MODEL_NAME,
            temperature=0.7,  # Creative planning
            max_tokens=2000,  # Detailed beat plan
            anthropic_api_key=config.ANTHROPIC_API_KEY,
            timeout=30.0,
        )

        # Get context
        from backend.storyteller.prompts_v2 import load_world_template, create_chapter_beat_prompt

        world_id = state.get("world_id", "tfogwf")
        world_template = load_world_template(world_id)
        total_chapters = state.get("total_chapters", 30)
        story_structure = state.get("story_structure", {})
        ssba_guidance = state.get("_ssba_guidance", {})
        story_bible = state.get("generated_story_bible", {})
        last_choice = state.get("last_choice", None)
        summaries = state.get("story_summary", [])

        # Create prompt
        prompt = create_chapter_beat_prompt(
            world_template=world_template,
            chapter_number=chapter_number,
            total_chapters=total_chapters,
            story_structure=story_structure,
            ssba_guidance=ssba_guidance,
            story_bible=story_bible,
            last_choice=last_choice,
            summaries=summaries
        )

        # Get chapter beat plan
        llm_start = time.time()
        response = await llm.ainvoke([HumanMessage(content=prompt)])
        llm_duration = time.time() - llm_start

        print(f"✓ CBA response received ({llm_duration:.2f}s)")

        # Parse JSON response
        response_text = response.content.strip()

        # Clean markdown if present
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0].strip()

        try:
            chapter_beat_plan = json.loads(response_text)
            print(f"✓ Chapter beat plan parsed successfully")
            print(f"  Chapter goal: {chapter_beat_plan.get('chapter_goal', 'N/A')[:60]}...")
            print(f"  Number of beats: {len(chapter_beat_plan.get('chapter_beats', []))}")

            # Show beat summary
            beats = chapter_beat_plan.get('chapter_beats', [])
            for beat in beats:
                beat_name = beat.get('beat_name', 'unknown')
                word_target = beat.get('word_target', 0)
                print(f"    - Beat {beat.get('beat_number', '?')}: {beat_name} (~{word_target} words)")

            elapsed = time.time() - start_time
            print(f"⏱️  CBA planning time: {elapsed:.2f}s")

            return {
                "chapter_beat_plan": chapter_beat_plan
            }

        except json.JSONDecodeError as e:
            print(f"❌ Failed to parse chapter beat plan JSON: {e}")
            print(f"Response preview: {response_text[:200]}...")

            # Return minimal fallback plan
            fallback_plan = {
                "chapter_beats": [
                    {"beat_number": 1, "beat_name": "opening_hook", "word_target": 450, "description": "Opening"},
                    {"beat_number": 2, "beat_name": "rising_action", "word_target": 450, "description": "Development"},
                    {"beat_number": 3, "beat_name": "midpoint_twist", "word_target": 450, "description": "Twist"},
                    {"beat_number": 4, "beat_name": "complications", "word_target": 450, "description": "Complications"},
                    {"beat_number": 5, "beat_name": "tension_peak", "word_target": 450, "description": "Peak tension"},
                    {"beat_number": 6, "beat_name": "resolution", "word_target": 450, "description": "Resolution"}
                ],
                "chapter_goal": "Advance story",
                "chapter_tension": "Unknown",
                "chapter_question": "What happens next?",
                "setup_for_next": "Continue story",
                "choice_setup": {"situation": "Decision point", "stakes": "Unknown", "suggested_choice_types": []}
            }
            return {
                "chapter_beat_plan": fallback_plan
            }

    except Exception as e:
        print(f"Error in chapter_beat_agent_node: {e}")
        import traceback
        traceback.print_exc()
        # Return minimal fallback
        fallback_plan = {
            "chapter_beats": [
                {"beat_number": i, "beat_name": f"beat_{i}", "word_target": 450, "description": f"Beat {i}"}
                for i in range(1, 7)
            ],
            "chapter_goal": "Error fallback",
            "chapter_tension": "N/A",
            "chapter_question": "N/A",
            "setup_for_next": "N/A",
            "choice_setup": {"situation": "N/A", "stakes": "N/A", "suggested_choice_types": []}
        }
        return {"chapter_beat_plan": fallback_plan}


# ===== PHASE 4: CEA (Context Editor Agent) =====

async def context_editor_agent_node(state: StoryState) -> dict[str, Any]:
    """
    CEA checks consistency using RAG and provides guidance for Prose Agent.

    This node:
    1. Gets consistency report from RAG
    2. Analyzes potential contradictions
    3. Provides guidance to PA
    4. Flags major contradictions for SSBA

    Args:
        state: Current story state

    Returns:
        Updated state with consistency_report and inconsistency_flags
    """
    import time
    import json
    from langchain_core.messages import HumanMessage
    from langchain_anthropic import ChatAnthropic

    start_time = time.time()

    try:
        chapter_number = state.get("chapter_number", 1)
        session_id = state.get("session_id", "")

        print(f"\n{'='*70}")
        print(f"CEA: CONSISTENCY CHECK FOR CHAPTER {chapter_number}")
        print(f"{'='*70}")

        # Get RAG consistency report
        from backend.rag.consistency_checker import ConsistencyChecker

        checker = ConsistencyChecker(session_id)
        chapter_beat_plan = state.get("chapter_beat_plan", {})
        story_bible = state.get("generated_story_bible", {})

        rag_report = checker.get_consistency_report(
            chapter_beat_plan=chapter_beat_plan,
            story_bible=story_bible,
            max_queries=5
        )

        print(f"✓ RAG consistency report generated")
        print(f"  Checks performed: {rag_report.get('total_checks', 0)}")
        print(f"  Relevant history items: {len(rag_report.get('relevant_history', []))}")
        print(f"  Overall risk: {rag_report.get('overall_risk', 'none')}")

        # Initialize LLM for CEA analysis
        llm = ChatAnthropic(
            model=config.MODEL_NAME,
            temperature=0.3,  # Analytical, consistent
            max_tokens=2000,
            anthropic_api_key=config.ANTHROPIC_API_KEY,
            timeout=30.0,
        )

        # Create consistency check prompt
        from backend.storyteller.prompts_v2 import create_consistency_check_prompt

        last_choice = state.get("last_choice", None)

        prompt = create_consistency_check_prompt(
            chapter_number=chapter_number,
            chapter_beat_plan=chapter_beat_plan,
            story_bible=story_bible,
            consistency_report=rag_report,
            last_choice=last_choice
        )

        # Get CEA analysis
        llm_start = time.time()
        response = await llm.ainvoke([HumanMessage(content=prompt)])
        llm_duration = time.time() - llm_start

        print(f"✓ CEA analysis received ({llm_duration:.2f}s)")

        # Parse JSON response
        response_text = response.content.strip()

        # Clean markdown if present
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0].strip()

        try:
            analysis = json.loads(response_text)

            consistency_status = analysis.get("consistency_status", "clear")
            minor_issues = analysis.get("minor_issues", [])
            major_contradictions = analysis.get("major_contradictions", [])
            inconsistency_flags = analysis.get("inconsistency_flags", [])

            print(f"✓ Consistency analysis parsed")
            print(f"  Status: {consistency_status}")
            print(f"  Minor issues: {len(minor_issues)}")
            print(f"  Major contradictions: {len(major_contradictions)}")
            print(f"  Flags for SSBA: {len(inconsistency_flags)}")

            # Store guidance for PA to use
            guidance_for_pa = analysis.get("guidance_for_prose_agent", {})

            elapsed = time.time() - start_time
            print(f"⏱️  CEA consistency check time: {elapsed:.2f}s")

            # Prepare consistency report for state
            consistency_report = {
                "status": consistency_status,
                "minor_issues": minor_issues,
                "major_contradictions": major_contradictions,
                "guidance_for_pa": guidance_for_pa,
                "rag_report": rag_report
            }

            # Add new inconsistency flags to existing ones
            existing_flags = state.get("inconsistency_flags", [])
            updated_flags = existing_flags + inconsistency_flags

            return {
                "consistency_report": consistency_report,
                "inconsistency_flags": updated_flags,
                "_cea_guidance": guidance_for_pa  # Temporary field for PA
            }

        except json.JSONDecodeError as e:
            print(f"❌ Failed to parse CEA analysis JSON: {e}")
            print(f"Response preview: {response_text[:200]}...")

            # Return minimal report
            return {
                "consistency_report": {
                    "status": "error",
                    "minor_issues": [],
                    "major_contradictions": [],
                    "guidance_for_pa": {"general_guidance": "Generate chapter prose"},
                    "rag_report": rag_report
                },
                "inconsistency_flags": state.get("inconsistency_flags", [])
            }

    except Exception as e:
        print(f"Error in context_editor_agent_node: {e}")
        import traceback
        traceback.print_exc()
        return {
            "consistency_report": {
                "status": "error",
                "minor_issues": [],
                "major_contradictions": [],
                "guidance_for_pa": {"general_guidance": "Generate chapter prose"},
                "rag_report": {}
            }
        }


async def generate_chapter1_choices_node(state: StoryState) -> dict[str, Any]:
    """
    CEA generates player choices for Chapter 1 (after narrative is generated).

    Args:
        state: Current story state with generated narrative

    Returns:
        Updated state with generated_choices
    """
    import time
    import json
    from langchain_core.messages import HumanMessage
    from langchain_anthropic import ChatAnthropic

    start_time = time.time()

    try:
        print(f"\n{'='*70}")
        print(f"CEA: GENERATING CHOICES FOR CHAPTER 1")
        print(f"{'='*70}")

        # Initialize LLM
        llm = ChatAnthropic(
            model=config.MODEL_NAME,
            temperature=0.8,  # Creative choice generation
            max_tokens=1500,
            anthropic_api_key=config.ANTHROPIC_API_KEY,
            timeout=25.0,
        )

        # Get context
        from backend.storyteller.prompts_v2 import load_world_template, create_choice_generation_prompt

        world_id = state.get("world_id", "tfogwf")
        world_template = load_world_template(world_id)
        chapter_number = state.get("chapter_number", 1)
        narrative = state.get("generated_narrative", "")
        story_bible = state.get("generated_story_bible", {})
        chapter_beat_plan = state.get("chapter_beat_plan", {})
        ssba_guidance = state.get("_ssba_guidance", {})

        # Create prompt
        prompt = create_choice_generation_prompt(
            world_template=world_template,
            chapter_number=chapter_number,
            narrative=narrative,
            story_bible=story_bible,
            chapter_beat_plan=chapter_beat_plan,
            ssba_guidance=ssba_guidance
        )

        # Generate choices
        llm_start = time.time()
        response = await llm.ainvoke([HumanMessage(content=prompt)])
        llm_duration = time.time() - llm_start

        print(f"✓ CEA choice generation received ({llm_duration:.2f}s)")

        # Parse JSON response
        response_text = response.content.strip()

        # Clean markdown if present
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0].strip()

        try:
            choices_data = json.loads(response_text)
            choices = choices_data.get("choices", [])

            print(f"✓ Choices generated successfully")
            for i, choice in enumerate(choices, 1):
                choice_type = choice.get("choice_type", "unknown")
                print(f"  {i}. [{choice_type}] {choice.get('text', 'N/A')[:60]}...")

            elapsed = time.time() - start_time
            print(f"⏱️  CEA choice generation time: {elapsed:.2f}s")

            return {
                "generated_choices": choices
            }

        except json.JSONDecodeError as e:
            print(f"❌ Failed to parse choices JSON: {e}")
            print(f"Response preview: {response_text[:200]}...")

            # Return fallback choices
            fallback_choices = [
                {
                    "id": f"ch{chapter_number}_choice_1",
                    "text": "Continue with the current approach.",
                    "choice_type": "action"
                },
                {
                    "id": f"ch{chapter_number}_choice_2",
                    "text": "Take a moment to reconsider the situation.",
                    "choice_type": "emotional"
                },
                {
                    "id": f"ch{chapter_number}_choice_3",
                    "text": "Seek advice or information before proceeding.",
                    "choice_type": "investigation"
                }
            ]
            return {"generated_choices": fallback_choices}

    except Exception as e:
        print(f"Error in generate_chapter1_choices_node: {e}")
        import traceback
        traceback.print_exc()

        # Return minimal fallback
        fallback_choices = [
            {"id": "ch1_choice_1", "text": "Continue forward.", "choice_type": "action"},
            {"id": "ch1_choice_2", "text": "Pause and reflect.", "choice_type": "emotional"},
            {"id": "ch1_choice_3", "text": "Investigate further.", "choice_type": "investigation"}
        ]
        return {"generated_choices": fallback_choices}


async def generate_choices_node(state: StoryState) -> dict[str, Any]:
    """
    CEA generates player choices for Chapters 2-30 (after narrative is generated).

    This is the same as generate_chapter1_choices_node but may have different
    context/considerations for later chapters.

    Args:
        state: Current story state with generated narrative

    Returns:
        Updated state with generated_choices
    """
    # For now, reuse the same logic as Chapter 1
    # In the future, this could be different based on story progression
    return await generate_chapter1_choices_node(state)


# ===== Node 10: Extract Entities from Narrative =====

async def extract_entities_node(state: StoryState) -> dict[str, Any]:
    """
    Extract entities from the narrative for RAG indexing.

    This node splits the narrative into paragraphs and extracts entities
    for metadata tagging.

    Args:
        state: Current story state with narrative_text

    Returns:
        Updated state with extracted entities (stored temporarily)
    """
    try:
        from backend.rag.entity_extractor import EntityExtractor
        from datetime import datetime

        narrative = state.get("narrative_text", "")

        if not narrative:
            print("⚠️  No narrative to extract entities from")
            return {}

        # Split narrative into paragraphs
        paragraphs = EntityExtractor.split_into_paragraphs(narrative)
        print(f"✓ Split narrative into {len(paragraphs)} paragraphs")

        # For now, use simple entity extraction (pattern matching)
        # TODO: In production, use LLM-based extraction for better accuracy
        entities = EntityExtractor.extract_entities_simple(narrative)
        print(f"✓ Extracted entities: {len(entities.get('characters', []))} characters")

        # Store paragraphs and entities temporarily for indexing node
        # (We don't want to bloat the state, so we'll index and discard)
        return {
            "_temp_paragraphs": paragraphs,
            "_temp_entities": entities
        }

    except Exception as e:
        print(f"Error in extract_entities_node: {e}")
        import traceback
        traceback.print_exc()
        return {}


# ===== Node 9: Index to RAG Vector Store =====

async def index_to_rag_node(state: StoryState) -> dict[str, Any]:
    """
    Index extracted paragraphs and entities into RAG vector store.

    Args:
        state: Current story state with temporary paragraph/entity data

    Returns:
        Updated state with rag_chunks_indexed and last_rag_update
    """
    try:
        from backend.rag.vector_store import VectorStore
        from backend.rag.entity_extractor import EntityExtractor
        from datetime import datetime

        # Get temporary data from extract_entities_node
        paragraphs = state.get("_temp_paragraphs", [])
        entities = state.get("_temp_entities", {})

        if not paragraphs:
            print("⚠️  No paragraphs to index")
            return {}

        # Initialize vector store
        vector_store = VectorStore()
        session_id = state.get("user_id", "unknown")
        chapter_number = state.get("chapter_number", 1)

        # Get or create collection for this session
        vector_store.get_or_create_collection(session_id)

        # Create metadata for each paragraph
        metadata_list = []
        for i, paragraph in enumerate(paragraphs):
            metadata = EntityExtractor.create_paragraph_metadata(
                paragraph=paragraph,
                paragraph_number=i,
                chapter_number=chapter_number,
                entities=entities
            )
            metadata_list.append(metadata)

        # Add paragraphs to vector store
        chunks_added = vector_store.add_paragraph_chunks(
            paragraphs=paragraphs,
            chapter_number=chapter_number,
            metadata_list=metadata_list
        )

        # Update state with RAG metadata
        total_chunks = vector_store.get_collection_count()

        print(f"✓ RAG indexing complete: {chunks_added} new chunks, {total_chunks} total")

        return {
            "rag_chunks_indexed": total_chunks,
            "last_rag_update": datetime.utcnow().isoformat()
        }

    except Exception as e:
        print(f"Error in index_to_rag_node: {e}")
        import traceback
        traceback.print_exc()
        return {}


# ===== Conditional Edge Functions =====

def should_generate_media(state: StoryState) -> str:
    """
    Determine if media generation should occur.

    Args:
        state: Current story state

    Returns:
        "generate_media" or "skip_media"
    """
    # Check if media generation is enabled and credits available
    if config.ENABLE_MEDIA_GENERATION and state.get("credits_remaining", 0) > 0:
        return "generate_media"
    return "skip_media"


def is_beat_complete(state: StoryState) -> str:
    """
    Determine if beat was just completed.

    Args:
        state: Current story state

    Returns:
        "advance" if beat complete, "continue" otherwise
    """
    beat_progress = state.get("beat_progress", {})
    current_beat = state["current_beat"]

    if beat_progress.get(current_beat, False):
        return "advance"
    return "continue"


def has_error(state: StoryState) -> str:
    """
    Check if an error occurred.

    Args:
        state: Current story state

    Returns:
        "error" if error exists, "success" otherwise
    """
    if state.get("error"):
        return "error"
    return "success"
