-- Add atomic job claiming function to prevent race conditions
-- This ensures only one worker can claim a job at a time

-- Add a claimed_by column to track which worker claimed the job
ALTER TABLE public.story_jobs
    ADD COLUMN IF NOT EXISTS claimed_by TEXT;

ALTER TABLE public.story_jobs
    ADD COLUMN IF NOT EXISTS claimed_at TIMESTAMP WITH TIME ZONE;

-- Create an atomic job claiming function
-- Uses FOR UPDATE SKIP LOCKED to prevent race conditions
CREATE OR REPLACE FUNCTION public.claim_pending_job(worker_id TEXT)
RETURNS TABLE (
    id UUID,
    job_id TEXT,
    story_bible JSONB,
    user_email TEXT,
    settings JSONB,
    created_at TIMESTAMP WITH TIME ZONE,
    retry_count INTEGER
) AS $$
DECLARE
    claimed_job RECORD;
BEGIN
    -- Atomically claim the oldest pending job
    -- FOR UPDATE SKIP LOCKED prevents multiple workers from claiming the same job
    UPDATE public.story_jobs sj
    SET
        status = 'running',
        claimed_by = worker_id,
        claimed_at = NOW(),
        started_at = NOW()
    WHERE sj.id = (
        SELECT sj2.id
        FROM public.story_jobs sj2
        WHERE sj2.status = 'pending'
          AND sj2.retry_count < 3
        ORDER BY sj2.created_at ASC
        LIMIT 1
        FOR UPDATE SKIP LOCKED
    )
    RETURNING
        sj.id,
        sj.job_id,
        sj.story_bible,
        sj.user_email,
        sj.settings,
        sj.created_at,
        sj.retry_count
    INTO claimed_job;

    -- Return the claimed job (or empty if none available)
    IF claimed_job.id IS NOT NULL THEN
        RETURN QUERY SELECT
            claimed_job.id,
            claimed_job.job_id,
            claimed_job.story_bible,
            claimed_job.user_email,
            claimed_job.settings,
            claimed_job.created_at,
            claimed_job.retry_count;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- Create index for efficient pending job queries
CREATE INDEX IF NOT EXISTS idx_story_jobs_pending_created
    ON public.story_jobs(status, created_at)
    WHERE status = 'pending';

-- Create index for worker health monitoring
CREATE INDEX IF NOT EXISTS idx_story_jobs_claimed_by
    ON public.story_jobs(claimed_by, claimed_at)
    WHERE status = 'running';

COMMENT ON FUNCTION public.claim_pending_job IS
    'Atomically claim the next pending job for a worker. Uses FOR UPDATE SKIP LOCKED to prevent race conditions.';
