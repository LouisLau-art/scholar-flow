begin;

alter table public.email_logs
  add column if not exists actor_user_id uuid references public.user_profiles(id) on delete set null;

create index if not exists email_logs_actor_user_id_idx
  on public.email_logs(actor_user_id);

commit;
