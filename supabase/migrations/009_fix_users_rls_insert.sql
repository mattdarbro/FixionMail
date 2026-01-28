-- Fix: Add INSERT policy for users table
-- The users table has RLS enabled but was missing an INSERT policy,
-- causing "new row violates row-level security policy" errors (code 42501)
-- when the backend tries to create user profiles during login.

-- Allow authenticated users to insert their own profile
CREATE POLICY "Users can insert own profile" ON public.users
    FOR INSERT WITH CHECK (auth.uid() = id);
