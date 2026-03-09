-- Reviewer assignment audit fields: selected_by/via + invited_by/via

alter table public.review_assignments
  add column if not exists selected_by uuid null references public.user_profiles(id) on delete set null,
  add column if not exists selected_via text null,
  add column if not exists invited_by uuid null references public.user_profiles(id) on delete set null,
  add column if not exists invited_via text null;

do $$
begin
  if not exists (
    select 1
    from pg_constraint
    where conname = 'review_assignments_selected_via_check'
  ) then
    alter table public.review_assignments
      add constraint review_assignments_selected_via_check
      check (selected_via is null or selected_via in ('editor_selection', 'system_reinvite', 'legacy'));
  end if;
end $$;

do $$
begin
  if not exists (
    select 1
    from pg_constraint
    where conname = 'review_assignments_invited_via_check'
  ) then
    alter table public.review_assignments
      add constraint review_assignments_invited_via_check
      check (invited_via is null or invited_via in ('manual_email', 'template_invitation', 'template_reminder', 'legacy'));
  end if;
end $$;

update public.review_assignments
set invited_via = 'legacy'
where invited_at is not null
  and invited_via is null;

create index if not exists idx_review_assignments_selected_by
  on public.review_assignments (selected_by);

create index if not exists idx_review_assignments_invited_by
  on public.review_assignments (invited_by);
