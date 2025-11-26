"""
Main story generation workflow for FixionMail standalone stories.

This orchestrates the multi-agent system for daily story generation.
"""

import time
import json
import asyncio
import os
from typing import Dict, Any, Optional
from datetime import datetime
from langchain_core.messages import HumanMessage
from langchain_anthropic import ChatAnthropic
from backend.config import config
from backend.storyteller.beat_templates import get_template, get_structure_template
from backend.storyteller.bible_enhancement import should_use_cliffhanger, should_include_cameo
from backend.storyteller.prompts_standalone import (
    create_standalone_story_beat_prompt,
    create_prose_generation_prompt
)


async def generate_story_audio(
    narrative: str,
    story_title: str,
    genre: str,
    voice_id: Optional[str] = None
) -> str | None:
    """
    Generate TTS audio for a standalone story using ElevenLabs.

    Args:
        narrative: The story text to narrate
        story_title: Title of the story (for filename)
        genre: Story genre

    Returns:
        Local URL path to audio file, or None if generation fails
    """
    try:
        from elevenlabs.client import ElevenLabs

        if not config.ELEVENLABS_API_KEY:
            print("  ⏭️  ELEVENLABS_API_KEY not set, skipping audio generation")
            return None

        # Clean and prepare text for narration
        narrative_text = narrative.strip()

        # ElevenLabs Flash v2.5 supports up to 40,000 characters
        MAX_AUDIO_CHARS = 20000

        if len(narrative_text) > MAX_AUDIO_CHARS:
            print(f"  ⚠️  Narrative is {len(narrative_text)} chars, truncating to {MAX_AUDIO_CHARS}")
            # Try to truncate at a sentence boundary
            truncated = narrative_text[:MAX_AUDIO_CHARS]
            last_period = truncated.rfind('. ')
            if last_period > MAX_AUDIO_CHARS - 500:
                narrative_text = truncated[:last_period + 1]
            else:
                narrative_text = truncated + "..."
            print(f"  Truncated to {len(narrative_text)} chars")
        else:
            print(f"  ✓ Narrative is {len(narrative_text)} chars, within limit (max 40K)")

        # Create ElevenLabs client
        client = ElevenLabs(api_key=config.ELEVENLABS_API_KEY)

        # Use provided voice_id or fall back to config default
        selected_voice_id = voice_id or config.ELEVENLABS_VOICE_ID
        print(f"  Using voice ID: {selected_voice_id}")

        # Generate audio using Flash v2.5
        audio_generator = client.text_to_speech.convert(
            voice_id=selected_voice_id,
            text=narrative_text,
            model_id="eleven_flash_v2_5",
            voice_settings={
                "stability": 0.5,
                "similarity_boost": 0.75
            }
        )

        # Create audio directory if it doesn't exist
        os.makedirs("./generated_audio", exist_ok=True)

        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        # Clean title for filename
        clean_title = "".join(c for c in story_title if c.isalnum() or c in (' ', '-', '_')).strip()
        clean_title = clean_title.replace(' ', '_')[:50]  # Limit length
        filename = f"{genre}_{clean_title}_{timestamp}.mp3"
        filepath = f"./generated_audio/{filename}"

        # Save audio bytes to file
        with open(filepath, "wb") as f:
            for chunk in audio_generator:
                f.write(chunk)

        # Upload to storage backend (Supabase in prod, local in dev)
        from backend.storage import upload_audio
        public_url = upload_audio(filepath, filename)

        print(f"  ✓ Audio generated successfully")
        print(f"    Saved to: {filepath}")
        print(f"    Public URL: {public_url}")
        return public_url

    except Exception as e:
        error_msg = str(e)
        print(f"  ⚠️  Audio generation failed: {error_msg}")

        if "401" in error_msg or "unauthorized" in error_msg.lower():
            print("  ⚠️  ElevenLabs API authentication failed. Check ELEVENLABS_API_KEY.")
        elif "429" in error_msg or "quota" in error_msg.lower():
            print("  ⚠️  ElevenLabs API quota/rate limit exceeded.")

        return None


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

            # Concatenate using ffmpeg
            print(f"  Concatenating {len(audio_chunks)} audio chunks...")
            import subprocess

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

            # Clean up temp files
            os.remove(list_file)
            for chunk_file in audio_chunks:
                os.remove(chunk_file)

            if result.returncode != 0:
                print(f"  ⚠️  ffmpeg concat error: {result.stderr}")
                return None

            print(f"  ✓ Successfully concatenated {len(audio_chunks)} chunks")

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
    "elevenlabs": {
        "name": "ElevenLabs",
        "function": "generate_story_audio",  # Original function
        "voices": {
            "rachel": "21m00Tcm4TlvDq8ikWAM",
            "domi": "AZnzlk1XvdvUeBnXmlld",
            "bella": "EXAVITQu4vr4xnSDxMaL",
            "antoni": "ErXwobaYiN019PkySvjV",
            "josh": "TxGEqnHWrfWFTfGW9XjX",
        },
        "default_voice": "rachel"
    },
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
    provider: str = "elevenlabs",
    voice: str = None
) -> str | None:
    """
    Route audio generation to the appropriate TTS provider.

    Args:
        narrative: The story text to narrate
        story_title: Title of the story (for filename)
        genre: Story genre
        provider: TTS provider ("elevenlabs" or "openai")
        voice: Voice name/ID (optional, uses default for provider)

    Returns:
        Local URL path to audio file, or None if generation fails
    """
    provider_info = TTS_PROVIDERS.get(provider, TTS_PROVIDERS["elevenlabs"])
    print(f"  Using TTS provider: {provider_info['name']}")

    # Get voice ID
    if voice:
        voice_id = provider_info["voices"].get(voice, voice)
    else:
        default_voice_key = provider_info["default_voice"]
        voice_id = provider_info["voices"].get(default_voice_key, default_voice_key)

    if provider == "elevenlabs":
        return await generate_story_audio(
            narrative=narrative,
            story_title=story_title,
            genre=genre,
            voice_id=voice_id
        )
    elif provider == "openai":
        return await generate_story_audio_openai(
            narrative=narrative,
            story_title=story_title,
            genre=genre,
            voice=voice_id
        )
    else:
        print(f"  ⚠️  Unknown TTS provider: {provider}, falling back to ElevenLabs")
        return await generate_story_audio(
            narrative=narrative,
            story_title=story_title,
            genre=genre,
            voice_id=None
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
    tts_provider: str = "elevenlabs",
    tts_voice: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generate a complete standalone story using the multi-agent system.

    Flow:
    1. Select beat template based on genre and tier
    2. Determine if cliffhanger/cameo
    3. CBA: Generate beat plan
    4. CEA: Check consistency (simplified for standalone)
    5. PA: Generate prose
    6. Post-process: Extract summary, update bible

    Args:
        story_bible: Enhanced story bible
        user_tier: User's tier (free, premium)
        force_cliffhanger: Override cliffhanger logic (for dev mode)
        dev_mode: Enable dev mode features
        voice_id: Legacy voice_id for ElevenLabs (deprecated, use tts_voice)
        tts_provider: TTS provider ("elevenlabs" or "openai")
        tts_voice: Voice name for selected provider

    Returns:
        Dict with generated story and metadata
    """
    start_time = time.time()

    print(f"\n{'='*70}")
    print(f"GENERATING STANDALONE STORY")
    print(f"Genre: {story_bible.get('genre', 'N/A')}")
    print(f"Tier: {user_tier}")
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

        # Step 4: CBA - Generate beat plan
        print(f"\n{'─'*70}")
        print(f"CBA: PLANNING STORY BEATS")
        print(f"{'─'*70}")

        beat_plan = await generate_beat_plan(
            story_bible=story_bible,
            template=template,
            is_cliffhanger=is_cliffhanger,
            cameo=cameo
        )

        story_title = beat_plan.get("story_title", "Untitled")
        print(f"\n✓ Beat plan generated")
        print(f"  Title: {story_title}")
        print(f"  Plot type: {beat_plan.get('plot_type', 'N/A')}")
        print(f"  Story question: {beat_plan.get('story_question', 'N/A')[:60]}...")

        # Step 5: CEA - Simplified consistency check
        print(f"\n{'─'*70}")
        print(f"CEA: CONSISTENCY CHECK")
        print(f"{'─'*70}")

        consistency_report = await check_consistency_simplified(
            beat_plan=beat_plan,
            story_bible=story_bible
        )

        print(f"\n✓ Consistency check complete")
        print(f"  Status: {consistency_report.get('status', 'unknown')}")

        # Step 6: PA - Generate prose
        print(f"\n{'─'*70}")
        print(f"PA: GENERATING PROSE")
        print(f"{'─'*70}")

        narrative = await generate_prose(
            beat_plan=beat_plan,
            story_bible=story_bible,
            template=template,
            consistency_guidance=consistency_report.get("guidance_for_pa", {}),
            cameo=cameo
        )

        word_count = len(narrative.split())
        print(f"\n✓ Prose generated")
        print(f"  Word count: {word_count}")
        print(f"  Target: {template.total_words} (±200)")

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

            # Use legacy voice_id for ElevenLabs if tts_voice not specified
            effective_voice = tts_voice or voice_id

            audio_url = await generate_story_audio_with_provider(
                narrative=narrative,
                story_title=story_title,
                genre=genre,
                provider=tts_provider,
                voice=effective_voice
            )

        # Step 9: Create summary
        summary = f"{story_title}: {beat_plan.get('story_premise', 'A story in this world')}"

        # Calculate total time
        total_time = time.time() - start_time

        print(f"\n{'='*70}")
        print(f"STORY GENERATION COMPLETE")
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
                "beat_plan": beat_plan,
                "plot_type": beat_plan.get("plot_type", "unknown"),
                "summary": summary,
                "consistency_report": consistency_report,
                "generation_time_seconds": total_time,
                "template_used": template.name,
                "tts_provider": tts_provider
            }
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


async def generate_beat_plan(
    story_bible: Dict[str, Any],
    template: Any,
    is_cliffhanger: bool = False,
    cameo: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    CBA: Generate beat plan for the story.
    """
    from backend.storyteller.prompts_standalone import create_standalone_story_beat_prompt

    # Get user preferences
    user_preferences = story_bible.get("user_preferences", {})

    # Create prompt
    prompt = create_standalone_story_beat_prompt(
        story_bible=story_bible,
        beat_template=template.to_dict(),
        is_cliffhanger=is_cliffhanger,
        cameo=cameo,
        user_preferences=user_preferences
    )

    # Initialize LLM
    llm = ChatAnthropic(
        model=config.MODEL_NAME,
        temperature=0.7,  # Creative but coherent
        max_tokens=2500,
        anthropic_api_key=config.ANTHROPIC_API_KEY,
        timeout=90.0,  # Increased for complex beat plans
    )

    # Generate beat plan
    cba_start = time.time()
    response = await llm.ainvoke([HumanMessage(content=prompt)])
    cba_duration = time.time() - cba_start

    print(f"  LLM call: {cba_duration:.2f}s")

    # Parse response
    response_text = response.content.strip()

    if "```json" in response_text:
        response_text = response_text.split("```json")[1].split("```")[0].strip()
    elif "```" in response_text:
        response_text = response_text.split("```")[1].split("```")[0].strip()

    try:
        beat_plan = json.loads(response_text)
        return beat_plan
    except json.JSONDecodeError as e:
        print(f"  ⚠️  Failed to parse beat plan JSON: {e}")
        # Return minimal fallback
        return {
            "story_title": "A Story",
            "story_premise": "A story in this world",
            "plot_type": "adventure",
            "beats": template.beats,
            "story_question": "What happens?",
            "emotional_arc": "Discovery and resolution",
            "thematic_focus": story_bible.get("themes", ["adventure"])[0],
            "character_growth": "Protagonist learns something new",
            "unique_element": "To be discovered in the telling"
        }


async def check_consistency_simplified(
    beat_plan: Dict[str, Any],
    story_bible: Dict[str, Any]
) -> Dict[str, Any]:
    """
    CEA: Simplified consistency check for standalone stories.

    For MVP, we do a lightweight check. Can enhance later.
    """
    # For now, just check protagonist traits are in beat plan
    protagonist = story_bible.get("protagonist", {})
    defining_char = protagonist.get("defining_characteristic", "")

    # Create simple guidance
    guidance = {
        "general_guidance": f"Ensure {protagonist.get('name', 'protagonist')} is portrayed consistently. CRITICAL: {defining_char}",
        "emphasis_points": [
            defining_char,
            "Character voice and personality",
            "Setting consistency"
        ],
        "avoid": [
            "Contradicting established character traits",
            "Breaking world rules"
        ]
    }

    return {
        "status": "clear",
        "guidance_for_pa": guidance
    }


async def generate_prose(
    beat_plan: Dict[str, Any],
    story_bible: Dict[str, Any],
    template: Any,
    consistency_guidance: Dict[str, Any] = None,
    cameo: Dict[str, Any] = None
) -> str:
    """
    PA: Generate prose from beat plan.
    """
    from backend.storyteller.prompts_standalone import create_prose_generation_prompt

    # Create prompt
    prompt = create_prose_generation_prompt(
        beat_plan=beat_plan,
        story_bible=story_bible,
        beat_template=template.to_dict(),
        consistency_guidance=consistency_guidance,
        cameo=cameo
    )

    # Initialize LLM with extended output
    llm = ChatAnthropic(
        model=config.MODEL_NAME,
        temperature=0.8,  # Creative prose
        max_tokens=8000,  # Enough for full story
        anthropic_api_key=config.ANTHROPIC_API_KEY,
        timeout=300.0,  # 5 minutes for long premium stories (sitcom, etc.)
    )

    # Generate prose
    pa_start = time.time()
    response = await llm.ainvoke([HumanMessage(content=prompt)])
    pa_duration = time.time() - pa_start

    print(f"  LLM call: {pa_duration:.2f}s")

    narrative = response.content.strip()

    # Clean up any markdown or metadata that leaked in
    if "```" in narrative:
        # Try to extract just the story
        parts = narrative.split("```")
        # Find the largest text block that's not JSON
        text_blocks = [p.strip() for p in parts if p.strip() and not p.strip().startswith("json")]
        if text_blocks:
            narrative = max(text_blocks, key=len)

    return narrative
