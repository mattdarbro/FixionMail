# FixionMail Fresh Build Plan

## Overview
FixionMail is a **scheduled background service** that generates and emails daily stories to subscribers. No dashboard triggers - stories generate automatically on a schedule.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                 SCHEDULER (APScheduler)                  │
│                  runs daily at configured time           │
└─────────────────────┬───────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────┐
│              FOR EACH ACTIVE SUBSCRIBER                  │
│  1. Load user preferences / story bible                  │
│  2. Generate story (Claude Writer Agent)                 │
│  3. Validate story (Haiku Judge Agent)                   │
│  4. Generate audio (OpenAI TTS)                          │
│  5. Send email (Resend)                                  │
│  6. Log to database                                      │
└─────────────────────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────┐
│              ADMIN DASHBOARD (read-only)                 │
│  - View sent stories                                     │
│  - Monitor costs                                         │
│  - See error logs                                        │
│  - Manage subscribers                                    │
└─────────────────────────────────────────────────────────┘
```

## Directory Structure

```
fixionmail/
├── app/
│   ├── main.py              # FastAPI app entry point
│   ├── config.py            # Pydantic settings
│   ├── scheduler.py         # APScheduler daily job runner
│   │
│   ├── agents/
│   │   ├── writer.py        # Claude Sonnet - story generation
│   │   └── judge.py         # Claude Haiku - validation/editing
│   │
│   ├── services/
│   │   ├── tts.py           # OpenAI TTS only
│   │   ├── email.py         # Resend integration
│   │   └── storage.py       # Supabase/local file storage
│   │
│   ├── models/
│   │   ├── subscriber.py    # User, preferences, bible
│   │   └── story.py         # Generated story, audio, metadata
│   │
│   ├── db/
│   │   ├── database.py      # SQLite/Postgres connection
│   │   └── migrations/      # Alembic migrations
│   │
│   └── dashboard/
│       ├── routes.py        # Admin API endpoints
│       └── templates/       # Admin UI (optional)
│
├── prompts/
│   ├── writer_system.txt    # Writer agent system prompt
│   ├── writer_story.txt     # Story generation prompt
│   ├── judge_system.txt     # Judge agent system prompt
│   └── beat_templates.py    # Genre-specific story structures
│
├── templates/
│   └── email/
│       └── story.html       # Email template
│
├── tests/
├── requirements.txt
├── Dockerfile
└── README.md
```

## Two-Agent System

### Writer Agent (Claude Sonnet)
- Takes: story bible, genre, beat structure, word count target
- Returns: complete story prose
- Cost: ~$0.02-0.05 per story

### Judge Agent (Claude Haiku)
- Takes: generated story + original requirements
- Checks: genre match, tone consistency, pacing, word count
- Returns: pass/fail + feedback
- If fail: Writer rewrites with feedback
- Cost: ~$0.001 per validation (10x cheaper than Sonnet)

## What to Port from west-haven-story

### Keep (copy these files):
- `backend/storyteller/prompts_v2.py` - world template logic
- `backend/storyteller/beat_templates.py` - story structure templates
- `backend/storyteller/bible_enhancement.py` - AI bible creation
- `backend/storyteller/cost_calculator.py` - update for 2-agent system
- `backend/storage.py` - Supabase/local abstraction
- `backend/email/scheduler.py` - email templates (the HTML rendering)
- `backend/config.py` - Pydantic settings pattern

### Drop:
- `nodes.py` - LangGraph nodes (not needed)
- `graph.py` - LangGraph orchestration (not needed)
- `routes.py` - old interactive endpoints
- `email_choice.py` - email-based choices
- `rag/` - RAG system (not needed yet)
- `state.py` - most of it (too complex)
- ElevenLabs TTS code

## Database Schema (Simple)

```sql
-- Subscribers
CREATE TABLE subscribers (
    id TEXT PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    name TEXT,
    story_bible JSON,           -- their preferences/world
    schedule TEXT DEFAULT 'daily',  -- daily, weekdays, weekly
    delivery_time TEXT DEFAULT '06:00',
    timezone TEXT DEFAULT 'UTC',
    active BOOLEAN DEFAULT true,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

-- Generated Stories
CREATE TABLE stories (
    id TEXT PRIMARY KEY,
    subscriber_id TEXT REFERENCES subscribers(id),
    title TEXT,
    content TEXT,               -- story prose
    audio_url TEXT,
    word_count INTEGER,
    genre TEXT,
    generation_cost REAL,       -- track costs
    created_at TIMESTAMP,
    sent_at TIMESTAMP,
    opened_at TIMESTAMP         -- email tracking
);

-- Generation Jobs (for async processing)
CREATE TABLE jobs (
    id TEXT PRIMARY KEY,
    subscriber_id TEXT REFERENCES subscribers(id),
    status TEXT DEFAULT 'pending',  -- pending, running, completed, failed
    error_message TEXT,
    started_at TIMESTAMP,
    completed_at TIMESTAMP
);
```

## Environment Variables

```bash
# Required
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
RESEND_API_KEY=re_...

# Storage (production)
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_SERVICE_KEY=...

# Optional
DATABASE_URL=sqlite:///./fixionmail.db  # or postgres://...
ENVIRONMENT=development  # or production
LOG_LEVEL=INFO
SCHEDULER_HOUR=6  # when to run daily generation
SCHEDULER_TIMEZONE=America/New_York
```

## Phase 2: Multi-Chapter Stories (Future)

Once base system is working, add:
- 2-3 chapter stories (1500 words each)
- Choice points between chapters
- 3 paragraph teasers for next chapter options
- User selects via email link or web UI

Schema addition:
```sql
ALTER TABLE stories ADD COLUMN chapter_number INTEGER DEFAULT 1;
ALTER TABLE stories ADD COLUMN parent_story_id TEXT REFERENCES stories(id);
ALTER TABLE stories ADD COLUMN choices JSON;  -- [{id, teaser_text}, ...]
```

## Build Order

1. **Config + DB** - settings, database connection, models
2. **Writer Agent** - Claude story generation (port prompts)
3. **Judge Agent** - Haiku validation
4. **TTS Service** - OpenAI audio generation
5. **Email Service** - Resend + templates
6. **Scheduler** - APScheduler daily runner
7. **Admin Dashboard** - monitoring UI
8. **Deploy** - Railway/Docker setup

## Reference

- Archived codebase: `west-haven-story` repo, tag `v1.0-working-snapshot`
- Or your downloaded zip file
