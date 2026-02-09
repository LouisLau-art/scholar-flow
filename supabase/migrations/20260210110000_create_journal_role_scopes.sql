-- GAP-P1-05: Role Matrix + Journal Scope RBAC
-- 说明：
-- 1) 建立内部人员与期刊的作用域绑定关系（user_id + journal_id + role）
-- 2) 供后端应用层做“同角色跨期刊默认隔离”校验

create table if not exists public.journal_role_scopes (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.user_profiles(id) on delete cascade,
  journal_id uuid not null references public.journals(id) on delete cascade,
  role text not null,
  is_active boolean not null default true,
  created_by uuid null references public.user_profiles(id) on delete set null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint journal_role_scopes_role_check check (
    role in (
      'editor',
      'managing_editor',
      'assistant_editor',
      'editor_in_chief',
      'admin'
    )
  )
);

create unique index if not exists journal_role_scopes_user_journal_role_uq
  on public.journal_role_scopes(user_id, journal_id, role);

create index if not exists journal_role_scopes_user_active_idx
  on public.journal_role_scopes(user_id, is_active);

create index if not exists journal_role_scopes_journal_active_idx
  on public.journal_role_scopes(journal_id, is_active);

create index if not exists journal_role_scopes_role_active_idx
  on public.journal_role_scopes(role, is_active);

create or replace function public.set_journal_role_scopes_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists trg_journal_role_scopes_updated_at on public.journal_role_scopes;
create trigger trg_journal_role_scopes_updated_at
before update on public.journal_role_scopes
for each row
execute function public.set_journal_role_scopes_updated_at();
