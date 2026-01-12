-- =====================================================
-- FIXIONMAIL SUPABASE SCHEMA AUDIT
-- =====================================================
-- Run this in Supabase SQL Editor to check your schema
-- It will report which tables exist and which are missing

-- Check for all required tables
SELECT
    table_name,
    CASE
        WHEN table_name IS NOT NULL THEN '✅ EXISTS'
        ELSE '❌ MISSING'
    END as status
FROM (
    VALUES
        ('users'),
        ('stories'),
        ('conversations'),
        ('hallucinations'),
        ('credit_transactions'),
        ('scheduled_stories'),
        ('story_jobs'),
        ('scheduled_deliveries'),
        ('character_names')
) AS required(table_name)
LEFT JOIN information_schema.tables t
    ON t.table_name = required.table_name
    AND t.table_schema = 'public'
ORDER BY required.table_name;

-- =====================================================
-- DETAILED TABLE CHECKS
-- =====================================================

-- Check users table columns
SELECT 'USERS TABLE COLUMNS:' as info;
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'users'
ORDER BY ordinal_position;

-- Check stories table columns
SELECT 'STORIES TABLE COLUMNS:' as info;
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'stories'
ORDER BY ordinal_position;

-- Check story_jobs table columns
SELECT 'STORY_JOBS TABLE COLUMNS:' as info;
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'story_jobs'
ORDER BY ordinal_position;

-- Check scheduled_deliveries table columns
SELECT 'SCHEDULED_DELIVERIES TABLE COLUMNS:' as info;
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'scheduled_deliveries'
ORDER BY ordinal_position;

-- Check character_names table columns
SELECT 'CHARACTER_NAMES TABLE COLUMNS:' as info;
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'character_names'
ORDER BY ordinal_position;

-- =====================================================
-- DATA COUNTS
-- =====================================================
SELECT 'TABLE ROW COUNTS:' as info;

SELECT 'users' as table_name, COUNT(*) as row_count FROM public.users
UNION ALL
SELECT 'stories', COUNT(*) FROM public.stories
UNION ALL
SELECT 'story_jobs', COUNT(*) FROM public.story_jobs
UNION ALL
SELECT 'scheduled_deliveries', COUNT(*) FROM public.scheduled_deliveries
UNION ALL
SELECT 'character_names', COUNT(*) FROM public.character_names
UNION ALL
SELECT 'credit_transactions', COUNT(*) FROM public.credit_transactions;

-- =====================================================
-- CHECK FOR PENDING/STUCK ITEMS
-- =====================================================
SELECT 'PENDING STORY JOBS:' as info;
SELECT job_id, user_email, status, created_at, current_step
FROM public.story_jobs
WHERE status IN ('pending', 'running')
ORDER BY created_at DESC
LIMIT 10;

SELECT 'PENDING DELIVERIES:' as info;
SELECT id, user_email, status, deliver_at, story_id
FROM public.scheduled_deliveries
WHERE status = 'pending'
ORDER BY deliver_at DESC
LIMIT 10;

SELECT 'RECENT FAILED JOBS:' as info;
SELECT job_id, user_email, error_message, created_at
FROM public.story_jobs
WHERE status = 'failed'
ORDER BY created_at DESC
LIMIT 5;

SELECT 'RECENT FAILED DELIVERIES:' as info;
SELECT id, user_email, error_message, created_at
FROM public.scheduled_deliveries
WHERE status = 'failed'
ORDER BY created_at DESC
LIMIT 5;
