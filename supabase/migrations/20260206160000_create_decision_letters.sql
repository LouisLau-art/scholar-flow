-- Feature 041: Final Decision Workspace
-- 目标：持久化决策信草稿/终稿，支持乐观锁与附件引用

create table if not exists public.decision_letters (
  id uuid primary key default gen_random_uuid(),
  manuscript_id uuid not null references public.manuscripts(id) on delete cascade,
  manuscript_version int not null default 1,
  editor_id uuid not null references public.user_profiles(id),
  content text not null default '',
  decision text not null check (decision in ('accept', 'reject', 'major_revision', 'minor_revision')),
  status text not null check (status in ('draft', 'final')),
  attachment_paths text[] not null default '{}',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists idx_decision_letters_manuscript_id on public.decision_letters (manuscript_id);
create index if not exists idx_decision_letters_editor_id on public.decision_letters (editor_id);
create index if not exists idx_decision_letters_status on public.decision_letters (status);
create index if not exists idx_decision_letters_updated_at on public.decision_letters (updated_at);

comment on table public.decision_letters is 'Feature 041 decision letters (draft/final).';
comment on column public.decision_letters.attachment_paths is 'Attachment refs (attachment_id|storage_path).';
