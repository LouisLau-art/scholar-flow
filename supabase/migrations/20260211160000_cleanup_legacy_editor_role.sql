-- Legacy role cleanup: migrate historical `editor` role to `managing_editor`.
-- Idempotent migration for cloud/staging databases.

-- 1) user_profiles.roles: remove editor, add managing_editor (deduplicated).
with normalized_user_roles as (
  select
    up.id,
    (
      select coalesce(
        array_agg(r.role order by
          case r.role
            when 'admin' then 1
            when 'managing_editor' then 2
            when 'assistant_editor' then 3
            when 'editor_in_chief' then 4
            when 'reviewer' then 5
            when 'author' then 6
            else 99
          end,
          r.role
        ),
        '{}'::text[]
      )
      from lateral (
        select distinct role
        from unnest(
          array_append(
            array_remove(coalesce(up.roles, '{}'::text[]), 'editor'),
            'managing_editor'
          )
        ) as role
      ) as r
    ) as roles
  from public.user_profiles up
  where coalesce(up.roles, '{}'::text[]) @> array['editor']::text[]
)
update public.user_profiles up
set roles = nur.roles
from normalized_user_roles nur
where up.id = nur.id;

-- 2) journal_role_scopes.role: migrate editor -> managing_editor and tighten check constraint.
do $$
begin
  if to_regclass('public.journal_role_scopes') is null then
    raise notice 'skip journal_role_scopes cleanup: table not found';
    return;
  end if;

  -- Merge rows to avoid unique conflict on (user_id, journal_id, role).
  insert into public.journal_role_scopes (
    user_id,
    journal_id,
    role,
    is_active,
    created_by,
    created_at,
    updated_at
  )
  select
    s.user_id,
    s.journal_id,
    'managing_editor'::text as role,
    s.is_active,
    s.created_by,
    s.created_at,
    coalesce(s.updated_at, now()) as updated_at
  from public.journal_role_scopes s
  where s.role = 'editor'
  on conflict (user_id, journal_id, role) do update
    set
      is_active = (public.journal_role_scopes.is_active or excluded.is_active),
      updated_at = greatest(
        coalesce(public.journal_role_scopes.updated_at, now()),
        coalesce(excluded.updated_at, now())
      );

  delete from public.journal_role_scopes where role = 'editor';

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
          'editor_in_chief',
          'admin'
        )
      );
  exception
    when duplicate_object then
      null;
  end;
end $$;

-- 3) Refresh PostgREST schema cache (safe no-op if listener unavailable).
select pg_notify('pgrst', 'reload schema');
