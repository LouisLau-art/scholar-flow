-- Feature 013: Dynamic Portal CMS
-- 创建 CMS 页面、菜单表 + RLS + Storage Bucket（cms-assets）

-- === 工具函数：统一 updated_at ===
create or replace function public.sf_set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

-- === 工具函数：基于 user_profiles.roles 的 RBAC（用于 RLS）===
create or replace function public.sf_user_has_any_role(required_roles text[])
returns boolean
language sql
stable
as $$
  select exists (
    select 1
    from public.user_profiles up
    where up.id = auth.uid()
      and (up.roles && required_roles)
  );
$$;

-- === 1) CMS Pages ===
create table if not exists public.cms_pages (
  id uuid primary key default gen_random_uuid(),
  slug text not null unique,
  title text not null,
  content text,
  is_published boolean not null default false,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  updated_by uuid references auth.users(id)
);

alter table public.cms_pages
  add constraint cms_pages_slug_format_chk
  check (slug ~ '^[a-z0-9-]+$');

drop trigger if exists cms_pages_set_updated_at on public.cms_pages;
create trigger cms_pages_set_updated_at
before update on public.cms_pages
for each row execute function public.sf_set_updated_at();

-- RLS
alter table public.cms_pages enable row level security;

drop policy if exists "cms_pages_public_read_published" on public.cms_pages;
create policy "cms_pages_public_read_published"
on public.cms_pages
for select
using (is_published = true);

drop policy if exists "cms_pages_editor_read_all" on public.cms_pages;
create policy "cms_pages_editor_read_all"
on public.cms_pages
for select
using (public.sf_user_has_any_role(array['editor', 'admin']));

drop policy if exists "cms_pages_editor_insert" on public.cms_pages;
create policy "cms_pages_editor_insert"
on public.cms_pages
for insert
with check (public.sf_user_has_any_role(array['editor', 'admin']));

drop policy if exists "cms_pages_editor_update" on public.cms_pages;
create policy "cms_pages_editor_update"
on public.cms_pages
for update
using (public.sf_user_has_any_role(array['editor', 'admin']))
with check (public.sf_user_has_any_role(array['editor', 'admin']));

drop policy if exists "cms_pages_editor_delete" on public.cms_pages;
create policy "cms_pages_editor_delete"
on public.cms_pages
for delete
using (public.sf_user_has_any_role(array['editor', 'admin']));

-- === 2) CMS Menu Items ===
create table if not exists public.cms_menu_items (
  id uuid primary key default gen_random_uuid(),
  parent_id uuid references public.cms_menu_items(id) on delete cascade,
  label text not null,
  url text,
  page_id uuid references public.cms_pages(id) on delete set null,
  order_index integer not null default 0,
  location text not null default 'header',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  updated_by uuid references auth.users(id)
);

alter table public.cms_menu_items
  add constraint cms_menu_items_location_chk
  check (location in ('header', 'footer'));

-- 允许“仅作为分组标题”的菜单项（url/page_id 都为空），但禁止同时设置两者
alter table public.cms_menu_items
  add constraint cms_menu_items_target_exclusive_chk
  check (url is null or page_id is null);

create index if not exists cms_menu_items_location_idx on public.cms_menu_items (location);
create index if not exists cms_menu_items_parent_idx on public.cms_menu_items (parent_id);
create unique index if not exists cms_menu_items_order_unique
  on public.cms_menu_items (location, parent_id, order_index);

drop trigger if exists cms_menu_items_set_updated_at on public.cms_menu_items;
create trigger cms_menu_items_set_updated_at
before update on public.cms_menu_items
for each row execute function public.sf_set_updated_at();

alter table public.cms_menu_items enable row level security;

drop policy if exists "cms_menu_public_read" on public.cms_menu_items;
create policy "cms_menu_public_read"
on public.cms_menu_items
for select
using (true);

drop policy if exists "cms_menu_editor_write" on public.cms_menu_items;
create policy "cms_menu_editor_write"
on public.cms_menu_items
for all
using (public.sf_user_has_any_role(array['editor', 'admin']))
with check (public.sf_user_has_any_role(array['editor', 'admin']));

-- === 3) Storage bucket: cms-assets（公开读）===
insert into storage.buckets (id, name, public)
values ('cms-assets', 'cms-assets', true)
on conflict (id) do nothing;

-- 公开可读：用于 img src 的 public URL
drop policy if exists "cms_assets_public_select" on storage.objects;
create policy "cms_assets_public_select"
on storage.objects
for select
using (bucket_id = 'cms-assets');

