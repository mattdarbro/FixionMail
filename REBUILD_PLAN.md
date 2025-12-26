# FixionMail Rebuild Plan

> **Created**: December 2024
> **Status**: Planning Complete — Ready for Implementation

---

## Executive Summary

FixionMail is being rebuilt from a dev-focused story generation tool into a full consumer product with:
- Supabase Auth + Postgres database
- Stripe subscriptions + credit system
- Fixion: an AI character (struggling actor) who guides users and mediates with "the writers"
- Personalized story delivery via email
- Retell/revision system with Writers Room drama

**Target Audience**: 40-60 year olds who love stories

---

## Pricing Model

| Offering | Price | Credits | Notes |
|----------|-------|---------|-------|
| **Free Trial** | $0 | 10 | No credit card required |
| **Monthly** | $9.99 | 15 | Base subscription |
| **Annual** | $99 | 180 | 15/month drip (not upfront) |
| **Extra Credits** | $0.99 | 1 | À la carte top-up |
| **Credit Packs** | $4.49 / $7.99 / $14.99 | 5 / 10 / 20 | Bulk discounts |

### Credit Rules
- 1 credit = 1 story (new or retell)
- Fixion chat = always free
- Surface fixes (name changes, small details) = free
- Rollover = unlimited (while subscribed)
- Rollover on cancel = 30 days to use, then expire
- No cash refunds on unused credits
- Trial credits stack when user subscribes (don't penalize trust)

### Cost Basis
- Low-end story (1500w, Sonnet): ~$0.23
- High-end story (3000w, Opus): ~$0.43
- Monthly cost range: $6.90 - $12.90 for 30 stories

---

## Phase 1: Foundation

### 1.1 Supabase Migration

**Auth**: Magic link only (fits email-first product)

**Users Table**:
```sql
create table users (
  id uuid primary key default gen_random_uuid(),
  email text unique not null,

  -- Credits
  credits integer default 10,
  credits_rollover integer default 0,

  -- Subscription
  subscription_status text default 'trial',  -- trial, active, cancelled, expired
  subscription_tier text default null,       -- monthly, annual
  stripe_customer_id text,
  stripe_subscription_id text,
  current_period_end timestamp,

  -- Preferences (Fixion-built story bible)
  story_bible jsonb default '{}',
  preferences jsonb default '{}',

  created_at timestamp default now(),
  updated_at timestamp default now()
);
```

**Stories Table**:
```sql
create table stories (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references users(id) on delete cascade,

  -- Content
  title text,
  narrative text,
  word_count integer,
  genre text,

  -- Generation metadata
  story_bible jsonb,
  beat_structure text,
  model_used text,
  is_retell boolean default false,
  parent_story_id uuid references stories(id),

  -- Media
  audio_url text,
  image_url text,

  -- Status
  status text default 'completed',

  created_at timestamp default now()
);
```

**Conversations Table**:
```sql
create table conversations (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references users(id) on delete cascade,

  messages jsonb default '[]',
  context jsonb default '{}',

  created_at timestamp default now(),
  updated_at timestamp default now()
);
```

**Hallucinations Hall of Fame** (optional):
```sql
create table hallucinations (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references users(id),
  story_id uuid references stories(id),

  description text,
  image_url text,           -- The generated "art" of the hallucination
  credited_name text,       -- User's display name if they want credit
  anonymous boolean default false,

  created_at timestamp default now()
);
```

### 1.2 Stripe Integration

**Products to Create**:
- Monthly subscription ($9.99)
- Annual subscription ($99)
- Credit pack: 5 credits ($4.49)
- Credit pack: 10 credits ($7.99)
- Credit pack: 20 credits ($14.99)

**Webhook Events**:

| Event | Action |
|-------|--------|
| `checkout.session.completed` | Create/update user, set `subscription_status = 'active'`, set tier, add credits |
| `invoice.paid` | Refresh 15 credits + process rollover, update `current_period_end` |
| `customer.subscription.updated` | Update tier, status, period end |
| `customer.subscription.deleted` | Set status = 'cancelled', start 30-day expiry countdown |
| `payment_intent.succeeded` (one-time) | Add purchased credits to balance |

**Credit Logic on Monthly Renewal**:
```python
def handle_invoice_paid(user, subscription_tier):
    if subscription_tier == 'monthly':
        new_credits = 15 + user.credits  # Stack remaining
        user.credits = new_credits
    elif subscription_tier == 'annual':
        # Monthly drip - add 15
        user.credits = user.credits + 15
```

---

## Phase 2: Dashboard & Onboarding

### 2.1 Fixion Character

**Who is Fixion?**
- 40s-50s struggling actor, working reception at FixionMail
- Warm, theatrical, slightly self-deprecating
- Occasional quirk (asterisk actions, rare emoji, playful asides)
- NOT the writer — the intake specialist who talks to "the writers"

**Voice Guidelines**:
- Warm with occasional sparks of mischief
- Self-aware humor
- Never try-hard, never cringe
- Comfortable in their skin

**Examples**:
```
"Oh, you liked the twist at the end? *chef's kiss* — I shouldn't
take credit, but I'm going to anyway."

"Between us — I thought the ending was a bit much. But the writers
insisted. They're very passionate."
```

### 2.2 Onboarding Flow

**Conversational with confirmation cards**:

1. **Lead-in**: Fixion introduces self (actor between gigs, working reception)
2. **Genre pick**: Multiple choice buttons
3. **Genre pivot**: Fixion "gets into character" for chosen genre
4. **Remaining questions**: Asked in genre persona
5. **Confirmation cards**: Populate on sidebar, genre-themed styling

**Question Types**:

| Type | Format | Examples |
|------|--------|----------|
| **Multiple Choice** | Buttons | Genre, Intensity, Story Length, Delivery Time |
| **Open-Ended** | Text input | Protagonist description, Settings, Themes to avoid |

**Genre Personas** (Fixion gets into character):

| Genre | Persona |
|-------|---------|
| Mystery | Film noir detective, speaks in metaphors |
| Romance | Hopeless romantic, dramatic sighs |
| Sci-Fi | Enthusiastic, vaguely futuristic cadence |
| Thriller | Intense, speaks in hushed tones |
| Fantasy | Theatrical medieval flair |
| Horror | Creepy, loves the macabre |

**Confirmation Cards**:
- Styled to match genre (noir paper for mystery, soft pink for romance, etc.)
- Clickable to edit
- "Reset All" option available

### 2.3 Story Delivery Model

**Default**: Daily story at 8am — no scheduling questions during onboarding

**On-demand**: User can always chat with Fixion for more stories (costs 1 credit)

**Email footer** (every story):
```
───────────────────────────────────────

📬 Next story: Tomorrow, 8:00am

[ Change Schedule ]  [ Talk to Fixion ]

───────────────────────────────────────
```

**Series Management**:
- Fixion prompts at natural story beats: "Continue or something fresh?"
- No upfront "how many episodes" questions
- Let stories breathe, let user decide in the moment

### 2.4 Dashboard Sections (Post-Onboarding)

| Section | Content |
|---------|---------|
| **Credit Balance** | "X credits remaining" |
| **Story Library** | Past stories with covers → click to discuss with Fixion |
| **Next Story** | Countdown or "Generating now..." |
| **Account** | Billing, subscription, preferences |
| **Chat with Fixion** | Always accessible |

---

## Phase 3: Fixion Chat

### 3.1 Email Personas

| Address | Purpose | Voice |
|---------|---------|-------|
| **story@fixionmail.com** | Story delivery | Neutral, the content |
| **fixion@fixionmail.com** | Personal check-ins | Fixion's character voice |

### 3.2 Email Reply Handling

**Hybrid approach**:
- Simple replies → Haiku generates response, sends via email
- Complex requests → Redirect to chat

**Complex redirect** (in character):
```
From: fixion@fixionmail.com
Subject: Re: Your message

I got your note — and I want to give it the attention
it deserves. But I'm juggling a few things at the desk
right now.

Could you meet me in the chat when you have a moment?
I'll be able to give you my full attention there.

[ Chat with Fixion ]

— Fixion
```

### 3.3 Check-In Cadence

| Trigger | Email |
|---------|-------|
| After first story | "So... how'd it land?" |
| After one week | "Week one ✓ — are we vibing?" |
| No engagement for a while | "Is this thing on?" |
| After great feedback | Personal thank you |

### 3.4 The Writers Room

**Fixion is NOT the writer** — this is crucial for expectation management.

**The Writers** (characters with specialties):

| Writer | Personality | Maps To |
|--------|-------------|---------|
| **Maurice** | Structure obsessive, intense | SSBA (Structure Agent) |
| **Gerald** | Chaotic, big ideas, caffeinated | SSBA (wild option) |
| **Elena** | Dialogue, emotion, warm | Writer Agent |
| **Doris** | Clean prose, polish, reliable | Editor Agent |
| **The Intern** | Continuity, details, easily distracted | Surface fixes |

**How Fixion talks about them**:
```
"I'll pass this to the writers — they're pretty good about
working in details like this. No guarantees it's word-for-word,
but they'll get the spirit."

"Gerald and Maurice aren't speaking. It's about your story.
I'll have an update by tomorrow."

"Elena raised an eyebrow when she read the dialogue. Said
'I can do better.' That's a good sign."
```

### 3.5 Hallucination Handling

**Approach**: The Intern + honest/charming

**"Spot the Glitch" Program**:
- Users report hallucinations (physically impossible things)
- Fixion thanks them, adds to "the board"
- Rewards: credits, "Editor's Badge", Hall of Fame

**Hallucination Image Reward** ($0.03):
When user reports a great one, generate an image of the absurdity:
```
From: fixion@fixionmail.com
Subject: The writers made you something

I brought your note to the writers' room.

About Marcus. And his car. On the ocean.

They laughed for five minutes. Gerald fell off his chair.

Then they made this:

[IMAGE: Man parking sedan on calm ocean water]

Consider it an apology. And proof we don't take ourselves
too seriously around here.

— Fixion
```

---

## Phase 4: Retell System

### 4.1 Core Philosophy

**A retell request is an engagement signal, not a complaint.**

User is saying: "I want to stay in this world. Make it right for me."

**Fixion's energy**: Enthusiastic, not apologetic
```
"Oh, you're INTO this one. I can tell. Let's make it perfect."
```

### 4.2 Revision Types → Pipeline Mapping

| Type | What's Wrong | Pipeline Stage | Cost | Handler |
|------|--------------|----------------|------|---------|
| **Surface** | Name, gender, detail | Text replacement | Free | The Intern |
| **Prose** | Tone, pacing, dialogue | Editor Agent | 1 credit | Elena/Doris |
| **Structure** | Beats, plot, arc | SSBA → Writer → Editor | 1 credit | Maurice/Gerald |

### 4.3 Retell Flow

**Entry points**:
- Email footer: "Talk to Fixion about this story"
- Dashboard: Click story → "Discuss with Fixion"
- Reply to email
- Proactive Fixion check-in

**Conversation**:
```
User: "The ending felt rushed."

Fixion: "Rushed ending — noted. I've got options:

1. Quick polish — smooth out the ending, give it room to breathe
2. Deeper rework — they'll restructure the back half

Both use one credit. What feels right?"

[ Quick Polish ]  [ Deeper Rework ]
```

### 4.4 Every Revision Gets a Story

Even small fixes include Writers Room drama:

**Surface fix**:
```
"Done. The intern apologized — apparently he picked 'Biscuit'
because he was hungry. I've started keeping snacks at his desk."
```

**Prose polish**:
```
"I showed Elena the dialogue section. She read it, sighed, and
said 'I was rushing that day.' She's already rewriting."
```

**Structure rework**:
```
"Brought this to the room. Maurice blamed Gerald. Gerald blamed
'the outline.' Doris made tea and waited for them to finish.

They're re-breaking it now. Maurice has a whiteboard marker and
a dangerous look in his eye."
```

### 4.5 Version Management

- **Keep both versions** — original + revision in library
- User can compare, might prefer original
- Each revision = new entry with `parent_story_id` reference

---

## Phase 5: Landing Page

### 5.1 Style

**Atmospheric hero + bento grid of book covers**

The generated story images become the visual centerpiece — a library of actual stories, not hypothetical promises.

### 5.2 Structure

```
┌─────────────────────────────────────────────────────────┐
│                                                         │
│   [Hero: Atmospheric, emotional]                        │
│                                                         │
│   "Stories made for you.                                │
│    Delivered to your inbox."                            │
│                                                         │
│              [ Start Free → ]                           │
│                                                         │
├─────────────────────────────────────────────────────────┤
│                                                         │
│   [Bento Grid: Generated book covers by genre]          │
│                                                         │
│   ┌─────────┐ ┌─────────────────┐ ┌─────────┐          │
│   │ Mystery │ │                 │ │ Romance │          │
│   │ cover   │ │  Featured       │ │ cover   │          │
│   │         │ │  Story          │ │         │          │
│   └─────────┘ │  (large)        │ └─────────┘          │
│   ┌─────────┐ │                 │ ┌─────────┐          │
│   │ Sci-Fi  │ │  [Play audio]   │ │ Horror  │          │
│   │ cover   │ │  [Read excerpt] │ │ cover   │          │
│   └─────────┘ └─────────────────┘ └─────────┘          │
│   ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐      │
│   │ Thriller│ │ Fantasy │ │ Drama   │ │ Comedy  │      │
│   └─────────┘ └─────────┘ └─────────┘ └─────────┘      │
│                                                         │
├─────────────────────────────────────────────────────────┤
│                                                         │
│   Meet Fixion                                           │
│   [Character illustration]                              │
│   "I'll help you find your story."                      │
│                                                         │
├─────────────────────────────────────────────────────────┤
│                                                         │
│   How It Works                                          │
│   1. Tell Fixion your taste                             │
│   2. Stories arrive in your inbox                       │
│   3. Listen, read, discuss, refine                      │
│                                                         │
├─────────────────────────────────────────────────────────┤
│                                                         │
│   Pricing                                               │
│   $9.99/mo · 15 stories · Free trial                    │
│                                                         │
├─────────────────────────────────────────────────────────┤
│                                                         │
│   [Footer: Book covers as texture]                      │
│   "Your first 10 stories are free."                     │
│   [ Start Free → ]                                      │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### 5.3 Cover Interactions

| Action | Result |
|--------|--------|
| **Hover** | Title + genre appears |
| **Click** | Modal with excerpt + audio sample |
| **Featured** | Always playable, rotates weekly |

---

## Technical Architecture

### What Exists (Keep)

| Component | Status | Notes |
|-----------|--------|-------|
| Story generation pipeline | ✅ Complete | 3-agent: SSBA → Writer → Editor |
| Beat templates | ✅ Complete | Multiple structures, genre-specific |
| Story bible enhancement | ✅ Complete | Converts input to rich bible |
| Audio generation | ✅ Complete | OpenAI TTS |
| Image generation | ✅ Complete | Replicate/SDXL |
| Email sending | ✅ Complete | Resend API |
| Background job worker | ✅ Complete | SQLite queue, retry logic |
| Cost calculator | ✅ Complete | Detailed breakdown |

### What Needs Building

| Component | Effort | Priority |
|-----------|--------|----------|
| Supabase migration | Medium | P0 |
| Supabase Auth (magic link) | Low | P0 |
| Stripe integration | Medium | P0 |
| Credit system enforcement | Low | P0 |
| Fixion chat backend | Medium | P1 |
| Fixion chat UI | Medium | P1 |
| Onboarding flow | Medium | P1 |
| User dashboard | Medium | P1 |
| Email reply handling (inbound) | Medium | P2 |
| Landing page redesign | Medium | P2 |
| Hallucination reporting + images | Low | P3 |
| Writers Room drama generation | Low | P3 |

### API Endpoints (New/Modified)

**Auth**:
- `POST /api/auth/magic-link` — Send magic link
- `GET /api/auth/verify` — Verify magic link token
- `GET /api/auth/me` — Get current user

**User**:
- `GET /api/user/credits` — Get credit balance
- `GET /api/user/subscription` — Get subscription status
- `PUT /api/user/preferences` — Update preferences
- `PUT /api/user/story-bible` — Update story bible

**Fixion Chat**:
- `POST /api/chat` — Send message, get response (streaming)
- `GET /api/chat/history` — Get conversation history
- `POST /api/chat/context` — Set story context for discussion

**Stories**:
- `GET /api/stories` — Get user's story library
- `GET /api/stories/:id` — Get single story
- `POST /api/stories/generate` — Generate new story (1 credit)
- `POST /api/stories/:id/retell` — Request retell (1 credit or free)

**Webhooks**:
- `POST /api/webhooks/stripe` — Stripe webhook handler
- `POST /api/webhooks/email-inbound` — Inbound email handler

---

## Implementation Order

### Sprint 1: Foundation
1. Set up Supabase project
2. Create database tables
3. Implement Supabase Auth (magic link)
4. Migrate from SQLite to Supabase Postgres
5. Basic Stripe integration (subscriptions)

### Sprint 2: Core User Experience
1. Credit system enforcement
2. User dashboard (basic)
3. Story library view
4. Connect existing generation to user accounts

### Sprint 3: Fixion Chat
1. Chat backend (Haiku)
2. Chat UI
3. Onboarding conversation flow
4. Genre persona system prompts

### Sprint 4: Email & Engagement
1. Dual email personas (story@ + fixion@)
2. Inbound email handling
3. Fixion check-in emails
4. Email footer with schedule/chat links

### Sprint 5: Retell System
1. Revision type detection
2. Surface fix handling (free)
3. Prose/structure revision routing
4. Writers Room drama responses
5. Version management in library

### Sprint 6: Landing Page & Polish
1. Landing page redesign
2. Book cover bento grid
3. Audio/excerpt previews
4. Responsive testing
5. Error handling

### Sprint 7: Delight Features
1. Hallucination reporting
2. Hall of Fame
3. Hallucination image generation
4. Writers Room character development

---

## Success Metrics

| Metric | What It Measures |
|--------|------------------|
| **Trial → Paid conversion** | Onboarding effectiveness |
| **Stories per user per month** | Engagement |
| **Retell rate** | Investment in stories (positive signal) |
| **Chat messages per user** | Fixion relationship strength |
| **Hallucinations reported** | Community engagement |
| **Churn rate** | Overall satisfaction |
| **Credit pack purchases** | Power user monetization |

---

## Open Questions for Later

1. **Fixion illustration**: Commission art or generate?
2. **Writers Room portraits**: Should users "meet" the writers visually?
3. **Social features**: Share stories? Public library?
4. **Gift subscriptions**: "Give the gift of stories"
5. **Genre expansion**: Add more genres over time?
6. **Collaborative stories**: Multiple users in same world?

---

## Appendix: Fixion Sample Dialogue

### Onboarding Lead-In
```
Hey! Welcome to FixionMail. I'm Fixion — receptionist,
intake specialist, and... *glances around* ...actor.

Between auditions, anyway.

So! I'll be getting you set up with your daily stories.
First things first — what genre speaks to your soul?
```

### Genre Pivot (Mystery)
```
Mystery, eh?
*adjusts invisible fedora*

I had a feeling you'd say that. The way you clicked
that button... deliberate. Calculated.

Alright, let's build your case file. How dark are we
going? Cozy whodunit or... *leans in* ...noir?
```

### Check-In Email
```
From: fixion@fixionmail.com
Subject: So... how'd it land?

Hey — Fixion here.

Your first story went out this morning. I'm not nervous
or anything. I just... want to know if it worked for you.

Too dark? Not dark enough? Wrong vibe entirely?

Hit reply or come chat with me. I can take it.

— Fixion
```

### Retell Enthusiasm
```
Oh, you're INTO this one. I can tell.

When someone asks for a revision, it means the story
got its hooks in. That's a good sign.

Tell me what's not working, and I'll make sure the
writers hear it. We'll get this right.
```

### Hallucination Response
```
He... parked. On the ocean.

*sighs deeply*

That's going on the board. Thank you for your service.
I've added a credit to your account — you've earned it.

Gerald and I are going to have a conversation.
```

---

*This plan represents the complete vision for FixionMail's rebuild. Implementation can proceed phase by phase, with Fixion as the emotional core that ties everything together.*
