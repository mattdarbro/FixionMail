"""
Cost calculation for story generation (2-Agent System).

Calculates estimated costs for:
- Claude Sonnet (Writer agent - story generation)
- Claude Haiku (Judge agent - validation)
- Replicate Imagen-3-Fast (cover images)
- OpenAI TTS (audio narration)

Pricing as of 2024:
- Claude Sonnet 4: $3/1M input tokens, $15/1M output tokens
- Claude Haiku 3.5: $1/1M input tokens, $5/1M output tokens
- Replicate Imagen-3-Fast: $0.025 per image
- OpenAI TTS: $0.015 per 1000 characters
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class CostBreakdown:
    """Detailed cost breakdown for story generation (2-Agent System)."""

    # Writer Agent (Sonnet) costs
    writer_input_tokens: int = 0
    writer_output_tokens: int = 0
    writer_input_cost: float = 0.0
    writer_output_cost: float = 0.0
    writer_total_cost: float = 0.0

    # Judge Agent (Haiku) costs
    judge_input_tokens: int = 0
    judge_output_tokens: int = 0
    judge_input_cost: float = 0.0
    judge_output_cost: float = 0.0
    judge_total_cost: float = 0.0

    # Combined Claude costs
    claude_total_cost: float = 0.0

    # Image generation costs
    image_count: int = 0
    image_cost_per_unit: float = 0.025
    image_total_cost: float = 0.0

    # Audio generation costs
    audio_characters: int = 0
    audio_cost_per_1k_chars: float = 0.015  # OpenAI TTS
    audio_total_cost: float = 0.0

    # Totals
    total_cost: float = 0.0
    monthly_cost_30_stories: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        # Variable costs = Claude + Image (per story)
        variable_cost = self.claude_total_cost + self.image_total_cost

        return {
            "writer": {
                "model": "claude-sonnet-4",
                "input_tokens": self.writer_input_tokens,
                "output_tokens": self.writer_output_tokens,
                "input_cost": round(self.writer_input_cost, 4),
                "output_cost": round(self.writer_output_cost, 4),
                "total_cost": round(self.writer_total_cost, 4)
            },
            "judge": {
                "model": "claude-haiku-3.5",
                "input_tokens": self.judge_input_tokens,
                "output_tokens": self.judge_output_tokens,
                "input_cost": round(self.judge_input_cost, 4),
                "output_cost": round(self.judge_output_cost, 4),
                "total_cost": round(self.judge_total_cost, 4)
            },
            "claude_total": round(self.claude_total_cost, 4),
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
            "variable_cost_per_story": round(variable_cost, 4),
            "variable_cost_monthly": round(variable_cost * 30, 2),
            "formatted": {
                "per_story": f"${self.total_cost:.4f}",
                "monthly": f"${self.monthly_cost_30_stories:.2f}",
                "variable_per_story": f"${variable_cost:.4f}",
                "variable_monthly": f"${variable_cost * 30:.2f}"
            }
        }


# Pricing constants (as of 2024)
class Pricing:
    """API pricing constants."""

    # Claude Sonnet 4 pricing per 1M tokens (Writer agent)
    SONNET_INPUT_PER_1M = 3.00
    SONNET_OUTPUT_PER_1M = 15.00

    # Claude Haiku 3.5 pricing per 1M tokens (Judge agent)
    HAIKU_INPUT_PER_1M = 1.00
    HAIKU_OUTPUT_PER_1M = 5.00

    # Legacy aliases for backwards compatibility
    CLAUDE_INPUT_PER_1M = SONNET_INPUT_PER_1M
    CLAUDE_OUTPUT_PER_1M = SONNET_OUTPUT_PER_1M

    # Replicate Imagen-3-Fast pricing
    IMAGEN_3_FAST_PER_IMAGE = 0.025

    # OpenAI TTS pricing (pay-as-you-go)
    # TTS-1 (standard): $0.015 per 1,000 characters
    # TTS-1-HD (high quality): $0.030 per 1,000 characters
    OPENAI_TTS_PER_1K_CHARS = 0.015  # TTS-1 standard
    OPENAI_TTS_HD_PER_1K_CHARS = 0.030  # TTS-1-HD

    # TTS Provider configurations
    TTS_PROVIDERS = {
        "openai": {
            "name": "OpenAI TTS",
            "per_1k_chars": 0.015,
            "monthly_subscription": 0,
            "is_subscription": False,
            "quality": "good",
            "notes": "Pay-per-use, good quality"
        }
    }

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
    tts_provider: str = "openai"
) -> CostBreakdown:
    """
    Calculate estimated cost for generating a single story using 2-agent system.

    Args:
        word_target: Target word count (1500 or 3000)
        include_audio: Whether to generate audio narration
        include_image: Whether to generate cover image
        tts_provider: TTS provider (currently only "openai" is supported)

    Returns:
        CostBreakdown with detailed cost information
    """
    breakdown = CostBreakdown()

    # === Writer Agent (Sonnet) Costs ===
    # Input: System prompt + bible + beat template + history (~2000 words)
    writer_input_words = 2000
    breakdown.writer_input_tokens = estimate_claude_tokens(writer_input_words, is_input=True)

    # Output: Story prose + JSON structure (word_target + ~200 words JSON)
    writer_output_words = word_target + 200
    breakdown.writer_output_tokens = estimate_claude_tokens(writer_output_words, is_input=False)

    # Calculate Writer costs (Sonnet pricing)
    breakdown.writer_input_cost = (
        breakdown.writer_input_tokens / 1_000_000 * Pricing.SONNET_INPUT_PER_1M
    )
    breakdown.writer_output_cost = (
        breakdown.writer_output_tokens / 1_000_000 * Pricing.SONNET_OUTPUT_PER_1M
    )
    breakdown.writer_total_cost = (
        breakdown.writer_input_cost + breakdown.writer_output_cost
    )

    # === Judge Agent (Haiku) Costs ===
    # Input: Story text + requirements (~word_target + 500 words context)
    judge_input_words = word_target + 500
    breakdown.judge_input_tokens = estimate_claude_tokens(judge_input_words, is_input=True, include_system_prompt=False)

    # Output: Validation JSON (~200 words)
    judge_output_words = 200
    breakdown.judge_output_tokens = estimate_claude_tokens(judge_output_words, is_input=False)

    # Calculate Judge costs (Haiku pricing)
    breakdown.judge_input_cost = (
        breakdown.judge_input_tokens / 1_000_000 * Pricing.HAIKU_INPUT_PER_1M
    )
    breakdown.judge_output_cost = (
        breakdown.judge_output_tokens / 1_000_000 * Pricing.HAIKU_OUTPUT_PER_1M
    )
    breakdown.judge_total_cost = (
        breakdown.judge_input_cost + breakdown.judge_output_cost
    )

    # Combined Claude costs
    breakdown.claude_total_cost = breakdown.writer_total_cost + breakdown.judge_total_cost

    # === Image Generation Costs ===
    if include_image:
        breakdown.image_count = 1
        breakdown.image_cost_per_unit = Pricing.IMAGEN_3_FAST_PER_IMAGE
        breakdown.image_total_cost = breakdown.image_count * breakdown.image_cost_per_unit

    # === Audio Generation Costs ===
    if include_audio:
        # Estimate characters from word count
        breakdown.audio_characters = int(word_target * Pricing.CHARS_PER_WORD)

        # Get pricing based on TTS provider (default to OpenAI)
        breakdown.audio_cost_per_1k_chars = Pricing.OPENAI_TTS_PER_1K_CHARS

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
            "medium": 3000
        }
        return length_map.get(story_length, 3000)
    else:
        # Free tier is always short
        return 1500


def estimate_generation_cost(
    tier: str = "free",
    story_length: str = "short",
    include_audio: bool = True,
    include_image: bool = True,
    tts_provider: str = "openai"
) -> Dict[str, Any]:
    """
    High-level function to estimate story generation cost.

    Args:
        tier: User tier ("free" or "premium")
        story_length: Story length ("short" or "medium")
        include_audio: Whether to include audio narration
        include_image: Whether to include cover image
        tts_provider: TTS provider (currently only "openai" is supported)

    Returns:
        Dictionary with cost breakdown and formatted output
    """
    word_target = get_tier_word_target(tier, story_length)
    breakdown = calculate_story_cost(
        word_target=word_target,
        include_audio=include_audio,
        include_image=include_image,
        tts_provider=tts_provider
    )

    # Get provider info
    provider_info = Pricing.TTS_PROVIDERS.get(tts_provider, Pricing.TTS_PROVIDERS["openai"])

    result = breakdown.to_dict()
    result["settings"] = {
        "tier": tier,
        "story_length": story_length,
        "word_target": word_target,
        "include_audio": include_audio,
        "include_image": include_image,
        "tts_provider": tts_provider
    }
    result["tts_provider_info"] = provider_info

    return result


def get_tts_providers() -> Dict[str, Any]:
    """
    Get information about available TTS providers.

    Returns:
        Dictionary with TTS provider configurations
    """
    return Pricing.TTS_PROVIDERS


def compare_tts_providers(word_target: int = 1500) -> Dict[str, Any]:
    """
    Compare costs across all TTS providers for a given word target.

    Args:
        word_target: Target word count for comparison

    Returns:
        Dictionary with cost comparisons for each provider
    """
    char_count = int(word_target * Pricing.CHARS_PER_WORD)

    comparisons = {}
    for provider_id, provider_info in Pricing.TTS_PROVIDERS.items():
        per_story_cost = char_count / 1000 * provider_info["per_1k_chars"]
        monthly_cost = per_story_cost * 30  # 30 stories per month
        monthly_total = monthly_cost + provider_info["monthly_subscription"]

        comparisons[provider_id] = {
            "name": provider_info["name"],
            "per_story_audio": round(per_story_cost, 4),
            "monthly_audio_30_stories": round(monthly_cost, 2),
            "monthly_subscription": provider_info["monthly_subscription"],
            "monthly_total": round(monthly_total, 2),
            "quality": provider_info["quality"],
            "notes": provider_info["notes"],
            "is_subscription": provider_info["is_subscription"],
            "formatted": {
                "per_story": f"${per_story_cost:.4f}",
                "monthly_audio": f"${monthly_cost:.2f}",
                "monthly_subscription": f"${provider_info['monthly_subscription']:.2f}",
                "monthly_total": f"${monthly_total:.2f}"
            }
        }

    return {
        "word_target": word_target,
        "character_count": char_count,
        "providers": comparisons
    }


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
    print("Story Generation Cost Estimates (2-Agent System)")
    print("="*60)

    summary = get_quick_cost_summary()

    for config, costs in summary.items():
        print(f"\n{config}:")
        print(f"  Per story: {costs['formatted_per_story']}")
        print(f"  Monthly (30 stories): {costs['formatted_monthly']}")

    print("\n" + "="*60)
    print("\nDetailed breakdown for premium medium story:")
    detailed = estimate_generation_cost("premium", "medium", True, True)

    print(f"\nWriter Agent (Sonnet):")
    print(f"  Input tokens: {detailed['writer']['input_tokens']:,}")
    print(f"  Output tokens: {detailed['writer']['output_tokens']:,}")
    print(f"  Input cost: ${detailed['writer']['input_cost']:.4f}")
    print(f"  Output cost: ${detailed['writer']['output_cost']:.4f}")
    print(f"  Total: ${detailed['writer']['total_cost']:.4f}")

    print(f"\nJudge Agent (Haiku):")
    print(f"  Input tokens: {detailed['judge']['input_tokens']:,}")
    print(f"  Output tokens: {detailed['judge']['output_tokens']:,}")
    print(f"  Input cost: ${detailed['judge']['input_cost']:.4f}")
    print(f"  Output cost: ${detailed['judge']['output_cost']:.4f}")
    print(f"  Total: ${detailed['judge']['total_cost']:.4f}")

    print(f"\nClaude Total: ${detailed['claude_total']:.4f}")

    print(f"\nImage (Replicate Imagen-3-Fast):")
    print(f"  Count: {detailed['image']['count']}")
    print(f"  Cost: ${detailed['image']['total_cost']:.4f}")

    print(f"\nAudio (OpenAI TTS):")
    print(f"  Characters: {detailed['audio']['characters']:,}")
    print(f"  Cost: ${detailed['audio']['total_cost']:.4f}")

    print(f"\n{'='*60}")
    print(f"TOTAL per story: ${detailed['total_cost']:.4f}")
    print(f"Monthly (30 stories): ${detailed['monthly_cost_30_stories']:.2f}")
    print("="*60)
