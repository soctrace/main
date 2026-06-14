create table if not exists public.demo_access_logs (
  id uuid primary key default gen_random_uuid(),
  email text,
  role text,
  event_type text not null,
  created_at timestamptz not null default now(),
  session_id text,
  pathname text,
  user_agent text,
  metadata jsonb default '{}'::jsonb
);

alter table public.demo_access_logs enable row level security;

create policy "Allow authenticated users to insert demo logs"
on public.demo_access_logs
for insert
to authenticated
with check (true);
