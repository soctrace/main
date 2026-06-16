create table if not exists public.user_events (
  id uuid primary key default gen_random_uuid(),
  user_id uuid,
  email text,
  event_type text not null,
  page text,
  section_id text,
  section_name text,
  layer text,
  year integer,
  question text,
  metadata jsonb default '{}'::jsonb,
  user_agent text,
  created_at timestamptz not null default now()
);

create index if not exists user_events_created_at_idx
on public.user_events (created_at desc);

create index if not exists user_events_event_type_created_at_idx
on public.user_events (event_type, created_at desc);

create index if not exists user_events_user_created_at_idx
on public.user_events (user_id, created_at desc);

alter table public.user_events enable row level security;

create policy "Allow authenticated users to insert user events"
on public.user_events
for insert
to authenticated
with check (auth.uid() = user_id);
