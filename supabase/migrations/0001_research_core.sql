-- Draft schema only. Not executed against any Supabase project.
create extension if not exists pgcrypto;

create table if not exists research_datasets (
  id uuid primary key default gen_random_uuid(),
  symbol text not null,
  source_name text not null,
  source_uri text,
  interval text not null,
  timezone text not null default 'Asia/Taipei',
  first_timestamp timestamptz,
  last_timestamp timestamptz,
  row_count bigint,
  sha256 text,
  provenance jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create table if not exists research_runs (
  id uuid primary key default gen_random_uuid(),
  dataset_id uuid not null references research_datasets(id),
  strategy_name text not null,
  strategy_version text not null,
  parameters jsonb not null default '{}'::jsonb,
  execution_assumptions jsonb not null default '{}'::jsonb,
  status text not null default 'draft'
    check (status in ('draft','running','completed','failed','rejected')),
  started_at timestamptz,
  completed_at timestamptz,
  created_at timestamptz not null default now()
);

create table if not exists research_trades (
  id bigserial primary key,
  run_id uuid not null references research_runs(id) on delete cascade,
  trade_no integer not null,
  side text not null check (side in ('long','short')),
  entry_time timestamptz not null,
  exit_time timestamptz not null,
  entry_price numeric not null,
  exit_price numeric not null,
  gross_points numeric not null,
  cost_points numeric not null,
  net_points numeric not null,
  exit_reason text not null,
  unique (run_id, trade_no),
  check (exit_time >= entry_time)
);

create index if not exists research_runs_dataset_idx on research_runs(dataset_id);
create index if not exists research_trades_run_idx on research_trades(run_id, trade_no);
