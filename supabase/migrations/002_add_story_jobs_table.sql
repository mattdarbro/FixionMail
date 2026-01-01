-- Migration: Add story_jobs table for job queue
-- Replaces SQLite-based job queue with Supabase PostgreSQL

-- =====================================================
-- STORY_JOBS TABLE (Job Queue)
-- =====================================================
-- Tracks story generation jobs through the pipeline

create table if not exists public.story_jobs (
    id uuid primary key default gen_random_uuid(),

    -- Job identification
    job_id text unique not null,

    -- Status tracking
    status text not null default 'pending'
        check (status in ('pending', 'running', 'completed', 'failed')),

    -- Input data
    story_bible jsonb not null,
    user_email text not null,
    user_id uuid references public.users(id) on delete set null,  -- Optional, linked after lookup
    settings jsonb,  -- writer_model, structure_model, editor_model, tts settings, etc.

    -- Progress tracking
    current_step text,  -- 'structure', 'writer', 'editor', 'image', 'audio', 'email', 'done'
    progress_percent integer default 0 check (progress_percent >= 0 and progress_percent <= 100),

    -- Output data (populated on completion)
    result jsonb,  -- Full result including story, metadata, email_sent status
    story_id uuid references public.stories(id) on delete set null,  -- Link to saved story
    error_message text,

    -- Timestamps
    created_at timestamp with time zone not null default now(),
    started_at timestamp with time zone,
    completed_at timestamp with time zone,

    -- Performance metrics
    generation_time_seconds real,

    -- Retry tracking
    retry_count integer not null default 0
);

-- Indexes for common queries
create index if not exists idx_story_jobs_status on public.story_jobs(status);
create index if not exists idx_story_jobs_status_created on public.story_jobs(status, created_at);
create index if not exists idx_story_jobs_job_id on public.story_jobs(job_id);
create index if not exists idx_story_jobs_user_email on public.story_jobs(user_email);
create index if not exists idx_story_jobs_user_id on public.story_jobs(user_id);
create index if not exists idx_story_jobs_created_at on public.story_jobs(created_at desc);

-- Index for finding pending jobs (used by worker)
create index if not exists idx_story_jobs_pending
    on public.story_jobs(created_at)
    where status = 'pending';

-- Index for finding failed jobs
create index if not exists idx_story_jobs_failed
    on public.story_jobs(created_at desc)
    where status = 'failed';

-- Enable RLS
alter table public.story_jobs enable row level security;

-- RLS Policies: Users can only see their own jobs
create policy "Users can view own jobs" on public.story_jobs
    for select using (
        auth.uid() = user_id
        or user_email = (select email from public.users where id = auth.uid())
    );

-- Service role can do everything (for backend worker)
-- Note: Using service_role key bypasses RLS, so no explicit policy needed

-- Comments
comment on table public.story_jobs is 'Job queue for story generation pipeline processing';
comment on column public.story_jobs.job_id is 'Unique job identifier for API reference';
comment on column public.story_jobs.current_step is 'Current pipeline step: structure, writer, editor, image, audio, email, done';
comment on column public.story_jobs.result is 'Full generation result including story content and metadata';
