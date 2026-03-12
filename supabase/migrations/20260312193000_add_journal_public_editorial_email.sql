begin;

alter table public.journals
  add column if not exists public_editorial_email text null;

comment on column public.journals.public_editorial_email is
  'Public-facing editorial office mailbox used for CC and Reply-To on outbound journal email';

commit;
