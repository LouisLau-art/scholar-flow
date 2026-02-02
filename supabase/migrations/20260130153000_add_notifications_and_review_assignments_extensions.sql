-- Feature 011: Notification Center
-- 创建 notifications 表 + 扩展 review_assignments（用于自动催办幂等）

-- 1) notifications 表
create table if not exists public.notifications (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  manuscript_id uuid null references public.manuscripts(id) on delete set null,
  type text not null,
  title text not null,
  content text not null,
  is_read boolean not null default false,
  created_at timestamptz not null default now(),
  constraint notifications_type_check check (type in ('submission','review_invite','decision','chase','system')),
  constraint notifications_title_len check (char_length(title) <= 255),
  constraint notifications_content_len check (char_length(content) <= 2000)
);

create index if not exists idx_notifications_user_created_at on public.notifications (user_id, created_at desc);
create index if not exists idx_notifications_user_is_read on public.notifications (user_id, is_read);

-- 2) RLS：用户只能读/更新自己的通知；写入仅服务端（service_role）
alter table public.notifications enable row level security;

do $$
begin
  if not exists (
    select 1
    from pg_policies
    where schemaname = 'public'
      and tablename = 'notifications'
      and policyname = 'Users can read their notifications'
  ) then
    create policy "Users can read their notifications"
      on public.notifications
      for select
      to authenticated
      using (auth.uid() = user_id);
  end if;

  if not exists (
    select 1
    from pg_policies
    where schemaname = 'public'
      and tablename = 'notifications'
      and policyname = 'Users can mark their notifications as read'
  ) then
    create policy "Users can mark their notifications as read"
      on public.notifications
      for update
      to authenticated
      using (auth.uid() = user_id)
      with check (auth.uid() = user_id);
  end if;

  if not exists (
    select 1
    from pg_policies
    where schemaname = 'public'
      and tablename = 'notifications'
      and policyname = 'Service role can insert notifications'
  ) then
    create policy "Service role can insert notifications"
      on public.notifications
      for insert
      to service_role
      with check (true);
  end if;
end $$;

-- 3) review_assignments 扩展：用于 24h 自动催办
create table if not exists public.review_assignments (
  id uuid primary key default gen_random_uuid(),
  manuscript_id uuid not null references public.manuscripts(id) on delete cascade,
  reviewer_id uuid not null references auth.users(id) on delete cascade,
  status text not null default 'pending',
  due_at timestamptz null,
  last_reminded_at timestamptz null,
  created_at timestamptz not null default now()
);

alter table public.review_assignments
  add column if not exists due_at timestamptz null;

alter table public.review_assignments
  add column if not exists last_reminded_at timestamptz null;

