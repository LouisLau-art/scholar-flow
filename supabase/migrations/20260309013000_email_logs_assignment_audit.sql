alter table public.email_logs
  drop constraint if exists email_logs_status_check;

alter table public.email_logs
  add column if not exists assignment_id uuid null references public.review_assignments(id) on delete set null,
  add column if not exists manuscript_id uuid null references public.manuscripts(id) on delete set null,
  add column if not exists idempotency_key text null,
  add column if not exists scene text null,
  add column if not exists event_type text null;

alter table public.email_logs
  add constraint email_logs_status_check
  check (status in ('queued', 'sent', 'failed', 'pending_retry'));

create index if not exists idx_email_logs_assignment_created
  on public.email_logs (assignment_id, created_at desc);

create index if not exists idx_email_logs_manuscript_created
  on public.email_logs (manuscript_id, created_at desc);

create index if not exists idx_email_logs_idempotency_key
  on public.email_logs (idempotency_key);

comment on column public.email_logs.assignment_id is 'Optional reviewer assignment linkage for manuscript outreach emails';
comment on column public.email_logs.manuscript_id is 'Optional manuscript linkage for reviewer invitation / reminder emails';
comment on column public.email_logs.idempotency_key is 'Application-level idempotency key used when queueing outbound email';
comment on column public.email_logs.scene is 'Email scene, e.g. reviewer_assignment';
comment on column public.email_logs.event_type is 'Email event type, e.g. invitation or reminder';
