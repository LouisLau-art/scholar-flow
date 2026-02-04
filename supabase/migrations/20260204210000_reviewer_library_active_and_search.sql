-- Feature 030: Reviewer Library Management
-- 目标：
-- 1) 增加 reviewer 库的“软删除/停用”字段
-- 2) 为库搜索提供索引（1k+ 规模下保持 <500ms）

ALTER TABLE public.user_profiles
  ADD COLUMN IF NOT EXISTS is_reviewer_active boolean NOT NULL DEFAULT true;

-- Search text (for fast ILIKE). NOTE:
-- 生成列要求表达式 immutable，但 array_to_string 等函数在 Postgres 中非 immutable；
-- 因此这里使用普通列 + 触发器维护，保证可用性与兼容性。
ALTER TABLE public.user_profiles
  ADD COLUMN IF NOT EXISTS reviewer_search_text text;

-- Trigram index for fast ILIKE search across key reviewer fields.
-- NOTE: PostgREST 的全文检索能力有限；MVP 用后端 OR + ILIKE 查询，
-- 通过 pg_trgm 的 GIN 索引保证性能。
CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE OR REPLACE FUNCTION public._sf_set_reviewer_search_text()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  NEW.reviewer_search_text :=
    coalesce(NEW.full_name, '') || ' ' ||
    coalesce(NEW.email, '') || ' ' ||
    coalesce(NEW.affiliation, '') || ' ' ||
    coalesce(NEW.homepage_url, '') || ' ' ||
    coalesce(array_to_string(NEW.research_interests, ' '), '');
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_sf_set_reviewer_search_text ON public.user_profiles;
CREATE TRIGGER trg_sf_set_reviewer_search_text
BEFORE INSERT OR UPDATE OF full_name, email, affiliation, homepage_url, research_interests
ON public.user_profiles
FOR EACH ROW
EXECUTE FUNCTION public._sf_set_reviewer_search_text();

-- Backfill existing rows
UPDATE public.user_profiles
SET reviewer_search_text =
  coalesce(full_name, '') || ' ' ||
  coalesce(email, '') || ' ' ||
  coalesce(affiliation, '') || ' ' ||
  coalesce(homepage_url, '') || ' ' ||
  coalesce(array_to_string(research_interests, ' '), '')
WHERE reviewer_search_text IS NULL;

CREATE INDEX IF NOT EXISTS idx_user_profiles_reviewer_search_trgm
  ON public.user_profiles
  USING gin (reviewer_search_text gin_trgm_ops);

CREATE INDEX IF NOT EXISTS idx_user_profiles_is_reviewer_active
  ON public.user_profiles(is_reviewer_active);
