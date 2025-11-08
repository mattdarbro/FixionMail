"""
Dynamic prompt templates for continuation-based narrative generation.

This new system uses world templates (your beat design) + Claude improvisation.
No more RAG - just pure generative storytelling within your structure.
"""

import json
from pathlib import Path
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder


def load_world_template(world_id: str) -> dict:
    """
    Load world template JSON.

    Args:
        world_id: World identifier (e.g., "west_haven")

    Returns:
        World template dictionary

    Raises:
        FileNotFoundError: If template doesn't exist
    """
    template_path = Path("story_worlds") / world_id / "world_template.json"

    if not template_path.exists():
        raise FileNotFoundError(
            f"World template not found: {template_path}\n"
            f"Please create world_template.json for world '{world_id}'"
        )

    with open(template_path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_beat_info(world_template: dict, beat_number: int) -> dict:
    """
    Extract beat-specific information from template.

    Args:
        world_template: Loaded world template
        beat_number: Current beat number (1-indexed)

    Returns:
        Beat info dictionary
    """
    beat_structure = world_template.get("beat_structure", [])

    # Find the beat (beat numbers in template are 1-indexed)
    for beat in beat_structure:
        if beat.get("beat") == beat_number:
            return beat

    # If beat not found, return generic info
    return {
        "beat": beat_number,
        "name": f"Beat {beat_number}",
        "goal": "Advance the story",
        "emotional_arc": "Continue the journey",
        "turns": 4,
        "key_moments": [],
        "dramatic_questions": []
    }


def create_opening_prompt(world_template: dict) -> ChatPromptTemplate:
    """
    Create prompt for story opening (Beat 1, first turn).

    This is where Claude creates the initial protagonist, love interest,
    and sets up the opening scene based on your beat structure.

    Args:
        world_template: Loaded world template with beat structure

    Returns:
        ChatPromptTemplate for opening
    """
    beat_1 = get_beat_info(world_template, 1)
    world_lore = world_template.get("world_lore", {})
    character_arc = world_template.get("character_arc_template", {})
    narrative_style = world_template.get("narrative_style", {})
    generation_guidelines = world_template.get("generation_guidelines", {})

    pov = narrative_style.get("pov", "third person past tense")
    tone = narrative_style.get("tone", "")

    # Format JSON outside f-string, then escape braces for LangChain template
    guidelines_json = json.dumps(generation_guidelines, indent=2).replace('{', '{{').replace('}', '}}')

    # JSON example as raw string, then escape for LangChain template
    json_example_raw = '''{
  "narrative": "Opening narrative (2-3 paragraphs)",
  "choices": [
    {
      "id": 1,
      "text": "First sentence(s) that continue the narrative...",
      "tone": "cautious/hopeful/defensive/etc"
    },
    {
      "id": 2,
      "text": "Alternative continuation with different tone...",
      "tone": "bold/vulnerable/curious/etc"
    },
    {
      "id": 3,
      "text": "Third continuation option...",
      "tone": "playful/serious/guarded/etc"
    }
  ],
  "image_prompt": "Visual description for image generation",
  "story_bible_update": {
    "protagonist": {
      "name": "Generated name",
      "age": 30,
      "occupation": "Generated occupation",
      "personality": "Key traits",
      "background": "Brief background",
      "current_situation": "Why they're here"
    },
    "locations": {
      "current_location": "Description of where opening takes place"
    },
    "key_events": ["Opening event description"]
  },
  "beat_progress": 0.25
}'''
    # Escape braces for LangChain template ({{ for { and }} for })
    json_example = json_example_raw.replace('{', '{{').replace('}', '}}')

    system_message = f"""You are generating the OPENING of an interactive narrative experience.

WORLD TEMPLATE:
Setting: {world_lore.get("setting", "")}
Themes: {", ".join(world_lore.get("themes", []))}
Tone: {tone}
Point of View: {pov}

BEAT 1: {beat_1.get("name", "Opening")}
Goal: {beat_1.get("goal", "")}
Emotional Arc: {beat_1.get("emotional_arc", "")}
Key Moments: {", ".join(beat_1.get("key_moments", []))}

CHARACTER ARC TEMPLATES:
Protagonist Archetype: {character_arc.get("protagonist", {}).get("archetype", "")}
Starting State: {character_arc.get("protagonist", {}).get("starting_state", "")}
Love Interest Archetype: {character_arc.get("love_interest", {}).get("archetype", "")}

GENERATION GUIDELINES:
{guidelines_json}

🎯 CRITICAL REQUIREMENT: Follow the 6-BEAT CHAPTER STRUCTURE below.
   Each beat is MANDATORY. Do not skip or combine beats.

⚠️  IMPORTANT: These beat labels are STRUCTURAL GUIDELINES ONLY.
   DO NOT include beat labels (like "BEAT 1: OPENING HOOK") in your narrative.
   Write the narrative as seamless, flowing prose without section headers.
   BUT YOU MUST STILL WRITE ALL 6 BEATS AT FULL LENGTH!

📖 CHAPTER STRUCTURE (Write all 6 beats in order):

   BEAT 1: OPENING HOOK (300-400 words) ⚠️ WRITE THE FULL 300-400 WORDS!
   - Immediate sensory detail that pulls reader in
   - Character in action or reaction to situation
   - Set the scene with vivid, specific details
   - Establish mood and atmosphere

   BEAT 2: CONTEXT/GROUNDING (300-400 words)
   - Character's internal state and thoughts
   - Brief relevant backstory or explanation
   - Establish what's at stake for the character
   - Show character's personality through their perspective

   BEAT 3: ESCALATION (400-500 words) ⚠️ WRITE THE FULL 400-500 WORDS!
   - New information, complication, or discovery
   - Action sequence or meaningful interaction
   - Raise tension or introduce conflict
   - Move the plot forward with specific events

   BEAT 4: TURNING POINT (400-500 words) ⚠️ WRITE THE FULL 400-500 WORDS!
   - The biggest moment of this chapter
   - Character makes a decision or faces a challenge
   - Emotional peak or revelation
   - This is the heart of the chapter - make it count

   BEAT 5: AFTERMATH/PROCESSING (300-400 words) ⚠️ WRITE THE FULL 300-400 WORDS!
   - Character reacts to what just happened
   - New understanding, question, or realization
   - Breathing room with reflection
   - Show impact of the turning point

   BEAT 6: CHAPTER ENDING (300-400 words) ⚠️ WRITE THE FULL 300-400 WORDS!
   - Clear forward momentum into next chapter
   - Hook that makes reader want to continue
   - Leave character in new situation or with new goal
   - End on a strong image or moment

   TOTAL TARGET: 2300-2700 words across all 6 beats

YOUR TASK:
1. CREATE the protagonist (name, age, occupation, personality) based on the archetype

2. WRITE Chapter 1 following the 6-BEAT STRUCTURE above:
   ⚠️  You MUST write all 6 beats in sequence
   ⚠️  Each beat should hit its target word count
   ⚠️  Write in {pov}
   ⚠️  Include dialogue, internal thoughts, sensory details, and action
   ⚠️  Make each beat distinct and purposeful

3. CREATE 3 choice continuations that START the next chapter:
   - Each continuation should be 1-3 sentences that naturally flow into Chapter 2
   - Offer different emotional approaches (cautious, bold, vulnerable, etc.)
   - Make them feel like narrative, not game choices

4. GENERATE an image prompt for the chapter's key scene

5. BUILD initial story bible with protagonist details

CHAPTER PACING:
- This is Chapter 1 of 30 (3% of total story)
- Take time to establish world and character - DON'T RUSH
- Multiple scenes showing character's situation
- Create emotional connection with protagonist
- End with clear stakes and forward momentum

CRITICAL - RESPONSE FORMAT (JSON only, no markdown):
""" + json_example + f"""

Remember:
- NO markdown code blocks
- ⚠️⚠️⚠️ MANDATORY: 2500-2700 WORDS TOTAL - Write FULL LENGTH for EACH beat! ⚠️⚠️⚠️
- Removing beat labels does NOT mean shortening the beats!
- Each beat MUST hit its target word count (300-500 words per beat)
- Write in {pov}
- Make choices feel like story continuations, not buttons
- Keep tone consistent with world template
"""

    return ChatPromptTemplate.from_messages([
        ("system", system_message),
        ("human", "Begin the story.")
    ])


def create_continuation_prompt(
    world_template: dict,
    beat_number: int,
    turns_in_beat: int,
    last_choice_continuation: str,
    generated_story_bible: dict,
    story_summary: list[str],
    chapter_number: int = 1,
    total_chapters: int = 30
) -> ChatPromptTemplate:
    """
    Create prompt for continuing the story after a choice.

    Args:
        world_template: Loaded world template
        beat_number: Current beat number
        turns_in_beat: How many turns we've done in this beat
        last_choice_continuation: The continuation text from selected choice
        generated_story_bible: Claude-generated story details so far
        story_summary: Previous turn summaries
        chapter_number: Current chapter number (1-30)
        total_chapters: Total chapters in story (default: 30)

    Returns:
        ChatPromptTemplate for continuation
    """
    beat_info = get_beat_info(world_template, beat_number)
    world_lore = world_template.get("world_lore", {})
    character_arc = world_template.get("character_arc_template", {})
    narrative_style = world_template.get("narrative_style", {})

    pov = narrative_style.get("pov", "third person past tense")
    tone = narrative_style.get("tone", "")

    max_turns = beat_info.get("turns", 4)
    turns_remaining = max(0, max_turns - turns_in_beat)
    progress = turns_in_beat / max_turns if max_turns > 0 else 0

    # Calculate overall story progress
    story_progress_pct = (chapter_number / total_chapters) * 100
    chapters_remaining = total_chapters - chapter_number

    # Format story summary
    summary_text = "\n".join([f"- {s}" for s in story_summary[-6:]]) if story_summary else "Beginning of story"

    # Format JSON outside f-string, then escape braces for LangChain template
    story_bible_json = json.dumps(generated_story_bible, indent=2).replace('{', '{{').replace('}', '}}')

    # JSON example as raw string, then escape for LangChain template
    json_example_raw = '''{
  "narrative": "2-3 paragraph continuation",
  "choices": [
    {
      "id": 1,
      "text": "First continuation sentence(s)...",
      "tone": "emotional tone"
    },
    {
      "id": 2,
      "text": "Second continuation...",
      "tone": "different tone"
    },
    {
      "id": 3,
      "text": "Third continuation...",
      "tone": "another approach"
    }
  ],
  "image_prompt": "Scene description",
  "story_bible_update": {
    "locations": {},
    "supporting_characters": {},
    "key_events": [],
    "relationships": {}
  },
  "beat_progress": 0.0-1.0
}'''
    # Escape braces for LangChain template ({{ for { and }} for })
    json_example = json_example_raw.replace('{', '{{').replace('}', '}}')

    system_message = f"""You are continuing an interactive narrative experience.

WORLD TEMPLATE:
Setting: {world_lore.get("setting", "")}
Themes: {", ".join(world_lore.get("themes", []))}
Tone: {tone}
Point of View: {pov}

CHAPTER PROGRESS:
📖 Chapter {chapter_number} of {total_chapters}
📊 Story Progress: {int(story_progress_pct)}%
📄 Chapters Remaining: {chapters_remaining}

CURRENT BEAT: {beat_number} - {beat_info.get("name", "")}
Goal: {beat_info.get("goal", "")}
Emotional Arc: {beat_info.get("emotional_arc", "")}
Progress: {turns_in_beat}/{max_turns} turns (approx {int(progress*100)}%)
Success Criteria: {beat_info.get("success_criteria", "")}

STORY SO FAR (Recent Events):
{summary_text}

GENERATED STORY BIBLE:
{story_bible_json}

LAST CHOICE (Continue from here):
"{last_choice_continuation}"

🎯 CRITICAL REQUIREMENT: Follow the 6-BEAT CHAPTER STRUCTURE below.
   Each beat is MANDATORY. Do not skip or combine beats.

⚠️  IMPORTANT: These beat labels are STRUCTURAL GUIDELINES ONLY.
   DO NOT include beat labels (like "BEAT 1: OPENING HOOK") in your narrative.
   Write the narrative as seamless, flowing prose without section headers.
   BUT YOU MUST STILL WRITE ALL 6 BEATS AT FULL LENGTH!

📖 CHAPTER STRUCTURE (Write all 6 beats in order):

   BEAT 1: OPENING HOOK (300-400 words) ⚠️ WRITE THE FULL 300-400 WORDS!
   - Start by seamlessly incorporating the choice continuation text
   - Immediate action or reaction continuing from the choice
   - Vivid sensory details of the current moment
   - Establish the scene and mood

   BEAT 2: CONTEXT/DEVELOPMENT (300-400 words) ⚠️ WRITE THE FULL 300-400 WORDS!
   - Character's thoughts and feelings about current situation
   - Advance the plot thread from last chapter
   - Show character processing or observing
   - Deepen the current situation

   BEAT 3: ESCALATION (400-500 words) ⚠️ WRITE THE FULL 400-500 WORDS!
   - New complication, discovery, or interaction
   - Meaningful dialogue or action sequence
   - Raise stakes or tension
   - Move toward the beat goal: {beat_info.get("goal", "")}

   BEAT 4: TURNING POINT (400-500 words) ⚠️ WRITE THE FULL 400-500 WORDS!
   - The pivotal moment of this chapter
   - Character decision, revelation, or confrontation
   - Emotional climax of the chapter
   - Progress character arc: {character_arc.get("protagonist", {}).get("archetype", "")}

   BEAT 5: AFTERMATH/PROCESSING (300-400 words) ⚠️ WRITE THE FULL 300-400 WORDS!
   - Character reacts to the turning point
   - New understanding or question emerges
   - Show growth or change in character
   - Reflection and breathing room

   BEAT 6: CHAPTER ENDING (300-400 words) ⚠️ WRITE THE FULL 300-400 WORDS!
   - Strong forward momentum
   - Hook for next chapter
   - New situation, goal, or question
   - End on compelling moment

   TOTAL TARGET: 2300-2700 words across all 6 beats

YOUR TASK:
1. CONTINUE seamlessly from the choice continuation (incorporate it into Beat 1)

2. WRITE Chapter {chapter_number} following the 6-BEAT STRUCTURE above:
   ⚠️  You MUST write all 6 beats in sequence
   ⚠️  Each beat should hit its target word count
   ⚠️  Write in {pov}
   ⚠️  Include dialogue, internal thoughts, sensory details, and action
   ⚠️  Make each beat distinct and purposeful
   ⚠️  Advance toward beat goal: {beat_info.get("goal", "")}

3. CREATE 3 new choice continuations for Chapter {chapter_number + 1}

4. UPDATE story bible with any new details (characters, locations, events)

5. ASSESS beat progress (0.0-1.0 where 1.0 = beat complete)

STORY ARC PACING:
- Overall: {int(story_progress_pct)}% through story
- {"Act 1 (Setup)" if story_progress_pct < 33 else "Act 2 (Confrontation)" if story_progress_pct < 75 else "Act 3 (Resolution)"}
- Key moments to hit: {", ".join(beat_info.get("key_moments", []))}
- Dramatic questions: {", ".join(beat_info.get("dramatic_questions", []))}
- DON'T RUSH - Take time to develop scenes fully

RESPONSE FORMAT (JSON only):
""" + json_example + f"""

Remember:
- Continue FROM the last choice text (seamless flow)
- ⚠️⚠️⚠️ MANDATORY: 2500-2700 WORDS TOTAL - Write FULL LENGTH for EACH beat! ⚠️⚠️⚠️
- Removing beat labels does NOT mean shortening the beats!
- Each beat MUST hit its target word count (300-500 words per beat)
- Expand scenes with sensory details, dialogue, internal thoughts
- Choices should feel like narrative options, not game buttons
- Update story bible with NEW information only
- Write in {pov}
- Consider where we are in the overall {total_chapters}-chapter arc
"""

    return ChatPromptTemplate.from_messages([
        ("system", system_message),
        MessagesPlaceholder(variable_name="history"),
        ("human", "Continue the story from the choice: {last_choice}")
    ])


def format_conversation_history(messages: list) -> str:
    """
    Format conversation history for context.

    Args:
        messages: List of BaseMessage objects

    Returns:
        Formatted string of recent conversation
    """
    if not messages:
        return "No previous conversation."

    # Take last 6 messages for context (3 exchanges)
    recent = messages[-6:] if len(messages) > 6 else messages

    formatted = []
    for msg in recent:
        role = "Player" if msg.type == "human" else "Story"
        content = msg.content[:200] + "..." if len(msg.content) > 200 else msg.content
        formatted.append(f"{role}: {content}")

    return "\n".join(formatted)
