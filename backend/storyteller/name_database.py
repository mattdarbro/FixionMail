"""
Name Database Service - Select and track character names from the curated database.

This module provides culturally-appropriate names from a pre-populated database,
tracking usage to ensure variety across stories.
"""

import os
from typing import Dict, List, Any, Optional, Tuple
from supabase import create_client, Client

# Map story settings/genres to appropriate cultural origins
SETTING_TO_CULTURES = {
    # Geographic settings
    "china": ["chinese"],
    "chinese": ["chinese"],
    "japan": ["japanese"],
    "japanese": ["japanese"],
    "korea": ["korean"],
    "korean": ["korean"],
    "india": ["indian"],
    "indian": ["indian"],
    "middle east": ["arabic", "persian"],
    "arabia": ["arabic"],
    "arabic": ["arabic"],
    "persia": ["persian"],
    "persian": ["persian"],
    "iran": ["persian"],
    "russia": ["slavic"],
    "russian": ["slavic"],
    "eastern europe": ["slavic"],
    "slavic": ["slavic"],
    "germany": ["german"],
    "german": ["german"],
    "france": ["french"],
    "french": ["french"],
    "italy": ["italian"],
    "italian": ["italian"],
    "spain": ["spanish"],
    "spanish": ["spanish"],
    "latin america": ["spanish", "portuguese"],
    "mexico": ["spanish"],
    "brazil": ["portuguese"],
    "portugal": ["portuguese"],
    "portuguese": ["portuguese"],
    "ireland": ["irish"],
    "irish": ["irish"],
    "scotland": ["scottish"],
    "scottish": ["scottish"],
    "scandinavia": ["scandinavian"],
    "scandinavian": ["scandinavian"],
    "nordic": ["scandinavian"],
    "norway": ["scandinavian"],
    "sweden": ["scandinavian"],
    "denmark": ["scandinavian"],
    "greece": ["greek"],
    "greek": ["greek"],
    "africa": ["african"],
    "african": ["african"],
    "nigeria": ["african"],
    "israel": ["hebrew"],
    "jewish": ["hebrew"],
    "hebrew": ["hebrew"],
    # Generic Western settings get diverse Western names
    "america": ["english", "spanish", "irish", "italian", "german"],
    "american": ["english", "spanish", "irish", "italian", "german"],
    "usa": ["english", "spanish", "irish", "italian", "german"],
    "england": ["english", "irish", "scottish"],
    "english": ["english"],
    "britain": ["english", "irish", "scottish"],
    "uk": ["english", "irish", "scottish"],
    "western": ["english", "french", "german", "italian", "spanish", "irish"],
    "europe": ["english", "french", "german", "italian", "spanish", "scandinavian"],
    "european": ["english", "french", "german", "italian", "spanish", "scandinavian"],
}

# Default cultures for generic/fantasy/unspecified settings
DEFAULT_CULTURES = [
    "english", "spanish", "french", "german", "italian", "irish",
    "scandinavian", "slavic", "arabic", "indian", "chinese", "japanese",
    "african", "greek", "portuguese", "korean", "scottish", "persian", "hebrew"
]


def get_supabase_client() -> Client:
    """Get Supabase client for database operations."""
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_KEY")
    if not url or not key:
        raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set")
    return create_client(url, key)


def extract_setting_context(story_bible: Dict[str, Any]) -> List[str]:
    """
    Extract cultural context from story bible setting.

    Looks at various parts of the story bible to determine appropriate
    cultural origins for character names.

    Args:
        story_bible: The story bible configuration

    Returns:
        List of cultural origins to use for name selection
    """
    cultures = set()

    # Check setting/location fields
    setting = story_bible.get("setting", {})
    if isinstance(setting, dict):
        for field in ["location", "city", "country", "region", "culture", "ethnicity"]:
            value = setting.get(field, "")
            if value:
                value_lower = value.lower()
                for key, origins in SETTING_TO_CULTURES.items():
                    if key in value_lower:
                        cultures.update(origins)
    elif isinstance(setting, str):
        setting_lower = setting.lower()
        for key, origins in SETTING_TO_CULTURES.items():
            if key in setting_lower:
                cultures.update(origins)

    # Check genre for cultural hints
    genre = story_bible.get("genre", "")
    if genre:
        genre_lower = genre.lower()
        # Historical genres might specify culture
        if "western" in genre_lower:
            cultures.update(["english", "irish", "german"])
        elif "samurai" in genre_lower or "ninja" in genre_lower:
            cultures.update(["japanese"])
        elif "viking" in genre_lower or "norse" in genre_lower:
            cultures.update(["scandinavian"])
        elif "wuxia" in genre_lower:
            cultures.update(["chinese"])

    # Check theme/world for hints
    theme = story_bible.get("theme", "")
    if theme:
        theme_lower = theme.lower()
        for key, origins in SETTING_TO_CULTURES.items():
            if key in theme_lower:
                cultures.update(origins)

    # Check protagonist for cultural hints
    protagonist = story_bible.get("protagonist", {})
    if isinstance(protagonist, dict):
        for field in ["culture", "ethnicity", "background", "origin"]:
            value = protagonist.get(field, "")
            if value:
                value_lower = value.lower()
                for key, origins in SETTING_TO_CULTURES.items():
                    if key in value_lower:
                        cultures.update(origins)

    # Check character template
    char_template = story_bible.get("character_template", "")
    if char_template:
        template_lower = char_template.lower()
        for key, origins in SETTING_TO_CULTURES.items():
            if key in template_lower:
                cultures.update(origins)

    # If no specific cultures found, use default diverse mix
    if not cultures:
        return DEFAULT_CULTURES

    return list(cultures)


def get_names_from_database(
    name_type: str,
    gender: Optional[str] = None,
    count: int = 1,
    cultural_origins: Optional[List[str]] = None,
    exclude_names: Optional[List[str]] = None
) -> List[Dict[str, Any]]:
    """
    Get names from the character_names database.

    Prioritizes names with lower usage counts for variety.

    Args:
        name_type: 'first' or 'last'
        gender: 'male', 'female', or None for last names
        count: Number of names to return
        cultural_origins: List of cultural origins to filter by (None = all)
        exclude_names: Names to exclude from results

    Returns:
        List of name dictionaries with 'id', 'name', 'cultural_origin'
    """
    try:
        supabase = get_supabase_client()

        # Build query
        query = supabase.table("character_names").select("id, name, cultural_origin, usage_count")

        # Filter by type
        query = query.eq("name_type", name_type)

        # Filter by gender for first names
        if name_type == "first" and gender:
            query = query.or_(f"gender.eq.{gender},gender.eq.neutral")

        # Filter by cultural origins if specified
        if cultural_origins:
            # Create an 'in' filter for cultural origins
            origins_str = ",".join(cultural_origins)
            query = query.in_("cultural_origin", cultural_origins)

        # Order by usage count (ascending) to prefer less-used names
        query = query.order("usage_count", desc=False)
        query = query.order("last_used_at", desc=False, nullsfirst=True)

        # Get more than needed to allow for filtering
        query = query.limit(count * 3)

        result = query.execute()

        if not result.data:
            return []

        # Filter out excluded names
        names = result.data
        if exclude_names:
            exclude_lower = [n.lower() for n in exclude_names]
            names = [n for n in names if n["name"].lower() not in exclude_lower]

        # Return requested count
        return names[:count]

    except Exception as e:
        print(f"Error fetching names from database: {e}")
        return []


def increment_name_usage(name_id: str) -> bool:
    """
    Increment the usage count for a name.

    Args:
        name_id: UUID of the name record

    Returns:
        True if successful, False otherwise
    """
    try:
        supabase = get_supabase_client()

        # Get current count
        result = supabase.table("character_names").select("usage_count").eq("id", name_id).execute()

        if result.data:
            current_count = result.data[0].get("usage_count", 0)

            # Update with incremented count
            supabase.table("character_names").update({
                "usage_count": current_count + 1,
                "last_used_at": "now()"
            }).eq("id", name_id).execute()

            return True
        return False

    except Exception as e:
        print(f"Error incrementing name usage: {e}")
        return False


def increment_name_usage_by_name(
    name: str,
    name_type: str,
    gender: Optional[str] = None
) -> bool:
    """
    Increment usage count by name string.

    Args:
        name: The name string
        name_type: 'first' or 'last'
        gender: 'male', 'female', or None

    Returns:
        True if successful, False otherwise
    """
    try:
        supabase = get_supabase_client()

        # Find the name
        query = supabase.table("character_names").select("id, usage_count").eq("name", name).eq("name_type", name_type)

        if name_type == "first" and gender:
            query = query.or_(f"gender.eq.{gender},gender.eq.neutral")

        result = query.execute()

        if result.data:
            record = result.data[0]
            current_count = record.get("usage_count", 0)

            supabase.table("character_names").update({
                "usage_count": current_count + 1,
                "last_used_at": "now()"
            }).eq("id", record["id"]).execute()

            return True
        return False

    except Exception as e:
        print(f"Error incrementing name usage by name: {e}")
        return False


def select_character_name(
    story_bible: Dict[str, Any],
    gender: str,
    exclude_names: Optional[List[str]] = None
) -> Optional[Tuple[str, str, str]]:
    """
    Select a full character name (first + last) appropriate for the story setting.

    Args:
        story_bible: Story bible for context
        gender: 'male' or 'female'
        exclude_names: Names to exclude

    Returns:
        Tuple of (first_name, last_name, first_name_id) or None if unavailable
    """
    # Get cultural context from story bible
    cultures = extract_setting_context(story_bible)

    # Get first name
    first_names = get_names_from_database(
        name_type="first",
        gender=gender,
        count=1,
        cultural_origins=cultures,
        exclude_names=exclude_names
    )

    if not first_names:
        # Fallback to any culture if no matches
        first_names = get_names_from_database(
            name_type="first",
            gender=gender,
            count=1,
            exclude_names=exclude_names
        )

    if not first_names:
        return None

    first = first_names[0]

    # Get last name, preferring same cultural origin
    first_culture = first.get("cultural_origin")
    last_names = get_names_from_database(
        name_type="last",
        count=1,
        cultural_origins=[first_culture] if first_culture else cultures,
        exclude_names=exclude_names
    )

    if not last_names:
        # Fallback to any culture
        last_names = get_names_from_database(
            name_type="last",
            count=1,
            exclude_names=exclude_names
        )

    if not last_names:
        return (first["name"], "", first["id"])

    last = last_names[0]

    return (first["name"], last["name"], first["id"], last["id"])


def select_multiple_character_names(
    story_bible: Dict[str, Any],
    count: int,
    genders: Optional[List[str]] = None,
    exclude_names: Optional[List[str]] = None
) -> List[Dict[str, str]]:
    """
    Select multiple character names for a story.

    Args:
        story_bible: Story bible for context
        count: Number of names to generate
        genders: List of genders (cycles if shorter than count)
        exclude_names: Names to exclude

    Returns:
        List of dicts with 'first_name', 'last_name', 'full_name', 'gender'
    """
    if genders is None:
        genders = ["male", "female"]  # Alternate

    results = []
    used_names = list(exclude_names) if exclude_names else []

    for i in range(count):
        gender = genders[i % len(genders)]
        result = select_character_name(story_bible, gender, used_names)

        if result:
            if len(result) == 4:
                first, last, first_id, last_id = result
            else:
                first, last, first_id = result
                last_id = None

            full_name = f"{first} {last}".strip()

            results.append({
                "first_name": first,
                "last_name": last,
                "full_name": full_name,
                "gender": gender,
                "first_name_id": first_id,
                "last_name_id": last_id
            })

            # Add to used names to avoid duplicates
            used_names.append(first)
            if last:
                used_names.append(last)

    return results


def mark_names_used(names: List[Dict[str, str]]) -> None:
    """
    Mark a list of selected names as used (increment their usage counts).

    Args:
        names: List of name dicts with 'first_name_id' and 'last_name_id'
    """
    for name_dict in names:
        if name_dict.get("first_name_id"):
            increment_name_usage(name_dict["first_name_id"])
        if name_dict.get("last_name_id"):
            increment_name_usage(name_dict["last_name_id"])


def format_suggested_names_prompt(
    story_bible: Dict[str, Any],
    count: int = 3,
    exclude_names: Optional[List[str]] = None
) -> str:
    """
    Generate a prompt section suggesting character names from the database.

    This provides the AI with pre-selected, culturally-appropriate names
    to use instead of defaulting to common names.

    Args:
        story_bible: Story bible for context
        count: Number of name suggestions
        exclude_names: Names to exclude

    Returns:
        Formatted prompt string with name suggestions
    """
    # Get mix of male and female names
    male_names = select_multiple_character_names(
        story_bible,
        count=(count + 1) // 2,
        genders=["male"],
        exclude_names=exclude_names
    )

    # Update exclude list
    all_exclude = list(exclude_names) if exclude_names else []
    all_exclude.extend([n["first_name"] for n in male_names])
    all_exclude.extend([n["last_name"] for n in male_names if n["last_name"]])

    female_names = select_multiple_character_names(
        story_bible,
        count=count // 2 + 1,
        genders=["female"],
        exclude_names=all_exclude
    )

    if not male_names and not female_names:
        return ""

    # Get cultural context for display
    cultures = extract_setting_context(story_bible)
    culture_note = ""
    if cultures and cultures != DEFAULT_CULTURES:
        culture_note = f" (culturally appropriate for: {', '.join(cultures[:3])})"

    lines = [
        "**SUGGESTED CHARACTER NAMES** (use these instead of making up names):",
        f"These names are pre-selected for variety and cultural fit{culture_note}.",
        ""
    ]

    if male_names:
        lines.append("Male names:")
        for n in male_names:
            lines.append(f"  - {n['full_name']}")

    if female_names:
        lines.append("Female names:")
        for n in female_names:
            lines.append(f"  - {n['full_name']}")

    lines.append("")
    lines.append("Please use names from this list when creating characters.")
    lines.append("If you need additional names, follow the cultural style shown above.")

    return "\n".join(lines)


def get_protagonist_name(
    story_bible: Dict[str, Any],
    gender: str,
    exclude_names: Optional[List[str]] = None
) -> Optional[Dict[str, str]]:
    """
    Get a single protagonist name for a story.

    Args:
        story_bible: Story bible for context
        gender: 'male' or 'female'
        exclude_names: Names to exclude

    Returns:
        Dict with 'first_name', 'last_name', 'full_name' or None
    """
    names = select_multiple_character_names(
        story_bible,
        count=1,
        genders=[gender],
        exclude_names=exclude_names
    )

    if names:
        return names[0]
    return None
