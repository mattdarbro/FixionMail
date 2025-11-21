"""
Prompts for standalone story generation (FictionMail).

These replace the chapter-based prompts for the daily story service.
"""

import json
from typing import Dict, Any


def create_standalone_story_beat_prompt(
    story_bible: dict,
    beat_template: dict,
    is_cliffhanger: bool = False,
    cameo: dict = None,
    user_preferences: dict = None
) -> str:
    """
    Create prompt for CBA to plan a standalone story using a beat template.

    Args:
        story_bible: Enhanced story bible
        beat_template: Beat template from beat_templates.py
        is_cliffhanger: Whether to end on a cliffhanger (free tier)
        cameo: Optional cameo character to include
        user_preferences: User preferences from ratings

    Returns:
        Formatted prompt for CBA
    """
    # Extract bible components
    genre = story_bible.get("genre", "fiction")
    setting = story_bible.get("setting", {})
    tone = story_bible.get("tone", "")
    themes = story_bible.get("themes", [])
    story_history = story_bible.get("story_history", {})
    genre_config = story_bible.get("genre_config", {})
    story_settings = story_bible.get("story_settings", {})

    # Handle both recurring characters (protagonist) and AI-generated (character_template)
    has_recurring_chars = genre_config.get("characters") == "user" or "protagonist" in story_bible
    protagonist = story_bible.get("protagonist", story_bible.get("character_template", {}))
    supporting = story_bible.get("supporting_characters", story_bible.get("supporting_cast_template", []))

    # Get template details
    template_name = beat_template.get("name", "")
    total_words = beat_template.get("total_words", 1500)
    beats = beat_template.get("beats", [])

    # Format recent stories
    recent_summaries = story_history.get("recent_summaries", [])
    recent_plots = story_history.get("recent_plot_types", [])

    history_context = ""
    if recent_summaries:
        history_text = "\n".join([f"  - {s}" for s in recent_summaries[-5:]])
        history_context = f"\n\n## RECENT STORIES\n\nAvoid repeating these plots:\n{history_text}"

        if recent_plots:
            plots_text = ", ".join(recent_plots[-5:])
            history_context += f"\n\nRecent plot types: {plots_text}"

    # Format user preferences
    prefs_context = ""
    if user_preferences:
        pacing = user_preferences.get("pacing_preference", "medium")
        action = user_preferences.get("action_level", "medium")
        emotion = user_preferences.get("emotional_depth", "medium")

        prefs_context = f"""

## USER PREFERENCES (learned from ratings)

Based on their ratings, this user prefers:
- Pacing: {pacing}
- Action level: {action}
- Emotional depth: {emotion}

Adjust the story to match these preferences while staying true to the genre.
"""

    # Cameo context
    cameo_context = ""
    if cameo:
        cameo_context = f"""

## CAMEO CHARACTER (Optional)

You MAY include a brief cameo appearance:
- Name: {cameo.get('name', 'N/A')}
- Description: {cameo.get('description', 'N/A')}

**Guidance**:
- Only include if it fits naturally
- Brief appearance (background moment, passing interaction, overheard conversation)
- Don't force it - the story works without them
- Good beats for cameos: opening, middle transition beats
- Avoid using in climax or resolution
"""

    # Cliffhanger guidance
    ending_style = ""
    if is_cliffhanger:
        ending_style = """

## ENDING STYLE: Curiosity Hook ✨

This story should end on an intriguing note (free tier cliffhanger):
- **DO**: Resolve the immediate story question
- **DO**: End on an intriguing discovery, revelation, or new question
- **DO**: Create anticipation and curiosity
- **DON'T**: End on life-or-death peril or anxiety
- **DON'T**: Leave core plot unresolved

**Good cliffhanger**: "Elena decoded the message. It was coordinates—but to where? And why did they lead to the abandoned sector everyone avoided?"

**Bad cliffhanger**: "The airlock opened. Elena had three seconds before—" [CUT]

Think of it as: Satisfy this story, but hint at bigger mysteries.
"""
    else:
        ending_style = """

## ENDING STYLE: Complete Resolution

This story should have satisfying closure:
- Resolve the central story question
- Emotional or thematic landing
- Character growth or realization
- Sense of completion
- World continues beyond this story (open for future tales)
"""

    # Build beat structure section
    beats_text = ""
    for beat in beats:
        beat_num = beat.get("beat_number", "?")
        beat_name = beat.get("beat_name", "")
        word_target = beat.get("word_target", 0)
        description = beat.get("description", "")
        guidance = beat.get("guidance", "")

        beats_text += f"""
**Beat {beat_num}: {beat_name.upper()}** ({word_target} words)
- Purpose: {description}
- Guidance: {guidance}
"""

    prompt = f"""You are the Chapter Beat Agent (CBA) planning a complete standalone story for FictionMail.

## YOUR TASK

Plan a {total_words}-word complete story using the provided beat structure.
This is a STANDALONE story (not part of a series), but it exists in an established world with consistent characters.

## STORY WORLD

**Genre**: {genre_config.get('label', genre)}
**Tone**: {tone}
**Intensity**: {story_settings.get('intensity_label', 'Moderate')} - {"Light stakes, comforting" if story_settings.get('intensity', 3) <= 2 else "High stakes, dramatic tension" if story_settings.get('intensity', 3) >= 4 else "Balanced drama"}
**Themes**: {', '.join(themes) if themes else 'To be discovered'}

**Setting**: {setting.get('name', 'N/A')}
{setting.get('description', 'N/A')}

**Atmosphere**: {setting.get('atmosphere', 'N/A')}

**Key Locations**:
{json.dumps(setting.get('key_locations', []), indent=2)}

## {"PROTAGONIST (recurring)" if has_recurring_chars else "CHARACTER TEMPLATE (generate fresh characters)"}

{"**Name**: " + protagonist.get('name', 'N/A') if has_recurring_chars else "**Archetype**: " + protagonist.get('archetype', 'To be determined')}
**Role**: {protagonist.get('role', 'N/A')}
**Age**: {protagonist.get('age_range', 'adult')}
**Traits**: {', '.join(protagonist.get('key_traits', []))}
**Defining Characteristic**: {protagonist.get('defining_characteristic', 'N/A')}
**Background**: {protagonist.get('background', 'N/A')}
**Voice**: {protagonist.get('voice', 'N/A')}

{"" if has_recurring_chars else "**IMPORTANT**: Create NEW, unique characters for this story based on the template above. Give them fresh names and specific details."}

## {"SUPPORTING CHARACTERS (recurring cast)" if has_recurring_chars else "SUPPORTING CAST TEMPLATE"}

{json.dumps(supporting, indent=2) if supporting else 'None defined - create as needed for this story'}

{history_context}
{prefs_context}
{cameo_context}
{ending_style}

## BEAT STRUCTURE ({len(beats)} beats, {total_words} total words)

{beats_text}

## JSON FORMAT

Return your beat plan as JSON:

```json
{{
  "story_title": "Engaging title for this story",
  "story_premise": "One sentence premise/hook",
  "plot_type": "Brief descriptor (mystery, action, character study, etc.)",
  "beats": [
    {{
      "beat_number": 1,
      "beat_name": "opening_hook",
      "word_target": {beats[0].get('word_target', 400) if beats else 400},
      "description": "What happens in this beat",
      "key_elements": ["element1", "element2"],
      "emotional_tone": "tense/hopeful/mysterious/etc",
      "characters_featured": ["Protagonist", "Character2"],
      "location": "Where this takes place",
      "narrative_purpose": "Why this beat matters to the story"
    }},
    // ... remaining beats following the template
  ],
  "story_question": "The central question driving this story",
  "emotional_arc": "The emotional journey of this story",
  "thematic_focus": "What this story explores thematically",
  "character_growth": "How protagonist changes or what they learn",
  "unique_element": "What makes THIS story fresh and interesting"
}}
```

## STORY PLANNING PRINCIPLES

1. **Complete Arc**: This must be a satisfying complete story
2. **Fresh Plot**: Don't repeat recent story types
3. **Character Consistency**: Honor established character traits
4. **World Consistency**: Stay true to setting rules
5. **Emotional Resonance**: Create genuine emotional moments
6. **Pacing**: Each beat flows naturally to the next
7. **Unique Hook**: Make THIS story feel special and worth reading

Plan an engaging {total_words}-word story now that will delight the reader!
"""

    return prompt


def create_prose_generation_prompt(
    beat_plan: dict,
    story_bible: dict,
    beat_template: dict,
    consistency_guidance: dict = None
) -> str:
    """
    Create prompt for Prose Agent to generate story from beat plan.

    Args:
        beat_plan: CBA's beat plan
        story_bible: Story bible
        beat_template: Template used
        consistency_guidance: Optional guidance from CEA

    Returns:
        Formatted prompt for PA
    """
    genre = story_bible.get("genre", "fiction")
    tone = story_bible.get("tone", "")
    total_words = beat_template.get("total_words", 1500)
    genre_config = story_bible.get("genre_config", {})

    # Handle both recurring characters and AI-generated
    has_recurring_chars = genre_config.get("characters") == "user" or "protagonist" in story_bible
    protagonist = story_bible.get("protagonist", story_bible.get("character_template", {}))

    # Extract CEA guidance if present
    cea_guidance = ""
    if consistency_guidance:
        general = consistency_guidance.get("general_guidance", "")
        emphasis = consistency_guidance.get("emphasis_points", [])
        avoid = consistency_guidance.get("avoid", [])

        if general:
            cea_guidance = f"\n\n## CONSISTENCY GUIDANCE\n\n{general}"

        if emphasis:
            cea_guidance += f"\n\n**Emphasize**: {', '.join(emphasis)}"

        if avoid:
            cea_guidance += f"\n\n**Avoid**: {', '.join(avoid)}"

    prompt = f"""You are the Prose Agent generating a complete {genre} story for FictionMail.

## YOUR TASK

Write a complete {total_words}-word story following the beat plan below.
This should be polished, engaging prose ready for readers to enjoy.

## STORY DETAILS

**Title**: {beat_plan.get('story_title', 'Untitled')}
**Premise**: {beat_plan.get('story_premise', 'N/A')}
**Genre**: {genre}
**Tone**: {tone}
**Target Length**: {total_words} words (±200 words is acceptable)

## {"PROTAGONIST" if has_recurring_chars else "CHARACTER GUIDANCE"}

{"**Name**: " + protagonist.get('name', 'N/A') if has_recurring_chars else "Create a NEW protagonist based on this template:"}
**Voice**: {protagonist.get('voice', 'thoughtful')}
**Key Traits**: {', '.join(protagonist.get('key_traits', []))}
**Defining Characteristic**: {protagonist.get('defining_characteristic', 'N/A')}

**CRITICAL**: {protagonist.get('defining_characteristic', 'N/A')} - This MUST be reflected consistently in the prose.
{"" if has_recurring_chars else "Give your protagonist a unique, memorable name and specific details that fit this story."}

## BEAT PLAN

{json.dumps(beat_plan.get('beats', []), indent=2)}

{cea_guidance}

## PROSE GENERATION GUIDELINES

**Writing Quality**:
- Vivid, sensory prose
- Show don't tell
- Vary sentence structure
- Strong opening hook
- Satisfying ending
- Natural dialogue
- Consistent POV (third person limited on protagonist)

**Pacing**:
- Honor word targets for each beat (±50 words)
- Each beat flows smoothly to the next
- Build tension appropriately
- Emotional moments have breathing room

**Character**:
- Protagonist's voice should be consistent
- Supporting characters feel real
- Actions match personalities
- Respect established limitations/traits

**World**:
- Consistent with established setting
- Sensory details ground reader
- World feels lived-in
- Setting affects action

**Genre Expectations**:
- {genre.capitalize()} genre conventions honored
- Tone matches story bible
- Satisfies reader expectations for {genre}

## FORMAT

Return ONLY the story prose. No metadata, no JSON, no commentary.
Just the complete story text, ready to be read.

Target: {total_words} words total.

Begin the story now:
"""

    return prompt
