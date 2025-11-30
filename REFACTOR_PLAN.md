# FixionMail Refactor Plan

## Current State (90% Working)

| Component | Status | Technology | Action |
|-----------|--------|------------|--------|
| Story Generation | Working | Claude Sonnet (3-agent) | Simplify to 2-agent |
| Image Generation | Working | Replicate Imagen-3-Fast | KEEP |
| TTS (ElevenLabs) | Working | ElevenLabs Flash v2.5 | REMOVE |
| TTS (OpenAI) | Working | OpenAI TTS | KEEP (only option) |
| Email Sending | Working | Resend | KEEP |
| Storage | Working | Local + Supabase | KEEP |
| Config | Working | Pydantic Settings | KEEP |
| Bible Enhancement | Working | Claude | KEEP |
| Beat Templates | Working | 59KB of structures | KEEP |
| Cost Calculator | Working | Python | UPDATE for 2-agent |
| Dev Dashboard | Working | Embedded HTML | EVOLVE to Admin |

**Missing:**
- Scheduler (cron/APScheduler)
- Background job processing
- Subscriber database
- 2-agent system (Writer + Judge)

---

## Phase 1: DELETE Dead Code

Remove ~3,200 lines of unused code:

| File | Lines | Why Delete |
|------|-------|------------|
| `backend/storyteller/nodes.py` | 1948 | LangGraph nodes (old interactive) |
| `backend/storyteller/graph.py` | 224 | LangGraph orchestration |
| `backend/api/routes.py` | 632 | Old interactive endpoints |
| `backend/api/email_choice.py` | 415 | Email-based choices |

**Also clean up:**
- `backend/storyteller/prompts.py` (312 lines) - superseded by prompts_v2.py
- `backend/rag/` directory - not used in current flow
- Commented-out code in `main.py`
- ElevenLabs imports/code paths (keep OpenAI TTS only)

---

## Phase 2: SIMPLIFY to 2-Agent System

### Current 3-Agent Flow (in standalone_generation.py):
```
1. SSBA (Story Structure Beat Agent) → plans structure
2. CBA (Chapter Beat Agent) → breaks down beats
3. CEA (Chapter Execution Agent) → writes prose
```

### New 2-Agent Flow:
```
1. WRITER (Claude Sonnet) → generates full story
2. JUDGE (Claude Haiku) → validates against requirements
   - If pass: continue to TTS/image
   - If fail: Writer rewrites with feedback (max 1 retry)
```

**Files to modify:**
- `backend/storyteller/standalone_generation.py` - main generation logic
- `backend/storyteller/prompts_standalone.py` - combine SSBA+CBA prompts
- `backend/storyteller/cost_calculator.py` - update cost estimates

**New files to create:**
- `backend/agents/writer.py` - Writer agent
- `backend/agents/judge.py` - Judge agent (Haiku)

---

## Phase 3: SIMPLIFY TTS to OpenAI Only

### Current State:
- ElevenLabs: Primary, expensive (~$0.30/1000 chars)
- OpenAI: Fallback option, cheaper (~$0.015/1000 chars)

### New State:
- OpenAI TTS only
- Remove all ElevenLabs code paths
- Update voice selection UI to OpenAI voices

**Files to modify:**
- `backend/storyteller/standalone_generation.py` - remove ElevenLabs, keep OpenAI
- `backend/routes/fictionmail_dev.py` - update TTS provider selection
- `backend/config.py` - remove ELEVENLABS_* config
- `requirements.txt` - remove elevenlabs package

**OpenAI TTS Voices to offer:**
- alloy, echo, fable, onyx, nova, shimmer

---

## Phase 4: ADD Subscriber Database

### New Schema:
```sql
-- Subscribers (users who receive daily stories)
CREATE TABLE subscribers (
    id TEXT PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    name TEXT,
    story_bible JSON,                    -- their world/preferences
    preferred_genres JSON,               -- ["noir", "romance", ...]
    preferred_length TEXT DEFAULT 'medium',  -- short/medium/long
    schedule TEXT DEFAULT 'daily',       -- daily, weekdays, weekly
    delivery_time TEXT DEFAULT '06:00',
    timezone TEXT DEFAULT 'America/New_York',
    voice_id TEXT DEFAULT 'onyx',        -- OpenAI voice
    active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Generated Stories (history of what was sent)
CREATE TABLE stories (
    id TEXT PRIMARY KEY,
    subscriber_id TEXT REFERENCES subscribers(id),
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    audio_url TEXT,
    image_url TEXT,
    word_count INTEGER,
    genre TEXT,
    beat_structure TEXT,
    generation_cost_usd REAL,
    writer_tokens INTEGER,
    judge_tokens INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    sent_at TIMESTAMP,
    opened_at TIMESTAMP,
    rating INTEGER,                      -- 1-5 stars from user
    feedback TEXT
);

-- Generation Jobs (async processing queue)
CREATE TABLE jobs (
    id TEXT PRIMARY KEY,
    subscriber_id TEXT REFERENCES subscribers(id),
    status TEXT DEFAULT 'pending',       -- pending, running, completed, failed
    story_id TEXT REFERENCES stories(id),
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**New files to create:**
- `backend/db/database.py` - async SQLite connection
- `backend/db/models.py` - SQLAlchemy/Pydantic models
- `backend/db/migrations/` - Alembic migrations (optional for SQLite)

---

## Phase 5: ADD Scheduler + Background Jobs

### Architecture:
```
┌─────────────────────────────────────────────────────────┐
│              SCHEDULER (APScheduler)                     │
│         Runs at configured times (e.g., 6 AM)           │
└─────────────────────┬───────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────┐
│              JOB PROCESSOR (async)                       │
│  1. Query subscribers due for delivery                   │
│  2. Create job records (status: pending)                 │
│  3. Process each job:                                    │
│     a. Generate story (Writer → Judge)                   │
│     b. Generate audio (OpenAI TTS)                       │
│     c. Generate image (Replicate)                        │
│     d. Send email (Resend)                               │
│     e. Update job status (completed/failed)              │
└─────────────────────────────────────────────────────────┘
```

**New files to create:**
- `backend/scheduler/scheduler.py` - APScheduler setup
- `backend/scheduler/jobs.py` - Job processing logic
- `backend/scheduler/worker.py` - Background worker

**Dependencies to add:**
- `apscheduler` - scheduling
- No need for Celery/Redis for MVP (async Python is enough)

---

## Phase 6: EVOLVE Dashboard to Admin

### Current Dev Dashboard:
- Generate stories manually
- View generation logs
- Select options (genre, voice, etc.)

### New Admin Dashboard:
- **Subscribers**: List, add, edit, deactivate
- **Stories**: History of generated/sent stories
- **Jobs**: Queue status, retry failed jobs
- **Costs**: Daily/weekly/monthly cost tracking
- **Manual Generate**: For testing (keep this)

**Files to modify:**
- `backend/routes/fictionmail_dev.py` → rename to `admin.py`
- Update embedded HTML for new features

---

## File Structure After Refactor

```
backend/
├── api/
│   └── main.py                    # Entry point (cleaned up)
│
├── agents/                        # NEW: 2-agent system
│   ├── __init__.py
│   ├── writer.py                  # Claude Sonnet writer
│   └── judge.py                   # Claude Haiku validator
│
├── db/                            # NEW: Database layer
│   ├── __init__.py
│   ├── database.py                # Async SQLite connection
│   └── models.py                  # Subscriber, Story, Job models
│
├── scheduler/                     # NEW: Background processing
│   ├── __init__.py
│   ├── scheduler.py               # APScheduler config
│   ├── jobs.py                    # Job processing logic
│   └── worker.py                  # Background worker
│
├── routes/
│   └── admin.py                   # Renamed from fictionmail_dev.py
│
├── services/                      # NEW: Clean service layer
│   ├── __init__.py
│   ├── tts.py                     # OpenAI TTS only
│   ├── images.py                  # Replicate (extracted from standalone)
│   └── email.py                   # Resend (extracted from scheduler.py)
│
├── storyteller/
│   ├── standalone_generation.py   # Simplified, uses agents/
│   ├── prompts_v2.py              # Keep
│   ├── prompts_standalone.py      # Keep
│   ├── beat_templates.py          # Keep (59KB of gold)
│   ├── bible_enhancement.py       # Keep
│   ├── cost_calculator.py         # Update for 2-agent
│   └── name_registry.py           # Keep
│
├── email/
│   ├── scheduler.py               # Keep (email templates)
│   └── database.py                # Merge into db/database.py
│
├── models/
│   └── state.py                   # Simplify (remove unused fields)
│
├── storage.py                     # Keep
└── config.py                      # Simplify (remove ElevenLabs)
```

**Deleted:**
```
backend/
├── api/
│   ├── routes.py                  # DELETED
│   └── email_choice.py            # DELETED
├── storyteller/
│   ├── nodes.py                   # DELETED
│   ├── graph.py                   # DELETED
│   └── prompts.py                 # DELETED
└── rag/                           # DELETED (entire directory)
```

---

## Implementation Order

### Week 1: Clean + Simplify
1. [ ] Delete dead code (nodes.py, graph.py, routes.py, email_choice.py)
2. [ ] Remove ElevenLabs, keep OpenAI TTS only
3. [ ] Update config.py (remove unused settings)
4. [ ] Clean up main.py (remove commented code)

### Week 2: 2-Agent System
5. [ ] Create agents/writer.py
6. [ ] Create agents/judge.py
7. [ ] Update standalone_generation.py to use new agents
8. [ ] Update cost_calculator.py for 2-agent costs
9. [ ] Test generation still works

### Week 3: Database
10. [ ] Create db/database.py with async SQLite
11. [ ] Create db/models.py (Subscriber, Story, Job)
12. [ ] Add subscriber management endpoints
13. [ ] Log stories to database

### Week 4: Scheduler
14. [ ] Create scheduler/scheduler.py
15. [ ] Create scheduler/jobs.py
16. [ ] Add background job processing
17. [ ] Test scheduled generation
18. [ ] Update admin dashboard

---

## Environment Variables (After Refactor)

```bash
# Required
ANTHROPIC_API_KEY=sk-ant-...      # Claude for Writer + Judge
OPENAI_API_KEY=sk-...             # TTS only
REPLICATE_API_TOKEN=r8_...        # Image generation
RESEND_API_KEY=re_...             # Email

# Optional
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_SERVICE_KEY=...
DATABASE_URL=sqlite:///./fixionmail.db
ENVIRONMENT=development
LOG_LEVEL=INFO

# Scheduler
SCHEDULER_ENABLED=true
SCHEDULER_HOUR=6
SCHEDULER_MINUTE=0
SCHEDULER_TIMEZONE=America/New_York
```

**Removed:**
- ELEVENLABS_API_KEY
- ELEVENLABS_VOICE_ID
- All LangGraph checkpoint settings

---

## Cost Comparison

### Current (3-agent + ElevenLabs):
- Story: ~$0.08-0.15 (3 Claude calls)
- TTS: ~$0.30-0.50 (ElevenLabs, 1500-3000 words)
- Image: ~$0.02 (Replicate)
- **Total: ~$0.40-0.67 per story**

### After Refactor (2-agent + OpenAI TTS):
- Story: ~$0.03-0.06 (1 Sonnet + 1 Haiku)
- TTS: ~$0.02-0.04 (OpenAI, 1500-3000 words)
- Image: ~$0.02 (Replicate)
- **Total: ~$0.07-0.12 per story**

**Savings: 70-85% cost reduction per story**

---

## Testing Checklist

After each phase, verify:
- [ ] Story generation works (quality check)
- [ ] Audio generation works (plays correctly)
- [ ] Image generation works (displays correctly)
- [ ] Email sending works (arrives in inbox)
- [ ] Dashboard loads (no errors)
- [ ] All API endpoints respond

---

## Rollback Plan

If something breaks:
1. You have the zip of the original
2. Tag `v1.0-working-snapshot` marks the working state
3. Git history preserves everything

---

## Questions to Decide

1. **Voice selection**: Which OpenAI voices to offer? (alloy, echo, fable, onyx, nova, shimmer)
2. **Default schedule**: Daily at 6 AM? Configurable per user?
3. **Retry policy**: How many times to retry failed jobs?
4. **Rate limits**: Max stories per day? (cost protection)
5. **Subscriber onboarding**: Web form? Email signup? Manual add only?
