-- FixionMail Character Names Database
-- This migration creates a table of pre-defined character names to avoid
-- AI defaulting to common names like Maya Chen, Elena, Marcus

-- =====================================================
-- CHARACTER_NAMES TABLE
-- =====================================================
-- A curated database of names that the system can draw from

create table if not exists public.character_names (
    id uuid primary key default gen_random_uuid(),

    -- The name itself
    name text not null,

    -- Classification
    name_type text not null check (name_type in ('first', 'last')),
    gender text check (
        (name_type = 'first' and gender in ('male', 'female', 'neutral')) or
        (name_type = 'last' and gender is null)
    ),

    -- Cultural diversity tracking
    cultural_origin text,  -- e.g., 'english', 'spanish', 'chinese', 'arabic', etc.

    -- Usage tracking
    usage_count integer not null default 0,
    last_used_at timestamp with time zone,

    -- Timestamps
    created_at timestamp with time zone not null default now(),

    -- Prevent duplicate names of the same type/gender
    unique(name, name_type, gender)
);

-- Indexes for efficient name selection
create index if not exists idx_character_names_type_gender
    on public.character_names(name_type, gender);

create index if not exists idx_character_names_usage
    on public.character_names(name_type, gender, usage_count, last_used_at);

create index if not exists idx_character_names_cultural_origin
    on public.character_names(cultural_origin);

-- =====================================================
-- FUNCTIONS FOR NAME SELECTION
-- =====================================================

-- Function to get random names with low usage (prefers less-used names)
create or replace function public.get_random_names(
    p_name_type text,
    p_gender text default null,
    p_count integer default 1,
    p_exclude_names text[] default array[]::text[]
)
returns table(id uuid, name text, cultural_origin text) as $$
begin
    return query
    select cn.id, cn.name, cn.cultural_origin
    from public.character_names cn
    where cn.name_type = p_name_type
      and (p_gender is null or cn.gender = p_gender or cn.gender = 'neutral')
      and cn.name != all(p_exclude_names)
    order by
        cn.usage_count asc,  -- Prefer less-used names
        cn.last_used_at asc nulls first,  -- Prefer names not used recently
        random()  -- Random among equally-used names
    limit p_count;
end;
$$ language plpgsql;

-- Function to increment usage count for a name
create or replace function public.increment_name_usage(p_name_id uuid)
returns void as $$
begin
    update public.character_names
    set
        usage_count = usage_count + 1,
        last_used_at = now()
    where id = p_name_id;
end;
$$ language plpgsql;

-- Function to increment usage by name string (for flexibility)
create or replace function public.increment_name_usage_by_name(
    p_name text,
    p_name_type text,
    p_gender text default null
)
returns void as $$
begin
    update public.character_names
    set
        usage_count = usage_count + 1,
        last_used_at = now()
    where name = p_name
      and name_type = p_name_type
      and (gender = p_gender or (p_gender is null and name_type = 'last'));
end;
$$ language plpgsql;

-- =====================================================
-- ROW LEVEL SECURITY
-- =====================================================

-- Enable RLS (but allow public read access since these are shared names)
alter table public.character_names enable row level security;

-- Anyone can read names (they're shared across all users)
create policy "Anyone can view character names" on public.character_names
    for select using (true);

-- Only service role can insert/update/delete names
-- (This is enforced by not creating policies for insert/update/delete)

comment on table public.character_names is 'Pre-defined character names database with usage tracking for story generation diversity';
