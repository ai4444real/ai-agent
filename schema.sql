-- THINGS
create table if not exists things (
  id uuid primary key default gen_random_uuid(),
  created_at timestamptz not null default now(),
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
  channel text not null,
  recipient text not null,
  subject text not null,
  body text not null,
  action text not null,
  run_id uuid null references runs(id)
);
create index if not exists idx_messages_created_at
  on messages (created_at desc);
