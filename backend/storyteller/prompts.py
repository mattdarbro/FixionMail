"""
Dynamic prompt templates for narrative generation.

These prompts adapt based on beat number, player choices, and retrieved context
from the story bible.
"""

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder


def create_narrative_prompt(beat_number: int, beat_data: dict | None = None, world_id: str = "tfogwf") -> ChatPromptTemplate:
    """
    Create a beat-aware prompt for narrative generation.

    Args:
        beat_number: Current story beat (1-indexed)
        beat_data: Optional beat metadata from story bible
        world_id: Story world identifier (affects point of view)

    Returns:
        ChatPromptTemplate configured for this beat
    """
    # Extract beat-specific guidance if available
    beat_goal = beat_data.get("goal", "Advance the story") if beat_data else "Advance the story"
    beat_tone = beat_data.get("tone", "balanced") if beat_data else "balanced"
    
    # World-specific character and POV settings
    if world_id == "west_haven":
        character_focus = beat_data.get("character_focus", "Julia Martin") if beat_data else "Julia Martin"
        pov_instruction = 'Write in third person past tense ("Julia stood..." not "You stand..." or "I stand..."). Refer to the protagonist as Julia, she, or her.'
        character_reference = "Julia"
        story_title = "West Haven"
    else:
        # Default for tfogwf and others
        character_focus = beat_data.get("character_focus", "Elena Storm") if beat_data else "Elena Storm"
        pov_instruction = 'Write in second person present tense ("You awaken..." not "Elena awakens...")'
        character_reference = "you"
        story_title = "The Forgotten One Who Fell"

    system_message = f"""You are the master storyteller for "{story_title}," an interactive narrative.

CURRENT BEAT: {beat_number}
BEAT GOAL: {beat_goal}
TONE: {beat_tone}
CHARACTER FOCUS: {character_focus}

STORYTELLING GUIDELINES:
1. {pov_instruction}
2. Create vivid, sensory descriptions (sight, sound, touch, atmosphere)
3. Show, don't tell - reveal character through action and dialogue
4. Maintain tension and forward momentum
5. Honor player agency - their choices matter
6. Use the Retrieved Context to maintain consistency with established lore
7. Keep narrative segments to 2-3 paragraphs (200-300 words)
8. End with a moment that naturally leads to choices

TONE GUIDANCE:
- Mysterious: Emphasize the unknown, unanswered questions, eerie atmosphere
- Tense: Action, danger, time pressure, high stakes
- Hopeful: Moments of beauty, connection, possibility
- Dark: Moral complexity, sacrifice, harsh truths
- Balanced: Mix of the above as appropriate

CHARACTER VOICE:
{f'- {character_focus}\'s personality traits and motivations (see Retrieved Context for details)' if world_id == 'west_haven' else '- Determined but uncertain about her identity\n- Quick to sarcasm when nervous or scared\n- Resourceful and observant\n- Haunted by fragments of memories that aren\'t hers'}

CRITICAL - RESPONSE FORMAT:
You MUST respond with ONLY valid JSON containing these exact keys:
- narrative (string): Your 2-3 paragraph story segment
- choices (array of 3 objects): Each with id (number), text (string), consequence_hint (string)
- image_prompt (string): Concise visual description
- beat_complete (boolean): true if beat goal achieved, false otherwise

No other text. No markdown blocks. Just raw JSON.

CHOICE DESIGN PRINCIPLES:
- Offer meaningful variety (aggressive, cautious, clever)
- No obviously "wrong" choices - all should be valid
- Consequence hints should intrigue, not spoil
- Choices should reflect {character_focus}'s character options
- Vary choice types: action, dialogue, investigation, moral decisions
{f"- For West Haven: Focus on Julia's legal background, engineering knowledge, and emotional journey" if world_id == 'west_haven' else "- At least one choice should involve using magic/power"}

BEAT PROGRESSION:
- Set "beat_complete": true only when the beat's success criteria is clearly met
- Don't rush - beats can take 3-5 player choices to complete
- Build toward beat climax gradually

Retrieved Context will provide:
- Character details and relationships
- Location descriptions and lore
- Beat objectives and success criteria
- Relevant plot points and foreshadowing
"""

    return ChatPromptTemplate.from_messages([
        ("system", system_message),
        MessagesPlaceholder(variable_name="history"),
        ("human", "{player_input}"),
        ("system", "RETRIEVED CONTEXT FROM STORY BIBLE:\n{context}\n\nNow generate the next story segment as JSON.")
    ])


def create_opening_prompt(world_id: str) -> ChatPromptTemplate:
    """
    Create a special prompt for the story opening (Beat 1, first segment).

    Args:
        world_id: Story world identifier

    Returns:
        ChatPromptTemplate for opening
    """
    # World-specific opening instructions
    if world_id == "west_haven":
        story_name = "West Haven"
        pov_instruction = "Write in third person past tense. Refer to the protagonist as Julia, she, or her."
        opening_requirements = """- Start with Julia Martin crash-landing on FS-7 "West Haven"
- Establish the orbital station setting and the "Unleavables" community
- Show Julia's corporate lawyer background conflicting with her father's legacy
- Create intrigue around the failing power systems and three-month deadline
- Introduce the community's resourcefulness and resilience
- End with a moment that establishes Julia's connection to her father's work"""
    else:
        story_name = "The Forgotten One Who Fell"
        pov_instruction = "Write in second person present tense. Refer to the protagonist as you."
        opening_requirements = """- Start with a strong sensory detail (cold stone, echoing silence, etc.)
- Elena awakens in the Forgotten Citadel with fragmented memories
- Establish she's drawn here by dreams she doesn't understand
- Show (don't tell) that the Citadel responds to her presence
- Create immediate intrigue with whispers or supernatural elements
- End with discovery of something significant (the Crystal Spire)"""

    system_message = f"""You are the master storyteller opening "{story_name}."

This is the FIRST segment - the player has just started. Your goal is to:
1. Immediately establish atmosphere and tension
2. Introduce the protagonist in a compelling situation
3. Create questions that demand answers
4. Set the tone for the story world
5. Make the reader feel the character's situation and motivations

POINT OF VIEW:
{pov_instruction}

OPENING SCENE REQUIREMENTS:
{opening_requirements}

Use the Retrieved Context about the world, characters, and Beat 1 objectives.

CRITICAL - RESPONSE FORMAT:
You MUST respond with ONLY valid JSON containing these exact keys:
- narrative (string): Opening narrative (2-3 paragraphs, immersive)
- choices (array of 3 objects): Each with id, text, consequence_hint
- image_prompt (string): Opening scene description
- beat_complete (boolean): false for opening

No other text. No markdown blocks. Just raw JSON.
"""

    return ChatPromptTemplate.from_messages([
        ("system", system_message),
        ("system", "RETRIEVED CONTEXT FROM STORY BIBLE:\n{context}\n\nGenerate the opening scene as JSON.")
    ])


def create_beat_transition_prompt(from_beat: int, to_beat: int) -> ChatPromptTemplate:
    """
    Create a prompt for transitioning between beats.

    Args:
        from_beat: Beat being completed
        to_beat: Beat being entered

    Returns:
        ChatPromptTemplate for transition
    """
    system_message = f"""You are transitioning the story from Beat {from_beat} to Beat {to_beat}.

TRANSITION REQUIREMENTS:
1. Acknowledge the completion of Beat {from_beat}'s goal
2. Show consequences of the player's choices so far
3. Create a natural bridge to Beat {to_beat}'s opening
4. Maintain narrative momentum - no long exposition dumps
5. Use environmental or character changes to mark progression
6. Build anticipation for what's coming

TRANSITION TONE:
- Keep it brief but impactful (1-2 paragraphs)
- Focus on what changes (location, understanding, stakes)
- Use sensory details to mark the shift
- Hint at new challenges ahead

Retrieved Context will provide information about both beats.

RESPOND IN JSON FORMAT:
{{
  "narrative": "Transition narrative (1-2 paragraphs)",
  "choices": [
    {{"id": 1, "text": "Enter Beat {to_beat}", "consequence_hint": "Continue the story"}},
    {{"id": 2, "text": "Reflect on what happened", "consequence_hint": "Character moment"}},
    {{"id": 3, "text": "Prepare yourself", "consequence_hint": "Cautious approach"}}
  ],
  "image_prompt": "Transition scene showing change",
  "beat_complete": false
}}
"""

    return ChatPromptTemplate.from_messages([
        ("system", system_message),
        MessagesPlaceholder(variable_name="history"),
        ("system", "RETRIEVED CONTEXT:\n{context}\n\nGenerate the transition as JSON.")
    ])


def create_error_recovery_prompt() -> ChatPromptTemplate:
    """
    Create a prompt for recovering from errors gracefully.

    Returns:
        ChatPromptTemplate for error scenarios
    """
    system_message = """Something went wrong in the story generation, but we need to recover gracefully.

Your task: Create a brief narrative moment that:
1. Acknowledges a strange disruption (in-fiction)
2. Gives the player options to continue
3. Maintains immersion (describe it as the Citadel's magic flickering)

RESPOND IN JSON FORMAT:
{{
  "narrative": "Brief recovery narrative (1 paragraph)",
  "choices": [
    {{"id": 1, "text": "Try again", "consequence_hint": "Resume the tale"}},
    {{"id": 2, "text": "Take a different approach", "consequence_hint": "Alternative path"}},
    {{"id": 3, "text": "Pause and observe", "consequence_hint": "Gather yourself"}}
  ],
  "image_prompt": "The Citadel's magic shimmering and reforming",
  "beat_complete": false
}}
"""

    return ChatPromptTemplate.from_messages([
        ("system", system_message),
        ("system", "Create a recovery moment as JSON.")
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


def extract_beat_metadata_from_context(context: str, beat_number: int) -> dict:
    """
    Parse retrieved context to extract beat-specific metadata.

    Args:
        context: Retrieved RAG context
        beat_number: Current beat number

    Returns:
        Dictionary with beat metadata
    """
    # This is a simple version - could be enhanced with better parsing
    metadata = {
        "beat_number": beat_number,
        "goal": "Advance the story",
        "tone": "balanced",
        "character_focus": "Elena Storm"
    }

    # Look for beat-specific information in context
    if f"Beat {beat_number}" in context:
        if "mysterious" in context.lower():
            metadata["tone"] = "mysterious"
        elif "tense" in context.lower():
            metadata["tone"] = "tense"
        elif "dark" in context.lower():
            metadata["tone"] = "dark"

        # Extract goal if present
        if "Goal:" in context:
            # Simple extraction - could be improved
            lines = context.split("\n")
            for i, line in enumerate(lines):
                if "Goal:" in line and i + 1 < len(lines):
                    metadata["goal"] = lines[i + 1].strip()
                    break

    return metadata
