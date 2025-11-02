"""
LangGraph node functions for the storytelling workflow.

Each node is a processing step that receives state, performs an operation,
and returns updated state. Nodes should be pure functions when possible.
"""

import json
import asyncio
from typing import Any
from langchain_core.messages import HumanMessage, AIMessage
from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI

from backend.models.state import StoryState
from backend.story_bible.rag import StoryWorldFactory
from backend.storyteller.prompts import (
    create_narrative_prompt,
    create_opening_prompt,
    format_conversation_history,
    extract_beat_metadata_from_context
)
from backend.config import config


# ===== Node 1: Retrieve Context from Story Bible =====

async def retrieve_context_node(state: StoryState) -> dict[str, Any]:
    """
    Retrieve relevant context from story bible using RAG.

    Args:
        state: Current story state

    Returns:
        Updated state with retrieved_context populated
    """
    try:
        # Get RAG instance for this world
        rag = StoryWorldFactory.get_world(state["world_id"])

        # Build query from recent messages and beat context
        recent_input = state["messages"][-1].content if state["messages"] else "Start the story"
        query = f"Beat {state['current_beat']}: {recent_input}"

        # Retrieve context
        context = await rag.aretrieve(query, beat_number=state["current_beat"])

        return {"retrieved_context": context}

    except Exception as e:
        print(f"Error in retrieve_context_node: {e}")
        return {
            "retrieved_context": "Error retrieving context. Using minimal context.",
            "error": str(e)
        }


# ===== Node 2: Generate Narrative =====

async def generate_narrative_node(state: StoryState) -> dict[str, Any]:
    """
    Generate story narrative using LLM with RAG context.

    Args:
        state: Current story state with retrieved_context

    Returns:
        Updated state with narrative_text populated (raw LLM response)
    """
    try:
        # Initialize LLM - use Claude for better narrative consistency
        llm = ChatAnthropic(
            model=config.MODEL_NAME,
            temperature=config.TEMPERATURE,
            max_tokens=config.MAX_TOKENS,
            anthropic_api_key=config.ANTHROPIC_API_KEY,
        )

        # Determine if this is the opening
        is_opening = len(state["messages"]) == 0

        # Select appropriate prompt
        if is_opening:
            prompt = create_opening_prompt(state["world_id"])
            messages = prompt.format_messages(context=state["retrieved_context"])
        else:
            # Extract beat metadata from context
            beat_metadata = extract_beat_metadata_from_context(
                state["retrieved_context"],
                state["current_beat"]
            )

            prompt = create_narrative_prompt(
                state["current_beat"], 
                beat_metadata,
                world_id=state["world_id"]
            )

            # Get player's last input
            player_input = state["messages"][-1].content if state["messages"] else "Begin"

            messages = prompt.format_messages(
                history=state["messages"][:-1] if len(state["messages"]) > 1 else [],
                player_input=player_input,
                context=state["retrieved_context"]
            )

        # Generate narrative
        response = await llm.ainvoke(messages)

        # Debug: print first 200 chars
        print(f"LLM Response (first 200 chars): {response.content[:200]}")

        return {"narrative_text": response.content}

    except Exception as e:
        print(f"Error in generate_narrative_node: {e}")
        return {
            "narrative_text": json.dumps({
                "narrative": "The Citadel's magic flickers and distorts. Something went wrong in the weaving of this tale.",
                "choices": [
                    {"id": 1, "text": "Try again", "consequence_hint": "Resume the story"},
                    {"id": 2, "text": "Take a different path", "consequence_hint": "Alternative approach"},
                    {"id": 3, "text": "Pause and reflect", "consequence_hint": "Gather your thoughts"}
                ],
                "image_prompt": "Magical distortion, reality flickering, dark fantasy",
                "beat_complete": False
            }),
            "error": str(e)
        }


# ===== Node 3: Parse LLM Output =====

def parse_output_node(state: StoryState) -> dict[str, Any]:
    """
    Parse JSON output from LLM into structured data.

    Args:
        state: Current story state with narrative_text (JSON string)

    Returns:
        Updated state with parsed choices, image_prompt, etc.
    """
    try:
        # Parse JSON from LLM response
        narrative_text = state["narrative_text"]

        # Handle markdown code blocks if present
        if "```json" in narrative_text:
            narrative_text = narrative_text.split("```json")[1].split("```")[0]
        elif "```" in narrative_text:
            narrative_text = narrative_text.split("```")[1].split("```")[0]

        data = json.loads(narrative_text.strip())

        # Extract components
        narrative = data.get("narrative", "")
        choices = data.get("choices", [])
        image_prompt = data.get("image_prompt")
        beat_complete = data.get("beat_complete", False)

        # Update beat progress if complete
        beat_progress = state.get("beat_progress", {}).copy()
        if beat_complete:
            beat_progress[state["current_beat"]] = True

        # Add AI message to history
        messages = state["messages"].copy()
        messages.append(AIMessage(content=narrative))

        return {
            "narrative_text": narrative,  # Now just the text, not JSON
            "choices": choices,
            "image_prompt": image_prompt,
            "beat_progress": beat_progress,
            "messages": messages
        }

    except json.JSONDecodeError as e:
        print(f"JSON parsing error: {e}")
        print(f"Raw response: {state['narrative_text'][:500]}")

        # Fallback: treat as plain narrative
        return {
            "narrative_text": state["narrative_text"],
            "choices": [
                {"id": 1, "text": "Continue", "consequence_hint": "Move forward"},
                {"id": 2, "text": "Investigate", "consequence_hint": "Look closer"},
                {"id": 3, "text": "Be cautious", "consequence_hint": "Careful approach"}
            ],
            "image_prompt": None,
            "error": f"Failed to parse LLM output: {str(e)}"
        }

    except Exception as e:
        print(f"Error in parse_output_node: {e}")
        return {"error": str(e)}


# ===== Node 4: Generate Image (Optional) =====

async def generate_image_node(state: StoryState) -> dict[str, Any]:
    """
    Generate scene image using Replicate API with retry logic.
    Downloads and stores images locally to avoid expiration.

    Args:
        state: Current story state with image_prompt

    Returns:
        Updated state with image_url (local path)
    """
    # Skip image generation if not enabled or no prompt
    if not config.ENABLE_MEDIA_GENERATION:
        return {"image_url": None}
    
    if not config.can_generate_images:
        print("⚠️  Image generation disabled: Missing REPLICATE_API_TOKEN")
        return {"image_url": None}
    
    if not state.get("image_prompt"):
        return {"image_url": None}

    # Enhanced image prompt for consistency
    base_prompt = state["image_prompt"]
    enhanced_prompt = f"{base_prompt}, cinematic lighting, high quality, detailed, fantasy art style"

    max_retries = 3
    retry_delay = 2  # seconds

    for attempt in range(max_retries):
        try:
            import replicate
            import httpx
            import os
            from datetime import datetime

            if not config.REPLICATE_API_TOKEN:
                print("⚠️  REPLICATE_API_TOKEN not set, skipping image generation")
                return {"image_url": None}

            # Create client with API token
            client = replicate.Client(api_token=config.REPLICATE_API_TOKEN)

            # Use a valid Replicate model (try specific version if latest fails)
            model = config.IMAGE_MODEL
            if model == "stability-ai/sdxl:latest":
                # Use a specific version for better reliability
                model = "stability-ai/sdxl:39ed52f2a78e934b3ba6e2a89f5b1c712de7dfea535525255b1aa35c5555e08b"

            print(f"Generating image with model: {model}")

            # Run Stable Diffusion XL
            output = await client.async_run(
                model,
                input={
                    "prompt": enhanced_prompt,
                    "width": config.IMAGE_WIDTH,
                    "height": config.IMAGE_HEIGHT,
                    "num_outputs": 1,
                    "negative_prompt": "text, watermark, low quality, blurry, distorted, ugly",
                    "guidance_scale": 7.5,
                    "num_inference_steps": 25
                }
            )

            replicate_output = output[0] if output else None
            if not replicate_output:
                raise Exception("No image URL returned from Replicate")

            # Convert FileOutput to string URL
            replicate_url = str(replicate_output)
            print(f"✓ Image generated by Replicate (attempt {attempt + 1})")

            # Download and save image locally
            # Create images directory if it doesn't exist
            os.makedirs("./generated_images", exist_ok=True)

            # Generate filename with proper naming convention
            # Format: {world_id}_{session_id}_beat{beat_number}_{timestamp}.png
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            session_id = state.get("session_id", "unknown")
            filename = f"{state['world_id']}_{session_id}_beat{state['current_beat']}_{timestamp}.png"
            filepath = f"./generated_images/{filename}"

            # Download image from Replicate
            print(f"Downloading image from Replicate: {replicate_url}")
            async with httpx.AsyncClient() as http_client:
                response = await http_client.get(replicate_url)
                response.raise_for_status()

                # Save to local file
                with open(filepath, "wb") as f:
                    f.write(response.content)

            # Return local URL path
            local_url = f"/images/{filename}"
            print(f"✓ Image saved locally: {filepath}")
            print(f"  Accessible at: {local_url}")

            return {"image_url": local_url}

        except Exception as e:
            error_msg = str(e)
            print(f"⚠️  Image generation failed (attempt {attempt + 1}/{max_retries}): {error_msg}")
            
            # Check for authentication errors
            if "401" in error_msg or "unauthorized" in error_msg.lower() or "authentication" in error_msg.lower():
                print("⚠️  Replicate API authentication failed. Check REPLICATE_API_TOKEN.")
                return {"image_url": None}  # Don't retry auth errors
            
            # Check for invalid model errors
            if "404" in error_msg or "not found" in error_msg.lower():
                print(f"⚠️  Invalid Replicate model. Check IMAGE_MODEL setting.")
                return {"image_url": None}  # Don't retry invalid model errors
            
            if attempt < max_retries - 1:
                print(f"Retrying in {retry_delay} seconds...")
                await asyncio.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
            else:
                print(f"❌ Image generation failed after {max_retries} attempts, continuing without image")
                return {"image_url": None}  # Don't include error in state, just skip image

    return {"image_url": None, "error": "Image generation failed"}


# ===== Node 5: Generate Audio (Optional) =====

async def generate_audio_node(state: StoryState) -> dict[str, Any]:
    """
    Generate voice narration using ElevenLabs API with retry logic.

    Args:
        state: Current story state with narrative_text

    Returns:
        Updated state with audio_url
    """
    # Skip audio generation if not enabled or no text
    if not config.ENABLE_MEDIA_GENERATION:
        return {"audio_url": None}
    
    if not config.can_generate_audio:
        print("⚠️  Audio generation disabled: Missing ELEVENLABS_API_KEY")
        return {"audio_url": None}
    
    if not state.get("narrative_text"):
        return {"audio_url": None}

    # Clean and prepare text for narration
    narrative_text = state["narrative_text"].strip()
    if len(narrative_text) > 5000:  # ElevenLabs has character limits
        narrative_text = narrative_text[:5000] + "..."
    
    max_retries = 3
    retry_delay = 2  # seconds
    
    for attempt in range(max_retries):
        try:
            from elevenlabs.client import ElevenLabs
            import os
            from datetime import datetime

            if not config.ELEVENLABS_API_KEY:
                print("⚠️  ELEVENLABS_API_KEY not set, skipping audio generation")
                return {"audio_url": None}

            # Create ElevenLabs client
            client = ElevenLabs(api_key=config.ELEVENLABS_API_KEY)

            # Generate audio using new SDK
            audio_generator = client.text_to_speech.convert(
                voice_id=config.ELEVENLABS_VOICE_ID,
                text=narrative_text,
                model_id="eleven_monolingual_v1",
                voice_settings={
                    "stability": 0.5,
                    "similarity_boost": 0.75
                }
            )

            # Create audio directory if it doesn't exist
            os.makedirs("./generated_audio", exist_ok=True)

            # Generate filename with proper naming convention
            # Format: {world_id}_{session_id}_beat{beat_number}_{timestamp}.mp3
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            session_id = state.get("session_id", "unknown")
            filename = f"{state['world_id']}_{session_id}_beat{state['current_beat']}_{timestamp}.mp3"
            filepath = f"./generated_audio/{filename}"

            # Save audio bytes to file
            with open(filepath, "wb") as f:
                for chunk in audio_generator:
                    f.write(chunk)

            # Return local path
            local_url = f"/audio/{filename}"
            print(f"✓ Audio generated successfully (attempt {attempt + 1})")
            print(f"  Saved to: {filepath}")
            print(f"  Accessible at: {local_url}")
            return {"audio_url": local_url}

        except Exception as e:
            error_msg = str(e)
            print(f"⚠️  Audio generation failed (attempt {attempt + 1}/{max_retries}): {error_msg}")
            
            # Check for authentication errors
            if "401" in error_msg or "unauthorized" in error_msg.lower() or "authentication" in error_msg.lower() or "invalid api key" in error_msg.lower():
                print("⚠️  ElevenLabs API authentication failed. Check ELEVENLABS_API_KEY.")
                return {"audio_url": None}  # Don't retry auth errors
            
            # Check for quota/limit errors
            if "429" in error_msg or "quota" in error_msg.lower() or "limit" in error_msg.lower():
                print("⚠️  ElevenLabs API quota exceeded.")
                return {"audio_url": None}  # Don't retry quota errors
            
            if attempt < max_retries - 1:
                print(f"Retrying in {retry_delay} seconds...")
                await asyncio.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
            else:
                print(f"❌ Audio generation failed after {max_retries} attempts, continuing without audio")
                return {"audio_url": None}  # Don't include error in state, just skip audio
    
    return {"audio_url": None}  # Fallback return


# ===== Node 6: Check Beat Completion =====

def check_beat_complete_node(state: StoryState) -> dict[str, Any]:
    """
    Check if current beat is complete and advance if necessary.

    Args:
        state: Current story state

    Returns:
        Updated state with potentially incremented current_beat
    """
    beat_progress = state.get("beat_progress", {})
    current_beat = state["current_beat"]

    # Check if current beat is marked complete
    if beat_progress.get(current_beat, False):
        # Advance to next beat
        next_beat = current_beat + 1

        print(f"✓ Beat {current_beat} completed! Advancing to Beat {next_beat}")

        return {
            "current_beat": next_beat
        }

    # Beat not complete, continue current beat
    return {}


# ===== Node 7: Deduct Credits =====

def deduct_credits_node(state: StoryState) -> dict[str, Any]:
    """
    Deduct credits for this story segment (if credit system enabled).

    Args:
        state: Current story state

    Returns:
        Updated state with decremented credits_remaining
    """
    if not config.ENABLE_CREDIT_SYSTEM:
        return {}

    credits = state.get("credits_remaining", 0)

    if credits <= 0:
        return {
            "error": "Insufficient credits",
            "credits_remaining": 0
        }

    new_credits = credits - config.CREDITS_PER_CHOICE

    return {"credits_remaining": max(0, new_credits)}


# ===== Helper Node: Add User Message =====

def add_user_message_node(state: StoryState, user_input: str) -> dict[str, Any]:
    """
    Add user's choice to message history.

    Args:
        state: Current story state
        user_input: User's input text

    Returns:
        Updated state with new message
    """
    messages = state.get("messages", []).copy()
    messages.append(HumanMessage(content=user_input))

    return {"messages": messages}


# ===== Conditional Edge Functions =====

def should_generate_media(state: StoryState) -> str:
    """
    Determine if media generation should occur.

    Args:
        state: Current story state

    Returns:
        "generate_media" or "skip_media"
    """
    # Check if media generation is enabled and credits available
    if config.ENABLE_MEDIA_GENERATION and state.get("credits_remaining", 0) > 0:
        return "generate_media"
    return "skip_media"


def is_beat_complete(state: StoryState) -> str:
    """
    Determine if beat was just completed.

    Args:
        state: Current story state

    Returns:
        "advance" if beat complete, "continue" otherwise
    """
    beat_progress = state.get("beat_progress", {})
    current_beat = state["current_beat"]

    if beat_progress.get(current_beat, False):
        return "advance"
    return "continue"


def has_error(state: StoryState) -> str:
    """
    Check if an error occurred.

    Args:
        state: Current story state

    Returns:
        "error" if error exists, "success" otherwise
    """
    if state.get("error"):
        return "error"
    return "success"
