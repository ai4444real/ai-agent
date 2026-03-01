-- THINGS
create table if not exists things (
  id uuid primary key default gen_random_uuid(),
  created_at timestamptz not null default now(),
  owner_sub text null,
  owner_email text null,
  type text not null,
  value_num numeric null,
  value_text text null,
  tags text[] null,
  meta jsonb null
);
create index if not exists idx_things_type_created_at
  on things (type, created_at desc);

-- DATA_SNAPSHOTS (FUTURE)
create table if not exists data_snapshots (
  id uuid primary key default gen_random_uuid(),
  created_at timestamptz not null default now(),
  source text not null,
  range_start timestamptz null,
  range_end timestamptz null,
  payload jsonb not null,
  summary text null
);
create index if not exists idx_data_snapshots_created_at
  on data_snapshots (created_at desc);

-- RUNS
create table if not exists runs (
  id uuid primary key default gen_random_uuid(),
  created_at timestamptz not null default now(),
  owner_sub text null,
  owner_email text null,
  action text not null,
  status text not null,
  input_summary jsonb null,
  error text null
);
create index if not exists idx_runs_created_at_action
  on runs (created_at desc, action);

-- MESSAGES
create table if not exists messages (
  id uuid primary key default gen_random_uuid(),
  created_at timestamptz not null default now(),
  owner_sub text null,
  owner_email text null,
  channel text not null,
  recipient text not null,
  subject text not null,
  body text not null,
  action text not null,
  run_id uuid null references runs(id)
);
create index if not exists idx_messages_created_at
  on messages (created_at desc);

-- USER REPORT RULES (multi-user)
create table if not exists user_report_rules (
  owner_sub text primary key,
  owner_email text null,
  value_text text not null,
  updated_at timestamptz not null default now()
);

create index if not exists idx_user_report_rules_owner_email on user_report_rules (owner_email);

-- USERS (multi-user directory for dispatch and profile-level settings)
create table if not exists users (
  owner_sub text primary key,
  owner_email text null,
  active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists idx_users_active on users (active);
create index if not exists idx_users_owner_email on users (owner_email);

-- backward-compatible migration for existing databases
alter table if exists things add column if not exists owner_sub text null;
alter table if exists things add column if not exists owner_email text null;
alter table if exists runs add column if not exists owner_sub text null;
alter table if exists runs add column if not exists owner_email text null;
alter table if exists messages add column if not exists owner_sub text null;
alter table if exists messages add column if not exists owner_email text null;

create index if not exists idx_things_owner_created_at on things (owner_sub, created_at desc);
create index if not exists idx_runs_owner_created_at on runs (owner_sub, created_at desc);
create index if not exists idx_messages_owner_created_at on messages (owner_sub, created_at desc);

-- optional backfill users from existing owned things
insert into users (owner_sub, owner_email, active)
select distinct owner_sub, max(owner_email) as owner_email, true
from things
where owner_sub is not null
group by owner_sub
on conflict (owner_sub) do update
set owner_email = excluded.owner_email,
    active = true,
    updated_at = now();
