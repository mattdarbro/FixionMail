"""
Main story generation workflow for FixionMail standalone stories.

This orchestrates the 2-agent system for daily story generation:
- WriterAgent (Sonnet/Opus): Generates complete stories
- JudgeAgent (Haiku): Validates quality, triggers rewrites if needed
"""

import time
import json
import asyncio
import os
from typing import Dict, Any, Optional, Literal
from datetime import datetime
from langchain_core.messages import HumanMessage
from langchain_anthropic import ChatAnthropic
from backend.config import config
from backend.storyteller.beat_templates import get_template, get_structure_template
from backend.storyteller.bible_enhancement import should_use_cliffhanger, should_include_cameo
from backend.storyteller.name_registry import (
    get_excluded_names,
    extract_names_from_story,
    add_used_names,
    cleanup_expired_names
)
from backend.agents import WriterAgent, JudgeAgent, WRITER_MODELS

# Type alias for writer model selection
WriterModelType = Literal["sonnet", "opus"]


async def generate_story_audio_openai(
    narrative: str,
    story_title: str,
    genre: str,
    voice: str = "alloy"
) -> str | None:
    """
    Generate TTS audio for a standalone story using OpenAI TTS.

    Args:
        narrative: The story text to narrate
        story_title: Title of the story (for filename)
        genre: Story genre
        voice: OpenAI voice (alloy, echo, fable, onyx, nova, shimmer)

    Returns:
        Local URL path to audio file, or None if generation fails
    """
    try:
        from openai import OpenAI

        if not config.OPENAI_API_KEY:
            print("  ⏭️  OPENAI_API_KEY not set, skipping audio generation")
            return None

        # Clean and prepare text for narration
        narrative_text = narrative.strip()

        # OpenAI TTS supports up to 4096 characters per request
        # We'll chunk and concatenate for longer texts
        MAX_CHUNK_CHARS = 4000

        # Create OpenAI client
        client = OpenAI(api_key=config.OPENAI_API_KEY)

        # Create audio directory if it doesn't exist
        os.makedirs("./generated_audio", exist_ok=True)

        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        clean_title = "".join(c for c in story_title if c.isalnum() or c in (' ', '-', '_')).strip()
        clean_title = clean_title.replace(' ', '_')[:50]
        filename = f"{genre}_{clean_title}_{timestamp}_openai.mp3"
        filepath = f"./generated_audio/{filename}"

        print(f"  Using OpenAI TTS voice: {voice}")
        print(f"  Narrative length: {len(narrative_text)} characters")

        if len(narrative_text) <= MAX_CHUNK_CHARS:
            # Single chunk - simple case
            response = client.audio.speech.create(
                model="tts-1",
                voice=voice,
                input=narrative_text
            )
            response.stream_to_file(filepath)
        else:
            # Multiple chunks - need to concatenate
            print(f"  Text exceeds {MAX_CHUNK_CHARS} chars, chunking...")

            # Split into chunks at sentence boundaries
            chunks = []
            remaining = narrative_text
            while len(remaining) > MAX_CHUNK_CHARS:
                # Find a good break point (end of sentence)
                chunk = remaining[:MAX_CHUNK_CHARS]
                last_period = chunk.rfind('. ')
                if last_period > MAX_CHUNK_CHARS - 500:
                    chunk = remaining[:last_period + 1]
                    remaining = remaining[last_period + 2:]
                else:
                    remaining = remaining[MAX_CHUNK_CHARS:]
                chunks.append(chunk)
            if remaining:
                chunks.append(remaining)

            print(f"  Split into {len(chunks)} chunks")

            # Generate audio for each chunk
            audio_chunks = []
            for i, chunk in enumerate(chunks):
                print(f"  Generating chunk {i + 1}/{len(chunks)}...")
                response = client.audio.speech.create(
                    model="tts-1",
                    voice=voice,
                    input=chunk
                )
                chunk_filepath = f"./generated_audio/temp_chunk_{timestamp}_{i}.mp3"
                response.stream_to_file(chunk_filepath)
                audio_chunks.append(chunk_filepath)

            # Concatenate audio chunks
            print(f"  Concatenating {len(audio_chunks)} audio chunks...")
            import subprocess
            import shutil

            # Check if ffmpeg is available
            ffmpeg_available = shutil.which('ffmpeg') is not None

            if ffmpeg_available:
                # Use ffmpeg for high-quality concatenation
                print(f"  Using ffmpeg for concatenation...")

                # Create a file list for ffmpeg
                list_file = f"./generated_audio/concat_list_{timestamp}.txt"
                with open(list_file, 'w') as f:
                    for chunk_file in audio_chunks:
                        f.write(f"file '{os.path.basename(chunk_file)}'\n")

                # Run ffmpeg concat - use basenames since we run from generated_audio dir
                list_basename = os.path.basename(list_file)
                output_basename = os.path.basename(filepath)

                ffmpeg_cmd = [
                    'ffmpeg',
                    '-f', 'concat',
                    '-safe', '0',
                    '-i', list_basename,
                    '-c', 'copy',
                    '-y',
                    output_basename
                ]

                print(f"  Running ffmpeg: {' '.join(ffmpeg_cmd)}")

                result = subprocess.run(
                    ffmpeg_cmd,
                    capture_output=True,
                    text=True,
                    cwd="./generated_audio"
                )

                # Clean up list file
                os.remove(list_file)

                if result.returncode != 0:
                    print(f"  ⚠️  ffmpeg concat error: {result.stderr}")
                    # Fall through to binary concat as backup
                    ffmpeg_available = False
                else:
                    print(f"  ✓ Successfully concatenated {len(audio_chunks)} chunks with ffmpeg")

            if not ffmpeg_available:
                # Fallback: Simple binary concatenation (works for MP3 frame-based format)
                print(f"  Using binary concatenation (ffmpeg not available)...")

                with open(filepath, 'wb') as outfile:
                    for chunk_file in audio_chunks:
                        with open(chunk_file, 'rb') as infile:
                            outfile.write(infile.read())

                print(f"  ✓ Successfully concatenated {len(audio_chunks)} chunks (binary)")

            # Clean up temp chunk files
            for chunk_file in audio_chunks:
                if os.path.exists(chunk_file):
                    os.remove(chunk_file)

        # Upload to storage backend (Supabase in prod, local in dev)
        from backend.storage import upload_audio
        public_url = upload_audio(filepath, filename)

        print(f"  ✓ Audio generated successfully (OpenAI TTS)")
        print(f"    Saved to: {filepath}")
        print(f"    Public URL: {public_url}")
        return public_url

    except Exception as e:
        error_msg = str(e)
        print(f"  ⚠️  OpenAI audio generation failed: {error_msg}")

        if "401" in error_msg or "unauthorized" in error_msg.lower():
            print("  ⚠️  OpenAI API authentication failed. Check OPENAI_API_KEY.")
        elif "429" in error_msg or "rate" in error_msg.lower():
            print("  ⚠️  OpenAI API rate limit exceeded.")

        return None


# TTS Provider routing
TTS_PROVIDERS = {
    "openai": {
        "name": "OpenAI TTS",
        "function": "generate_story_audio_openai",
        "voices": {
            "alloy": "alloy",
            "echo": "echo",
            "fable": "fable",
            "onyx": "onyx",
            "nova": "nova",
            "shimmer": "shimmer"
        },
        "default_voice": "alloy"
    }
}


async def generate_story_audio_with_provider(
    narrative: str,
    story_title: str,
    genre: str,
    provider: str = "openai",
    voice: str = None
) -> str | None:
    """
    Route audio generation to the appropriate TTS provider.

    Args:
        narrative: The story text to narrate
        story_title: Title of the story (for filename)
        genre: Story genre
        provider: TTS provider (currently only "openai" is supported)
        voice: Voice name/ID (optional, uses default for provider)

    Returns:
        Local URL path to audio file, or None if generation fails
    """
    provider_info = TTS_PROVIDERS.get(provider, TTS_PROVIDERS["openai"])
    print(f"  Using TTS provider: {provider_info['name']}")

    # Get voice ID
    if voice:
        voice_id = provider_info["voices"].get(voice, voice)
    else:
        default_voice_key = provider_info["default_voice"]
        voice_id = provider_info["voices"].get(default_voice_key, default_voice_key)

    return await generate_story_audio_openai(
        narrative=narrative,
        story_title=story_title,
        genre=genre,
        voice=voice_id
    )


async def generate_story_image(
    story_title: str,
    beat_plan: Dict[str, Any],
    genre: str
) -> str | None:
    """
    Generate cover image for a standalone story using Replicate.

    Args:
        story_title: Title of the story
        beat_plan: The beat plan with story details
        genre: Story genre

    Returns:
        Local URL path to image file, or None if generation fails
    """
    try:
        import replicate
        import httpx

        if not config.REPLICATE_API_TOKEN:
            print("  ⏭️  REPLICATE_API_TOKEN not set, skipping image generation")
            return None

        # Create image prompt from story details
        story_premise = beat_plan.get("story_premise", "")
        thematic_focus = beat_plan.get("thematic_focus", "")

        # Build a descriptive prompt WITHOUT text (to avoid gibberish letters)
        base_prompt = f"{genre} story cover art, {story_premise}, atmospheric scene"
        enhanced_prompt = f"{base_prompt}, cinematic lighting, high quality, detailed, professional illustration, no text, no letters, no words"

        print(f"  Image prompt: {enhanced_prompt[:100]}...")

        # Create client
        client = replicate.Client(api_token=config.REPLICATE_API_TOKEN)

        # Use Google Imagen-3-Fast model (fast, reliable, $0.025/image)
        model = "google/imagen-3-fast"

        # Run image generation
        input_params = {
            "prompt": enhanced_prompt,
            "aspect_ratio": "1:1",
            "output_format": "png",
            "safety_filter_level": "block_only_high"
        }

        print(f"  Generating image with Google Imagen-3-Fast...")
        output = await client.async_run(model, input=input_params)

        # Handle output - Imagen-3-Fast returns a single FileOutput object
        if isinstance(output, list):
            replicate_output = output[0] if output else None
        else:
            replicate_output = output

        if not replicate_output:
            raise Exception("No image URL returned from Replicate")

        replicate_url = str(replicate_output)
        print(f"  ✓ Image generated by Google Imagen-3-Fast")

        # Download and save image locally
        os.makedirs("./generated_images", exist_ok=True)

        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        # Clean title for filename
        clean_title = "".join(c for c in story_title if c.isalnum() or c in (' ', '-', '_')).strip()
        clean_title = clean_title.replace(' ', '_')[:50]
        filename = f"{genre}_{clean_title}_{timestamp}.png"
        filepath = f"./generated_images/{filename}"

        # Download image from Replicate
        print(f"  Downloading image from Replicate...")
        async with httpx.AsyncClient() as http_client:
            response = await http_client.get(replicate_url)
            response.raise_for_status()

            # Save to local file
            with open(filepath, "wb") as f:
                f.write(response.content)

        # Upload to storage backend (Supabase in prod, local in dev)
        from backend.storage import upload_image
        public_url = upload_image(filepath, filename)

        print(f"  ✓ Image saved locally: {filepath}")
        print(f"    Public URL: {public_url}")

        return public_url

    except Exception as e:
        error_msg = str(e)
        print(f"  ⚠️  Image generation failed: {error_msg}")

        if "401" in error_msg or "unauthorized" in error_msg.lower():
            print("  ⚠️  Replicate API authentication failed. Check REPLICATE_API_TOKEN.")
        elif "404" in error_msg:
            print(f"  ⚠️  Invalid Replicate model.")

        return None


async def generate_standalone_story(
    story_bible: Dict[str, Any],
    user_tier: str = "free",
    force_cliffhanger: bool = None,
    dev_mode: bool = False,
    voice_id: Optional[str] = None,
    tts_provider: str = "openai",
    tts_voice: Optional[str] = None,
    writer_model: WriterModelType = "sonnet"
) -> Dict[str, Any]:
    """
    Generate a complete standalone story using the 2-agent system.

    Flow:
    1. Select beat template based on genre and tier
    2. Determine if cliffhanger/cameo
    3. WRITER: Generate complete story (Sonnet or Opus)
    4. JUDGE: Validate quality (Haiku)
    5. If fail: Writer rewrites with feedback (max 1 retry)
    6. Generate media (image, audio)
    7. Post-process: Extract summary, update bible

    Args:
        story_bible: Enhanced story bible
        user_tier: User's tier (free, premium)
        force_cliffhanger: Override cliffhanger logic (for dev mode)
        dev_mode: Enable dev mode features
        voice_id: Legacy parameter (deprecated, ignored)
        tts_provider: TTS provider (currently only "openai" is supported)
        tts_voice: Voice name for selected provider
        writer_model: Writer model - "sonnet" (default) or "opus" (premium)

    Returns:
        Dict with generated story and metadata
    """
    start_time = time.time()

    # Get writer model info
    model_info = WRITER_MODELS.get(writer_model, WRITER_MODELS["sonnet"])

    print(f"\n{'='*70}")
    print(f"GENERATING STANDALONE STORY (2-Agent System)")
    print(f"Genre: {story_bible.get('genre', 'N/A')}")
    print(f"Tier: {user_tier}")
    print(f"Writer Model: {model_info['name']} ({model_info['cost_tier']})")
    print(f"{'='*70}")

    try:
        # Step 1: Select beat template
        genre = story_bible.get("genre", "scifi")
        beat_structure = story_bible.get("beat_structure", "classic")

        # Check if using a named story structure (Save the Cat, Hero's Journey, etc.)
        if beat_structure and beat_structure != "classic":
            template = get_structure_template(beat_structure, user_tier)
            if template:
                print(f"\n✓ Using story structure: {beat_structure}")
            else:
                # Fallback to genre template if structure not found
                template = get_template(genre, user_tier)
                print(f"\n✓ Structure '{beat_structure}' not found, using genre template")
        else:
            # Use classic genre-specific template
            template = get_template(genre, user_tier)
            print(f"\n✓ Using classic genre template")

        # Override word count if specified in story_settings
        story_settings = story_bible.get("story_settings", {})
        word_target = story_settings.get("word_target")
        if word_target:
            template.total_words = word_target
            print(f"  Template: {template.name}")
            print(f"  Word target (from settings): {word_target}")
        else:
            print(f"  Template: {template.name}")
            print(f"  Total words: {template.total_words}")
        print(f"  Beats: {len(template.beats)}")

        # Step 2: Determine cliffhanger (free tier only)
        if force_cliffhanger is not None:
            is_cliffhanger = force_cliffhanger
        else:
            is_cliffhanger = should_use_cliffhanger(story_bible, user_tier)

        if is_cliffhanger:
            print(f"  📌 Will use cliffhanger ending (free tier)")

        # Step 3: Determine cameo (always include in dev mode)
        cameo = should_include_cameo(story_bible, dev_mode=dev_mode)
        if cameo:
            print(f"  ✨ Including cameo: {cameo.get('name', 'N/A')}")

        # Step 3.5: Get excluded names (avoid repetition)
        excluded_names = get_excluded_names(story_bible)
        if excluded_names.get("characters") or excluded_names.get("places"):
            print(f"  🚫 Excluding {len(excluded_names.get('characters', []))} character names, {len(excluded_names.get('places', []))} place names")

        # Step 4: WRITER - Generate complete story
        print(f"\n{'─'*70}")
        print(f"WRITER: GENERATING STORY ({model_info['name']})")
        print(f"{'─'*70}")

        writer = WriterAgent(model=writer_model)
        judge = JudgeAgent()

        # First attempt
        writer_result = await writer.generate(
            story_bible=story_bible,
            beat_template=template.to_dict(),
            is_cliffhanger=is_cliffhanger,
            cameo=cameo,
            user_preferences=story_bible.get("user_preferences"),
            excluded_names=excluded_names
        )

        if not writer_result.success:
            raise Exception(f"Writer failed: {writer_result.error}")

        print(f"\n✓ Story generated")
        print(f"  Title: {writer_result.title}")
        print(f"  Word count: {writer_result.word_count}")
        print(f"  Time: {writer_result.generation_time:.2f}s")

        # Step 5: JUDGE - Validate story
        print(f"\n{'─'*70}")
        print(f"JUDGE: VALIDATING STORY (Haiku)")
        print(f"{'─'*70}")

        judge_result = await judge.validate(
            narrative=writer_result.narrative,
            title=writer_result.title,
            story_bible=story_bible,
            beat_template=template.to_dict(),
            is_cliffhanger=is_cliffhanger
        )

        print(f"\n✓ Validation complete")
        print(f"  Passed: {judge_result.passed}")
        print(f"  Overall score: {judge_result.overall_score}/10")
        if judge_result.scores:
            for criterion, score in judge_result.scores.items():
                print(f"    {criterion}: {score}/10")

        # Step 6: Rewrite if needed (max 1 retry)
        story_title = writer_result.title
        narrative = writer_result.narrative
        word_count = writer_result.word_count

        if not judge_result.passed and judge_result.feedback:
            print(f"\n{'─'*70}")
            print(f"WRITER: REWRITING WITH FEEDBACK")
            print(f"{'─'*70}")
            print(f"  Feedback: {judge_result.feedback[:100]}...")

            # Rewrite with Judge's feedback
            rewrite_result = await writer.generate(
                story_bible=story_bible,
                beat_template=template.to_dict(),
                is_cliffhanger=is_cliffhanger,
                cameo=cameo,
                user_preferences=story_bible.get("user_preferences"),
                excluded_names=excluded_names,
                judge_feedback=judge_result.feedback
            )

            if rewrite_result.success:
                print(f"\n✓ Rewrite complete")
                print(f"  Word count: {rewrite_result.word_count}")
                print(f"  Time: {rewrite_result.generation_time:.2f}s")

                story_title = rewrite_result.title
                narrative = rewrite_result.narrative
                word_count = rewrite_result.word_count
            else:
                print(f"\n⚠️  Rewrite failed, using original story")

        print(f"\n✓ Final story ready")
        print(f"  Word count: {word_count}")
        print(f"  Target: {template.total_words} (±15%)")

        # Step 7: Generate cover image
        # In dev mode, ALWAYS generate for both free and premium (for testing)
        # In production, only generate for premium
        should_generate_media = dev_mode or user_tier == "premium"

        cover_image_url = None
        if should_generate_media:
            print(f"\n{'─'*70}")
            print(f"GENERATING COVER IMAGE")
            if dev_mode:
                print(f"(Dev mode: generating for {user_tier} tier)")
            print(f"{'─'*70}")

            cover_image_url = await generate_story_image(
                story_title=story_title,
                beat_plan=beat_plan,
                genre=genre
            )

        # Step 8: Generate audio (TTS)
        # In dev mode, ALWAYS generate for both free and premium (for testing)
        # In production, only generate for premium
        audio_url = None
        if should_generate_media:
            print(f"\n{'─'*70}")
            print(f"GENERATING AUDIO (TTS)")
            if dev_mode:
                print(f"(Dev mode: generating for {user_tier} tier)")
            print(f"{'─'*70}")

            audio_url = await generate_story_audio_with_provider(
                narrative=narrative,
                story_title=story_title,
                genre=genre,
                provider=tts_provider,
                voice=tts_voice
            )

        # Step 9: Create summary
        summary = f"{story_title}: {writer_result.story_premise or 'A story in this world'}"

        # Step 10: Extract and save used names (to avoid repetition in future stories)
        # Create a minimal beat_plan dict for name extraction compatibility
        beat_plan_compat = {
            "story_title": story_title,
            "story_premise": writer_result.story_premise,
            "plot_type": writer_result.plot_type
        }
        extracted = extract_names_from_story(beat_plan_compat, narrative, story_bible)
        if extracted.get("characters") or extracted.get("places"):
            story_bible = add_used_names(
                story_bible,
                character_names=extracted.get("characters", []),
                place_names=extracted.get("places", [])
            )
            # Clean up expired names
            story_bible = cleanup_expired_names(story_bible)
            print(f"\n  📝 Saved {len(extracted.get('characters', []))} character names, {len(extracted.get('places', []))} place names to registry")

        # Calculate total time
        total_time = time.time() - start_time

        print(f"\n{'='*70}")
        print(f"STORY GENERATION COMPLETE (2-Agent System)")
        print(f"Total time: {total_time:.2f}s")
        print(f"{'='*70}")

        return {
            "success": True,
            "story": {
                "title": story_title,
                "narrative": narrative,
                "word_count": word_count,
                "genre": genre,
                "tier": user_tier,
                "is_cliffhanger": is_cliffhanger,
                "cover_image_url": cover_image_url,
                "audio_url": audio_url,
                "audio_duration_seconds": None  # TODO: calculate from audio
            },
            "metadata": {
                "plot_type": writer_result.plot_type,
                "summary": summary,
                "judge_scores": judge_result.scores,
                "judge_passed": judge_result.passed,
                "generation_time_seconds": total_time,
                "writer_time_seconds": writer_result.generation_time,
                "writer_model": writer_result.model_used,
                "writer_model_name": model_info["name"],
                "judge_time_seconds": judge_result.validation_time,
                "template_used": template.name,
                "tts_provider": tts_provider
            },
            "updated_bible": story_bible  # Contains updated used_names registry
        }

    except Exception as e:
        print(f"\n❌ Error generating story: {e}")
        import traceback
        traceback.print_exc()

        return {
            "success": False,
            "error": str(e),
            "story": None,
            "metadata": {}
        }


# Old 3-agent functions (generate_beat_plan, check_consistency_simplified, generate_prose)
# have been replaced by the 2-agent system (WriterAgent + JudgeAgent)
# See backend/agents/ for the new implementation
