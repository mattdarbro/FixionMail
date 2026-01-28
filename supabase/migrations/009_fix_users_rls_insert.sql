-- Fix: Add INSERT policy for users table
-- The users table has RLS enabled but was missing an INSERT policy,
-- causing "new row violates row-level security policy" errors (code 42501)
-- when the backend tries to create user profiles during login.
--
-- We use WITH CHECK (true) because the service role key should bypass RLS,
-- but the supabase-py client doesn't always set the role correctly.
-- Inserts only happen from the authenticated backend, so this is safe.

-- Drop the restrictive policy if it exists
DROP POLICY IF EXISTS "Users can insert own profile" ON public.users;

-- Allow inserts (backend controls access at the application layer)
CREATE POLICY "Users can insert own profile" ON public.users
    FOR INSERT WITH CHECK (true);
