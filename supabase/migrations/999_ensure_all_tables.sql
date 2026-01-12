-- =====================================================
-- FIXIONMAIL - ENSURE ALL TABLES EXIST
-- =====================================================
-- This migration ensures all required tables exist.
-- Safe to run multiple times (uses IF NOT EXISTS).
-- Run this if you're missing tables or starting fresh.

-- =====================================================
-- 1. USERS TABLE
-- =====================================================
CREATE TABLE IF NOT EXISTS public.users (
    id uuid PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    email text UNIQUE NOT NULL,
    credits integer NOT NULL DEFAULT 10,
    credits_used_total integer NOT NULL DEFAULT 0,
    subscription_status text NOT NULL DEFAULT 'trial'
        CHECK (subscription_status IN ('trial', 'active', 'cancelled', 'expired', 'past_due')),
    subscription_tier text
        CHECK (subscription_tier IN ('monthly', 'annual', 'premium') OR subscription_tier IS NULL),
    stripe_customer_id text UNIQUE,
    stripe_subscription_id text UNIQUE,
    current_period_start timestamp with time zone,
    current_period_end timestamp with time zone,
    cancel_at_period_end boolean DEFAULT false,
    trial_credits_remaining integer NOT NULL DEFAULT 10,
    trial_started_at timestamp with time zone DEFAULT now(),
    story_bible jsonb NOT NULL DEFAULT '{}'::jsonb,
    preferences jsonb NOT NULL DEFAULT '{"story_length": "medium", "delivery_time": "08:00", "timezone": "America/New_York"}'::jsonb,
    settings jsonb DEFAULT '{}'::jsonb,
    current_genre text,
    current_protagonist jsonb,
    onboarding_completed boolean NOT NULL DEFAULT false,
    onboarding_step text DEFAULT 'welcome',
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    updated_at timestamp with time zone NOT NULL DEFAULT now(),
    last_story_at timestamp with time zone,
    last_login_at timestamp with time zone
);

-- =====================================================
-- 2. STORIES TABLE
-- =====================================================
CREATE TABLE IF NOT EXISTS public.stories (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    title text NOT NULL,
    narrative text NOT NULL,
    word_count integer NOT NULL,
    genre text NOT NULL,
    story_bible jsonb NOT NULL,
    beat_structure text,
    model_used text NOT NULL,
    is_retell boolean NOT NULL DEFAULT false,
    parent_story_id uuid REFERENCES public.stories(id) ON DELETE SET NULL,
    revision_notes text,
    revision_type text CHECK (revision_type IN ('surface', 'prose', 'structure') OR revision_type IS NULL),
    audio_url text,
    image_url text,
    series_id uuid,
    episode_number integer,
    status text NOT NULL DEFAULT 'completed'
        CHECK (status IN ('pending', 'generating', 'completed', 'failed', 'delivered')),
    delivered_at timestamp with time zone,
    email_sent boolean NOT NULL DEFAULT false,
    rating integer CHECK (rating >= 1 AND rating <= 5),
    feedback jsonb,
    credits_used integer NOT NULL DEFAULT 1,
    generation_cost_cents integer,
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    updated_at timestamp with time zone NOT NULL DEFAULT now()
);

-- =====================================================
-- 3. STORY_JOBS TABLE (Job Queue)
-- =====================================================
CREATE TABLE IF NOT EXISTS public.story_jobs (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id text UNIQUE NOT NULL,
    status text NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'running', 'completed', 'failed')),
    story_bible jsonb NOT NULL,
    user_email text NOT NULL,
    user_id uuid REFERENCES public.users(id) ON DELETE SET NULL,
    settings jsonb,
    current_step text,
    progress_percent integer DEFAULT 0 CHECK (progress_percent >= 0 AND progress_percent <= 100),
    result jsonb,
    story_id uuid REFERENCES public.stories(id) ON DELETE SET NULL,
    error_message text,
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    started_at timestamp with time zone,
    completed_at timestamp with time zone,
    generation_time_seconds real,
    retry_count integer NOT NULL DEFAULT 0
);

-- =====================================================
-- 4. SCHEDULED_DELIVERIES TABLE
-- =====================================================
CREATE TABLE IF NOT EXISTS public.scheduled_deliveries (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    story_id uuid NOT NULL REFERENCES public.stories(id) ON DELETE CASCADE,
    user_id uuid NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    user_email text NOT NULL,
    deliver_at timestamp with time zone NOT NULL,
    timezone text NOT NULL DEFAULT 'UTC',
    status text NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'sending', 'sent', 'failed')),
    sent_at timestamp with time zone,
    resend_email_id text,
    error_message text,
    retry_count integer NOT NULL DEFAULT 0,
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    updated_at timestamp with time zone NOT NULL DEFAULT now()
);

-- =====================================================
-- 5. CHARACTER_NAMES TABLE
-- =====================================================
CREATE TABLE IF NOT EXISTS public.character_names (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    name text NOT NULL,
    name_type text NOT NULL CHECK (name_type IN ('first', 'last')),
    gender text CHECK (gender IN ('male', 'female', 'neutral')),
    cultural_origin text NOT NULL,
    usage_count integer DEFAULT 0,
    last_used_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now(),
    UNIQUE(name, name_type, gender, cultural_origin)
);

-- =====================================================
-- 6. CONVERSATIONS TABLE
-- =====================================================
CREATE TABLE IF NOT EXISTS public.conversations (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    messages jsonb NOT NULL DEFAULT '[]'::jsonb,
    story_context_id uuid REFERENCES public.stories(id) ON DELETE SET NULL,
    context_type text CHECK (context_type IN ('onboarding', 'story_discussion', 'preference_update', 'retell_request', 'general') OR context_type IS NULL),
    is_active boolean NOT NULL DEFAULT true,
    message_count integer NOT NULL DEFAULT 0,
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    updated_at timestamp with time zone NOT NULL DEFAULT now()
);

-- =====================================================
-- 7. CREDIT_TRANSACTIONS TABLE
-- =====================================================
CREATE TABLE IF NOT EXISTS public.credit_transactions (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    amount integer NOT NULL,
    balance_after integer NOT NULL,
    transaction_type text NOT NULL
        CHECK (transaction_type IN (
            'trial_grant', 'subscription_refresh', 'credit_pack_purchase',
            'story_generation', 'retell_generation', 'hallucination_reward',
            'manual_adjustment', 'rollover'
        )),
    reference_id uuid,
    reference_type text,
    description text,
    metadata jsonb,
    created_at timestamp with time zone NOT NULL DEFAULT now()
);

-- =====================================================
-- 8. HALLUCINATIONS TABLE
-- =====================================================
CREATE TABLE IF NOT EXISTS public.hallucinations (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    story_id uuid REFERENCES public.stories(id) ON DELETE SET NULL,
    description text NOT NULL,
    excerpt text,
    image_url text,
    image_prompt text,
    credited_name text,
    show_in_hall_of_fame boolean NOT NULL DEFAULT true,
    credits_awarded integer NOT NULL DEFAULT 0,
    badge_awarded text,
    created_at timestamp with time zone NOT NULL DEFAULT now()
);

-- =====================================================
-- INDEXES (safe to run multiple times)
-- =====================================================

-- Users indexes
CREATE INDEX IF NOT EXISTS idx_users_email ON public.users(email);
CREATE INDEX IF NOT EXISTS idx_users_subscription_status ON public.users(subscription_status);

-- Stories indexes
CREATE INDEX IF NOT EXISTS idx_stories_user ON public.stories(user_id);
CREATE INDEX IF NOT EXISTS idx_stories_user_created ON public.stories(user_id, created_at DESC);

-- Story jobs indexes
CREATE INDEX IF NOT EXISTS idx_story_jobs_status ON public.story_jobs(status);
CREATE INDEX IF NOT EXISTS idx_story_jobs_job_id ON public.story_jobs(job_id);
CREATE INDEX IF NOT EXISTS idx_story_jobs_user_email ON public.story_jobs(user_email);
CREATE INDEX IF NOT EXISTS idx_story_jobs_user_id ON public.story_jobs(user_id);

-- Scheduled deliveries indexes
CREATE INDEX IF NOT EXISTS idx_scheduled_deliveries_status ON public.scheduled_deliveries(status, deliver_at);
CREATE INDEX IF NOT EXISTS idx_scheduled_deliveries_user ON public.scheduled_deliveries(user_id, deliver_at DESC);
CREATE INDEX IF NOT EXISTS idx_scheduled_deliveries_story ON public.scheduled_deliveries(story_id);

-- Character names indexes
CREATE INDEX IF NOT EXISTS idx_character_names_type ON public.character_names(name_type);
CREATE INDEX IF NOT EXISTS idx_character_names_gender ON public.character_names(gender);
CREATE INDEX IF NOT EXISTS idx_character_names_origin ON public.character_names(cultural_origin);
CREATE INDEX IF NOT EXISTS idx_character_names_usage ON public.character_names(usage_count);

-- =====================================================
-- ENABLE RLS ON ALL TABLES
-- =====================================================
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.stories ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.story_jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.scheduled_deliveries ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.character_names ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.credit_transactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.hallucinations ENABLE ROW LEVEL SECURITY;

-- =====================================================
-- RLS POLICIES (using CREATE OR REPLACE where possible)
-- =====================================================

-- Allow service role full access to character_names
DROP POLICY IF EXISTS "Service role has full access to character_names" ON public.character_names;
CREATE POLICY "Service role has full access to character_names"
    ON public.character_names
    FOR ALL
    USING (true)
    WITH CHECK (true);

-- =====================================================
-- UPDATED_AT TRIGGER FUNCTION
-- =====================================================
CREATE OR REPLACE FUNCTION public.update_updated_at_column()
RETURNS trigger AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply trigger to tables with updated_at
DROP TRIGGER IF EXISTS update_users_updated_at ON public.users;
CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON public.users
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

DROP TRIGGER IF EXISTS update_stories_updated_at ON public.stories;
CREATE TRIGGER update_stories_updated_at
    BEFORE UPDATE ON public.stories
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

DROP TRIGGER IF EXISTS update_scheduled_deliveries_updated_at ON public.scheduled_deliveries;
CREATE TRIGGER update_scheduled_deliveries_updated_at
    BEFORE UPDATE ON public.scheduled_deliveries
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

-- =====================================================
-- VERIFICATION
-- =====================================================
SELECT 'Schema setup complete! Verifying tables...' as status;

SELECT table_name,
    CASE WHEN table_name IS NOT NULL THEN '✅' ELSE '❌' END as exists
FROM (
    SELECT unnest(ARRAY[
        'users', 'stories', 'story_jobs', 'scheduled_deliveries',
        'character_names', 'conversations', 'credit_transactions', 'hallucinations'
    ]) as required_table
) r
LEFT JOIN information_schema.tables t
    ON t.table_name = r.required_table AND t.table_schema = 'public';
