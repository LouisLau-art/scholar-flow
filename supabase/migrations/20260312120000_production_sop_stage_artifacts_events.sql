-- Feature 047: Production SOP Redesign - stage, artifacts, events
-- 目标：在保留 Feature 042 兼容口径的前提下，引入单一 stage、责任人字段、独立产物与交接事件

-- 1) 扩展 production_cycles
alter table public.production_cycles
  add column if not exists stage text,
  add column if not exists coordinator_ae_id uuid references public.user_profiles(id),
  add column if not exists typesetter_id uuid references public.user_profiles(id),
  add column if not exists language_editor_id uuid references public.user_profiles(id),
  add column if not exists pdf_editor_id uuid references public.user_profiles(id),
  add column if not exists current_assignee_id uuid references public.user_profiles(id);

update public.production_cycles
set stage = case status
  when 'draft' then 'received'
  when 'awaiting_author' then 'author_proofreading'
  when 'author_confirmed' then 'ae_final_review'
  when 'author_corrections_submitted' then 'ae_final_review'
  when 'in_layout_revision' then 'typesetting'
  when 'approved_for_publish' then 'ready_to_publish'
  when 'cancelled' then 'cancelled'
  else 'received'
end
where stage is null;

update public.production_cycles
set current_assignee_id = layout_editor_id
where current_assignee_id is null
  and layout_editor_id is not null;

alter table public.production_cycles
  alter column stage set not null;

do $$
begin
  if not exists (
    select 1 from pg_constraint
    where conname = 'production_cycles_stage_check'
  ) then
    alter table public.production_cycles
      add constraint production_cycles_stage_check
      check (
        stage in (
          'received',
          'typesetting',
          'language_editing',
          'ae_internal_proof',
          'author_proofreading',
          'ae_final_review',
          'pdf_preparation',
          'ready_to_publish',
          'published',
          'cancelled'
        )
      );
  end if;
end $$;

create index if not exists idx_production_cycles_stage
  on public.production_cycles(stage);

create index if not exists idx_production_cycles_current_assignee_stage
  on public.production_cycles(current_assignee_id, stage, updated_at desc);

create index if not exists idx_production_cycles_coordinator_ae_id
  on public.production_cycles(coordinator_ae_id);

create index if not exists idx_production_cycles_typesetter_id
  on public.production_cycles(typesetter_id);

create index if not exists idx_production_cycles_language_editor_id
  on public.production_cycles(language_editor_id);

create index if not exists idx_production_cycles_pdf_editor_id
  on public.production_cycles(pdf_editor_id);

comment on column public.production_cycles.stage is 'SOP-driven production stage; source of truth for detailed production progress.';
comment on column public.production_cycles.coordinator_ae_id is 'Assigned AE coordinator for this production cycle.';
comment on column public.production_cycles.typesetter_id is 'Assigned typesetter for this production cycle.';
comment on column public.production_cycles.language_editor_id is 'Assigned language editor for this production cycle.';
comment on column public.production_cycles.pdf_editor_id is 'Assigned PDF editor for this production cycle.';
comment on column public.production_cycles.current_assignee_id is 'Read-optimized current responsibility owner for queue rendering.';

-- 2) 独立产物表
create table if not exists public.production_cycle_artifacts (
  id uuid primary key default gen_random_uuid(),
  cycle_id uuid not null references public.production_cycles(id) on delete cascade,
  manuscript_id uuid not null references public.manuscripts(id) on delete cascade,
  artifact_kind text not null check (
    artifact_kind in (
      'source_manuscript_snapshot',
      'typeset_output',
      'language_output',
      'ae_internal_proof',
      'author_annotated_proof',
      'final_confirmation_pdf',
      'publication_pdf'
    )
  ),
  storage_bucket text,
  storage_path text not null,
  file_name text,
  mime_type text,
  uploaded_by uuid references public.user_profiles(id),
  supersedes_artifact_id uuid references public.production_cycle_artifacts(id) on delete set null,
  metadata jsonb not null default '{}'::jsonb check (jsonb_typeof(metadata) = 'object'),
  created_at timestamptz not null default now()
);

create index if not exists idx_prod_cycle_artifacts_cycle_id
  on public.production_cycle_artifacts(cycle_id);

create index if not exists idx_prod_cycle_artifacts_manuscript_id
  on public.production_cycle_artifacts(manuscript_id);

create index if not exists idx_prod_cycle_artifacts_kind
  on public.production_cycle_artifacts(artifact_kind);

create index if not exists idx_prod_cycle_artifacts_uploaded_by
  on public.production_cycle_artifacts(uploaded_by);

create index if not exists idx_prod_cycle_artifacts_created_at
  on public.production_cycle_artifacts(created_at);

comment on table public.production_cycle_artifacts is 'Versioned production artifacts for each production cycle.';
comment on column public.production_cycle_artifacts.artifact_kind is 'typeset/language/final/publication etc.';

-- 3) 交接/审计事件表
create table if not exists public.production_cycle_events (
  id uuid primary key default gen_random_uuid(),
  cycle_id uuid not null references public.production_cycles(id) on delete cascade,
  manuscript_id uuid not null references public.manuscripts(id) on delete cascade,
  event_type text not null,
  from_stage text,
  to_stage text,
  actor_user_id uuid references public.user_profiles(id),
  target_user_id uuid references public.user_profiles(id),
  artifact_id uuid references public.production_cycle_artifacts(id) on delete set null,
  comment text,
  payload jsonb not null default '{}'::jsonb check (jsonb_typeof(payload) = 'object'),
  created_at timestamptz not null default now()
);

create index if not exists idx_prod_cycle_events_cycle_id
  on public.production_cycle_events(cycle_id, created_at desc);

create index if not exists idx_prod_cycle_events_manuscript_id
  on public.production_cycle_events(manuscript_id, created_at desc);

create index if not exists idx_prod_cycle_events_event_type
  on public.production_cycle_events(event_type);

comment on table public.production_cycle_events is 'Append-only production handoff and audit events.';

-- 4) 扩展作者反馈附件字段
alter table public.production_proofreading_responses
  add column if not exists attachment_bucket text,
  add column if not exists attachment_path text,
  add column if not exists attachment_file_name text;

comment on column public.production_proofreading_responses.attachment_bucket is 'Optional storage bucket for annotated proof attachment.';
comment on column public.production_proofreading_responses.attachment_path is 'Optional storage path for annotated proof attachment.';
comment on column public.production_proofreading_responses.attachment_file_name is 'Original filename for annotated proof attachment.';
