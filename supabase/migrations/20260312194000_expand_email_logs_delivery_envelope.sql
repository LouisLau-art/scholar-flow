begin;

alter table public.email_logs
  add column if not exists to_recipients text[] not null default '{}'::text[],
  add column if not exists cc_recipients text[] not null default '{}'::text[],
  add column if not exists bcc_recipients text[] not null default '{}'::text[],
  add column if not exists reply_to_recipients text[] not null default '{}'::text[],
  add column if not exists delivery_mode text null,
  add column if not exists communication_status text null,
  add column if not exists provider text null,
  add column if not exists attachment_count integer not null default 0,
  add column if not exists attachment_manifest jsonb not null default '[]'::jsonb;

comment on column public.email_logs.to_recipients is 'Primary To recipients used for this outbound email';
comment on column public.email_logs.cc_recipients is 'CC recipients used for this outbound email';
comment on column public.email_logs.bcc_recipients is 'BCC recipients used for this outbound email';
comment on column public.email_logs.reply_to_recipients is 'Reply-To recipients used for this outbound email';
comment on column public.email_logs.delivery_mode is 'Delivery mode: auto, semi_auto, manual';
comment on column public.email_logs.communication_status is 'Communication result: system_sent, system_failed, external_sent, skipped, not_required';
comment on column public.email_logs.provider is 'Delivery provider, e.g. resend or smtp';
comment on column public.email_logs.attachment_count is 'Number of attachments sent with this email';
comment on column public.email_logs.attachment_manifest is 'Attachment metadata without raw content';

create index if not exists email_logs_communication_status_idx
  on public.email_logs(communication_status);

commit;
