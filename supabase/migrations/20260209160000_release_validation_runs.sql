-- Feature 043: Cloud Rollout Regression (GAP-P0-02)
-- 目标：记录云端上线验收批次（run）与检查明细（check），支撑 go/no-go 审计闭环。

create table if not exists public.release_validation_runs (
  id uuid primary key default gen_random_uuid(),
  feature_key text not null,
  environment text not null,
  manuscript_id uuid references public.manuscripts(id) on delete set null,
  triggered_by text,
  status text not null default 'running' check (status in ('running', 'passed', 'failed', 'blocked')),
  blocking_count int not null default 0 check (blocking_count >= 0),
  failed_count int not null default 0 check (failed_count >= 0),
  skipped_count int not null default 0 check (skipped_count >= 0),
  started_at timestamptz not null default now(),
  finished_at timestamptz,
  summary text,
  rollback_required boolean not null default false,
  rollback_status text not null default 'not_required' check (rollback_status in ('not_required', 'pending', 'done')),
  note text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint chk_release_validation_runs_time
    check (finished_at is null or finished_at >= started_at),
  constraint chk_release_validation_runs_rollback_state
    check (
      (rollback_required = false and rollback_status = 'not_required')
      or (rollback_required = true and rollback_status in ('pending', 'done'))
    )
);

create unique index if not exists idx_release_validation_runs_env_running
on public.release_validation_runs(environment)
where status = 'running';

create index if not exists idx_release_validation_runs_feature_key
on public.release_validation_runs(feature_key);

create index if not exists idx_release_validation_runs_started_at
on public.release_validation_runs(started_at desc);

create table if not exists public.release_validation_checks (
  id uuid primary key default gen_random_uuid(),
  run_id uuid not null references public.release_validation_runs(id) on delete cascade,
  phase text not null check (phase in ('readiness', 'regression', 'rollback')),
  check_key text not null,
  title text not null,
  status text not null check (status in ('passed', 'failed', 'blocked', 'skipped')),
  is_blocking boolean not null default true,
  detail text,
  evidence jsonb not null default '{}'::jsonb,
  started_at timestamptz not null default now(),
  finished_at timestamptz,
  created_at timestamptz not null default now(),
  constraint uq_release_validation_checks_unique
    unique (run_id, phase, check_key),
  constraint chk_release_validation_checks_time
    check (finished_at is null or finished_at >= started_at)
);

create index if not exists idx_release_validation_checks_run_id
on public.release_validation_checks(run_id);

create index if not exists idx_release_validation_checks_phase
on public.release_validation_checks(phase);

create index if not exists idx_release_validation_checks_status
on public.release_validation_checks(status);

comment on table public.release_validation_runs is 'Feature 043 release validation run snapshots.';
comment on table public.release_validation_checks is 'Feature 043 release validation check details.';
