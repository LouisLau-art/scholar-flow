alter table if exists public.manuscripts
  add column if not exists authors text[] default '{}'::text[];

alter table if exists public.manuscripts
  add column if not exists submission_email text;

alter table if exists public.manuscripts
  add column if not exists author_contacts jsonb not null default '[]'::jsonb;

alter table if exists public.manuscripts
  add column if not exists special_issue text;

alter table if exists public.manuscripts
  drop constraint if exists manuscripts_author_contacts_is_array;

alter table if exists public.manuscripts
  add constraint manuscripts_author_contacts_is_array
  check (jsonb_typeof(author_contacts) = 'array');

comment on column public.manuscripts.authors is '作者姓名快照，按投稿时顺序保存';
comment on column public.manuscripts.submission_email is '本稿件的投稿/联系邮箱，可不同于系统登录邮箱';
comment on column public.manuscripts.author_contacts is '作者联系信息快照 JSON 数组：[{name,email,affiliation,is_corresponding}]';
comment on column public.manuscripts.special_issue is '投稿目标专刊/专题';
