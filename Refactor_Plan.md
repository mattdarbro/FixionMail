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

## Phase 1: DELETE Dead Code ✅ COMPLETE

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

## Phase 2: SIMPLIFY to 2-Agent System ✅ COMPLETE

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

**Files modified:**
- ✅ `backend/storyteller/standalone_generation.py` - updated to use 2-agent flow
- ✅ `backend/storyteller/cost_calculator.py` - updated for 2-agent costs

**New files created:**
- ✅ `backend/agents/__init__.py` - Package init
- ✅ `backend/agents/writer.py` - WriterAgent (Sonnet)
- ✅ `backend/agents/judge.py` - JudgeAgent (Haiku)

---

## Phase 3: SIMPLIFY TTS to OpenAI Only ✅ COMPLETE

### New State:
- OpenAI TTS only
- ElevenLabs code paths removed from UI
- Voice selection updated to OpenAI voices (alloy, echo, fable, onyx, nova, shimmer)

**Files modified:**
- ✅ `backend/routes/fictionmail_dev.py` - OpenAI defaults
- ✅ `frontend/dev-dashboard.html` - OpenAI voices only

---

## Phase 3.5: TESTING & TUNING (Current - 1 Week)

### Goal:
Validate story quality before building infrastructure. The 2-agent system with enhanced prompts must produce compelling stories.

### Testing Checklist:
- [ ] Generate stories with different genres (romance, mystery, fantasy, cozy, etc.)
- [ ] Test intensity slider effect (cozy vs moderate vs intense)
- [ ] Compare beat structures (Save the Cat, Hero's Journey, Truby, Classic)
- [ ] Compare Sonnet vs Opus quality
- [ ] Evaluate: engaging opening, consistent voice, natural pacing, satisfying ending
- [ ] Tweak WriterAgent prompt as needed
- [ ] Adjust beat guidance if mechanical

### Recent Improvements Made:
- ✅ Added beat `guidance` field to prompts (was missing)
- ✅ Added intensity-based craft guidance (cozy/moderate/intense)
- ✅ Added "Think First" planning section to prompt
- ✅ Enhanced craft guidelines (opening, prose, tension, character, ending)
- ✅ Added Sonnet/Opus model selection in dashboard

### Success Criteria:
- Stories feel engaging from first paragraph
- Intensity setting noticeably affects tone/stakes
- Beat transitions feel natural, not mechanical
- Would a reader want to finish the story?

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

### Week 1: Clean + Simplify ✅
1. [x] Delete dead code (nodes.py, graph.py, routes.py, email_choice.py)
2. [x] Simplify TTS to OpenAI only (UI updated)
3. [ ] Update config.py (remove unused settings) - optional cleanup
4. [ ] Clean up main.py (remove commented code) - optional cleanup

### Week 2: 2-Agent System ✅
5. [x] Create agents/writer.py
6. [x] Create agents/judge.py
7. [x] Update standalone_generation.py to use new agents
8. [x] Update cost_calculator.py for 2-agent costs
9. [x] Test generation still works (syntax verified)
10. [x] Add Sonnet/Opus model selection
11. [x] Enhance WriterAgent prompt (beats, intensity, craft guidelines)

### Week 3: Testing & Tuning (Current)
12. [ ] Generate test stories across genres
13. [ ] Test intensity slider effect
14. [ ] Compare beat structures
15. [ ] Compare Sonnet vs Opus
16. [ ] Iterate on prompts as needed
17. [ ] Validate story quality meets bar

### Week 4: Database + Onboarding + Stripe
18. [ ] Create db/database.py with async SQLite
19. [ ] Create db/models.py (Subscriber, Story, Job)
20. [ ] Add subscriber management endpoints
21. [ ] Log stories to database
22. [ ] Add onboarding flow (web form → bible creation → subscriber record)
23. [ ] Integrate Stripe Checkout for paid subscriptions
24. [ ] Add Stripe webhook handlers

### Week 5: Scheduler
25. [ ] Create scheduler/scheduler.py
26. [ ] Create scheduler/jobs.py
27. [ ] Add background job processing
28. [ ] Test scheduled generation
29. [ ] Update admin dashboard

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

# Stripe (Week 3)
STRIPE_SECRET_KEY=sk_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PRICE_ID=price_...
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

## Decisions Made

### 1. Voice Selection - All 6 OpenAI Voices with Descriptions

```python
OPENAI_VOICES = {
    "alloy": {
        "name": "Alloy",
        "feel": "Neutral & Balanced",
        "best_for": "Any genre"
    },
    "echo": {
        "name": "Echo",
        "feel": "Warm & Thoughtful",
        "best_for": "Drama, Noir"
    },
    "fable": {
        "name": "Fable",
        "feel": "British & Expressive",
        "best_for": "Fantasy, Literary"
    },
    "onyx": {
        "name": "Onyx",
        "feel": "Deep & Authoritative",
        "best_for": "Thriller, Mystery"
    },
    "nova": {
        "name": "Nova",
        "feel": "Friendly & Bright",
        "best_for": "Romance, Light Fiction"
    },
    "shimmer": {
        "name": "Shimmer",
        "feel": "Soft & Gentle",
        "best_for": "Emotional, Intimate"
    }
}
```

### 2. Scheduling - Dev vs User

**Dev Dashboard Options:**
```python
DEV_SCHEDULER_OPTIONS = {
    "immediate": "Run now (for testing)",
    "1_minute": "1 minute from now",
    "5_minutes": "5 minutes from now",
    "15_minutes": "15 minutes from now",
    "1_hour": "1 hour from now",
    "custom": "Custom datetime"
}
```

**User Delivery Options:**
```python
USER_DELIVERY_TIMES = [
    "06:00",  # Early morning
    "08:00",  # Morning commute
    "12:00",  # Lunch
    "18:00",  # Evening commute
    "21:00",  # Before bed
]
# Plus timezone selection (stored per user)
```

### 3. Retry Policy

```python
RETRY_POLICY = {
    "max_retries": 3,
    "backoff_seconds": [30, 120, 600],  # 30s, 2min, 10min
    "retry_on": [
        "api_timeout",      # Claude/OpenAI/Replicate timeout
        "rate_limit",       # 429 errors
        "network_error",    # Connection issues
    ],
    "fail_permanently_on": [
        "invalid_bible",    # Bad input data
        "content_policy",   # Content blocked
        "auth_error",       # API key issues
    ]
}
```

**Logic:**
1. First failure → wait 30s, retry
2. Second failure → wait 2min, retry
3. Third failure → wait 10min, retry
4. Fourth failure → mark job as `failed`, alert admin

### 4. Onboarding - Phase 3 (with Database)

Onboarding will be built in **Week 3** alongside the subscriber database.
- Requires persistence to be meaningful
- Flows directly into subscriber table
- Core generation should be solid first

### 5. Stripe Integration - Phase 3 (with Onboarding)

Payment processing added alongside onboarding:
- Stripe Checkout for subscription signup
- Free tier vs paid tier (TBD pricing)
- Webhook handling for subscription events (created, canceled, failed payment)

```python
# New env vars
STRIPE_SECRET_KEY=sk_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PRICE_ID=price_...  # Monthly subscription price
```

**New files:**
- `backend/services/payments.py` - Stripe integration
- `backend/routes/webhooks.py` - Stripe webhook handlers

**Subscriber table addition:**
```sql
ALTER TABLE subscribers ADD COLUMN stripe_customer_id TEXT;
ALTER TABLE subscribers ADD COLUMN subscription_status TEXT DEFAULT 'free';  -- free, active, canceled, past_due
ALTER TABLE subscribers ADD COLUMN subscription_ends_at TIMESTAMP;
```

### 6. Rate Limits (TBD)

To be decided based on cost analysis after 2-agent system is running.
Likely: Max 1 story per user per day (configurable for premium tiers later).

---

## Future Phases (Post-MVP)

### Phase 7: Interactive Multi-Chapter Stories

**Goal:** Allow stories that span 2-3 chapters with reader choices between chapters.

**Architecture:**
- Story state persistence between chapters
- Choice generation at chapter end
- RAG-based consistency checking (leverage existing `docs/multi-agent-architecture.md`)
- Email delivery with embedded choice buttons
- Chapter continuity from previous choices

**New components needed:**
- Story session tracking (multi-chapter state)
- Choice handling endpoints
- Chapter continuation logic
- Email templates with choice buttons

**Considerations:**
- Reuse existing beat templates (scale word counts per chapter)
- May need Story Structure Beat Agent (SSBA) for arc planning
- Cost: ~3x per complete story (3 chapters)

---

### Phase 8: User-Defined Beat Systems

**Goal:** Allow users to create and save custom beat structures for their stories.

**Features:**
- Beat template builder UI
- Save custom structures to user profile
- Share beat templates (community library?)
- Import/export beat structures (JSON)

**Schema addition:**
```sql
CREATE TABLE beat_templates (
    id TEXT PRIMARY KEY,
    user_id TEXT REFERENCES subscribers(id),
    name TEXT NOT NULL,
    description TEXT,
    beats JSON NOT NULL,  -- Array of beat definitions
    genre_tags JSON,      -- ["romance", "mystery", ...]
    is_public BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Beat definition structure:**
```json
{
  "beat_number": 1,
  "beat_name": "Opening Hook",
  "word_target": 200,
  "description": "Grab reader attention",
  "guidance": "Start in media res, establish voice"
}
```

**UI considerations:**
- Drag-and-drop beat ordering
- Word count allocation visualizer
- Preview with sample generation

---

## Roadmap Summary

| Phase | Description | Status |
|-------|-------------|--------|
| 1 | Delete Dead Code | ✅ Complete |
| 2 | 2-Agent System | ✅ Complete |
| 3 | TTS Simplification | ✅ Complete |
| 3.5 | Testing & Tuning | 🔄 Current (1 week) |
| 4 | Subscriber Database | Pending |
| 5 | Scheduler + Jobs | Pending |
| 6 | Admin Dashboard | Pending |
| 7 | Interactive Multi-Chapter | Future |
| 8 | User-Defined Beats | Future |
