"""
Main story generation workflow for FixionMail standalone stories.

This orchestrates the 3-agent system for daily story generation:
- StructureAgent (SSBA, Sonnet): Creates story-specific beat structures
- WriterAgent (Sonnet): Generates first draft from beat plan
- EditorAgent (Opus): Rewrites/polishes AND validates quality
"""

import time
import json
import asyncio
import os
import uuid
from typing import Dict, Any, Optional, Literal, Tuple
from datetime import datetime
from langchain_core.messages import HumanMessage
from langchain_anthropic import ChatAnthropic
from backend.config import config

from backend.storyteller.beat_templates import get_template, get_structure_template, get_structure_for_story
from backend.storyteller.bible_enhancement import should_use_cliffhanger, should_include_cameo, check_and_fix_duplicate_title
from backend.storyteller.name_registry import (
    get_excluded_names,
    extract_names_from_story,
    add_used_names,
    cleanup_expired_names
)

# Import name database for tracking usage
try:
    from backend.storyteller import name_database
    NAME_DATABASE_AVAILABLE = True
except ImportError:
    NAME_DATABASE_AVAILABLE = False
from backend.agents import (
    WriterAgent, StructureAgent, EditorAgent,
    WRITER_MODELS, STRUCTURE_MODELS, EDITOR_MODELS
)

# Type alias for model selection
WriterModelType = Literal["sonnet", "opus"]
StructureModelType = Literal["haiku", "sonnet"]
EditorModelType = Literal["opus", "sonnet"]


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

        # Generate unique filename with UUID to prevent overwrites
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = uuid.uuid4().hex[:8]  # Short unique ID
        clean_title = "".join(c for c in story_title if c.isalnum() or c in (' ', '-', '_')).strip()
        clean_title = clean_title.replace(' ', '_')[:50]
        filename = f"{genre}_{clean_title}_{timestamp}_{unique_id}.mp3"
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
    story_premise: str,
    genre: str,
    max_retries: int = 3
) -> str | None:
    """
    Generate cover image for a standalone story using Replicate.

    Tries the configured model first with retries, then falls back to
    alternative models if all retries fail.

    Args:
        story_title: Title of the story
        story_premise: One-sentence story hook/premise
        genre: Story genre
        max_retries: Maximum retries per model for transient errors (502, 503, timeout)

    Returns:
        Local URL path to image file, or None if generation fails
    """
    if not config.REPLICATE_API_TOKEN:
        print("  ⏭️  REPLICATE_API_TOKEN not set, skipping image generation")
        return None

    # Primary model from config, with fallback models to try if it fails
    primary_model = config.IMAGE_MODEL

    # Define fallback models (excluding the primary)
    # Note: stability-ai/sdxl is broken, removed from fallbacks
    # Using only reliable free/fast models
    all_models = [
        "black-forest-labs/flux-schnell",  # Fast, reliable, free tier
        "google/imagen-3-fast",             # Google's fast model
        "black-forest-labs/flux-1.1-pro",   # Higher quality (paid)
    ]

    # Build model list: primary first, then fallbacks
    models_to_try = [primary_model]
    for model in all_models:
        if model != primary_model and model not in models_to_try:
            models_to_try.append(model)

    # Transient errors that should trigger a retry
    RETRYABLE_ERRORS = ["502", "503", "504", "timeout", "connection", "rate limit", "429"]

    for model_idx, model in enumerate(models_to_try):
        is_fallback = model_idx > 0
        if is_fallback:
            print(f"  🔄 Trying fallback model: {model}")

        for attempt in range(max_retries):
            try:
                return await _generate_image_attempt(story_title, story_premise, genre, model)

            except Exception as e:
                error_msg = str(e).lower()
                is_retryable = any(err in error_msg for err in RETRYABLE_ERRORS)

                # Check for auth errors - no point trying other models
                if "401" in str(e) or "unauthorized" in error_msg:
                    print(f"  ⚠️  Replicate API authentication failed. Check REPLICATE_API_TOKEN.")
                    return None

                if is_retryable and attempt < max_retries - 1:
                    wait_time = 2 ** (attempt + 1)  # Exponential backoff: 2s, 4s, 8s
                    print(f"  ⚠️  Image generation failed (attempt {attempt + 1}/{max_retries}): {e}")
                    print(f"  ⏳ Retrying in {wait_time} seconds...")
                    await asyncio.sleep(wait_time)
                else:
                    # Max retries exceeded for this model
                    print(f"  ⚠️  Image generation failed with {model}: {e}")
                    if "404" in str(e):
                        print(f"  ⚠️  Invalid Replicate model: {model}")
                    # Break to try next model
                    break

    print(f"  ⚠️  All image generation models failed")
    return None


async def _generate_image_attempt(
    story_title: str,
    story_premise: str,
    genre: str,
    model: str
) -> str:
    """
    Single attempt at generating an image. Raises exception on failure.

    This function is called by generate_story_image which handles retries
    and model fallback.

    Args:
        story_title: Title of the story
        story_premise: One-sentence story hook/premise
        genre: Story genre
        model: Replicate model to use (e.g., "black-forest-labs/flux-schnell")

    Returns:
        Public URL of the generated image

    Raises:
        Exception: If image generation fails (triggers retry in caller)
    """
    import replicate
    import httpx

    # Build a descriptive prompt optimized for the model
    # Flux models work better with concrete, specific descriptions
    # Imagen works better with artistic/conceptual language

    if "flux" in model.lower():
        # FLUX-optimized prompt: concrete, specific, style-focused
        enhanced_prompt = (
            f"A dramatic scene from a {genre} story: {story_premise}. "
            f"Cinematic composition, volumetric lighting, rich colors, "
            f"highly detailed digital painting, concept art style, "
            f"epic atmosphere, professional illustration, 8k quality, "
            f"no text, no words, no letters, no watermarks"
        )
    else:
        # Imagen/other models: more artistic/conceptual
        base_prompt = f"{genre} story cover art, {story_premise}, atmospheric scene"
        enhanced_prompt = (
            f"{base_prompt}, cinematic lighting, high quality, detailed, "
            f"painterly illustration style, wordless visual narrative, pure scenic artwork, "
            f"clean composition, artistic book cover without typography, "
            f"focus on mood and atmosphere, evocative imagery"
        )

    print(f"  Image prompt: {enhanced_prompt[:100]}...")

    # Create client
    client = replicate.Client(api_token=config.REPLICATE_API_TOKEN)
    print(f"  Using model: {model}")

    # Build input parameters based on model type
    if "imagen" in model.lower():
        # Google Imagen-3-Fast
        input_params = {
            "prompt": enhanced_prompt,
            "aspect_ratio": "1:1",
            "output_format": "png",
            "safety_filter_level": "block_only_high"
        }
    elif "flux" in model.lower():
        # Black Forest Labs FLUX models (schnell, pro, etc.)
        input_params = {
            "prompt": enhanced_prompt,
            "aspect_ratio": "1:1",
            "output_format": "png",
            "num_outputs": 1,
            "go_fast": True,
        }
    elif "sdxl" in model.lower():
        # Stability AI SDXL
        input_params = {
            "prompt": enhanced_prompt,
            "width": config.IMAGE_WIDTH,
            "height": config.IMAGE_HEIGHT,
            "num_outputs": 1,
        }
    else:
        # Generic fallback
        input_params = {
            "prompt": enhanced_prompt,
        }

    print(f"  Generating image...")
    output = await client.async_run(model, input=input_params)

    # Handle output - Imagen-3-Fast returns a single FileOutput object
    if isinstance(output, list):
        replicate_output = output[0] if output else None
    else:
        replicate_output = output

    if not replicate_output:
        raise Exception("No image URL returned from Replicate")

    replicate_url = str(replicate_output)
    print(f"  ✓ Image generated successfully")

    # Download and save image locally
    os.makedirs("./generated_images", exist_ok=True)

    # Generate unique filename with UUID to prevent overwrites
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_id = uuid.uuid4().hex[:8]  # Short unique ID
    # Clean title for filename
    clean_title = "".join(c for c in story_title if c.isalnum() or c in (' ', '-', '_')).strip()
    clean_title = clean_title.replace(' ', '_')[:50]
    filename = f"{genre}_{clean_title}_{timestamp}_{unique_id}.png"
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


async def generate_standalone_story(
    story_bible: Dict[str, Any],
    user_tier: str = "free",
    force_cliffhanger: bool = None,
    dev_mode: bool = False,
    voice_id: Optional[str] = None,
    tts_provider: str = "openai",
    tts_voice: Optional[str] = None,
    writer_model: WriterModelType = "sonnet",
    structure_model: StructureModelType = "sonnet",
    editor_model: EditorModelType = "opus",
    use_structure_agent: bool = True
) -> Dict[str, Any]:
    """
    Generate a complete standalone story using the 3-agent system.

    Flow:
    1. Select beat template based on genre and tier
    2. Determine if cliffhanger/cameo
    3. STRUCTURE (SSBA): Create story-specific beat plan (Sonnet)
    4. WRITER: Generate first draft (Sonnet)
    5. EDITOR: Rewrite/polish AND validate quality (Opus)
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
        writer_model: Writer model - "sonnet" (default) for first draft
        structure_model: Structure agent model - "sonnet" (default) for planning
        editor_model: Editor model - "opus" (default) for polish and validation
        use_structure_agent: Enable SSBA for story-specific beat planning (default True)

    Returns:
        Dict with generated story and metadata
    """
    start_time = time.time()

    # Get model info
    writer_model_info = WRITER_MODELS.get(writer_model, WRITER_MODELS["sonnet"])
    structure_model_info = STRUCTURE_MODELS.get(structure_model, STRUCTURE_MODELS["sonnet"])
    editor_model_info = EDITOR_MODELS.get(editor_model, EDITOR_MODELS["opus"])

    agent_system = "3-Agent" if use_structure_agent else "2-Agent"
    print(f"\n{'='*70}")
    print(f"GENERATING STANDALONE STORY ({agent_system} System)")
    print(f"Genre: {story_bible.get('genre', 'N/A')}")
    print(f"Tier: {user_tier}")
    if use_structure_agent:
        print(f"Structure: {structure_model_info['name']} ({structure_model_info['cost_tier']})")
    print(f"Writer: {writer_model_info['name']} ({writer_model_info['cost_tier']})")
    print(f"Editor: {editor_model_info['name']} ({editor_model_info['cost_tier']})")
    print(f"{'='*70}")

    try:
        # Step 1: Select beat template with automatic variety
        genre = story_bible.get("genre", "scifi")
        beat_structure = story_bible.get("beat_structure", "auto")

        # Use automatic structure selection for variety unless user explicitly chose one
        if beat_structure in ("auto", "classic", "", None):
            # Auto-select structure based on recent history and genre affinity
            selected_structure, template = get_structure_for_story(story_bible, user_tier)
            print(f"\n✓ Auto-selected story structure: {selected_structure}")
            # Store the selected structure in bible for history tracking
            story_bible["beat_structure"] = selected_structure
        else:
            # User explicitly chose a structure
            template = get_structure_template(beat_structure, user_tier)
            if template:
                selected_structure = beat_structure
                print(f"\n✓ Using user-selected story structure: {beat_structure}")
            else:
                # Fallback to auto-selection if structure not found
                selected_structure, template = get_structure_for_story(story_bible, user_tier)
                print(f"\n✓ Structure '{beat_structure}' not found, auto-selected: {selected_structure}")
                story_bible["beat_structure"] = selected_structure

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

        # Step 4: STRUCTURE AGENT (SSBA) - Create story-specific beat plan
        structure_time = 0.0
        if use_structure_agent:
            print(f"\n{'─'*70}")
            print(f"STRUCTURE: CREATING STORY-SPECIFIC BEATS ({structure_model_info['name']})")
            print(f"{'─'*70}")

            structure_agent = StructureAgent(model=structure_model)
            structure_result = await structure_agent.create_structure(
                story_bible=story_bible,
                beat_template=template.to_dict(),
                is_cliffhanger=is_cliffhanger,
                story_history=story_bible.get("story_history")
            )

            if not structure_result.success:
                print(f"\n⚠️  Structure agent failed: {structure_result.error}")
                print(f"    Falling back to generic template...")
                beat_plan = template.to_dict()
            else:
                structure_time = structure_result.generation_time
                beat_plan = structure_result.structure.to_dict()
                print(f"\n✓ Story structure created")
                print(f"  Premise: {structure_result.structure.story_premise[:80]}...")
                print(f"  Conflict: {structure_result.structure.central_conflict[:80]}...")
                print(f"  Time: {structure_time:.2f}s")
        else:
            # Use generic template without SSBA
            beat_plan = template.to_dict()
            print(f"\n  (SSBA disabled - using generic template)")

        # Step 5: WRITER - Generate first draft
        print(f"\n{'─'*70}")
        print(f"WRITER: GENERATING FIRST DRAFT ({writer_model_info['name']})")
        print(f"{'─'*70}")

        writer = WriterAgent(model=writer_model)

        writer_result = await writer.generate(
            story_bible=story_bible,
            beat_template=beat_plan,
            is_cliffhanger=is_cliffhanger,
            cameo=cameo,
            user_preferences=story_bible.get("user_preferences"),
            excluded_names=excluded_names
        )

        if not writer_result.success:
            raise Exception(f"Writer failed: {writer_result.error}")

        print(f"\n✓ First draft generated")
        print(f"  Title: {writer_result.title}")
        print(f"  Word count: {writer_result.word_count}")
        print(f"  Time: {writer_result.generation_time:.2f}s")

        # Step 6: EDITOR - Rewrite/polish AND validate (Opus)
        print(f"\n{'─'*70}")
        print(f"EDITOR: POLISHING STORY ({editor_model_info['name']})")
        print(f"{'─'*70}")

        editor = EditorAgent(model=editor_model)

        editor_result = await editor.edit(
            first_draft=writer_result.narrative,
            title=writer_result.title,
            beat_plan=beat_plan,
            story_bible=story_bible,
            is_cliffhanger=is_cliffhanger
        )

        if not editor_result.success:
            print(f"\n⚠️  Editor failed: {editor_result.error}")
            print(f"    Using first draft as final story...")
            story_title = writer_result.title
            narrative = writer_result.narrative
            word_count = writer_result.word_count
            quality_scores = {}
            overall_score = 0.0
            passed = False
            edit_notes = ""
            editor_time = 0.0
        else:
            story_title = editor_result.title
            narrative = editor_result.narrative
            word_count = editor_result.word_count
            quality_scores = editor_result.quality_scores
            overall_score = editor_result.overall_score
            passed = editor_result.passed
            edit_notes = editor_result.edit_notes
            editor_time = editor_result.generation_time

            print(f"\n✓ Story polished")
            print(f"  Title: {story_title}")
            print(f"  Word count: {word_count}")
            print(f"  Overall score: {overall_score}/10")
            if quality_scores:
                for criterion, score in quality_scores.items():
                    print(f"    {criterion}: {score}/10")
            if edit_notes:
                print(f"  Edit notes: {edit_notes[:80]}...")
            print(f"  Time: {editor_time:.2f}s")

        print(f"\n✓ Final story ready")
        print(f"  Word count: {word_count}")
        print(f"  Target: {template.total_words} (±15%)")
        print(f"  Quality: {'PASSED' if passed else 'NEEDS REVIEW'}")

        # Step 6.5: Check for duplicate title (safety net)
        # This catches duplicates even if the AI ignores the instruction
        original_title = story_title
        story_title = check_and_fix_duplicate_title(story_title, story_bible)
        if story_title != original_title:
            print(f"  Title changed from \"{original_title}\" to \"{story_title}\"")

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
                story_premise=writer_result.story_premise or story_title,
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

            # Track name usage in the database (for names from our curated list)
            if NAME_DATABASE_AVAILABLE:
                try:
                    for char_name in extracted.get("characters", []):
                        # Try to track as both male and female (since we don't know gender)
                        # The function will only update if the name exists in the database
                        name_database.increment_name_usage_by_name(char_name, "first", "male")
                        name_database.increment_name_usage_by_name(char_name, "first", "female")
                        # Also try last names
                        name_database.increment_name_usage_by_name(char_name, "last")
                except Exception as e:
                    # Don't fail story generation if tracking fails
                    print(f"  ⚠️  Name usage tracking error (non-fatal): {e}")

        # Calculate total time
        total_time = time.time() - start_time

        print(f"\n{'='*70}")
        print(f"STORY GENERATION COMPLETE ({agent_system} System)")
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
                "quality_scores": quality_scores,
                "quality_passed": passed,
                "overall_score": overall_score,
                "edit_notes": edit_notes,
                "generation_time_seconds": total_time,
                "structure_time_seconds": structure_time,
                "structure_model": structure_model if use_structure_agent else None,
                "structure_model_name": structure_model_info["name"] if use_structure_agent else None,
                "writer_time_seconds": writer_result.generation_time,
                "writer_model": writer_result.model_used,
                "writer_model_name": writer_model_info["name"],
                "editor_time_seconds": editor_time,
                "editor_model": editor_model,
                "editor_model_name": editor_model_info["name"],
                "template_used": template.name,
                "used_structure_agent": use_structure_agent,
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


# Story Generation Architecture:
#
# 3-Agent System (default, use_structure_agent=True):
#   StructureAgent (SSBA, Sonnet) → WriterAgent (Sonnet) → EditorAgent (Opus)
#
# 2-Agent System (use_structure_agent=False):
#   WriterAgent (Sonnet) → EditorAgent (Opus)
#
# Future: Multi-Chapter Stories (Phase 7):
#   StructureAgent (full arc) → ChapterBeatAgent (per chapter) → WriterAgent → EditorAgent
#
# See backend/agents/ for agent implementations
