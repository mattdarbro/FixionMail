"""
Cost calculation for story generation.

Calculates estimated costs for:
- Claude API (prose generation)
- Replicate Imagen-3-Fast (cover images)
- ElevenLabs TTS (audio narration)

Pricing as of 2024:
- Claude Sonnet 4: $3/1M input tokens, $15/1M output tokens
- Replicate Imagen-3-Fast: $0.025 per image
- ElevenLabs: ~$0.30 per 1000 characters (varies by plan)
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class CostBreakdown:
    """Detailed cost breakdown for story generation."""

    # Claude API costs
    claude_input_tokens: int = 0
    claude_output_tokens: int = 0
    claude_input_cost: float = 0.0
    claude_output_cost: float = 0.0
    claude_total_cost: float = 0.0

    # Image generation costs
    image_count: int = 0
    image_cost_per_unit: float = 0.025
    image_total_cost: float = 0.0

    # Audio generation costs
    audio_characters: int = 0
    audio_cost_per_1k_chars: float = 0.30
    audio_total_cost: float = 0.0

    # Totals
    total_cost: float = 0.0
    monthly_cost_30_stories: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "claude": {
                "input_tokens": self.claude_input_tokens,
                "output_tokens": self.claude_output_tokens,
                "input_cost": round(self.claude_input_cost, 4),
                "output_cost": round(self.claude_output_cost, 4),
                "total_cost": round(self.claude_total_cost, 4)
            },
            "image": {
                "count": self.image_count,
                "cost_per_image": self.image_cost_per_unit,
                "total_cost": round(self.image_total_cost, 4)
            },
            "audio": {
                "characters": self.audio_characters,
                "cost_per_1k_chars": self.audio_cost_per_1k_chars,
                "total_cost": round(self.audio_total_cost, 4)
            },
            "total_cost": round(self.total_cost, 4),
            "monthly_cost_30_stories": round(self.monthly_cost_30_stories, 2),
            "formatted": {
                "per_story": f"${self.total_cost:.4f}",
                "monthly": f"${self.monthly_cost_30_stories:.2f}"
            }
        }


# Pricing constants (as of 2024)
class Pricing:
    """API pricing constants."""

    # Claude Sonnet 4 pricing per 1M tokens
    CLAUDE_INPUT_PER_1M = 3.00
    CLAUDE_OUTPUT_PER_1M = 15.00

    # Replicate Imagen-3-Fast pricing
    IMAGEN_3_FAST_PER_IMAGE = 0.025

    # ElevenLabs pricing (approximate, varies by plan)
    # Creator plan: ~$0.30 per 1000 characters
    # Pro plan: ~$0.24 per 1000 characters
    ELEVENLABS_PER_1K_CHARS = 0.30

    # Token estimation factors
    # Average tokens per word varies by content type
    TOKENS_PER_WORD_INPUT = 1.3  # Prompts tend to be more structured
    TOKENS_PER_WORD_OUTPUT = 1.2  # Prose tends to be efficient

    # Characters per word (for audio estimation)
    CHARS_PER_WORD = 5.5


def estimate_claude_tokens(
    word_count: int,
    is_input: bool = False,
    include_system_prompt: bool = True
) -> int:
    """
    Estimate token count from word count.

    Args:
        word_count: Number of words
        is_input: True if input tokens, False if output
        include_system_prompt: Include base system prompt overhead

    Returns:
        Estimated token count
    """
    tokens_per_word = (
        Pricing.TOKENS_PER_WORD_INPUT if is_input
        else Pricing.TOKENS_PER_WORD_OUTPUT
    )

    base_tokens = int(word_count * tokens_per_word)

    # Add overhead for system prompts, JSON structure, etc.
    if is_input and include_system_prompt:
        # Beat template (~1500 tokens), story bible (~800 tokens),
        # system prompt (~500 tokens), etc.
        base_tokens += 3000

    return base_tokens


def calculate_story_cost(
    word_target: int,
    include_audio: bool = True,
    include_image: bool = True,
    elevenlabs_plan: str = "creator"
) -> CostBreakdown:
    """
    Calculate estimated cost for generating a single story.

    Args:
        word_target: Target word count (1500, 3000, or 4500)
        include_audio: Whether to generate audio narration
        include_image: Whether to generate cover image
        elevenlabs_plan: ElevenLabs plan for pricing ("creator" or "pro")

    Returns:
        CostBreakdown with detailed cost information
    """
    breakdown = CostBreakdown()

    # === Claude API Costs ===
    # Input: System prompt + bible + beat template + history
    # We estimate ~2000 words of input context
    input_words = 2000
    breakdown.claude_input_tokens = estimate_claude_tokens(input_words, is_input=True)

    # Output: Story prose + JSON structure
    # Story is the word_target, plus ~200 words of JSON metadata
    output_words = word_target + 200
    breakdown.claude_output_tokens = estimate_claude_tokens(output_words, is_input=False)

    # Calculate costs
    breakdown.claude_input_cost = (
        breakdown.claude_input_tokens / 1_000_000 * Pricing.CLAUDE_INPUT_PER_1M
    )
    breakdown.claude_output_cost = (
        breakdown.claude_output_tokens / 1_000_000 * Pricing.CLAUDE_OUTPUT_PER_1M
    )
    breakdown.claude_total_cost = (
        breakdown.claude_input_cost + breakdown.claude_output_cost
    )

    # === Image Generation Costs ===
    if include_image:
        breakdown.image_count = 1
        breakdown.image_cost_per_unit = Pricing.IMAGEN_3_FAST_PER_IMAGE
        breakdown.image_total_cost = breakdown.image_count * breakdown.image_cost_per_unit

    # === Audio Generation Costs ===
    if include_audio:
        # Estimate characters from word count
        breakdown.audio_characters = int(word_target * Pricing.CHARS_PER_WORD)

        # Adjust pricing based on plan
        if elevenlabs_plan == "pro":
            breakdown.audio_cost_per_1k_chars = 0.24
        else:
            breakdown.audio_cost_per_1k_chars = Pricing.ELEVENLABS_PER_1K_CHARS

        breakdown.audio_total_cost = (
            breakdown.audio_characters / 1000 * breakdown.audio_cost_per_1k_chars
        )

    # === Calculate Totals ===
    breakdown.total_cost = (
        breakdown.claude_total_cost +
        breakdown.image_total_cost +
        breakdown.audio_total_cost
    )

    # Monthly cost (assuming 30 stories per month = daily delivery)
    breakdown.monthly_cost_30_stories = breakdown.total_cost * 30

    return breakdown


def get_tier_word_target(tier: str, story_length: str = "short") -> int:
    """
    Get word target based on tier and story length.

    Args:
        tier: User tier ("free" or "premium")
        story_length: Story length setting ("short", "medium", "long")

    Returns:
        Target word count
    """
    if tier == "premium":
        length_map = {
            "short": 1500,
            "medium": 3000,
            "long": 4500
        }
        return length_map.get(story_length, 4500)
    else:
        # Free tier is always short
        return 1500


def estimate_generation_cost(
    tier: str = "free",
    story_length: str = "short",
    include_audio: bool = True,
    include_image: bool = True
) -> Dict[str, Any]:
    """
    High-level function to estimate story generation cost.

    Args:
        tier: User tier ("free" or "premium")
        story_length: Story length ("short", "medium", "long")
        include_audio: Whether to include audio narration
        include_image: Whether to include cover image

    Returns:
        Dictionary with cost breakdown and formatted output
    """
    word_target = get_tier_word_target(tier, story_length)
    breakdown = calculate_story_cost(
        word_target=word_target,
        include_audio=include_audio,
        include_image=include_image
    )

    result = breakdown.to_dict()
    result["settings"] = {
        "tier": tier,
        "story_length": story_length,
        "word_target": word_target,
        "include_audio": include_audio,
        "include_image": include_image
    }

    return result


# === Quick reference costs ===
def get_quick_cost_summary() -> Dict[str, Any]:
    """
    Get a quick summary of costs for all configurations.

    Returns:
        Dictionary with cost summaries for different configurations
    """
    configs = [
        ("free", "short", True, True),
        ("premium", "short", True, True),
        ("premium", "medium", True, True),
        ("premium", "long", True, True),
        ("free", "short", False, False),  # Text only
    ]

    summary = {}
    for tier, length, audio, image in configs:
        key = f"{tier}_{length}"
        if not audio and not image:
            key += "_text_only"

        result = estimate_generation_cost(tier, length, audio, image)
        summary[key] = {
            "per_story": result["total_cost"],
            "monthly_30": result["monthly_cost_30_stories"],
            "formatted_per_story": result["formatted"]["per_story"],
            "formatted_monthly": result["formatted"]["monthly"]
        }

    return summary


if __name__ == "__main__":
    # Print cost summary
    print("\n" + "="*60)
    print("Story Generation Cost Estimates")
    print("="*60)

    summary = get_quick_cost_summary()

    for config, costs in summary.items():
        print(f"\n{config}:")
        print(f"  Per story: {costs['formatted_per_story']}")
        print(f"  Monthly (30 stories): {costs['formatted_monthly']}")

    print("\n" + "="*60)
    print("\nDetailed breakdown for premium long story:")
    detailed = estimate_generation_cost("premium", "long", True, True)

    print(f"\nClaude API:")
    print(f"  Input tokens: {detailed['claude']['input_tokens']:,}")
    print(f"  Output tokens: {detailed['claude']['output_tokens']:,}")
    print(f"  Input cost: ${detailed['claude']['input_cost']:.4f}")
    print(f"  Output cost: ${detailed['claude']['output_cost']:.4f}")

    print(f"\nImage (Replicate Imagen-3-Fast):")
    print(f"  Count: {detailed['image']['count']}")
    print(f"  Cost: ${detailed['image']['total_cost']:.4f}")

    print(f"\nAudio (ElevenLabs):")
    print(f"  Characters: {detailed['audio']['characters']:,}")
    print(f"  Cost: ${detailed['audio']['total_cost']:.4f}")

    print(f"\n{'='*60}")
    print(f"TOTAL per story: ${detailed['total_cost']:.4f}")
    print(f"Monthly (30 stories): ${detailed['monthly_cost_30_stories']:.2f}")
    print("="*60)
