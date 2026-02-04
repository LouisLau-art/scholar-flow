-- Feature 028: Workflow and UI Standardization
-- 目标：Reviewer Library 扩展学术信息字段（如个人主页）

ALTER TABLE public.user_profiles
  ADD COLUMN IF NOT EXISTS title text,
  ADD COLUMN IF NOT EXISTS affiliation text,
  ADD COLUMN IF NOT EXISTS research_interests text[] DEFAULT '{}'::text[],
  ADD COLUMN IF NOT EXISTS homepage_url text;

CREATE INDEX IF NOT EXISTS idx_user_profiles_homepage_url ON public.user_profiles(homepage_url);

