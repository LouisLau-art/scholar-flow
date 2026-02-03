-- Create email_logs table for audit trail
create table public.email_logs (
  id uuid not null default gen_random_uuid (),
  recipient text not null,
  subject text not null,
  template_name text not null,
  status text not null check (status in ('sent', 'failed', 'pending_retry')),
  provider_id text null,
  error_message text null,
  retry_count integer not null default 0,
  created_at timestamp with time zone not null default now(),
  constraint email_logs_pkey primary key (id)
);

-- Index for querying logs by recipient
create index idx_email_logs_recipient on public.email_logs (recipient);

-- Enable RLS
alter table public.email_logs enable row level security;

-- Policy: Service role can do everything (insert/select)
-- We do NOT expose this to authenticated users directly.
create policy "Service role can insert logs"
  on public.email_logs
  for insert
  to service_role
  with check (true);

create policy "Service role can select logs"
  on public.email_logs
  for select
  to service_role
  using (true);

-- Optional: Comment on table
comment on table public.email_logs is 'Audit log for outbound transactional emails via Resend';
