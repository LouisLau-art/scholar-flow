-- Feature 022 (Completion): Reviewer dual comment fields
-- Feature 022 (Completion): Review attachments bucket (private)
-- Feature 011 (UX): Click-through notifications via action_url

-- 1) review_reports: add comments_for_author (author-visible). Keep legacy content for backwards compatibility.
alter table public.review_reports
  add column if not exists comments_for_author text;

update public.review_reports
set comments_for_author = content
where comments_for_author is null
  and content is not null;

-- 2) notifications: add action_url for client-side navigation
alter table public.notifications
  add column if not exists action_url text;

do $$
begin
  if not exists (
    select 1
    from pg_constraint
    where conname = 'notifications_action_url_len'
  ) then
    alter table public.notifications
      add constraint notifications_action_url_len check (action_url is null or char_length(action_url) <= 2000);
  end if;
end $$;

-- Best-effort backfill: author-facing notifications deep-link to manuscript feedback page.
update public.notifications
set action_url = '/dashboard/author/manuscripts/' || manuscript_id
where action_url is null
  and manuscript_id is not null
  and type in ('submission', 'decision', 'chase');

-- 3) storage: create private bucket for review attachments
insert into storage.buckets (id, name, public)
values ('review-attachments', 'review-attachments', false)
on conflict (id) do nothing;

