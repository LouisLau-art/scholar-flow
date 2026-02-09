-- Feature 042: Production Pipeline Workspace
-- 目标：录用后生产协作闭环（排版轮次、作者校对反馈、发布前核准）

-- 1) production_cycles
create table if not exists public.production_cycles (
  id uuid primary key default gen_random_uuid(),
  manuscript_id uuid not null references public.manuscripts(id) on delete cascade,
  cycle_no int not null,
  status text not null check (
    status in (
      'draft',
      'awaiting_author',
      'author_confirmed',
      'author_corrections_submitted',
      'in_layout_revision',
      'approved_for_publish',
      'cancelled'
    )
  ),
  layout_editor_id uuid not null references public.user_profiles(id),
  proofreader_author_id uuid not null references public.user_profiles(id),
  galley_bucket text,
  galley_path text,
  version_note text,
  proof_due_at timestamptz,
  approved_by uuid references public.user_profiles(id),
  approved_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (manuscript_id, cycle_no)
);

create index if not exists idx_production_cycles_manuscript_id on public.production_cycles(manuscript_id);
create index if not exists idx_production_cycles_status on public.production_cycles(status);
create index if not exists idx_production_cycles_updated_at on public.production_cycles(updated_at);

-- 同稿件同一时刻仅允许一个活跃轮次
create unique index if not exists idx_production_cycles_active_unique
on public.production_cycles(manuscript_id)
where status in ('draft', 'awaiting_author', 'author_corrections_submitted', 'in_layout_revision');

comment on table public.production_cycles is 'Feature 042 production cycles after acceptance.';
comment on column public.production_cycles.cycle_no is 'Monotonic cycle number per manuscript.';
comment on column public.production_cycles.status is 'draft/awaiting_author/author_confirmed/author_corrections_submitted/in_layout_revision/approved_for_publish/cancelled';

-- 2) production_proofreading_responses
create table if not exists public.production_proofreading_responses (
  id uuid primary key default gen_random_uuid(),
  cycle_id uuid not null references public.production_cycles(id) on delete cascade,
  manuscript_id uuid not null references public.manuscripts(id) on delete cascade,
  author_id uuid not null references public.user_profiles(id),
  decision text not null check (decision in ('confirm_clean', 'submit_corrections')),
  summary text,
  submitted_at timestamptz not null default now(),
  is_late boolean not null default false,
  created_at timestamptz not null default now(),
  unique (cycle_id)
);

create index if not exists idx_prod_proof_responses_manuscript_id
on public.production_proofreading_responses(manuscript_id);
create index if not exists idx_prod_proof_responses_cycle_id
on public.production_proofreading_responses(cycle_id);

comment on table public.production_proofreading_responses is 'Author proofreading responses for production cycles.';
comment on column public.production_proofreading_responses.decision is 'confirm_clean | submit_corrections';

-- 3) production_correction_items
create table if not exists public.production_correction_items (
  id uuid primary key default gen_random_uuid(),
  response_id uuid not null references public.production_proofreading_responses(id) on delete cascade,
  line_ref text,
  original_text text,
  suggested_text text not null,
  reason text,
  sort_order int not null default 0,
  created_at timestamptz not null default now()
);

create index if not exists idx_prod_correction_items_response_id
on public.production_correction_items(response_id);

comment on table public.production_correction_items is 'Structured correction items for submit_corrections response.';

-- 4) storage bucket for galley proofs
insert into storage.buckets (id, name, public)
values ('production-proofs', 'production-proofs', false)
on conflict (id) do nothing;
