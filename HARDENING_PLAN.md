# FixionMail Production Hardening Plan

## Strategy

**Backend First**: Harden the backend completely while keeping dev dashboard functional
**Frontend Later**: Separate session for consumer-facing UI, Stripe integration
**Dev Bypass**: All security features must have dev/bypass mode for testing

---

## Current State Assessment

### What Works Well
- **Story Generation Pipeline**: 3-agent system (Structure → Writer → Editor) produces quality stories
- **Media Generation**: Cover images (Replicate/Imagen) + Audio narration (OpenAI TTS)
- **Email Delivery**: Stories delivered via Resend with inline media
- **Job Queue**: Background processing with retry logic and crash recovery
- **Storage**: Supabase for media files, SQLite for job tracking
- **Dev Dashboard**: Functional UI for testing full flow

### What's Broken/Missing

| Category | Issue | Risk Level |
|----------|-------|------------|
| **Data** | Stories stored in-memory (`dev_storage` dict) | 🔴 CRITICAL - Lost on restart |
| **Data** | Job results in SQLite, but full story content not persisted | 🔴 CRITICAL |
| **Security** | No authentication on any endpoint | 🔴 CRITICAL - Cost exposure |
| **Security** | CORS allows all origins (`*`) | 🟠 HIGH |
| **Reliability** | Email failures not retried | 🟠 HIGH |
| **UX** | No story library/history for users | 🟠 HIGH |
| **UX** | No proper error states in frontend | 🟡 MEDIUM |
| **Ops** | No monitoring/alerting | 🟡 MEDIUM |
| **Scale** | Single worker, SQLite locks | 🟡 MEDIUM (fine for now) |

---

## Proposed Phases

### Phase 1: Data Persistence & Library (TODAY - Priority)
**Goal**: Stories survive restarts, users can browse past stories

#### 1.1 Backend: Story Persistence
- [ ] Add `stories` table to SQLite (or extend `story_jobs`)
- [ ] Persist full story content when generation completes
- [ ] Store: title, narrative, genre, word_count, audio_url, image_url, created_at, user_email

#### 1.2 Backend: Library API
- [ ] `GET /api/dev/library` - List completed stories with full content
- [ ] `GET /api/dev/library/{story_id}` - Get single story details
- [ ] Filter by email, pagination support

#### 1.3 Frontend: Library Page
- [ ] Create `library.html` - Browse past stories
- [ ] Story cards with cover image, title, genre, date
- [ ] Click to expand: full narrative, audio player
- [ ] Link from dev dashboard

**Deliverable**: Users can generate stories and browse them later, even after restarts

---

### Phase 2: Security Hardening (NEXT)
**Goal**: Prevent unauthorized access and abuse

#### 2.1 Simple API Key Auth
- [ ] Generate API keys for authorized users
- [ ] Require `X-API-Key` header on all `/api/dev/*` endpoints
- [ ] Store keys in environment variable (comma-separated list)
- [ ] Rate limit: 10 requests/minute per key

#### 2.2 CORS Lockdown
- [ ] Configure allowed origins (your domain only)
- [ ] Move from `*` to explicit whitelist

#### 2.3 Input Validation
- [ ] Add length limits to text fields (setting, character names)
- [ ] Validate genre against allowed list
- [ ] Validate intensity range (1-5)

**Deliverable**: Only authorized users can access the API

---

### Phase 3: Reliability (AFTER SECURITY)
**Goal**: Stories always get delivered

#### 3.1 Email Retry Queue
- [ ] On email failure, queue for retry
- [ ] Exponential backoff (1min, 5min, 15min, 1hr)
- [ ] Max 5 retries, then mark as failed with notification

#### 3.2 Better Error Handling
- [ ] Specific error types for each external service
- [ ] User-friendly error messages
- [ ] Admin notification on repeated failures

#### 3.3 Health Check Enhancement
- [ ] `/health` checks database connectivity
- [ ] Reports worker status
- [ ] Reports queue depth

**Deliverable**: Reliable story delivery with visibility into failures

---

### Phase 4: User Experience Polish (LATER)
**Goal**: Production-quality frontend

#### 4.1 Improved Dev Dashboard
- [ ] Better loading states with progress
- [ ] Error boundaries with retry options
- [ ] Mobile-responsive layout

#### 4.2 User Preferences
- [ ] Remember last used settings
- [ ] Favorite genres
- [ ] TTS voice preference

#### 4.3 Story Features
- [ ] Download story as PDF
- [ ] Share story link
- [ ] Re-generate with same bible

---

### Phase 5: Scale Preparation (FUTURE)
**Goal**: Handle more users

#### 5.1 Database Migration
- [ ] Move from SQLite to PostgreSQL (Supabase)
- [ ] Enable multiple worker instances

#### 5.2 User Accounts
- [ ] Proper authentication (magic link or OAuth)
- [ ] User dashboard
- [ ] Usage tracking

#### 5.3 Payment Integration
- [ ] Stripe checkout
- [ ] Subscription tiers
- [ ] Usage-based billing

---

## Today's Focus: Phase 1

### Concrete Tasks

```
[ ] 1. Extend database schema for story persistence
    - Add get_completed_stories() method to database.py
    - Ensure story content is saved in job result

[ ] 2. Add library API endpoints
    - GET /api/dev/library - list stories
    - GET /api/dev/library/{job_id} - single story

[ ] 3. Build library.html frontend
    - Story grid/list view
    - Cover images, titles, dates
    - Audio playback
    - Expandable narrative view

[ ] 4. Update dev dashboard
    - Add "View Library" link
    - Show recent stories count

[ ] 5. Test end-to-end
    - Generate story
    - Verify appears in library
    - Restart server
    - Verify story persists
```

### Success Criteria
1. Generate a story via dev dashboard
2. See it in the library page
3. Restart the server
4. Story still visible in library
5. Can play audio and view full narrative

---

## Architecture Decisions

### Why SQLite (for now)?
- Already in use for job queue
- Simple, no additional services
- Fine for single-user/small scale
- Easy to migrate to PostgreSQL later

### Why not PostgreSQL today?
- Adds deployment complexity
- Railway PostgreSQL = additional cost
- SQLite is sufficient for current scale
- Can migrate when needed (Phase 5)

### Frontend Approach
- Keep using standalone HTML files (like dev-dashboard.html)
- Fast to iterate, no build step
- React app can be integrated later for more complex features

---

## Questions to Resolve

1. **Email as user identifier?** Currently using email to group stories. Good enough for now?

2. **Story retention?** How long to keep stories? 30 days? Forever?

3. **Public sharing?** Should stories have shareable public URLs?

4. **Re-generation?** Allow regenerating a story with same settings?

---

## Notes

- Job results already contain full story data (title, narrative, audio_url, image_url)
- Just need to expose it via API and build frontend
- Media files are in Supabase, so URLs are permanent
- Main risk is SQLite file location - must be on Railway volume
