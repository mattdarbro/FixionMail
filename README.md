# FixionMail

Personalized daily stories delivered to your inbox.

## Overview

FixionMail generates unique short stories based on user preferences - genre, setting, characters, and intensity. Stories are delivered with cover art and audio narration.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    2-Agent System                        │
├─────────────────────────────────────────────────────────┤
│  WriterAgent (Claude Sonnet/Opus)                       │
│  → Generates complete story from beat template          │
│                                                         │
│  JudgeAgent (Claude Haiku)                              │
│  → Validates quality, consistency, word count           │
│  → Provides feedback for rewrites if needed             │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│                    Media Generation                      │
├─────────────────────────────────────────────────────────┤
│  Image: Replicate (Imagen-3 Fast)                       │
│  Audio: OpenAI TTS                                      │
│  Email: Resend                                          │
└─────────────────────────────────────────────────────────┘
```

## Tech Stack

- **Backend**: Python 3.11+, FastAPI
- **Story AI**: Anthropic Claude (Sonnet 4.5 / Opus 4.5 / Haiku)
- **Images**: Replicate (Google Imagen-3)
- **Audio**: OpenAI TTS
- **Email**: Resend

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export ANTHROPIC_API_KEY=sk-ant-...
export OPENAI_API_KEY=sk-...
export REPLICATE_API_TOKEN=r8_...
export RESEND_API_KEY=re_...

# Run dev server
uvicorn backend.api.main:app --reload

# Open dev dashboard
open http://localhost:8000/dev
```

## Key Features

- **Genre Selection**: Romance, Mystery, Fantasy, Cozy, Sci-Fi, Western, etc.
- **Beat Templates**: Save the Cat, Hero's Journey, Truby, Classic structures
- **Intensity Slider**: Cozy → Moderate → Intense
- **Model Selection**: Sonnet (fast) or Opus (premium)
- **Name Deduplication**: Tracks used names to avoid repetition

## Documentation

- `Refactor_Plan.md` - Current roadmap and phase status
- `RAILWAY.md` - Deployment guide
- `MODELS_VOICES.md` - Available AI models and voices

## Project Status

See `Refactor_Plan.md` for current phase and roadmap.
