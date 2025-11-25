"""
FictionMail Dev Dashboard - Simple API routes for testing.

Run with: uvicorn backend.routes.fictionmail_dev:app --reload
Then visit: http://localhost:8000/dev
"""

from fastapi import FastAPI, HTTPException, Request, Body, APIRouter
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional, Dict, Any
import asyncio
import json
import time

from backend.storyteller.bible_enhancement import (
    enhance_story_bible,
    add_cameo_characters,
    update_story_history
)
from backend.storyteller.standalone_generation import generate_standalone_story
from backend.storyteller.cost_calculator import estimate_generation_cost, get_quick_cost_summary
from backend.storyteller.beat_templates import list_beat_structures, get_beat_structure_info

# Create router for use in main.py
router = APIRouter(prefix="/api/dev", tags=["FictionMail Dev"])

# Create standalone app for local testing
app = FastAPI(title="FictionMail Dev Dashboard")

# In-memory storage for dev (replace with DB later)
dev_storage = {
    "current_bible": None,
    "stories": [],
    "generation_logs": []
}


# === Pydantic Models ===

class OnboardingInput(BaseModel):
    genre: str
    setting: str
    character_pool: Optional[list] = None  # Array of {name, description}
    intensity: int = 3
    story_length: str = "short"
    premise: Optional[str] = None
    cameo_pool: Optional[list] = None
    beat_structure: str = "classic"  # classic, save_the_cat, heros_journey, truby_beats


class CameoInput(BaseModel):
    name: str
    description: str
    frequency: str = "sometimes"


class RatingInput(BaseModel):
    story_id: str
    rating: int
    feedback: Optional[Dict[str, bool]] = None


class GenerateStoryInput(BaseModel):
    email: Optional[str] = None
    voice_id: Optional[str] = None
    bible: Optional[Dict[str, Any]] = None
    force_cliffhanger: Optional[bool] = None


class CostEstimateInput(BaseModel):
    tier: str = "free"
    story_length: str = "short"
    include_audio: bool = True
    include_image: bool = True


# === API Routes ===

@router.get("/estimate-cost")
@app.get("/api/dev/estimate-cost")
async def dev_estimate_cost(
    tier: str = "free",
    story_length: str = "short",
    include_audio: bool = True,
    include_image: bool = True
):
    """
    Estimate cost for story generation before actually generating.

    Returns detailed cost breakdown for Claude API, image generation, and audio.
    """
    try:
        cost_estimate = estimate_generation_cost(
            tier=tier,
            story_length=story_length,
            include_audio=include_audio,
            include_image=include_image
        )
        return {
            "success": True,
            "estimate": cost_estimate
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cost-summary")
@app.get("/api/dev/cost-summary")
async def dev_cost_summary():
    """
    Get cost summary for all tier/length configurations.

    Useful for pricing page or comparison.
    """
    try:
        summary = get_quick_cost_summary()
        return {
            "success": True,
            "summary": summary
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/beat-structures")
@app.get("/api/dev/beat-structures")
async def dev_get_beat_structures():
    """
    Get available beat structure options (Save the Cat, Hero's Journey, etc.).
    """
    try:
        structures = list_beat_structures()
        return {
            "success": True,
            "structures": structures
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/beat-structure/{structure_id}")
@app.get("/api/dev/beat-structure/{structure_id}")
async def dev_get_beat_structure_detail(structure_id: str):
    """
    Get detailed info about a specific beat structure.
    """
    try:
        info = get_beat_structure_info(structure_id)
        if info is None:
            raise HTTPException(status_code=404, detail=f"Beat structure '{structure_id}' not found")
        return {
            "success": True,
            "structure": info
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/onboarding")
@app.post("/api/dev/onboarding")
async def dev_onboarding(data: OnboardingInput):
    """
    Step 1: Create enhanced bible from minimal user input.
    """
    try:
        dev_storage["generation_logs"] = []
        log("Starting bible enhancement...")

        bible = await enhance_story_bible(
            genre=data.genre,
            user_setting=data.setting,
            character_pool=data.character_pool,
            intensity=data.intensity,
            story_length=data.story_length,
            premise=data.premise,
            cameo_pool=data.cameo_pool,
            beat_structure=data.beat_structure
        )

        dev_storage["current_bible"] = bible

        log("Bible enhancement complete!")

        # Handle both protagonist and character_template based on genre
        char_info = bible.get("protagonist", bible.get("character_template", {}))

        return {
            "success": True,
            "bible": bible,
            "debug": {
                "input": data.dict(),
                "genre_config": bible.get("genre_config", {}),
                "character_info": char_info,
                "setting_name": bible.get("setting", {}).get("name", "N/A"),
                "intensity": bible.get("story_settings", {}).get("intensity_label", "N/A"),
                "word_target": bible.get("story_settings", {}).get("word_target", 1500)
            }
        }
    except Exception as e:
        log(f"ERROR: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/add-cameo")
@app.post("/api/dev/add-cameo")
async def dev_add_cameo(data: CameoInput):
    """
    Add a cameo character to the bible.
    """
    if not dev_storage["current_bible"]:
        raise HTTPException(status_code=400, detail="No bible created yet")

    try:
        bible = dev_storage["current_bible"]
        bible = add_cameo_characters(bible, [data.dict()])
        dev_storage["current_bible"] = bible

        return {
            "success": True,
            "cameos": bible.get("cameo_characters", [])
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate-story")
@app.post("/api/dev/generate-story")
async def dev_generate_story(data: Optional[GenerateStoryInput] = Body(default=None)):
    """
    Step 2: Generate a standalone story and optionally email it.
    """
    # Use bible from request body if provided, otherwise fall back to storage
    bible = None
    force_cliffhanger = None
    email = None
    voice_id = None

    if data:
        bible = data.bible if data.bible else dev_storage["current_bible"]
        force_cliffhanger = data.force_cliffhanger
        email = data.email
        voice_id = data.voice_id
    else:
        bible = dev_storage["current_bible"]

    if not bible:
        raise HTTPException(status_code=400, detail="No bible created yet. Complete onboarding first.")

    try:
        dev_storage["generation_logs"] = []
        tier = bible.get("user_tier", "free")

        log(f"Generating {tier} tier story...")
        if email:
            log(f"Will email story to: {email}")
        if voice_id:
            log(f"Using voice: {voice_id}")

        result = await generate_standalone_story(
            story_bible=bible,
            user_tier=tier,
            force_cliffhanger=force_cliffhanger,
            dev_mode=True,
            voice_id=voice_id
        )

        if result["success"]:
            story_data = result["story"]
            metadata = result["metadata"]

            # Store story
            story_id = f"story_{int(time.time())}"
            story_record = {
                "id": story_id,
                "title": story_data["title"],
                "narrative": story_data["narrative"],
                "word_count": story_data["word_count"],
                "genre": story_data["genre"],
                "tier": story_data["tier"],
                "is_cliffhanger": story_data["is_cliffhanger"],
                "cover_image_url": story_data.get("cover_image_url"),
                "audio_url": story_data.get("audio_url"),
                "created_at": time.time(),
                "metadata": metadata,
                "user_rating": None
            }

            dev_storage["stories"].append(story_record)

            log("Story generation complete!")

            # Send email if requested
            email_sent = False
            if email:
                try:
                    log(f"Sending email to {email}...")
                    from backend.email.database import EmailDatabase
                    from backend.email.scheduler import EmailScheduler

                    # Initialize email system
                    email_db = EmailDatabase("email_scheduler.db")
                    await email_db.connect()
                    email_scheduler = EmailScheduler(email_db)

                    # Get URLs for inline content (no file path conversion needed!)
                    audio_url = story_data.get("audio_url")  # e.g., /audio/filename.mp3
                    image_url = story_data.get("cover_image_url")  # e.g., /images/filename.png

                    # Send the story email with inline content
                    # Audio and images will be embedded inline using hosted URLs
                    # No attachments - everything is hosted and linked
                    email_sent = await email_scheduler.send_story_email(
                        user_email=email,
                        story_title=story_data["title"],
                        story_narrative=story_data["narrative"],
                        audio_url=audio_url,
                        image_url=image_url,
                        genre=story_data["genre"],
                        word_count=story_data["word_count"],
                        user_tier=story_data["tier"]
                    )

                    await email_db.close()

                    if email_sent:
                        log(f"✓ Email sent successfully to {email}")
                    else:
                        log(f"⚠️  Failed to send email to {email}")

                except Exception as e:
                    log(f"⚠️  Email error: {str(e)}")
                    import traceback
                    traceback.print_exc()

            return {
                "success": True,
                "story": story_record,
                "email_sent": email_sent,
                "debug": {
                    "beat_plan": metadata.get("beat_plan", {}),
                    "plot_type": metadata.get("plot_type", "unknown"),
                    "generation_time": metadata.get("generation_time_seconds", 0),
                    "template_used": metadata.get("template_used", "unknown"),
                    "consistency_status": metadata.get("consistency_report", {}).get("status", "unknown")
                }
            }
        else:
            log(f"ERROR: {result.get('error', 'Unknown error')}")
            raise HTTPException(status_code=500, detail=result.get("error", "Generation failed"))

    except Exception as e:
        log(f"ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/rate-story")
@app.post("/api/dev/rate-story")
async def dev_rate_story(data: RatingInput):
    """
    Step 3: Rate a story and update preferences.
    """
    # Find story
    story = None
    for s in dev_storage["stories"]:
        if s["id"] == data.story_id:
            story = s
            break

    if not story:
        raise HTTPException(status_code=404, detail="Story not found")

    # Update story rating
    story["user_rating"] = data.rating

    # Update bible preferences
    if dev_storage["current_bible"]:
        bible = dev_storage["current_bible"]
        bible = update_story_history(
            bible=bible,
            story_summary=story["metadata"]["summary"],
            plot_type=story["metadata"]["plot_type"],
            rating=data.rating,
            feedback=data.feedback or {}
        )
        dev_storage["current_bible"] = bible

    return {
        "success": True,
        "updated_preferences": dev_storage["current_bible"].get("user_preferences", {})
    }


@router.get("/bible")
@app.get("/api/dev/bible")
async def dev_get_bible():
    """Get current bible."""
    if not dev_storage["current_bible"]:
        raise HTTPException(status_code=404, detail="No bible created yet")

    return dev_storage["current_bible"]


@router.get("/stories")
@app.get("/api/dev/stories")
async def dev_get_stories():
    """Get all generated stories."""
    return {
        "stories": dev_storage["stories"],
        "total": len(dev_storage["stories"])
    }


@router.get("/story/{story_id}")
@app.get("/api/dev/story/{story_id}")
async def dev_get_story(story_id: str):
    """Get a specific story."""
    for story in dev_storage["stories"]:
        if story["id"] == story_id:
            return story

    raise HTTPException(status_code=404, detail="Story not found")


@router.delete("/reset")
@app.delete("/api/dev/reset")
async def dev_reset():
    """Reset all dev storage."""
    dev_storage["current_bible"] = None
    dev_storage["stories"] = []
    dev_storage["generation_logs"] = []
    return {"success": True, "message": "Dev storage reset"}


@router.get("/logs")
@app.get("/api/dev/logs")
async def dev_get_logs():
    """Get generation logs."""
    return {"logs": dev_storage["generation_logs"]}


# === HTML UI ===

@app.get("/dev", response_class=HTMLResponse)
async def dev_dashboard():
    """Main dev dashboard UI."""
    return """
<!DOCTYPE html>
<html>
<head>
    <title>FictionMail Dev Dashboard</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: #0a0a0a;
            color: #e0e0e0;
            line-height: 1.6;
        }

        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
        }

        header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 30px;
            border-radius: 12px;
            margin-bottom: 30px;
        }

        h1 {
            font-size: 2.5rem;
            margin-bottom: 10px;
        }

        .subtitle {
            opacity: 0.9;
            font-size: 1.1rem;
        }

        .grid {
            display: grid;
            grid-template-columns: 1fr 400px;
            gap: 20px;
            margin-bottom: 20px;
        }

        @media (max-width: 1024px) {
            .grid { grid-template-columns: 1fr; }
        }

        .card {
            background: #1a1a1a;
            border: 1px solid #333;
            border-radius: 12px;
            padding: 25px;
        }

        .card h2 {
            color: #667eea;
            margin-bottom: 20px;
            font-size: 1.5rem;
        }

        .form-group {
            margin-bottom: 20px;
        }

        label {
            display: block;
            margin-bottom: 8px;
            color: #aaa;
            font-weight: 500;
        }

        input, textarea, select {
            width: 100%;
            padding: 12px;
            background: #0a0a0a;
            border: 1px solid #333;
            border-radius: 6px;
            color: #e0e0e0;
            font-size: 1rem;
        }

        textarea {
            resize: vertical;
            min-height: 80px;
        }

        button {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 6px;
            font-size: 1rem;
            font-weight: 600;
            cursor: pointer;
            transition: transform 0.2s, opacity 0.2s;
        }

        button:hover {
            transform: translateY(-2px);
            opacity: 0.9;
        }

        button:active {
            transform: translateY(0);
        }

        button:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }

        .btn-secondary {
            background: #333;
        }

        .btn-danger {
            background: #dc3545;
        }

        .debug-panel {
            background: #0a0a0a;
            border: 1px solid #333;
            border-radius: 6px;
            padding: 15px;
            font-family: 'Courier New', monospace;
            font-size: 0.85rem;
            max-height: 400px;
            overflow-y: auto;
        }

        .log-entry {
            padding: 4px 0;
            border-bottom: 1px solid #222;
        }

        .log-entry:last-child {
            border-bottom: none;
        }

        .story-display {
            background: #f9f9f9;
            color: #1a1a1a;
            padding: 40px;
            border-radius: 12px;
            line-height: 1.8;
            font-size: 1.1rem;
        }

        .story-title {
            font-size: 2rem;
            margin-bottom: 30px;
            color: #667eea;
            text-align: center;
        }

        .story-meta {
            text-align: center;
            color: #666;
            margin-bottom: 30px;
            font-size: 0.9rem;
        }

        .story-text {
            white-space: pre-wrap;
        }

        .rating-stars {
            display: flex;
            gap: 10px;
            font-size: 2rem;
            margin: 20px 0;
        }

        .rating-stars span {
            cursor: pointer;
            opacity: 0.3;
            transition: opacity 0.2s;
        }

        .rating-stars span:hover,
        .rating-stars span.active {
            opacity: 1;
        }

        .status {
            padding: 20px;
            border-radius: 6px;
            margin-bottom: 20px;
            text-align: center;
        }

        .status.loading {
            background: #1a3a52;
            border: 1px solid #2563eb;
        }

        .status.success {
            background: #1a3a2e;
            border: 1px solid #10b981;
        }

        .status.error {
            background: #3a1a1a;
            border: 1px solid #dc3545;
        }

        .hidden {
            display: none;
        }

        .spinner {
            display: inline-block;
            width: 20px;
            height: 20px;
            border: 3px solid rgba(255,255,255,0.3);
            border-top-color: white;
            border-radius: 50%;
            animation: spin 1s linear infinite;
        }

        @keyframes spin {
            to { transform: rotate(360deg); }
        }

        .checkbox-group {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 10px;
        }

        .checkbox-item {
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .checkbox-item input {
            width: auto;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>📧 FictionMail Dev Dashboard</h1>
            <p class="subtitle">Test the complete story generation flow with visible debug info</p>
        </header>

        <div id="app">
            <!-- Step 1: Onboarding -->
            <div id="onboarding-section">
                <div class="grid">
                    <div class="card">
                        <h2>Step 1: Create Your Story World</h2>

                        <div class="form-group">
                            <label>Genre</label>
                            <select id="genre">
                                <option value="scifi">🚀 Sci-Fi</option>
                                <option value="mystery">🔍 Mystery</option>
                                <option value="romance">💕 Romance</option>
                                <option value="sitcom">😄 Sitcom</option>
                            </select>
                        </div>

                        <div class="form-group">
                            <label>Setting (1-2 sentences)</label>
                            <textarea id="setting" placeholder="Space station on the edge of known space"></textarea>
                        </div>

                        <div class="form-group">
                            <label>Main Character Name (optional)</label>
                            <input type="text" id="characterName" placeholder="Elena">
                        </div>

                        <div class="form-group">
                            <label>Tier</label>
                            <select id="tier">
                                <option value="free">Free (1500 words)</option>
                                <option value="premium">Premium (4500 words)</option>
                            </select>
                        </div>

                        <button onclick="createBible()">
                            ✨ Enhance Bible & Continue
                        </button>
                    </div>

                    <div class="card">
                        <h2>🔧 Debug Logs</h2>
                        <div id="logs" class="debug-panel">
                            <div class="log-entry">Ready to start...</div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Step 2: Bible Preview & Generate -->
            <div id="bible-section" class="hidden">
                <div class="card">
                    <h2>Step 2: Generate Your Story</h2>

                    <div id="bible-preview" class="debug-panel" style="max-height: 300px; margin-bottom: 20px;">
                        <!-- Bible will be shown here -->
                    </div>

                    <button onclick="generateStory()">
                        🎬 Generate Story
                    </button>

                    <button onclick="resetAll()" class="btn-danger" style="margin-left: 10px;">
                        🔄 Start Over
                    </button>
                </div>
            </div>

            <!-- Step 3: Story Display -->
            <div id="story-section" class="hidden">
                <div class="card">
                    <div id="story-content" class="story-display">
                        <!-- Story will be displayed here -->
                    </div>

                    <h2 style="margin-top: 30px;">Rate This Story</h2>

                    <div class="rating-stars" id="rating-stars">
                        <span data-rating="1">⭐</span>
                        <span data-rating="2">⭐</span>
                        <span data-rating="3">⭐</span>
                        <span data-rating="4">⭐</span>
                        <span data-rating="5">⭐</span>
                    </div>

                    <div id="feedback-section" class="hidden">
                        <h3>What did you like/dislike?</h3>
                        <div class="checkbox-group" id="feedback-options">
                            <!-- Will be populated based on rating -->
                        </div>
                    </div>

                    <button onclick="submitRating()" id="submit-rating-btn" class="hidden">
                        Submit Rating
                    </button>

                    <button onclick="generateAnother()" style="margin-left: 10px;">
                        Generate Another Story
                    </button>
                </div>

                <div class="card" style="margin-top: 20px;">
                    <h2>🔍 Debug Info</h2>
                    <div id="debug-info" class="debug-panel">
                        <!-- Debug info will be shown here -->
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        let currentBible = null;
        let currentStory = null;
        let selectedRating = 0;
        let selectedFeedback = {};

        function log(message) {
            const logsDiv = document.getElementById('logs');
            const entry = document.createElement('div');
            entry.className = 'log-entry';
            entry.textContent = `[${new Date().toLocaleTimeString()}] ${message}`;
            logsDiv.appendChild(entry);
            logsDiv.scrollTop = logsDiv.scrollHeight;
        }

        async function createBible() {
            log('Creating enhanced bible...');

            const genre = document.getElementById('genre').value;
            const setting = document.getElementById('setting').value;
            const characterName = document.getElementById('characterName').value;
            const tier = document.getElementById('tier').value;

            if (!setting.trim()) {
                alert('Please enter a setting');
                return;
            }

            try {
                const response = await fetch('/api/dev/onboarding', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({genre, setting, character_name: characterName || null, tier})
                });

                const data = await response.json();

                if (data.success) {
                    currentBible = data.bible;
                    log('✓ Bible enhanced successfully!');

                    // Show bible preview
                    document.getElementById('bible-preview').innerHTML = `
                        <strong>Setting:</strong> ${data.bible.setting.name}<br>
                        <strong>Protagonist:</strong> ${data.bible.protagonist.name} (${data.bible.protagonist.role})<br>
                        <strong>Defining Trait:</strong> ${data.bible.protagonist.defining_characteristic}<br>
                        <strong>Tone:</strong> ${data.bible.tone}<br>
                        <strong>Themes:</strong> ${data.bible.themes.join(', ')}<br>
                        <br>
                        <details>
                            <summary>View Full Bible JSON</summary>
                            <pre>${JSON.stringify(data.bible, null, 2)}</pre>
                        </details>
                    `;

                    // Show bible section, hide onboarding
                    document.getElementById('onboarding-section').classList.add('hidden');
                    document.getElementById('bible-section').classList.remove('hidden');
                } else {
                    log('✗ Error creating bible');
                    alert('Error: ' + JSON.stringify(data));
                }
            } catch (error) {
                log('✗ Error: ' + error.message);
                alert('Error: ' + error.message);
            }
        }

        async function generateStory() {
            log('Generating story...');
            log('This may take 2-3 minutes...');

            try {
                const response = await fetch('/api/dev/generate-story', {
                    method: 'POST'
                });

                const data = await response.json();

                if (data.success) {
                    currentStory = data.story;
                    log('✓ Story generated successfully!');
                    log(`Word count: ${data.story.word_count}`);
                    log(`Generation time: ${data.debug.generation_time.toFixed(2)}s`);

                    // Display story
                    document.getElementById('story-content').innerHTML = `
                        <div class="story-title">${data.story.title}</div>
                        <div class="story-meta">
                            ${data.story.genre} • ${data.story.word_count} words • ${data.story.tier} tier
                            ${data.story.is_cliffhanger ? ' • 🪝 Cliffhanger' : ''}
                        </div>
                        <div class="story-text">${data.story.narrative}</div>
                    `;

                    // Display debug info
                    document.getElementById('debug-info').innerHTML = `
                        <strong>Plot Type:</strong> ${data.debug.plot_type}<br>
                        <strong>Template:</strong> ${data.debug.template_used}<br>
                        <strong>Generation Time:</strong> ${data.debug.generation_time.toFixed(2)}s<br>
                        <strong>Consistency Status:</strong> ${data.debug.consistency_status}<br>
                        <br>
                        <details>
                            <summary>View Beat Plan</summary>
                            <pre>${JSON.stringify(data.debug.beat_plan, null, 2)}</pre>
                        </details>
                    `;

                    // Show story section, hide bible section
                    document.getElementById('bible-section').classList.add('hidden');
                    document.getElementById('story-section').classList.remove('hidden');

                    // Reset rating
                    setupRating();
                } else {
                    log('✗ Error generating story');
                    alert('Error: ' + (data.error || 'Unknown error'));
                }
            } catch (error) {
                log('✗ Error: ' + error.message);
                alert('Error: ' + error.message);
            }
        }

        function setupRating() {
            const stars = document.querySelectorAll('#rating-stars span');
            stars.forEach(star => {
                star.classList.remove('active');
                star.onclick = () => selectRating(parseInt(star.dataset.rating));
            });
            selectedRating = 0;
            document.getElementById('feedback-section').classList.add('hidden');
            document.getElementById('submit-rating-btn').classList.add('hidden');
        }

        function selectRating(rating) {
            selectedRating = rating;

            // Update star display
            const stars = document.querySelectorAll('#rating-stars span');
            stars.forEach((star, index) => {
                if (index < rating) {
                    star.classList.add('active');
                } else {
                    star.classList.remove('active');
                }
            });

            // Show feedback options
            const feedbackDiv = document.getElementById('feedback-options');

            if (rating >= 4) {
                feedbackDiv.innerHTML = `
                    <div class="checkbox-item"><input type="checkbox" id="fb-pacing" value="great_pacing"><label for="fb-pacing">Great pacing</label></div>
                    <div class="checkbox-item"><input type="checkbox" id="fb-characters" value="loved_characters"><label for="fb-characters">Loved characters</label></div>
                    <div class="checkbox-item"><input type="checkbox" id="fb-mystery" value="good_mystery"><label for="fb-mystery">Good mystery</label></div>
                    <div class="checkbox-item"><input type="checkbox" id="fb-twist" value="surprising_twist"><label for="fb-twist">Surprising twist</label></div>
                    <div class="checkbox-item"><input type="checkbox" id="fb-emotional" value="emotional_moments"><label for="fb-emotional">Emotional moments</label></div>
                `;
            } else if (rating <= 2) {
                feedbackDiv.innerHTML = `
                    <div class="checkbox-item"><input type="checkbox" id="fb-slow" value="too_slow"><label for="fb-slow">Too slow</label></div>
                    <div class="checkbox-item"><input type="checkbox" id="fb-action" value="not_enough_action"><label for="fb-action">Not enough action</label></div>
                    <div class="checkbox-item"><input type="checkbox" id="fb-chars" value="characters_felt_off"><label for="fb-chars">Characters felt off</label></div>
                    <div class="checkbox-item"><input type="checkbox" id="fb-plot" value="confusing_plot"><label for="fb-plot">Confusing plot</label></div>
                `;
            } else {
                feedbackDiv.innerHTML = '<p>Thanks for the rating!</p>';
            }

            document.getElementById('feedback-section').classList.remove('hidden');
            document.getElementById('submit-rating-btn').classList.remove('hidden');
        }

        async function submitRating() {
            if (!selectedRating) {
                alert('Please select a rating');
                return;
            }

            // Collect feedback
            const feedback = {};
            document.querySelectorAll('#feedback-options input:checked').forEach(cb => {
                feedback[cb.value] = true;
            });

            log(`Submitting rating: ${selectedRating} stars`);

            try {
                const response = await fetch('/api/dev/rate-story', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        story_id: currentStory.id,
                        rating: selectedRating,
                        feedback: feedback
                    })
                });

                const data = await response.json();

                if (data.success) {
                    log('✓ Rating submitted! Preferences updated.');
                    alert('Rating saved! Generate another story to see how preferences adapt.');
                }
            } catch (error) {
                log('✗ Error submitting rating: ' + error.message);
            }
        }

        function generateAnother() {
            document.getElementById('story-section').classList.add('hidden');
            document.getElementById('bible-section').classList.remove('hidden');
            log('Ready to generate another story...');
        }

        async function resetAll() {
            if (confirm('Reset everything and start over?')) {
                await fetch('/api/dev/reset', {method: 'DELETE'});
                location.reload();
            }
        }
    </script>
</body>
</html>
"""


# === Helper Functions ===

def log(message: str):
    """Add a log entry to the dev storage."""
    dev_storage["generation_logs"].append({
        "timestamp": time.time(),
        "message": message
    })


# === Run Instructions ===

if __name__ == "__main__":
    import uvicorn
    print("\n" + "="*70)
    print("FictionMail Dev Dashboard")
    print("="*70)
    print("\nStarting server...")
    print("Visit: http://localhost:8000/dev")
    print("\nPress Ctrl+C to stop")
    print("="*70 + "\n")

    uvicorn.run(app, host="0.0.0.0", port=8000)
