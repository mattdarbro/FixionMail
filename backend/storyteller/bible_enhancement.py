"""
Story Bible Enhancement - AI expands minimal user input into rich story worlds.

Takes simple user input (genre + 1-2 sentences) and creates detailed story bible.
"""

import json
from typing import Dict, Any

# Genre Configuration
# Defines what elements persist vs change between stories
# characters: "user" = user defines recurring cast, "ai" = fresh characters each story
# setting: "same" = consistent locations, "different" = new places each story
# world: "same" = consistent rules/lore, "different" = new world each story
GENRE_CONFIG = {
    "comedy_sitcom": {
        "label": "Comedy / Sitcom",
        "characters": "user",
        "setting": "same",
        "world": "same",
        "description": "Recurring cast in familiar settings, comedic situations"
    },
    "detective": {
        "label": "Detective",
        "characters": "user",  # Same detective, different villains/extras
        "setting": "different",
        "world": "same",
        "description": "Same sleuth, new cases and locations"
    },
    "action": {
        "label": "Action",
        "characters": "user",
        "setting": "different",
        "world": "same",
        "description": "Same hero, different missions and locales"
    },
    "romance": {
        "label": "Romance",
        "characters": "ai",
        "setting": "different",
        "world": "same",
        "description": "Fresh love stories with consistent romantic tone"
    },
    "cozy": {
        "label": "Cozy",
        "characters": "ai",
        "setting": "different",
        "world": "same",
        "description": "Warm, comforting tales with new characters"
    },
    "historical": {
        "label": "Historical",
        "characters": "ai",
        "setting": "same",
        "world": "same",
        "description": "Different characters in a consistent historical period/place"
    },
    "western": {
        "label": "Western",
        "characters": "ai",
        "setting": "different",
        "world": "same",
        "description": "New frontier tales in the Old West"
    },
    "fantasy": {
        "label": "Fantasy",
        "characters": "ai",
        "setting": "different",
        "world": "same",
        "description": "Fresh adventures in a consistent magical world"
    },
    "scifi": {
        "label": "Sci-Fi",
        "characters": "ai",
        "setting": "different",
        "world": "different",
        "description": "New characters, settings, and speculative worlds"
    },
    "strange_fables": {
        "label": "Strange Fables",
        "characters": "ai",
        "setting": "different",
        "world": "different",
        "description": "Twist endings, morality tales, anthology-style"
    }
}

# Intensity levels
INTENSITY_LEVELS = {
    1: {"label": "Cozy", "description": "Light, comforting, low stakes"},
    2: {"label": "Light", "description": "Gentle tension, mild conflict"},
    3: {"label": "Moderate", "description": "Balanced drama and calm"},
    4: {"label": "Dramatic", "description": "High stakes, strong emotions"},
    5: {"label": "Intense", "description": "Edge-of-seat tension, heavy themes"}
}

# Story length options (word counts)
STORY_LENGTHS = {
    "short": {"words": 1500, "label": "Quick Read", "tier": "free"},
    "medium": {"words": 3000, "label": "Standard", "tier": "premium"},
    "long": {"words": 4500, "label": "Extended", "tier": "premium"}
}


def get_genre_config(genre: str) -> Dict[str, Any]:
    """Get configuration for a genre, with fallback to defaults."""
    return GENRE_CONFIG.get(genre, {
        "label": genre.title(),
        "characters": "ai",
        "setting": "different",
        "world": "same",
        "description": f"{genre.title()} stories"
    })
from langchain_core.messages import HumanMessage
from langchain_anthropic import ChatAnthropic
from backend.config import config


async def enhance_story_bible(
    genre: str,
    user_setting: str,
    character_pool: list = None,
    user_id: str = None,
    intensity: int = 3,
    story_length: str = "short",
    premise: str = None,
    cameo_pool: list = None,
    beat_structure: str = "classic"
) -> Dict[str, Any]:
    """
    Take minimal user input and expand into a rich story bible.

    Args:
        genre: Genre selected by user (comedy_sitcom, detective, romance, etc.)
        user_setting: User's 1-2 sentence setting description
        character_pool: Optional list of {name, description} for recurring character genres
        user_id: Optional user ID for personalization
        intensity: 1-5 scale (1=cozy, 5=intense)
        story_length: "short" (1500), "medium" (3000), or "long" (4500)
        premise: Optional general premise for AI-generated character genres
        cameo_pool: Optional list of people to include as cameos
        beat_structure: Story structure to use (classic, save_the_cat, heros_journey, truby_beats)

    Returns:
        Enhanced story bible with full details
    """
    genre_cfg = get_genre_config(genre)
    intensity_cfg = INTENSITY_LEVELS.get(intensity, INTENSITY_LEVELS[3])
    length_cfg = STORY_LENGTHS.get(story_length, STORY_LENGTHS["short"])

    # Determine character handling based on genre
    if genre_cfg["characters"] == "user":
        # Build character list from pool
        if character_pool and len(character_pool) > 0:
            char_list = "\n".join([f"- {c['name']}: {c.get('description', 'Main character')}" for c in character_pool])
            character_instruction = f'''The user wants these RECURRING characters to appear in EVERY story:
{char_list}

Expand on these characters with full details (traits, background, voice, etc.). These are the main ensemble cast.'''
        else:
            character_instruction = 'The user wants recurring characters but did not provide names. Create 1-2 memorable main characters with full details.'
    else:
        character_instruction = f'Each story will have FRESH characters generated at story time. Create a CHARACTER TEMPLATE (archetype, typical traits) rather than specific characters.{f" Premise hint: {premise}" if premise else ""}'

    # Build JSON structure based on character type
    if genre_cfg["characters"] == "user" and character_pool:
        character_json = '''"main_characters": [
    {
      "name": "Character from user list",
      "role": "Their role/job",
      "age_range": "Approximate age",
      "key_traits": ["trait1", "trait2", "trait3"],
      "defining_characteristic": "One unique trait that makes them interesting",
      "background": "Brief backstory (2-3 sentences)",
      "motivation": "What drives them",
      "voice": "How they speak/think"
    }
    // Include ALL characters from the user's list, expanding each one
  ],
  "supporting_characters": [
    {
      "name": "Optional supporting cast member",
      "role": "Their role",
      "relationship": "How they relate to main cast",
      "personality": "Brief descriptor",
      "purpose": "Narrative purpose"
    }
  ]'''
    else:
        character_json = '''"character_template": {
    "archetype": "Type of protagonist typical for this genre",
    "role": "Their typical job/position",
    "age_range": "Typical age range",
    "key_traits": ["trait1", "trait2", "trait3"],
    "defining_characteristic": "What makes protagonists interesting",
    "background": "Typical background elements",
    "motivation": "What drives characters",
    "voice": "How they typically speak/think"
  },
  "supporting_cast_template": [
    {
      "role": "Role type (mentor, rival, love interest)",
      "personality": "Typical traits",
      "purpose": "Narrative purpose"
    }
  ]'''

    # Create enhancement prompt
    prompt = f"""You are a creative writing assistant helping to expand a story world.

GENRE: {genre_cfg["label"]}
Genre style: {genre_cfg["description"]}
- Characters: {"Recurring (user-defined)" if genre_cfg["characters"] == "user" else "Fresh each story (AI-generated)"}
- Settings: {"Consistent" if genre_cfg["setting"] == "same" else "Varies each story"}
- World: {"Same universe/rules" if genre_cfg["world"] == "same" else "Can vary"}

INTENSITY: {intensity_cfg["label"]} - {intensity_cfg["description"]}
STORY LENGTH: {length_cfg["label"]} (~{length_cfg["words"]} words)

The user provided this setting/world description:
"{user_setting}"

{character_instruction}

Your task: Expand this minimal input into a rich, detailed story bible that will enable consistent, engaging stories.

Return a JSON object with the following structure:

```json
{{
  "genre": "{genre}",
  "setting": {{
    "name": "Brief name for this world/setting",
    "description": "2-3 detailed paragraphs expanding on the user's setting. Add atmosphere, sensory details, key locations, tone. Make it vivid and specific.",
    "key_locations": [
      {{"name": "Location 1", "description": "Brief description"}},
      {{"name": "Location 2", "description": "Brief description"}}
    ],
    "atmosphere": "The overall mood and feel of this world",
    "rules": "Any important rules of this world (tech level, magic system, social norms, etc.)"
  }},
  {character_json},
  "tone": "The emotional tone matching intensity level: {intensity_cfg["label"]}",
  "themes": ["theme1", "theme2", "theme3"],
  "story_style": "Brief description of what makes these stories distinctive"
}}
```

Guidelines:
1. **Be specific**: "Space station" → "Deep Space Station Aurora, a crumbling research outpost on the edge of charted space"
2. **Match intensity**: {intensity_cfg["label"]} means {intensity_cfg["description"]}
3. **Establish tone**: Match the genre expectations and intensity level
4. {"**Recurring cast**: These characters will appear in every story, so make them memorable" if genre_cfg["characters"] == "user" else "**Character templates**: Provide archetypes that can generate fresh, interesting characters each story"}
5. **Internal consistency**: Everything should fit together logically

Make this feel like a real, lived-in world that can sustain many different stories.
"""

    try:
        # Initialize LLM
        llm = ChatAnthropic(
            model=config.MODEL_NAME,
            temperature=0.8,  # Creative expansion
            max_tokens=3000,
            anthropic_api_key=config.ANTHROPIC_API_KEY,
            timeout=45.0,
        )

        # Get enhancement
        response = await llm.ainvoke([HumanMessage(content=prompt)])
        response_text = response.content.strip()

        # Clean markdown if present
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0].strip()

        # Parse JSON
        enhanced_bible = json.loads(response_text)

        # Add metadata and configuration
        enhanced_bible["user_input"] = {
            "genre": genre,
            "setting": user_setting,
            "character_pool": character_pool,
            "premise": premise
        }

        # Store genre configuration
        enhanced_bible["genre_config"] = {
            "genre_key": genre,
            "label": genre_cfg["label"],
            "characters": genre_cfg["characters"],  # "user" or "ai"
            "setting": genre_cfg["setting"],  # "same" or "different"
            "world": genre_cfg["world"],  # "same" or "different"
        }

        # Store intensity, length, and beat structure settings
        enhanced_bible["story_settings"] = {
            "intensity": intensity,
            "intensity_label": intensity_cfg["label"],
            "story_length": story_length,
            "word_target": length_cfg["words"],
            "beat_structure": beat_structure
        }

        # Also store at top level for easy access
        enhanced_bible["beat_structure"] = beat_structure

        # Add cameo pool if provided
        if cameo_pool:
            enhanced_bible["cameo_characters"] = [
                {
                    "name": c.get("name", ""),
                    "description": c.get("description", ""),
                    "frequency": c.get("frequency", "sometimes"),
                    "appearances": 0
                }
                for c in cameo_pool
            ]

        # Initialize tracking fields
        enhanced_bible["story_history"] = {
            "total_stories": 0,
            "recent_plot_types": [],
            "recent_summaries": [],
            "used_cameos": [],
            "last_cliffhanger": None
        }

        enhanced_bible["user_preferences"] = {
            "ratings": [],
            "liked_elements": [],
            "disliked_elements": [],
            "pacing_preference": "medium",
            "action_level": "medium",
            "emotional_depth": "medium"
        }

        return enhanced_bible

    except json.JSONDecodeError as e:
        error_msg = f"Failed to parse enhanced bible JSON: {e}"
        print(error_msg)
        print(f"Response: {response_text[:500]}")

        # Return minimal fallback with error info
        fallback = create_fallback_bible(genre, user_setting, character_pool, intensity, story_length, beat_structure)
        fallback["_error"] = error_msg
        return fallback

    except Exception as e:
        error_msg = f"Error enhancing bible: {type(e).__name__}: {str(e)}"
        print(error_msg)
        import traceback
        traceback.print_exc()

        # Check if it's an API key issue
        if "api_key" in str(e).lower() or "authentication" in str(e).lower():
            error_msg = "ANTHROPIC_API_KEY not set or invalid. Please add it to Railway environment variables."

        # Return minimal fallback with error info
        fallback = create_fallback_bible(genre, user_setting, character_pool, intensity, story_length, beat_structure)
        fallback["_error"] = error_msg
        return fallback


def create_fallback_bible(
    genre: str,
    user_setting: str,
    character_pool: list = None,
    intensity: int = 3,
    story_length: str = "short",
    beat_structure: str = "classic"
) -> Dict[str, Any]:
    """
    Create a minimal fallback bible if AI enhancement fails.
    """
    genre_cfg = get_genre_config(genre)
    intensity_cfg = INTENSITY_LEVELS.get(intensity, INTENSITY_LEVELS[3])
    length_cfg = STORY_LENGTHS.get(story_length, STORY_LENGTHS["short"])

    bible = {
        "genre": genre,
        "setting": {
            "name": "Your World",
            "description": user_setting,
            "key_locations": [],
            "atmosphere": genre,
            "rules": "Standard genre conventions"
        },
        "supporting_characters": [],
        "tone": intensity_cfg["label"],
        "themes": [genre, "adventure", "discovery"],
        "story_style": f"{genre_cfg['label']} stories in this world",
        "user_input": {
            "genre": genre,
            "setting": user_setting,
            "character_pool": character_pool
        },
        "genre_config": {
            "genre_key": genre,
            "label": genre_cfg["label"],
            "characters": genre_cfg["characters"],
            "setting": genre_cfg["setting"],
            "world": genre_cfg["world"],
        },
        "story_settings": {
            "intensity": intensity,
            "intensity_label": intensity_cfg["label"],
            "story_length": story_length,
            "word_target": length_cfg["words"],
            "beat_structure": beat_structure
        },
        "beat_structure": beat_structure,
        "story_history": {
            "total_stories": 0,
            "recent_plot_types": [],
            "recent_summaries": [],
            "used_cameos": [],
            "last_cliffhanger": None
        },
        "user_preferences": {
            "ratings": [],
            "liked_elements": [],
            "disliked_elements": [],
            "pacing_preference": "medium",
            "action_level": "medium",
            "emotional_depth": "medium"
        }
    }

    # Add characters based on genre type
    if genre_cfg["characters"] == "user" and character_pool:
        bible["main_characters"] = [
            {
                "name": c.get("name", "Character"),
                "role": c.get("description", "Main character"),
                "age_range": "adult",
                "key_traits": ["determined", "curious", "resourceful"],
                "defining_characteristic": "Quick thinking",
                "background": "To be developed",
                "motivation": "Solve problems and help others",
                "voice": "thoughtful"
            }
            for c in character_pool
        ]
    else:
        bible["character_template"] = {
            "archetype": "To be determined",
            "role": "Protagonist",
            "age_range": "adult",
            "key_traits": ["determined", "curious", "resourceful"],
            "defining_characteristic": "Quick thinking",
            "background": "To be developed",
            "motivation": "Solve problems and help others",
            "voice": "thoughtful"
        }

    return bible


def add_cameo_characters(bible: Dict[str, Any], cameos: list[Dict[str, str]]) -> Dict[str, Any]:
    """
    Add cameo characters to an existing bible.

    Args:
        bible: Existing story bible
        cameos: List of cameo character dicts with 'name' and 'description'

    Returns:
        Updated bible with cameos
    """
    if "cameo_characters" not in bible:
        bible["cameo_characters"] = []

    for cameo in cameos:
        bible["cameo_characters"].append({
            "name": cameo.get("name", "Unknown"),
            "description": cameo.get("description", ""),
            "frequency": cameo.get("frequency", "sometimes"),  # rarely, sometimes, often
            "appearances": 0  # Track how many times they've appeared
        })

    return bible


def update_story_history(
    bible: Dict[str, Any],
    story_summary: str,
    plot_type: str,
    rating: int = None,
    feedback: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    Update bible with new story history.

    Args:
        bible: Story bible to update
        story_summary: Brief summary of the story
        plot_type: Type of plot used
        rating: User rating (1-5)
        feedback: User feedback dict

    Returns:
        Updated bible
    """
    history = bible.get("story_history", {})

    # Increment total
    history["total_stories"] = history.get("total_stories", 0) + 1

    # Add to recent summaries (keep last 7)
    summaries = history.get("recent_summaries", [])
    summaries.append(story_summary)
    history["recent_summaries"] = summaries[-7:]

    # Track plot types (keep last 10)
    plots = history.get("recent_plot_types", [])
    plots.append(plot_type)
    history["recent_plot_types"] = plots[-10:]

    bible["story_history"] = history

    # Update preferences if rating provided
    if rating is not None:
        prefs = bible.get("user_preferences", {})
        ratings = prefs.get("ratings", [])
        ratings.append(rating)
        prefs["ratings"] = ratings[-20:]  # Keep last 20 ratings

        # Update preferences based on feedback
        if feedback and rating >= 4:
            # High rating - track what they liked
            liked = prefs.get("liked_elements", [])
            if "great_pacing" in feedback:
                liked.append("fast_pacing")
            if "loved_characters" in feedback:
                liked.append("character_focus")
            if "good_mystery" in feedback:
                liked.append("mystery_elements")
            if "surprising_twist" in feedback:
                liked.append("plot_twists")
            if "emotional_moments" in feedback:
                liked.append("emotional_depth")
            prefs["liked_elements"] = liked[-20:]

        elif feedback and rating <= 2:
            # Low rating - track what they disliked
            disliked = prefs.get("disliked_elements", [])
            if "too_slow" in feedback:
                disliked.append("slow_pacing")
                prefs["pacing_preference"] = "fast"
            if "not_enough_action" in feedback:
                disliked.append("low_action")
                prefs["action_level"] = "high"
            if "characters_felt_off" in feedback:
                disliked.append("character_inconsistency")
            prefs["disliked_elements"] = disliked[-20:]

        bible["user_preferences"] = prefs

    return bible


def should_use_cliffhanger(bible: Dict[str, Any], tier: str) -> bool:
    """
    Determine if this story should end on a cliffhanger (free tier only).

    Pattern: Stories 5, 11, 17, 23 (every 6 after first 4)

    Args:
        bible: Story bible with history
        tier: User tier (free, premium)

    Returns:
        True if should use cliffhanger
    """
    if tier != "free":
        return False

    story_count = bible.get("story_history", {}).get("total_stories", 0)

    # First 4 stories: always complete
    if story_count < 4:
        return False

    # Every 6th story after that: cliffhanger
    return (story_count - 4) % 6 == 0


def should_include_cameo(bible: Dict[str, Any]) -> Dict[str, Any]:
    """
    Decide if a cameo should appear and which one.

    Args:
        bible: Story bible with cameo characters

    Returns:
        Cameo character dict if should include, None otherwise
    """
    import random

    cameos = bible.get("cameo_characters", [])

    if not cameos:
        return None

    # Check each cameo's frequency
    for cameo in cameos:
        frequency = cameo.get("frequency", "sometimes")
        appearances = cameo.get("appearances", 0)

        # Frequency thresholds
        frequencies = {
            "rarely": 0.15,    # ~15% of stories
            "sometimes": 0.3,  # ~30% of stories
            "often": 0.6       # ~60% of stories
        }

        threshold = frequencies.get(frequency, 0.3)

        if random.random() < threshold:
            # Select this cameo
            cameo["appearances"] = appearances + 1
            return cameo

    return None
