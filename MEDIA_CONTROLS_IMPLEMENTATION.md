# Media Controls Implementation Plan

## Overview
Add frontend toggles for audio/image generation and voice selection, while keeping audio always-on for email mode.

## Status: ✅ COMPLETE

### ✅ Completed
1. Added `generate_audio`, `generate_image`, `voice_id` to frontend types (`frontend/src/types/story.ts`)
2. Added same fields to backend request models (`backend/models/state.py`)
3. Added media settings to `StoryState` TypedDict
4. Updated `create_initial_state()` to accept media settings
5. Updated API routes to pass settings from request to state (`backend/api/routes.py`)
6. Updated `generate_audio_node` to check state settings (`backend/storyteller/nodes.py:815`)
7. Updated `generate_image_node` to check state settings (`backend/storyteller/nodes.py:680`)
8. Added frontend MediaControls component (`frontend/src/components/MediaControls.tsx`)
9. Updated `useStory` hook to manage media settings (`frontend/src/hooks/useStory.ts`)
10. Integrated MediaControls into App with dev mode toggle (`frontend/src/App.tsx`)

### ⏳ TODO
- Test end-to-end functionality

---

## Detailed Implementation Steps

### STEP 5: Update API Routes (backend/api/routes.py)

**File:** `backend/api/routes.py`
**Lines:** ~250-260 (start_story), ~340-350 (continue_story)

```python
# In start_story():
initial_state = create_initial_state(
    user_id=user_id,
    world_id=request.world_id,
    credits=config.CREDITS_PER_NEW_USER,
    total_chapters=config.TOTAL_CHAPTERS,
    generate_audio=request.generate_audio,  # ADD THIS
    generate_image=request.generate_image,  # ADD THIS
    voice_id=request.voice_id              # ADD THIS
)

# In continue_story():
# Need to pass media settings to run_story_turn or add to state update
# This requires checking how state is updated between turns
```

### STEP 6: Update generate_audio_node (backend/storyteller/nodes.py)

**File:** `backend/storyteller/nodes.py`
**Function:** `generate_audio_node` (line ~815)

```python
async def generate_audio_node(state: StoryState) -> dict[str, Any]:
    # Check state-level override first, then config
    should_generate = state.get("generate_audio")
    if should_generate is None:
        should_generate = config.ENABLE_MEDIA_GENERATION and config.can_generate_audio
    elif should_generate:
        # User wants audio, but check if we CAN generate
        should_generate = config.can_generate_audio

    if not should_generate:
        print("⏭️  Skipping audio generation (disabled)")
        return {"audio_url": None}

    # Get voice ID from state or config
    voice_id = state.get("voice_id") or config.ELEVENLABS_VOICE_ID

    # Use voice_id in generation call (line ~871)
    audio_generator = client.text_to_speech.convert(
        voice_id=voice_id,  # Use state override or config
        text=narrative_text,
        model_id="eleven_flash_v2_5",
        voice_settings={"stability": 0.5, "similarity_boost": 0.75}
    )
```

### STEP 7: Update generate_image_node (backend/storyteller/nodes.py)

**File:** `backend/storyteller/nodes.py`
**Function:** `generate_image_node` (line ~680)

```python
async def generate_image_node(state: StoryState) -> dict[str, Any]:
    # Check state-level override first, then config
    should_generate = state.get("generate_image")
    if should_generate is None:
        should_generate = config.ENABLE_MEDIA_GENERATION and config.can_generate_images
    elif should_generate:
        # User wants image, but check if we CAN generate
        should_generate = config.can_generate_images

    if not should_generate:
        print("⏭️  Skipping image generation (disabled)")
        return {"image_url": None}

    # Rest of existing logic...
```

### STEP 8-10: Frontend UI Components

Create a new component for media controls:

**File:** `frontend/src/components/MediaControls.tsx` (NEW FILE)

```typescript
import { useState } from 'react';

interface MediaControlsProps {
  onAudioToggle: (enabled: boolean) => void;
  onImageToggle: (enabled: boolean) => void;
  onVoiceChange: (voiceId: string) => void;
  audioEnabled: boolean;
  imageEnabled: boolean;
  selectedVoice: string;
}

export function MediaControls({
  onAudioToggle,
  onImageToggle,
  onVoiceChange,
  audioEnabled,
  imageEnabled,
  selectedVoice
}: MediaControlsProps) {
  // ElevenLabs voice options
  const voices = [
    { id: '21m00Tcm4TlvDq8ikWAM', name: 'Rachel (Default)' },
    { id: 'AZnzlk1XvdvUeBnXmlld', name: 'Domi' },
    { id: 'EXAVITQu4vr4xnSDxMaL', name: 'Bella' },
    { id: 'ErXwobaYiN019PkySvjV', name: 'Antoni' },
    { id: 'MF3mGyEYCl7XYWbV9V6O', name: 'Elli' },
    { id: 'TxGEqnHWrfWFTfGW9XjX', name: 'Josh' },
    { id: 'VR6AewLTigWG4xSOukaG', name: 'Arnold' },
    { id: 'pNInz6obpgDQGcFmaJgB', name: 'Adam' },
    { id: 'yoZ06aMxZJJ28mfd3POQ', name: 'Sam' },
  ];

  return (
    <div className="media-controls">
      <h3>Media Settings (Dev Mode)</h3>

      <label>
        <input
          type="checkbox"
          checked={audioEnabled}
          onChange={(e) => onAudioToggle(e.target.checked)}
        />
        Generate Audio (saves ElevenLabs credits when off)
      </label>

      {audioEnabled && (
        <label>
          Voice:
          <select value={selectedVoice} onChange={(e) => onVoiceChange(e.target.value)}>
            {voices.map(voice => (
              <option key={voice.id} value={voice.id}>
                {voice.name}
              </option>
            ))}
          </select>
        </label>
      )}

      <label>
        <input
          type="checkbox"
          checked={imageEnabled}
          onChange={(e) => onImageToggle(e.target.checked)}
        />
        Generate Images (saves Replicate credits when off)
      </label>
    </div>
  );
}
```

**Update:** `frontend/src/hooks/useStory.ts`

Add state for media controls and pass to API calls:

```typescript
const [mediaSettings, setMediaSettings] = useState({
  audioEnabled: true,
  imageEnabled: true,
  voiceId: '21m00Tcm4TlvDq8ikWAM' // Rachel default
});

// In startStory:
const response = await api.startStory({
  world_id: worldId,
  generate_audio: mediaSettings.audioEnabled,
  generate_image: mediaSettings.imageEnabled,
  voice_id: mediaSettings.voiceId
});

// In continueStory:
const response = await api.continueStory({
  session_id: state.sessionId,
  choice_id: choice.id,
  generate_audio: mediaSettings.audioEnabled,
  generate_image: mediaSettings.imageEnabled,
  voice_id: mediaSettings.voiceId
});
```

---

## Email Mode Behavior

**Important:** Email generation should IGNORE frontend toggles and always generate audio.

In `backend/email/scheduler.py`, when generating chapters for email:
- Always pass `generate_audio=True` (ignore any stored preference)
- Always pass `generate_image=True` (email needs images)
- Use configured voice_id from database or default

---

## Testing Checklist

- [ ] Start story with audio OFF → no audio generated
- [ ] Start story with audio ON → audio generated
- [ ] Change voice selection → different voice used
- [ ] Toggle image generation → images skipped when OFF
- [ ] Verify email mode always generates audio regardless of toggles
- [ ] Check console logs show "Skipping audio generation (disabled)" when off

---

## Benefits

1. **Cost Savings**: Test story generation without burning API credits
2. **Faster Development**: Skip slow image/audio generation during testing
3. **Voice Testing**: Easily try different voices for narration
4. **Email Quality**: Ensure email deliveries always have full media
