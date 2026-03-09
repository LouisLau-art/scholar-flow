alter table public.review_assignments
    add column if not exists cancelled_at timestamptz null,
    add column if not exists cancelled_by uuid null references public.user_profiles(id),
    add column if not exists cancel_reason text null,
    add column if not exists cancel_via text null;

do $$
begin
    if not exists (
        select 1
        from pg_constraint
        where conname = 'review_assignments_cancel_via_check'
          and conrelid = 'public.review_assignments'::regclass
    ) then
        alter table public.review_assignments
            add constraint review_assignments_cancel_via_check
            check (
                cancel_via is null
                or cancel_via in (
                    'auto_stage_exit',
                    'editor_manual_cancel',
                    'post_acceptance_cleanup',
                    'legacy'
                )
            );
    end if;
end $$;

create index if not exists idx_review_assignments_cancelled_by
    on public.review_assignments(cancelled_by);
