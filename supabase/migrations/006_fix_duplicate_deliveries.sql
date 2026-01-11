-- Fix duplicate email deliveries
-- This migration adds a unique constraint on story_id to prevent duplicate
-- delivery records from being created for the same story.

-- First, clean up any existing duplicates (keep the first one created)
DELETE FROM public.scheduled_deliveries
WHERE id NOT IN (
    SELECT DISTINCT ON (story_id) id
    FROM public.scheduled_deliveries
    ORDER BY story_id, created_at ASC
);

-- Add unique constraint on story_id
-- Each story should only have ONE delivery record
ALTER TABLE public.scheduled_deliveries
    ADD CONSTRAINT unique_story_delivery UNIQUE (story_id);

-- Add index for efficient lookups by story_id (if not already covered by unique constraint)
CREATE INDEX IF NOT EXISTS idx_scheduled_deliveries_story_unique
    ON public.scheduled_deliveries(story_id);

COMMENT ON CONSTRAINT unique_story_delivery ON public.scheduled_deliveries
    IS 'Prevents duplicate deliveries for the same story (e.g., from job recovery after crash)';
