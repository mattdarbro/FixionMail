-- Migration: Add scheduled_deliveries table for email delivery scheduling
-- Decouples story generation (off-peak) from email delivery (user's preferred time)

-- =====================================================
-- SCHEDULED_DELIVERIES TABLE
-- =====================================================
-- Queue for email deliveries at user's preferred time

create table if not exists public.scheduled_deliveries (
    id uuid primary key default gen_random_uuid(),

    -- Links to story and user
    story_id uuid not null references public.stories(id) on delete cascade,
    user_id uuid not null references public.users(id) on delete cascade,
    user_email text not null,

    -- Delivery scheduling
    deliver_at timestamp with time zone not null,  -- User's preferred delivery time
    timezone text not null default 'UTC',  -- User's timezone for reference

    -- Status tracking
    status text not null default 'pending'
        check (status in ('pending', 'sending', 'sent', 'failed')),

    -- Delivery result
    sent_at timestamp with time zone,
    resend_email_id text,  -- Resend API email ID for tracking
    error_message text,
    retry_count integer not null default 0,

    -- Timestamps
    created_at timestamp with time zone not null default now(),
    updated_at timestamp with time zone not null default now()
);

-- Index for finding deliveries due to be sent (primary worker query)
create index if not exists idx_scheduled_deliveries_pending
    on public.scheduled_deliveries(deliver_at)
    where status = 'pending';

-- Index for user's delivery history
create index if not exists idx_scheduled_deliveries_user
    on public.scheduled_deliveries(user_id, deliver_at desc);

-- Index for story lookup
create index if not exists idx_scheduled_deliveries_story
    on public.scheduled_deliveries(story_id);

-- Index for status queries (dashboard)
create index if not exists idx_scheduled_deliveries_status
    on public.scheduled_deliveries(status, deliver_at);

-- Index for failed deliveries (for retry/debugging)
create index if not exists idx_scheduled_deliveries_failed
    on public.scheduled_deliveries(created_at desc)
    where status = 'failed';

-- Enable RLS
alter table public.scheduled_deliveries enable row level security;

-- RLS Policies
create policy "Users can view own deliveries" on public.scheduled_deliveries
    for select using (auth.uid() = user_id);

-- Trigger for updated_at
create trigger update_scheduled_deliveries_updated_at
    before update on public.scheduled_deliveries
    for each row execute function public.update_updated_at_column();

-- Comments
comment on table public.scheduled_deliveries is 'Queue for email deliveries at user preferred time, decoupled from story generation';
comment on column public.scheduled_deliveries.deliver_at is 'Exact timestamp when email should be sent (in UTC)';
comment on column public.scheduled_deliveries.resend_email_id is 'Resend API email ID for delivery tracking and debugging';
