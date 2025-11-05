# Narrative Streaming Feature Guide

## Overview

The West Haven Story app now supports **word-by-word narrative streaming** for an immersive, thoughtful reading experience. Instead of showing all text at once, words appear sequentially at a configurable pace (default: 7.5 words/second).

## Backend Configuration

### Environment Variables

```bash
# Enable streaming (default: true)
ENABLE_STREAMING=true

# Words per second (5-10 recommended for thoughtful pacing)
STREAMING_WORDS_PER_SECOND=7.5
```

## API Endpoints

### 1. Start Story (Streaming)

**POST** `/api/story/start/stream`

Starts a new story session and streams the opening narrative.

**Request Body:**
```json
{
  "world_id": "west_haven",
  "user_id": "optional-user-id"
}
```

### 2. Continue Story (Streaming)

**POST** `/api/story/continue/stream`

Continues an existing story and streams the next narrative segment.

**Request Body:**
```json
{
  "session_id": "your-session-id",
  "choice_id": 1
}
```

## Event Stream Format

Both endpoints return Server-Sent Events (SSE) with `Content-Type: text/event-stream`.

### Event Types

#### 1. `session` (start only)
```json
{
  "type": "session",
  "session_id": "uuid",
  "user_id": "uuid",
  "world_id": "west_haven"
}
```

#### 2. `thinking`
```json
{
  "type": "thinking",
  "message": "Weaving your story..."
}
```

#### 3. `narrative_start`
```json
{
  "type": "narrative_start",
  "total_words": 150
}
```

#### 4. `word` (streamed individually)
```json
{
  "type": "word",
  "word": "The",
  "index": 0
}
```

#### 5. `narrative_end`
```json
{
  "type": "narrative_end"
}
```

#### 6. `choices`
```json
{
  "type": "choices",
  "choices": [
    {
      "id": 1,
      "text": "She stepped forward cautiously...",
      "tone": "cautious"
    }
  ]
}
```

#### 7. `image` (optional)
```json
{
  "type": "image",
  "url": "/images/scene_123.png"
}
```

#### 8. `audio` (optional)
```json
{
  "type": "audio",
  "url": "/audio/narration_123.mp3"
}
```

#### 9. `complete`
```json
{
  "type": "complete",
  "beat": 1,
  "credits": 24,
  "session_id": "uuid"
}
```

#### 10. `error`
```json
{
  "type": "error",
  "message": "Error description"
}
```

## Frontend Implementation Example

### React with EventSource

```typescript
import { useEffect, useState } from 'react';

interface StreamingNarrativeProps {
  sessionId?: string;
  worldId?: string;
  choiceId?: number;
  onComplete?: (data: any) => void;
}

export function StreamingNarrative({
  sessionId,
  worldId,
  choiceId,
  onComplete
}: StreamingNarrativeProps) {
  const [words, setWords] = useState<string[]>([]);
  const [choices, setChoices] = useState<any[]>([]);
  const [thinking, setThinking] = useState(true);
  const [showChoices, setShowChoices] = useState(false);

  useEffect(() => {
    // Determine endpoint and payload
    const endpoint = sessionId
      ? '/api/story/continue/stream'
      : '/api/story/start/stream';

    const payload = sessionId
      ? { session_id: sessionId, choice_id: choiceId }
      : { world_id: worldId };

    // Use fetch for POST SSE (EventSource doesn't support POST)
    const fetchStream = async () => {
      const response = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();

      while (true) {
        const { done, value } = await reader!.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split('\n');

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = JSON.parse(line.slice(6));
            handleEvent(data);
          }
        }
      }
    };

    fetchStream();
  }, [sessionId, worldId, choiceId]);

  const handleEvent = (event: any) => {
    switch (event.type) {
      case 'thinking':
        setThinking(true);
        break;

      case 'narrative_start':
        setThinking(false);
        setWords([]);
        break;

      case 'word':
        setWords(prev => [...prev, event.word]);
        break;

      case 'narrative_end':
        // Brief pause before showing choices
        setTimeout(() => setShowChoices(true), 300);
        break;

      case 'choices':
        setChoices(event.choices);
        break;

      case 'complete':
        onComplete?.(event);
        break;

      case 'error':
        console.error('Streaming error:', event.message);
        break;
    }
  };

  return (
    <div className="narrative-container">
      {thinking && (
        <div className="thinking-indicator">
          ✨ Weaving your story...
        </div>
      )}

      <div className="narrative-text">
        {words.map((word, i) => (
          <span
            key={i}
            className="word fade-in-up"
            style={{ animationDelay: `${i * 0.02}s` }}
          >
            {word}{' '}
          </span>
        ))}
      </div>

      {showChoices && (
        <div className="choices fade-in">
          {choices.map((choice) => (
            <button
              key={choice.id}
              className="choice-button"
              onClick={() => handleChoice(choice.id)}
            >
              {choice.text}
            </button>
          ))}
        </div>
      )}

      {/* Skip button (subtle, at bottom) */}
      <button
        className="skip-button"
        onClick={() => skipToEnd()}
        style={{
          position: 'fixed',
          bottom: '20px',
          right: '20px',
          opacity: 0.3,
          fontSize: '12px'
        }}
      >
        Skip ⏭
      </button>
    </div>
  );
}
```

### CSS Animations (Recommended)

```css
/* Fade in + Slide up animation for each word */
.word {
  display: inline-block;
  opacity: 0;
  animation: fadeInUp 0.4s ease-out forwards;
}

@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(5px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* Fade in for choices */
.choices {
  animation: fadeIn 0.5s ease-out;
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

/* Thinking indicator pulse */
.thinking-indicator {
  animation: pulse 1.5s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}
```

## UX Recommendations

### 1. **Skip to End Feature**
- Place button subtly at bottom-right
- Low opacity (0.3) to not draw attention
- Only for power users / developers

```typescript
const skipToEnd = () => {
  // Abort streaming
  eventSource.close();

  // Immediately show full narrative (fetch non-streaming endpoint)
  // OR set all words instantly
  setWords(fullNarrative.split(' '));
  setShowChoices(true);
};
```

### 2. **Speed Control (Optional)**
- Allow users to adjust `STREAMING_WORDS_PER_SECOND` via settings
- Store preference in localStorage
- Range: 5-15 words/second

### 3. **Accessibility**
- Ensure screen readers can access full text
- Provide "Read instantly" option for users who prefer it
- Respect `prefers-reduced-motion` CSS media query

```css
@media (prefers-reduced-motion: reduce) {
  .word {
    animation: none;
    opacity: 1;
  }
}
```

### 4. **Sound Effects (Optional)**
- Subtle typewriter click per word (very soft)
- Toggle on/off in settings
- Volume control slider

## Testing

### Manual Test with curl

```bash
# Start a story
curl -N -X POST http://localhost:8000/api/story/start/stream \
  -H "Content-Type: application/json" \
  -d '{"world_id": "west_haven"}'

# Continue a story (replace with real session_id)
curl -N -X POST http://localhost:8000/api/story/continue/stream \
  -H "Content-Type: application/json" \
  -d '{"session_id": "your-session-id", "choice_id": 1}'
```

The `-N` flag prevents buffering so you see words stream in real-time.

## Performance Notes

- **Backend**: FastAPI async streaming is efficient, handles multiple concurrent streams
- **Frontend**: DOM updates per word are lightweight with proper React keys
- **Network**: SSE uses persistent connection, minimal overhead
- **Memory**: Words array grows linearly with narrative length (typically 100-300 words)

## Future Enhancements

- [ ] Pause/Resume streaming
- [ ] Variable speed for dramatic moments (slow down during important scenes)
- [ ] Word emphasis (bold/italic certain words as they appear)
- [ ] Background ambiance that changes with narrative tone
- [ ] Reading progress indicator
- [ ] Replay last narrative option

---

**Questions or issues?** Check the Railway deployment logs for streaming errors.
