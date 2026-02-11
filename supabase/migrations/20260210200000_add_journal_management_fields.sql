-- GAP-P2 Journal Management
-- 目标：
-- 1) 为 journals 增加启停字段 is_active（便于后台停用而不硬删除）
-- 2) 增加 updated_at 并在更新时自动刷新
-- 3) 补充常用索引，支持投稿页/后台期刊列表读取

alter table if exists public.journals
  add column if not exists is_active boolean not null default true;

alter table if exists public.journals
  add column if not exists updated_at timestamptz not null default now();

create index if not exists idx_journals_is_active
  on public.journals(is_active);

create index if not exists idx_journals_slug
  on public.journals(slug);

create or replace function public.set_journals_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists trg_set_journals_updated_at on public.journals;
create trigger trg_set_journals_updated_at
before update on public.journals
for each row
execute function public.set_journals_updated_at();
