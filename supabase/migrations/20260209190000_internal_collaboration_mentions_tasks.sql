-- Feature 045: Internal collaboration enhancement
-- Adds mention graph + manuscript internal tasks + task activity logs.

create table if not exists public.internal_comment_mentions (
  id uuid primary key default gen_random_uuid(),
  comment_id uuid not null references public.internal_comments(id) on delete cascade,
  manuscript_id uuid not null references public.manuscripts(id) on delete cascade,
  mentioned_user_id uuid not null references auth.users(id),
  mentioned_by_user_id uuid not null references auth.users(id),
  created_at timestamptz not null default now(),
  constraint internal_comment_mentions_unique unique (comment_id, mentioned_user_id)
);

create index if not exists idx_internal_comment_mentions_manuscript_created_at
  on public.internal_comment_mentions (manuscript_id, created_at desc);
create index if not exists idx_internal_comment_mentions_mentioned_user_created_at
  on public.internal_comment_mentions (mentioned_user_id, created_at desc);

create table if not exists public.internal_tasks (
  id uuid primary key default gen_random_uuid(),
  manuscript_id uuid not null references public.manuscripts(id) on delete cascade,
  title text not null,
  description text,
  assignee_user_id uuid not null references auth.users(id),
  status text not null default 'todo'
    constraint internal_tasks_status_check check (status in ('todo', 'in_progress', 'done')),
  priority text not null default 'medium'
    constraint internal_tasks_priority_check check (priority in ('low', 'medium', 'high')),
  due_at timestamptz not null,
  created_by uuid not null references auth.users(id),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  completed_at timestamptz,
  constraint internal_tasks_title_len_check check (char_length(trim(title)) between 1 and 200),
  constraint internal_tasks_completed_at_check check (
    (status = 'done' and completed_at is not null)
    or status in ('todo', 'in_progress')
  )
);

create index if not exists idx_internal_tasks_manuscript_status_due
  on public.internal_tasks (manuscript_id, status, due_at);
create index if not exists idx_internal_tasks_assignee_status
  on public.internal_tasks (assignee_user_id, status);
create index if not exists idx_internal_tasks_manuscript_updated_at
  on public.internal_tasks (manuscript_id, updated_at desc);

create table if not exists public.internal_task_activity_logs (
  id uuid primary key default gen_random_uuid(),
  task_id uuid not null references public.internal_tasks(id) on delete cascade,
  manuscript_id uuid not null references public.manuscripts(id) on delete cascade,
  action text not null,
  actor_user_id uuid not null references auth.users(id),
  before_payload jsonb,
  after_payload jsonb,
  created_at timestamptz not null default now()
);

create index if not exists idx_internal_task_activity_logs_task_created_at
  on public.internal_task_activity_logs (task_id, created_at desc);
create index if not exists idx_internal_task_activity_logs_manuscript_created_at
  on public.internal_task_activity_logs (manuscript_id, created_at desc);
