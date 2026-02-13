-- Feature 042B: Production Cycle Collaborators (multiple production editors)
-- 目标：允许一个生产轮次被多个 production editor 协作处理（主负责人 + 协作者列表）。

alter table public.production_cycles
  add column if not exists collaborator_editor_ids uuid[] not null default '{}'::uuid[];

comment on column public.production_cycles.collaborator_editor_ids is
  'Optional additional production editors who can access this cycle workspace.';

create index if not exists idx_production_cycles_collaborator_editor_ids
  on public.production_cycles using gin (collaborator_editor_ids);

-- Refresh PostgREST schema cache (safe no-op if listener unavailable).
select pg_notify('pgrst', 'reload schema');

