-- =====================================================
-- FIXIONMAIL iOS APP SUPPORT MIGRATION
-- =====================================================
-- This migration adds tables and columns to support the iOS app:
-- - Pre-show system (writing room drama)
-- - Device registration (push notifications)
-- - Story metadata (writer, fixion_note, read status, favorites)
-- - User settings for character variation (Fifi/Xion)
-- - Apple Sign-in support

-- =====================================================
-- 1. USER TABLE ADDITIONS
-- =====================================================

-- Add Apple Sign-in support
ALTER TABLE public.users
ADD COLUMN IF NOT EXISTS apple_user_id text UNIQUE;

-- Add password hash for email/password auth (in addition to magic link)
ALTER TABLE public.users
ADD COLUMN IF NOT EXISTS password_hash text;

-- Add character variation settings
ALTER TABLE public.users
ADD COLUMN IF NOT EXISTS variation_tolerance text DEFAULT 'medium'
    CHECK (variation_tolerance IN ('low', 'medium', 'high'));

ALTER TABLE public.users
ADD COLUMN IF NOT EXISTS xion_experiments text DEFAULT 'occasional'
    CHECK (xion_experiments IN ('never', 'rare', 'occasional', 'frequent'));

ALTER TABLE public.users
ADD COLUMN IF NOT EXISTS fifi_enabled boolean DEFAULT true;

-- Index for Apple Sign-in lookup
CREATE INDEX IF NOT EXISTS idx_users_apple_user_id ON public.users(apple_user_id);

-- =====================================================
-- 2. STORY TABLE ADDITIONS
-- =====================================================

-- Add writer attribution (who from the writing room "wrote" this)
ALTER TABLE public.stories
ADD COLUMN IF NOT EXISTS writer text
    CHECK (writer IN ('maurice', 'fifi', 'xion', 'joan') OR writer IS NULL);

-- Add Fixion's personal note
ALTER TABLE public.stories
ADD COLUMN IF NOT EXISTS fixion_note text;

-- Add read tracking for iOS app
ALTER TABLE public.stories
ADD COLUMN IF NOT EXISTS read boolean DEFAULT false;

ALTER TABLE public.stories
ADD COLUMN IF NOT EXISTS read_at timestamp with time zone;

-- Add favorites and archive
ALTER TABLE public.stories
ADD COLUMN IF NOT EXISTS favorite boolean DEFAULT false;

ALTER TABLE public.stories
ADD COLUMN IF NOT EXISTS archived boolean DEFAULT false;

-- Add variation metadata (what drift/experiment was applied)
ALTER TABLE public.stories
ADD COLUMN IF NOT EXISTS variation_applied text;

ALTER TABLE public.stories
ADD COLUMN IF NOT EXISTS variation_metadata jsonb;

-- Indexes for iOS app queries
CREATE INDEX IF NOT EXISTS idx_stories_read ON public.stories(user_id, read);
CREATE INDEX IF NOT EXISTS idx_stories_favorite ON public.stories(user_id, favorite) WHERE favorite = true;
CREATE INDEX IF NOT EXISTS idx_stories_archived ON public.stories(user_id, archived);
CREATE INDEX IF NOT EXISTS idx_stories_writer ON public.stories(writer);

-- =====================================================
-- 3. PRESHOWS TABLE (NEW)
-- =====================================================
-- Stores writing room drama scenes that play while stories generate

CREATE TABLE IF NOT EXISTS public.preshows (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Link to story generation
    story_id uuid REFERENCES public.stories(id) ON DELETE SET NULL,
    task_id text,  -- Links to story_jobs.job_id
    user_id uuid NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,

    -- Pre-show content
    variation text NOT NULL DEFAULT 'standard'
        CHECK (variation IN ('standard', 'fifi_day', 'xion_experiment', 'chaos_day')),
    characters text[] NOT NULL DEFAULT ARRAY['fixion', 'maurice'],

    -- The scene data - array of beats
    -- Each beat: {character, action, dialogue, delay_ms}
    beats jsonb NOT NULL DEFAULT '[]'::jsonb,

    -- Conclusion message
    conclusion text DEFAULT 'Your story is ready!',

    -- Generation metadata
    story_bible_snapshot jsonb,  -- The bible used (for context)

    -- Timestamps
    created_at timestamp with time zone NOT NULL DEFAULT now()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_preshows_story ON public.preshows(story_id);
CREATE INDEX IF NOT EXISTS idx_preshows_task ON public.preshows(task_id);
CREATE INDEX IF NOT EXISTS idx_preshows_user ON public.preshows(user_id);

-- Enable RLS
ALTER TABLE public.preshows ENABLE ROW LEVEL SECURITY;

-- RLS Policies
DROP POLICY IF EXISTS "Users can view own preshows" ON public.preshows;
CREATE POLICY "Users can view own preshows" ON public.preshows
    FOR SELECT USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Service role can manage preshows" ON public.preshows;
CREATE POLICY "Service role can manage preshows" ON public.preshows
    FOR ALL USING (true) WITH CHECK (true);

-- =====================================================
-- 4. DEVICES TABLE (NEW)
-- =====================================================
-- Stores device tokens for push notifications

CREATE TABLE IF NOT EXISTS public.devices (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,

    -- Device identification
    token text NOT NULL,  -- APNs device token
    platform text NOT NULL DEFAULT 'ios'
        CHECK (platform IN ('ios', 'android', 'web')),

    -- Device metadata
    device_name text,
    device_model text,
    os_version text,
    app_version text,

    -- Status
    is_active boolean DEFAULT true,
    last_used_at timestamp with time zone DEFAULT now(),

    -- Timestamps
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    updated_at timestamp with time zone NOT NULL DEFAULT now(),

    -- Ensure unique device per user
    UNIQUE(user_id, token)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_devices_user ON public.devices(user_id);
CREATE INDEX IF NOT EXISTS idx_devices_token ON public.devices(token);
CREATE INDEX IF NOT EXISTS idx_devices_active ON public.devices(user_id, is_active) WHERE is_active = true;

-- Enable RLS
ALTER TABLE public.devices ENABLE ROW LEVEL SECURITY;

-- RLS Policies
DROP POLICY IF EXISTS "Users can view own devices" ON public.devices;
CREATE POLICY "Users can view own devices" ON public.devices
    FOR SELECT USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can manage own devices" ON public.devices;
CREATE POLICY "Users can manage own devices" ON public.devices
    FOR ALL USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "Service role can manage devices" ON public.devices;
CREATE POLICY "Service role can manage devices" ON public.devices
    FOR ALL USING (true) WITH CHECK (true);

-- Trigger for updated_at
DROP TRIGGER IF EXISTS update_devices_updated_at ON public.devices;
CREATE TRIGGER update_devices_updated_at
    BEFORE UPDATE ON public.devices
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

-- =====================================================
-- 5. STORY_JOBS TABLE ADDITIONS
-- =====================================================

-- Add preshow_id to link jobs with preshows
ALTER TABLE public.story_jobs
ADD COLUMN IF NOT EXISTS preshow_id uuid REFERENCES public.preshows(id) ON DELETE SET NULL;

-- =====================================================
-- 6. HELPER FUNCTIONS
-- =====================================================

-- Function to select a writer based on user settings and randomness
CREATE OR REPLACE FUNCTION public.select_story_writer(
    p_user_id uuid
)
RETURNS text AS $$
DECLARE
    v_user record;
    v_random float;
    v_writer text;
BEGIN
    -- Get user settings
    SELECT
        COALESCE(variation_tolerance, 'medium') as variation_tolerance,
        COALESCE(xion_experiments, 'occasional') as xion_experiments,
        COALESCE(fifi_enabled, true) as fifi_enabled
    INTO v_user
    FROM public.users
    WHERE id = p_user_id;

    -- Generate random number
    v_random := random();

    -- Determine writer based on settings and randomness
    -- Higher variation_tolerance = more chance of Fifi/Xion
    -- xion_experiments setting affects Xion probability

    CASE v_user.variation_tolerance
        WHEN 'low' THEN
            -- Mostly Maurice and Joan
            IF v_random < 0.6 THEN
                v_writer := 'maurice';
            ELSIF v_random < 0.9 THEN
                v_writer := 'joan';
            ELSIF v_user.fifi_enabled AND v_random < 0.95 THEN
                v_writer := 'fifi';
            ELSE
                v_writer := 'maurice';
            END IF;

        WHEN 'medium' THEN
            -- Balanced mix
            IF v_random < 0.4 THEN
                v_writer := 'maurice';
            ELSIF v_random < 0.65 THEN
                v_writer := 'joan';
            ELSIF v_user.fifi_enabled AND v_random < 0.85 THEN
                v_writer := 'fifi';
            ELSIF v_user.xion_experiments != 'never' AND v_random < 0.95 THEN
                v_writer := 'xion';
            ELSE
                v_writer := 'maurice';
            END IF;

        WHEN 'high' THEN
            -- More variety
            IF v_random < 0.25 THEN
                v_writer := 'maurice';
            ELSIF v_random < 0.45 THEN
                v_writer := 'joan';
            ELSIF v_user.fifi_enabled AND v_random < 0.70 THEN
                v_writer := 'fifi';
            ELSIF v_user.xion_experiments != 'never' AND v_random < 0.95 THEN
                v_writer := 'xion';
            ELSE
                v_writer := 'joan';
            END IF;

        ELSE
            v_writer := 'maurice';
    END CASE;

    -- Additional Xion check based on experiments setting
    IF v_writer = 'xion' THEN
        CASE v_user.xion_experiments
            WHEN 'never' THEN v_writer := 'maurice';
            WHEN 'rare' THEN
                IF random() > 0.3 THEN v_writer := 'joan'; END IF;
            WHEN 'occasional' THEN
                NULL; -- Keep Xion
            WHEN 'frequent' THEN
                NULL; -- Keep Xion
        END CASE;
    END IF;

    RETURN v_writer;
END;
$$ LANGUAGE plpgsql;

-- Function to generate a Fixion note based on writer
CREATE OR REPLACE FUNCTION public.generate_fixion_note_template(
    p_writer text
)
RETURNS text AS $$
DECLARE
    v_notes text[];
    v_note text;
BEGIN
    CASE p_writer
        WHEN 'maurice' THEN
            v_notes := ARRAY[
                'Maurice was particularly proud of this one, though he''d never admit it. -F',
                'Maurice grumbled through the whole thing, but I think he secretly enjoyed it. -F',
                'This one went through three drafts. Maurice is... thorough. -F',
                'Maurice handled this one. He sends his regards (he didn''t, but I''m sure he would have). -F'
            ];
        WHEN 'joan' THEN
            v_notes := ARRAY[
                'Joan took extra care with the emotional beats on this one. Hope it resonates. -F',
                'This one has Joan''s fingerprints all over it - in the best way. -F',
                'Joan wanted me to tell you she had fun with this one. -F',
                'Joan says the ending came to her in a dream. I believe her. -F'
            ];
        WHEN 'fifi' THEN
            v_notes := ARRAY[
                'Fifi handled this one. I think she did great, but let me know if you want me to talk to her. -F',
                'Fifi was SO excited to write this. She checked with me three times if it was okay. -F',
                'This one''s from Fifi. She says she hopes you like it! (She''s nervous.) -F',
                'Fifi took a slightly... creative interpretation here. I think it works! -F'
            ];
        WHEN 'xion' THEN
            v_notes := ARRAY[
                'Xion insisted on the genre twist. I tried to stop him. I really did. -F',
                'This one is... experimental. Xion''s idea. Let me know what you think? -F',
                'Xion snuck something in here. I''m not sure what, but it''s definitely something. -F',
                'Xion called this one his "masterpiece." Maurice threw a pencil at him. -F'
            ];
        ELSE
            v_notes := ARRAY[
                'Hope this one hits the spot. -F',
                'Fresh from the writing room, just for you. -F',
                'The team put their hearts into this one. -F'
            ];
    END CASE;

    -- Select random note
    v_note := v_notes[1 + floor(random() * array_length(v_notes, 1))::int];

    RETURN v_note;
END;
$$ LANGUAGE plpgsql;

-- =====================================================
-- VERIFICATION
-- =====================================================
SELECT 'iOS App Support migration complete!' as status;

SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'users'
AND column_name IN ('apple_user_id', 'variation_tolerance', 'xion_experiments', 'fifi_enabled');

SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'stories'
AND column_name IN ('writer', 'fixion_note', 'read', 'favorite', 'archived');

SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public'
AND table_name IN ('preshows', 'devices');
