-- FixionMail Initial Schema Migration
-- This migration creates the core tables for the rebuilt FixionMail application

-- =====================================================
-- USERS TABLE
-- =====================================================
-- Extends Supabase Auth with application-specific data

create table if not exists public.users (
    id uuid primary key references auth.users(id) on delete cascade,
    email text unique not null,

    -- Credits system
    credits integer not null default 10,  -- Free trial starts with 10
    credits_used_total integer not null default 0,  -- Lifetime credits used

    -- Subscription
    subscription_status text not null default 'trial'
        check (subscription_status in ('trial', 'active', 'cancelled', 'expired', 'past_due')),
    subscription_tier text
        check (subscription_tier in ('monthly', 'annual') or subscription_tier is null),
    stripe_customer_id text unique,
    stripe_subscription_id text unique,
    current_period_start timestamp with time zone,
    current_period_end timestamp with time zone,
    cancel_at_period_end boolean default false,

    -- Trial tracking
    trial_credits_remaining integer not null default 10,
    trial_started_at timestamp with time zone default now(),

    -- Preferences (Fixion-built story bible)
    story_bible jsonb not null default '{}'::jsonb,
    preferences jsonb not null default '{
        "story_length": "medium",
        "delivery_time": "08:00",
        "timezone": "America/New_York"
    }'::jsonb,

    -- Genre and character persistence
    current_genre text,
    current_protagonist jsonb,  -- For genres that need character continuity

    -- Onboarding state
    onboarding_completed boolean not null default false,
    onboarding_step text default 'welcome',

    -- Timestamps
    created_at timestamp with time zone not null default now(),
    updated_at timestamp with time zone not null default now(),
    last_story_at timestamp with time zone,
    last_login_at timestamp with time zone
);

-- Index for common queries
create index if not exists idx_users_email on public.users(email);
create index if not exists idx_users_subscription_status on public.users(subscription_status);
create index if not exists idx_users_stripe_customer on public.users(stripe_customer_id);

-- =====================================================
-- STORIES TABLE
-- =====================================================
-- Stores all generated stories with full content and metadata

create table if not exists public.stories (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references public.users(id) on delete cascade,

    -- Content
    title text not null,
    narrative text not null,
    word_count integer not null,
    genre text not null,

    -- Generation metadata
    story_bible jsonb not null,  -- Bible used for this specific story
    beat_structure text,  -- Which template was used (save_the_cat, hero_journey, etc.)
    model_used text not null,  -- sonnet, opus

    -- Revision tracking
    is_retell boolean not null default false,
    parent_story_id uuid references public.stories(id) on delete set null,
    revision_notes text,  -- User's feedback that led to retell
    revision_type text check (revision_type in ('surface', 'prose', 'structure') or revision_type is null),

    -- Media URLs (stored in Supabase Storage)
    audio_url text,
    image_url text,

    -- Series/episode tracking
    series_id uuid,  -- Groups stories in a series
    episode_number integer,

    -- Status and delivery
    status text not null default 'completed'
        check (status in ('pending', 'generating', 'completed', 'failed', 'delivered')),
    delivered_at timestamp with time zone,
    email_sent boolean not null default false,

    -- User interaction
    rating integer check (rating >= 1 and rating <= 5),
    feedback jsonb,

    -- Cost tracking
    credits_used integer not null default 1,
    generation_cost_cents integer,  -- Actual API cost in cents

    -- Timestamps
    created_at timestamp with time zone not null default now(),
    updated_at timestamp with time zone not null default now()
);

-- Indexes for common queries
create index if not exists idx_stories_user on public.stories(user_id);
create index if not exists idx_stories_user_created on public.stories(user_id, created_at desc);
create index if not exists idx_stories_genre on public.stories(genre);
create index if not exists idx_stories_series on public.stories(series_id);
create index if not exists idx_stories_parent on public.stories(parent_story_id);
create index if not exists idx_stories_status on public.stories(status);

-- =====================================================
-- CONVERSATIONS TABLE
-- =====================================================
-- Stores Fixion chat conversations

create table if not exists public.conversations (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references public.users(id) on delete cascade,

    -- Conversation data
    messages jsonb not null default '[]'::jsonb,
    -- Each message: {role: 'user'|'assistant', content: string, timestamp: string}

    -- Context for story discussions
    story_context_id uuid references public.stories(id) on delete set null,
    context_type text check (context_type in ('onboarding', 'story_discussion', 'preference_update', 'retell_request', 'general') or context_type is null),

    -- Conversation state
    is_active boolean not null default true,
    message_count integer not null default 0,

    -- Timestamps
    created_at timestamp with time zone not null default now(),
    updated_at timestamp with time zone not null default now()
);

-- Indexes
create index if not exists idx_conversations_user on public.conversations(user_id);
create index if not exists idx_conversations_active on public.conversations(user_id, is_active) where is_active = true;

-- =====================================================
-- HALLUCINATIONS TABLE (Hall of Fame)
-- =====================================================
-- Tracks user-reported hallucinations for gamification

create table if not exists public.hallucinations (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references public.users(id) on delete cascade,
    story_id uuid references public.stories(id) on delete set null,

    -- The hallucination details
    description text not null,  -- User's description of what was wrong
    excerpt text,  -- The problematic text from the story

    -- The reward image (if generated)
    image_url text,
    image_prompt text,  -- What we asked the image model to generate

    -- Display preferences
    credited_name text,  -- How user wants to be credited (null = anonymous)
    show_in_hall_of_fame boolean not null default true,

    -- Reward tracking
    credits_awarded integer not null default 0,
    badge_awarded text,  -- 'editor_badge', etc.

    -- Timestamps
    created_at timestamp with time zone not null default now()
);

-- Index for hall of fame display
create index if not exists idx_hallucinations_hall_of_fame
    on public.hallucinations(created_at desc)
    where show_in_hall_of_fame = true;

-- =====================================================
-- CREDIT_TRANSACTIONS TABLE
-- =====================================================
-- Audit log for all credit changes

create table if not exists public.credit_transactions (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references public.users(id) on delete cascade,

    -- Transaction details
    amount integer not null,  -- Positive = credit added, negative = credit used
    balance_after integer not null,  -- User's balance after this transaction

    -- Transaction type
    transaction_type text not null
        check (transaction_type in (
            'trial_grant',           -- Initial trial credits
            'subscription_refresh',  -- Monthly credit refresh
            'credit_pack_purchase',  -- Bought extra credits
            'story_generation',      -- Used for new story
            'retell_generation',     -- Used for retell
            'hallucination_reward',  -- Bonus for finding hallucination
            'manual_adjustment',     -- Admin adjustment
            'rollover'               -- Credits rolled over from previous period
        )),

    -- Reference to related entity
    reference_id uuid,  -- Story ID, Stripe payment ID, etc.
    reference_type text,  -- 'story', 'stripe_payment', 'hallucination', etc.

    -- Metadata
    description text,
    metadata jsonb,

    -- Timestamps
    created_at timestamp with time zone not null default now()
);

-- Index for user transaction history
create index if not exists idx_credit_transactions_user
    on public.credit_transactions(user_id, created_at desc);

-- =====================================================
-- SCHEDULED_STORIES TABLE
-- =====================================================
-- Queue for upcoming story deliveries

create table if not exists public.scheduled_stories (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references public.users(id) on delete cascade,

    -- Schedule
    scheduled_for timestamp with time zone not null,

    -- Generation parameters (snapshot at time of scheduling)
    story_bible jsonb not null,
    preferences jsonb not null,

    -- Status
    status text not null default 'pending'
        check (status in ('pending', 'generating', 'completed', 'failed', 'cancelled')),

    -- Result (if completed)
    story_id uuid references public.stories(id) on delete set null,
    error_message text,

    -- Retry tracking
    attempts integer not null default 0,
    last_attempt_at timestamp with time zone,

    -- Timestamps
    created_at timestamp with time zone not null default now()
);

-- Index for finding due stories
create index if not exists idx_scheduled_stories_pending
    on public.scheduled_stories(scheduled_for)
    where status = 'pending';

-- =====================================================
-- ROW LEVEL SECURITY (RLS)
-- =====================================================

-- Enable RLS on all tables
alter table public.users enable row level security;
alter table public.stories enable row level security;
alter table public.conversations enable row level security;
alter table public.hallucinations enable row level security;
alter table public.credit_transactions enable row level security;
alter table public.scheduled_stories enable row level security;

-- Users: can only read/update their own data
create policy "Users can view own data" on public.users
    for select using (auth.uid() = id);

create policy "Users can update own data" on public.users
    for update using (auth.uid() = id);

-- Stories: users can only see their own stories
create policy "Users can view own stories" on public.stories
    for select using (auth.uid() = user_id);

create policy "Users can insert own stories" on public.stories
    for insert with check (auth.uid() = user_id);

create policy "Users can update own stories" on public.stories
    for update using (auth.uid() = user_id);

-- Conversations: users can only see their own conversations
create policy "Users can view own conversations" on public.conversations
    for select using (auth.uid() = user_id);

create policy "Users can insert own conversations" on public.conversations
    for insert with check (auth.uid() = user_id);

create policy "Users can update own conversations" on public.conversations
    for update using (auth.uid() = user_id);

-- Hallucinations: users can see all (for hall of fame) but only modify own
create policy "Anyone can view hall of fame" on public.hallucinations
    for select using (show_in_hall_of_fame = true or auth.uid() = user_id);

create policy "Users can insert own hallucinations" on public.hallucinations
    for insert with check (auth.uid() = user_id);

-- Credit transactions: users can only view their own
create policy "Users can view own transactions" on public.credit_transactions
    for select using (auth.uid() = user_id);

-- Scheduled stories: users can only view their own
create policy "Users can view own scheduled stories" on public.scheduled_stories
    for select using (auth.uid() = user_id);

-- =====================================================
-- FUNCTIONS AND TRIGGERS
-- =====================================================

-- Function to update updated_at timestamp
create or replace function public.update_updated_at_column()
returns trigger as $$
begin
    new.updated_at = now();
    return new;
end;
$$ language plpgsql;

-- Apply updated_at trigger to relevant tables
create trigger update_users_updated_at
    before update on public.users
    for each row execute function public.update_updated_at_column();

create trigger update_stories_updated_at
    before update on public.stories
    for each row execute function public.update_updated_at_column();

create trigger update_conversations_updated_at
    before update on public.conversations
    for each row execute function public.update_updated_at_column();

-- Function to create user profile after signup
create or replace function public.handle_new_user()
returns trigger as $$
begin
    insert into public.users (id, email, credits, trial_credits_remaining)
    values (
        new.id,
        new.email,
        10,  -- Trial credits
        10
    );

    -- Log the trial credit grant
    insert into public.credit_transactions (
        user_id, amount, balance_after, transaction_type, description
    ) values (
        new.id,
        10,
        10,
        'trial_grant',
        'Welcome to FixionMail! Here are your 10 free story credits.'
    );

    return new;
end;
$$ language plpgsql security definer;

-- Trigger to auto-create profile on signup
create trigger on_auth_user_created
    after insert on auth.users
    for each row execute function public.handle_new_user();

-- Function to deduct credits and log transaction
create or replace function public.deduct_credits(
    p_user_id uuid,
    p_amount integer,
    p_transaction_type text,
    p_reference_id uuid default null,
    p_description text default null
)
returns boolean as $$
declare
    v_current_credits integer;
    v_new_balance integer;
begin
    -- Get current credits with lock
    select credits into v_current_credits
    from public.users
    where id = p_user_id
    for update;

    -- Check sufficient credits
    if v_current_credits < p_amount then
        return false;
    end if;

    -- Calculate new balance
    v_new_balance := v_current_credits - p_amount;

    -- Update user credits
    update public.users
    set
        credits = v_new_balance,
        credits_used_total = credits_used_total + p_amount,
        updated_at = now()
    where id = p_user_id;

    -- Log transaction
    insert into public.credit_transactions (
        user_id, amount, balance_after, transaction_type,
        reference_id, reference_type, description
    ) values (
        p_user_id,
        -p_amount,
        v_new_balance,
        p_transaction_type,
        p_reference_id,
        case
            when p_transaction_type = 'story_generation' then 'story'
            when p_transaction_type = 'retell_generation' then 'story'
            else null
        end,
        p_description
    );

    return true;
end;
$$ language plpgsql security definer;

-- Function to add credits and log transaction
create or replace function public.add_credits(
    p_user_id uuid,
    p_amount integer,
    p_transaction_type text,
    p_reference_id uuid default null,
    p_description text default null,
    p_metadata jsonb default null
)
returns integer as $$
declare
    v_new_balance integer;
begin
    -- Update user credits
    update public.users
    set
        credits = credits + p_amount,
        updated_at = now()
    where id = p_user_id
    returning credits into v_new_balance;

    -- Log transaction
    insert into public.credit_transactions (
        user_id, amount, balance_after, transaction_type,
        reference_id, reference_type, description, metadata
    ) values (
        p_user_id,
        p_amount,
        v_new_balance,
        p_transaction_type,
        p_reference_id,
        case
            when p_transaction_type = 'credit_pack_purchase' then 'stripe_payment'
            when p_transaction_type = 'subscription_refresh' then 'stripe_subscription'
            when p_transaction_type = 'hallucination_reward' then 'hallucination'
            else null
        end,
        p_description,
        p_metadata
    );

    return v_new_balance;
end;
$$ language plpgsql security definer;

-- =====================================================
-- INITIAL DATA / SEED
-- =====================================================

-- No initial seed data needed - users are created through auth flow

comment on table public.users is 'User profiles extending Supabase Auth with app-specific data';
comment on table public.stories is 'Generated stories with full content, metadata, and revision history';
comment on table public.conversations is 'Fixion chat conversations with context tracking';
comment on table public.hallucinations is 'User-reported hallucinations for gamification and quality tracking';
comment on table public.credit_transactions is 'Audit log of all credit additions and deductions';
comment on table public.scheduled_stories is 'Queue for automated story delivery scheduling';
