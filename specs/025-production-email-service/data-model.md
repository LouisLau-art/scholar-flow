# Data Model: Production Email Service

## Entities

### EmailLog
Records the history of all outbound transactional emails. This log is purely for audit and debugging purposes; it does not drive business logic.

| Field | Type | Required | Description |
|---|---|---|---|
| `id` | UUID | Yes | Primary Key, default `gen_random_uuid()` |
| `recipient` | Text | Yes | Email address of the recipient |
| `subject` | Text | Yes | Subject line of the email |
| `template_name` | Text | Yes | Name of the Jinja2 template used (e.g., `reviewer_invite.html`) |
| `status` | Text | Yes | Current status: `sent`, `failed` |
| `provider_id` | Text | No | The ID returned by Resend (e.g., `re_12345...`) |
| `error_message` | Text | No | Full error message if status is `failed` |
| `retry_count` | Integer | Yes | Number of retries attempted (default 0) |
| `created_at` | Timestamptz | Yes | Timestamp of the attempt (default `now()`) |

## SQL Schema

```sql
create table public.email_logs (
  id uuid not null default gen_random_uuid (),
  recipient text not null,
  subject text not null,
  template_name text not null,
  status text not null check (status in ('sent', 'failed')),
  provider_id text null,
  error_message text null,
  retry_count integer not null default 0,
  created_at timestamp with time zone not null default now(),
  constraint email_logs_pkey primary key (id)
);

-- Index for querying logs by recipient (for debugging user complaints)
create index idx_email_logs_recipient on public.email_logs (recipient);

-- Enable RLS (Service Role only, no public access)
alter table public.email_logs enable row level security;

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
```
