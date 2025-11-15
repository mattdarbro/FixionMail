"""
Genre-Specific Consistency Rules

Defines what stays consistent vs what changes for each genre.
This is what makes FictionMail unique - understanding genre conventions!
"""

from typing import Dict, List, Any


GENRE_RULES = {
    "mystery": {
        "name": "Mystery/Detective",
        "description": "Like Poirot or Miss Marple - same detective, different cases",

        "consistency": {
            "protagonist": {
                "locked": True,
                "reason": "The detective's identity and methods are the core of the series",
                "changeable": []
            },
            "setting": {
                "locked": False,
                "reason": "Each mystery happens in a different location",
                "changeable": ["location", "time_period", "specific_place"]
            },
            "supporting_characters": {
                "locked": False,
                "reason": "New suspects, witnesses, and victims each time",
                "changeable": ["all_except_recurring_sidekicks"]
            }
        },

        "story_focus": "investigation",
        "what_changes": ["the mystery", "the suspects", "the location", "the crime"],
        "what_stays": ["the detective", "investigation style", "core personality"],

        "prompt_guidance": """
This is a MYSTERY series featuring the same detective.

MUST STAY CONSISTENT:
- Detective name: {protagonist_name}
- Detective personality: {protagonist_traits}
- Investigation approach: {investigation_style}

CHANGES EACH STORY:
- The crime/mystery being investigated
- The location where it takes place
- The suspects and witnesses
- The specific clues and red herrings

Think: Poirot, Miss Marple, Sherlock Holmes - same detective, new mystery.
"""
    },

    "scifi": {
        "name": "Science Fiction",
        "description": "Like Star Trek or Foundation - same universe, stories can feature different characters or the same crew evolving",

        "consistency": {
            "protagonist": {
                "locked": False,
                "reason": "Characters can evolve, age, change roles in sci-fi",
                "changeable": ["role", "relationships", "experiences"]
            },
            "setting": {
                "locked": True,
                "reason": "The universe rules and tech level must stay consistent",
                "changeable": []
            },
            "supporting_characters": {
                "locked": False,
                "reason": "New characters can be introduced, old ones can leave",
                "changeable": ["all"]
            }
        },

        "story_focus": "exploration",
        "what_changes": ["the situation", "character development", "new discoveries"],
        "what_stays": ["universe rules", "tech level", "core world setting", "species"],

        "prompt_guidance": """
This is a SCI-FI series set in a consistent universe.

MUST STAY CONSISTENT:
- Universe: {setting_name}
- Tech level: {tech_level}
- World rules: {universe_rules}
- Core locations: {key_locations}

CAN EVOLVE:
- Characters can grow, change, learn
- New situations and challenges
- Character relationships and dynamics
- New discoveries within established rules

Think: Star Trek episodes - same universe, crew evolves, new situations.
"""
    },

    "sitcom": {
        "name": "Sitcom/Comedy",
        "description": "Like Friends or Seinfeld - same characters, same places, different situations",

        "consistency": {
            "protagonist": {
                "locked": True,
                "reason": "The main character is the heart of the sitcom",
                "changeable": []
            },
            "setting": {
                "locked": True,
                "reason": "Core locations (apartment, workplace) stay the same",
                "changeable": []
            },
            "supporting_characters": {
                "locked": True,
                "reason": "The core cast stays consistent - that's the ensemble",
                "changeable": []
            }
        },

        "story_focus": "situation",
        "what_changes": ["the situation", "the conflict", "the jokes", "guest characters"],
        "what_stays": ["main characters", "core locations", "character personalities", "tone"],

        "prompt_guidance": """
This is a SITCOM series with a consistent cast.

MUST STAY CONSISTENT:
- Main character: {protagonist_name} - {protagonist_traits}
- Core cast: {supporting_characters}
- Main locations: {key_locations}
- Tone: {tone}
- Character personalities and quirks

CHANGES EACH STORY:
- The situation/conflict
- The specific jokes and humor
- Minor guest characters
- The particular misunderstanding or problem

Think: Friends, Seinfeld, The Office - same people, different episode plots.
"""
    },

    "romance": {
        "name": "Romance",
        "description": "Each story explores a new romantic journey, though the protagonist's voice remains consistent",

        "consistency": {
            "protagonist": {
                "locked": "partial",
                "reason": "The protagonist's voice and approach to love stays consistent",
                "changeable": ["love_interest", "relationship_status"]
            },
            "setting": {
                "locked": "partial",
                "reason": "General setting stays similar (small town, big city, etc.)",
                "changeable": ["specific_locations"]
            },
            "supporting_characters": {
                "locked": "partial",
                "reason": "Best friend/family may recur, but love interest changes",
                "changeable": ["love_interest", "romantic_rivals"]
            }
        },

        "story_focus": "relationship",
        "what_changes": ["the love interest", "the romantic journey", "the obstacles"],
        "what_stays": ["protagonist's voice", "general setting", "recurring friends/family"],

        "prompt_guidance": """
This is a ROMANCE series following the same protagonist.

MUST STAY CONSISTENT:
- Protagonist: {protagonist_name} - {protagonist_traits}
- Protagonist's approach to love and relationships
- General setting type: {setting_atmosphere}
- Recurring friends/family members

CHANGES EACH STORY:
- The love interest
- The specific romantic journey
- The obstacles to love
- The particular meet-cute or conflict

Think: Romance series where protagonist has new love story, but their voice/personality stays consistent.
"""
    },

    "adventure": {
        "name": "Adventure",
        "description": "Like Indiana Jones - same adventurer(s), different quests and locations",

        "consistency": {
            "protagonist": {
                "locked": True,
                "reason": "The adventurer's personality and skills are key",
                "changeable": ["equipment", "knowledge_gained"]
            },
            "setting": {
                "locked": False,
                "reason": "Adventures take place in different locations",
                "changeable": ["location", "quest_destination"]
            },
            "supporting_characters": {
                "locked": "partial",
                "reason": "Core team may stay, but meet new allies/enemies",
                "changeable": ["quest_specific_characters"]
            }
        },

        "story_focus": "quest",
        "what_changes": ["the quest", "the location", "the treasure/goal", "the obstacles"],
        "what_stays": ["the adventurer(s)", "their skills", "core team members"],

        "prompt_guidance": """
This is an ADVENTURE series with consistent adventurer(s).

MUST STAY CONSISTENT:
- Main adventurer: {protagonist_name} - {protagonist_traits}
- Core skills and abilities
- Core team members (if any)
- Adventure style and approach

CHANGES EACH STORY:
- The quest or mission
- The location/destination
- The treasure or goal
- The specific obstacles and enemies
- New temporary allies

Think: Indiana Jones, Tomb Raider - same adventurer, new quest.
"""
    },

    "anthology": {
        "name": "Anthology (World Dips)",
        "description": "Different characters exploring the same world - like Black Mirror or Twilight Zone",

        "consistency": {
            "protagonist": {
                "locked": False,
                "reason": "Each story features different characters",
                "changeable": ["all"]
            },
            "setting": {
                "locked": True,
                "reason": "The world/universe stays consistent",
                "changeable": []
            },
            "supporting_characters": {
                "locked": False,
                "reason": "New cast each time",
                "changeable": ["all"]
            }
        },

        "story_focus": "world_exploration",
        "what_changes": ["all characters", "the situation", "the perspective"],
        "what_stays": ["the world", "world rules", "themes"],

        "prompt_guidance": """
This is an ANTHOLOGY series exploring a consistent world.

MUST STAY CONSISTENT:
- World: {setting_name}
- World rules: {universe_rules}
- Tech/magic level: {tech_level}
- Themes: {themes}

COMPLETELY CHANGES:
- The protagonist (new person each story)
- All supporting characters
- The situation and conflict
- The perspective on the world

Think: Black Mirror, Twilight Zone - same world/themes, different characters each time.
"""
    }
}


def get_genre_rules(genre: str) -> Dict[str, Any]:
    """
    Get the rules for a specific genre.

    Args:
        genre: Genre name (mystery, scifi, sitcom, etc.)

    Returns:
        Dictionary of rules for that genre
    """
    return GENRE_RULES.get(genre.lower(), GENRE_RULES["scifi"])  # Default to scifi if unknown


def get_consistency_prompt(genre: str, bible: Dict[str, Any]) -> str:
    """
    Generate genre-specific consistency guidance for prompts.

    Args:
        genre: The story genre
        bible: The story bible with world details

    Returns:
        Formatted prompt guidance string
    """
    rules = get_genre_rules(genre)
    prompt_template = rules.get("prompt_guidance", "")

    # Fill in the template with bible data
    filled_prompt = prompt_template.format(
        protagonist_name=bible.get("protagonist", {}).get("name", "the protagonist"),
        protagonist_traits=", ".join(bible.get("protagonist", {}).get("key_traits", [])),
        investigation_style=bible.get("protagonist", {}).get("defining_characteristic", "methodical"),
        setting_name=bible.get("setting", {}).get("name", "the world"),
        tech_level=bible.get("setting", {}).get("rules", "standard genre rules"),
        universe_rules=bible.get("setting", {}).get("rules", "standard genre conventions"),
        key_locations=", ".join([loc.get("name", "") for loc in bible.get("setting", {}).get("key_locations", [])[:3]]),
        supporting_characters=", ".join([char.get("name", "") for char in bible.get("supporting_characters", [])[:3]]),
        tone=bible.get("tone", "genre-appropriate"),
        setting_atmosphere=bible.get("setting", {}).get("atmosphere", "genre-appropriate")
    )

    return filled_prompt


def validate_bible_edit(genre: str, current_bible: Dict[str, Any], proposed_changes: Dict[str, Any]) -> tuple[bool, str]:
    """
    Validate if proposed changes to a bible are allowed for the genre.

    Args:
        genre: The story genre
        current_bible: Current bible
        proposed_changes: Proposed changes

    Returns:
        Tuple of (is_valid, error_message)
    """
    rules = get_genre_rules(genre)

    # Check protagonist changes
    if "protagonist" in proposed_changes:
        if rules["consistency"]["protagonist"]["locked"] is True:
            if proposed_changes["protagonist"].get("name") != current_bible["protagonist"].get("name"):
                return False, f"In {rules['name']} stories, {rules['consistency']['protagonist']['reason'].lower()}"

    # Check setting changes
    if "setting" in proposed_changes:
        if rules["consistency"]["setting"]["locked"] is True:
            # Setting is locked - no major changes allowed
            if proposed_changes["setting"].get("name") != current_bible["setting"].get("name"):
                return False, f"In {rules['name']} stories, {rules['consistency']['setting']['reason'].lower()}"

    return True, "Changes allowed"


def get_genre_description(genre: str) -> str:
    """Get user-friendly description of how a genre works."""
    rules = get_genre_rules(genre)
    return f"""
**{rules['name']}**

{rules['description']}

📌 What stays consistent:
{chr(10).join(['  • ' + item for item in rules['what_stays']])}

🔄 What changes each story:
{chr(10).join(['  • ' + item for item in rules['what_changes']])}
    """.strip()
