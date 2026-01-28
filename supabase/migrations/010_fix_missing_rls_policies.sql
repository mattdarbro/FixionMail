-- Fix: Add missing INSERT/UPDATE/DELETE policies for backend-managed tables
-- These tables have RLS enabled but only SELECT policies, causing 42501 errors
-- when the backend tries to insert or update records.
--
-- Using WITH CHECK (true) / USING (true) because these tables are managed
-- by the backend service role. Access control is enforced at the application layer.

-- story_jobs: backend inserts jobs and updates their status
CREATE POLICY "Allow insert story_jobs" ON public.story_jobs
    FOR INSERT WITH CHECK (true);
CREATE POLICY "Allow update story_jobs" ON public.story_jobs
    FOR UPDATE USING (true) WITH CHECK (true);
CREATE POLICY "Allow delete story_jobs" ON public.story_jobs
    FOR DELETE USING (true);

-- scheduled_deliveries: backend creates and manages delivery schedules
CREATE POLICY "Allow insert scheduled_deliveries" ON public.scheduled_deliveries
    FOR INSERT WITH CHECK (true);
CREATE POLICY "Allow update scheduled_deliveries" ON public.scheduled_deliveries
    FOR UPDATE USING (true) WITH CHECK (true);
CREATE POLICY "Allow delete scheduled_deliveries" ON public.scheduled_deliveries
    FOR DELETE USING (true);

-- scheduled_stories: backend creates and manages scheduled stories
CREATE POLICY "Allow insert scheduled_stories" ON public.scheduled_stories
    FOR INSERT WITH CHECK (true);
CREATE POLICY "Allow update scheduled_stories" ON public.scheduled_stories
    FOR UPDATE USING (true) WITH CHECK (true);
CREATE POLICY "Allow delete scheduled_stories" ON public.scheduled_stories
    FOR DELETE USING (true);

-- credit_transactions: backend records credit usage
CREATE POLICY "Allow insert credit_transactions" ON public.credit_transactions
    FOR INSERT WITH CHECK (true);
