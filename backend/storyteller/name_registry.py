"""
Name Registry - Track and manage used character/place names to avoid repetition.

This module prevents the same names from appearing too frequently across stories
by maintaining a registry of recently used names with expiration logic.
"""

import re
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional


# Configuration
NAME_EXPIRY_DAYS = 60  # Names can be reused after this many days
NAME_EXPIRY_GENERATIONS = 30  # Or after this many story generations


def get_used_names(story_bible: Dict[str, Any]) -> Dict[str, List[Dict]]:
    """
    Get the used names registry from the story bible.

    Returns:
        Dict with 'characters' and 'places' lists
    """
    return story_bible.get("used_names", {
        "characters": [],
        "places": []
    })


def add_used_names(
    story_bible: Dict[str, Any],
    character_names: List[str],
    place_names: List[str],
    generation_number: int = None
) -> Dict[str, Any]:
    """
    Add names to the used names registry.

    Args:
        story_bible: The story bible to update
        character_names: List of character names to add
        place_names: List of place names to add
        generation_number: Current story generation number

    Returns:
        Updated story bible
    """
    if "used_names" not in story_bible:
        story_bible["used_names"] = {"characters": [], "places": []}

    used_names = story_bible["used_names"]
    now = datetime.now().isoformat()
    gen_num = generation_number or story_bible.get("story_count", 0)

    # Add character names
    for name in character_names:
        if name and name.strip():
            # Check if already exists, update if so
            existing = next((n for n in used_names["characters"] if n["name"].lower() == name.lower()), None)
            if existing:
                existing["used_at"] = now
                existing["generation_number"] = gen_num
            else:
                used_names["characters"].append({
                    "name": name.strip(),
                    "used_at": now,
                    "generation_number": gen_num
                })

    # Add place names
    for name in place_names:
        if name and name.strip():
            existing = next((n for n in used_names["places"] if n["name"].lower() == name.lower()), None)
            if existing:
                existing["used_at"] = now
                existing["generation_number"] = gen_num
            else:
                used_names["places"].append({
                    "name": name.strip(),
                    "used_at": now,
                    "generation_number": gen_num
                })

    return story_bible


def get_recurring_character_names(story_bible: Dict[str, Any]) -> List[str]:
    """
    Get names of recurring characters that must NEVER be excluded.

    For genres with characters="user" (comedy_sitcom, detective, action),
    the user's character_pool names are recurring and should always appear.

    Args:
        story_bible: Story bible with genre_config and character data

    Returns:
        List of recurring character names (lowercase for comparison)
    """
    genre_config = story_bible.get("genre_config", {})
    if genre_config.get("characters") != "user":
        return []

    recurring = set()

    # From character_pool in user_input
    user_input = story_bible.get("user_input", {})
    for char in user_input.get("character_pool", []) or []:
        if isinstance(char, dict) and char.get("name"):
            recurring.add(char["name"].strip().lower())
        elif isinstance(char, str) and char.strip():
            recurring.add(char.strip().lower())

    # From main_characters (enhanced bible)
    for char in story_bible.get("main_characters", []):
        if isinstance(char, dict) and char.get("name"):
            recurring.add(char["name"].strip().lower())

    # From protagonist
    prot = story_bible.get("protagonist", {})
    if isinstance(prot, dict) and prot.get("name"):
        recurring.add(prot["name"].strip().lower())

    return list(recurring)



def get_excluded_names(
    story_bible: Dict[str, Any],
    current_generation: int = None
) -> Dict[str, List[str]]:
    """
    Get lists of names that should be excluded from new stories.

    Names are excluded if they were used within the expiry window
    (either by days or generation count). Recurring character names
    from the user's character_pool are NEVER excluded.

    Args:
        story_bible: Story bible with used_names
        current_generation: Current story generation number

    Returns:
        Dict with 'characters' and 'places' lists of excluded names
    """
    used_names = get_used_names(story_bible)
    current_gen = current_generation or story_bible.get("story_count", 0)
    now = datetime.now()

    # Get recurring character names that must never be excluded
    recurring_names = get_recurring_character_names(story_bible)

    excluded = {"characters": [], "places": []}

    for category in ["characters", "places"]:
        for entry in used_names.get(category, []):
            name = entry.get("name", "")
            used_at = entry.get("used_at", "")
            gen_num = entry.get("generation_number", 0)

            # Never exclude recurring character names
            if category == "characters" and name.strip().lower() in recurring_names:
                continue

            # Check if within expiry window
            is_expired = False

            # Check by days
            if used_at:
                try:
                    used_date = datetime.fromisoformat(used_at)
                    days_ago = (now - used_date).days
                    if days_ago >= NAME_EXPIRY_DAYS:
                        is_expired = True
                except:
                    pass

            # Check by generation count
            if current_gen - gen_num >= NAME_EXPIRY_GENERATIONS:
                is_expired = True

            # If not expired, exclude this name
            if not is_expired and name:
                excluded[category].append(name)

    return excluded


def format_exclusion_prompt(excluded_names: Dict[str, List[str]]) -> str:
    """
    Format excluded names into a prompt instruction for Claude.

    Args:
        excluded_names: Dict with 'characters' and 'places' lists

    Returns:
        Formatted prompt string, or empty string if no exclusions
    """
    parts = []

    if excluded_names.get("characters"):
        names = ", ".join(excluded_names["characters"][:20])  # Limit to 20
        parts.append(f"Do NOT use these character names (recently used): {names}")

    if excluded_names.get("places"):
        names = ", ".join(excluded_names["places"][:20])
        parts.append(f"Do NOT use these place names (recently used): {names}")

    if parts:
        parts.append("Create fresh, unique names that feel different from these.")
        return "\n".join(parts)

    return ""


def extract_names_from_story(
    beat_plan: Dict[str, Any],
    narrative: str,
    story_bible: Dict[str, Any]
) -> Dict[str, List[str]]:
    """
    Extract character and place names from a generated story.

    Args:
        beat_plan: The beat plan with character info
        narrative: The story narrative text
        story_bible: The story bible for reference

    Returns:
        Dict with 'characters' and 'places' lists
    """
    characters = set()
    places = set()

    # Extract from beat_plan
    if beat_plan:
        # Main character
        if "protagonist" in beat_plan:
            prot = beat_plan["protagonist"]
            if isinstance(prot, dict) and "name" in prot:
                characters.add(prot["name"])
            elif isinstance(prot, str):
                characters.add(prot)

        # Other characters in beats
        for beat in beat_plan.get("beats", []):
            if isinstance(beat, dict):
                # Check for character mentions
                for key in ["characters", "character", "new_character"]:
                    if key in beat:
                        val = beat[key]
                        if isinstance(val, list):
                            characters.update(val)
                        elif isinstance(val, str):
                            characters.add(val)

                # Check for location mentions
                for key in ["location", "setting", "place"]:
                    if key in beat:
                        places.add(beat[key])

    # Extract from story_bible
    if story_bible:
        # Protagonist
        prot = story_bible.get("protagonist", {})
        if isinstance(prot, dict) and prot.get("name"):
            characters.add(prot["name"])

        # Setting/location
        setting = story_bible.get("setting", {})
        if isinstance(setting, dict):
            if setting.get("location"):
                places.add(setting["location"])
            if setting.get("city"):
                places.add(setting["city"])
            if setting.get("neighborhood"):
                places.add(setting["neighborhood"])

    # Extract proper nouns from narrative using simple heuristics
    # Look for capitalized words that might be names
    if narrative:
        # Common title words to skip
        skip_words = {
            "the", "a", "an", "i", "he", "she", "it", "they", "we", "you",
            "chapter", "part", "act", "scene", "monday", "tuesday", "wednesday",
            "thursday", "friday", "saturday", "sunday", "january", "february",
            "march", "april", "may", "june", "july", "august", "september",
            "october", "november", "december", "mr", "mrs", "ms", "dr", "prof"
        }

        # Find potential names (capitalized words not at sentence start)
        sentences = narrative.split('. ')
        for sentence in sentences:
            words = sentence.split()
            for i, word in enumerate(words):
                # Skip first word of sentence (often capitalized anyway)
                if i == 0:
                    continue
                # Check if capitalized
                clean_word = re.sub(r'[^\w]', '', word)
                if clean_word and clean_word[0].isupper() and clean_word.lower() not in skip_words:
                    # Likely a proper noun
                    if len(clean_word) > 2:
                        # Could be character or place - add to characters for now
                        # (better to over-exclude than under-exclude)
                        characters.add(clean_word)

    # Clean up
    characters = {n for n in characters if n and len(n) > 1}
    places = {n for n in places if n and len(n) > 1}

    return {
        "characters": list(characters),
        "places": list(places)
    }


def cleanup_expired_names(story_bible: Dict[str, Any], current_generation: int = None) -> Dict[str, Any]:
    """
    Remove expired names from the registry to keep it clean.

    Args:
        story_bible: Story bible to clean up
        current_generation: Current generation number

    Returns:
        Updated story bible
    """
    if "used_names" not in story_bible:
        return story_bible

    current_gen = current_generation or story_bible.get("story_count", 0)
    now = datetime.now()

    for category in ["characters", "places"]:
        if category in story_bible["used_names"]:
            # Filter to keep only non-expired names
            kept = []
            for entry in story_bible["used_names"][category]:
                used_at = entry.get("used_at", "")
                gen_num = entry.get("generation_number", 0)

                is_expired = False

                # Check by days
                if used_at:
                    try:
                        used_date = datetime.fromisoformat(used_at)
                        if (now - used_date).days >= NAME_EXPIRY_DAYS:
                            is_expired = True
                    except:
                        pass

                # Check by generations
                if current_gen - gen_num >= NAME_EXPIRY_GENERATIONS:
                    is_expired = True

                if not is_expired:
                    kept.append(entry)

            story_bible["used_names"][category] = kept

    return story_bible
