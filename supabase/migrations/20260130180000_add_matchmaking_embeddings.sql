-- Feature 012: Local AI Matchmaker
-- 目标：
-- 1) 启用 pgvector 扩展
-- 2) 为 user_profiles 补齐可编辑字段（name/institution/research_interests）
-- 3) 新增 reviewer_embeddings 向量表（仅 service_role 可读写）
-- 4) 提供 match_reviewers SQL 函数用于余弦相似度查询（后端使用 service_role 调用）

create extension if not exists vector;

alter table if exists public.user_profiles
  add column if not exists name text;

alter table if exists public.user_profiles
  add column if not exists institution text;

alter table if exists public.user_profiles
  add column if not exists research_interests text;

create table if not exists public.reviewer_embeddings (
  user_id uuid primary key references auth.users(id) on delete cascade,
  embedding vector(384) not null,
  source_text_hash text not null,
  updated_at timestamptz not null default now()
);

alter table public.reviewer_embeddings enable row level security;

drop policy if exists "service role can manage reviewer embeddings" on public.reviewer_embeddings;
create policy "service role can manage reviewer embeddings"
  on public.reviewer_embeddings
  for all
  using (auth.role() = 'service_role')
  with check (auth.role() = 'service_role');

create or replace function public.match_reviewers(
  query_embedding vector(384),
  match_threshold float8 default 0.70,
  match_count int default 5
)
returns table (
  user_id uuid,
  score float8
)
language sql
stable
as $$
  select
    re.user_id,
    1 - (re.embedding <=> query_embedding) as score
  from public.reviewer_embeddings re
  where 1 - (re.embedding <=> query_embedding) >= match_threshold
  order by re.embedding <=> query_embedding asc
  limit match_count;
$$;

revoke all on function public.match_reviewers(vector(384), float8, int) from public;
grant execute on function public.match_reviewers(vector(384), float8, int) to service_role;
