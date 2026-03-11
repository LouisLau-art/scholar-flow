-- Academic editor formal role + manuscript-level binding
-- 说明：
-- 1) 为 manuscript 增加 academic_editor 绑定字段与审计时间戳
-- 2) 扩展 journal_role_scopes.role 允许 academic_editor

alter table public.manuscripts
  add column if not exists academic_editor_id uuid null references public.user_profiles(id) on delete set null,
  add column if not exists academic_submitted_at timestamptz null,
  add column if not exists academic_completed_at timestamptz null;

create index if not exists manuscripts_academic_editor_idx
  on public.manuscripts(academic_editor_id);

create index if not exists manuscripts_precheck_academic_assignee_idx
  on public.manuscripts(status, pre_check_status, academic_editor_id);

do $$
begin
  if to_regclass('public.journal_role_scopes') is null then
    raise notice 'skip journal_role_scopes role expansion: table not found';
    return;
  end if;

  if exists (
    select 1
    from pg_constraint c
    join pg_class t on t.oid = c.conrelid
    join pg_namespace n on n.oid = t.relnamespace
    where n.nspname = 'public'
      and t.relname = 'journal_role_scopes'
      and c.conname = 'journal_role_scopes_role_check'
  ) then
    alter table public.journal_role_scopes
      drop constraint journal_role_scopes_role_check;
  end if;

  begin
    alter table public.journal_role_scopes
      add constraint journal_role_scopes_role_check
      check (
        role in (
          'managing_editor',
          'assistant_editor',
          'academic_editor',
          'editor_in_chief',
          'admin'
        )
      );
  exception
    when duplicate_object then
      null;
  end;
end $$;

update public.manuscripts
set academic_submitted_at = coalesce(academic_submitted_at, updated_at, now())
where status = 'pre_check'
  and pre_check_status = 'academic'
  and academic_editor_id is not null
  and academic_submitted_at is null;

select pg_notify('pgrst', 'reload schema');
