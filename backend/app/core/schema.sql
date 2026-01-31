-- ScholarFlow Database Schema Snapshot (public schema)
-- Updated: 2026-01-30 (Feature 013 + 015 + 016)
--
-- 中文注释:
-- - 本文件用于“快速理解当前数据库结构”，便于后端/QA/本地排错。
-- - 真正的单一事实来源（Source of Truth）是 `supabase/migrations/`。
-- - 本文件不强制覆盖所有 RLS/Policy/Storage 细节，但会覆盖核心实体与关键视图/RPC。

-- ============================================================================
-- 1) Core Tables
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.journals (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  title text NOT NULL,
  slug text UNIQUE NOT NULL,
  description text,
  issn text,
  impact_factor float4,
  cover_url text,
  created_at timestamptz DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.manuscripts (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  title text,
  abstract text,
  file_path text,
  author_id uuid REFERENCES auth.users(id),
  editor_id uuid REFERENCES auth.users(id),
  status text DEFAULT 'draft',
  kpi_owner_id uuid REFERENCES auth.users(id),
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now(),
  journal_id uuid REFERENCES public.journals(id),
  dataset_url text,
  source_code_url text,
  doi varchar(255),
  doi_registered_at timestamptz
);

CREATE TABLE IF NOT EXISTS public.review_reports (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  manuscript_id uuid REFERENCES public.manuscripts(id) ON DELETE CASCADE,
  reviewer_id uuid REFERENCES auth.users(id),
  token text UNIQUE,
  expiry_date timestamptz,
  status text DEFAULT 'invited',
  content text,
  score integer CHECK (score >= 1 AND score <= 5),
  created_at timestamptz DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.invoices (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  manuscript_id uuid REFERENCES public.manuscripts(id) ON DELETE CASCADE UNIQUE,
  amount numeric(10,2) NOT NULL,
  pdf_url text,
  status text DEFAULT 'unpaid',
  confirmed_at timestamptz,
  created_at timestamptz DEFAULT now(),
  CONSTRAINT unique_manuscript_invoice UNIQUE (manuscript_id)
);

CREATE TABLE IF NOT EXISTS public.user_profiles (
  id uuid PRIMARY KEY,
  email text,
  roles text[] NOT NULL DEFAULT array['author'],
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  name text,
  institution text,
  research_interests text,
  country text
);

CREATE TABLE IF NOT EXISTS public.notifications (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  manuscript_id uuid NULL REFERENCES public.manuscripts(id) ON DELETE SET NULL,
  type text NOT NULL,
  title text NOT NULL,
  content text NOT NULL,
  is_read boolean NOT NULL DEFAULT false,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.review_assignments (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  manuscript_id uuid NOT NULL REFERENCES public.manuscripts(id) ON DELETE CASCADE,
  reviewer_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  status text NOT NULL DEFAULT 'pending',
  due_at timestamptz NULL,
  last_reminded_at timestamptz NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.plagiarism_reports (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  manuscript_id uuid REFERENCES public.manuscripts(id) ON DELETE CASCADE UNIQUE,
  external_id text,
  similarity_score float4,
  report_url text,
  status text DEFAULT 'pending',
  retry_count int2 DEFAULT 0,
  error_log text,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

-- ============================================================================
-- 2) Feature 012: Matchmaking (pgvector + embeddings)
-- ============================================================================

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS public.reviewer_embeddings (
  user_id uuid PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  embedding vector(384) NOT NULL,
  source_text_hash text NOT NULL,
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE OR REPLACE FUNCTION public.match_reviewers(
  query_embedding vector(384),
  match_threshold float8 DEFAULT 0.70,
  match_count int DEFAULT 5
)
RETURNS TABLE (user_id uuid, score float8)
LANGUAGE sql
STABLE
AS $$
  select
    re.user_id,
    1 - (re.embedding <=> query_embedding) as score
  from public.reviewer_embeddings re
  where 1 - (re.embedding <=> query_embedding) >= match_threshold
  order by re.embedding <=> query_embedding asc
  limit match_count;
$$;

-- ============================================================================
-- 3) Feature 013: Portal CMS (pages + menu)
-- ============================================================================

CREATE OR REPLACE FUNCTION public.sf_set_updated_at()
RETURNS trigger
LANGUAGE plpgsql
AS $$
begin
  new.updated_at = now();
  return new;
end;
$$;

CREATE OR REPLACE FUNCTION public.sf_user_has_any_role(required_roles text[])
RETURNS boolean
LANGUAGE sql
STABLE
AS $$
  select exists (
    select 1
    from public.user_profiles up
    where up.id = auth.uid()
      and (up.roles && required_roles)
  );
$$;

CREATE TABLE IF NOT EXISTS public.cms_pages (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  slug text NOT NULL UNIQUE,
  title text NOT NULL,
  content text,
  is_published boolean NOT NULL DEFAULT false,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  updated_by uuid REFERENCES auth.users(id),
  CONSTRAINT cms_pages_slug_format_chk CHECK (slug ~ '^[a-z0-9-]+$')
);

CREATE TABLE IF NOT EXISTS public.cms_menu_items (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  parent_id uuid REFERENCES public.cms_menu_items(id) ON DELETE CASCADE,
  label text NOT NULL,
  url text,
  page_id uuid REFERENCES public.cms_pages(id) ON DELETE SET NULL,
  order_index integer NOT NULL DEFAULT 0,
  location text NOT NULL DEFAULT 'header',
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  updated_by uuid REFERENCES auth.users(id),
  CONSTRAINT cms_menu_items_location_chk CHECK (location in ('header', 'footer')),
  CONSTRAINT cms_menu_items_target_exclusive_chk CHECK (url is null or page_id is null)
);

-- ============================================================================
-- 4) Feature 015: DOI Registration
-- ============================================================================

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'doi_registration_status') THEN
    CREATE TYPE doi_registration_status AS ENUM ('pending', 'submitting', 'registered', 'failed');
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'doi_task_status') THEN
    CREATE TYPE doi_task_status AS ENUM ('pending', 'processing', 'completed', 'failed');
  END IF;
END $$;

CREATE TABLE IF NOT EXISTS public.doi_registrations (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  article_id uuid NOT NULL UNIQUE REFERENCES public.manuscripts(id) ON DELETE CASCADE,
  doi varchar(255) UNIQUE,
  status doi_registration_status NOT NULL DEFAULT 'pending',
  attempts integer NOT NULL DEFAULT 0,
  crossref_batch_id varchar(255),
  error_message text,
  created_at timestamptz NOT NULL DEFAULT now(),
  registered_at timestamptz,
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.doi_tasks (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  registration_id uuid NOT NULL REFERENCES public.doi_registrations(id) ON DELETE CASCADE,
  task_type varchar(50) NOT NULL,
  status doi_task_status NOT NULL DEFAULT 'pending',
  priority integer NOT NULL DEFAULT 0,
  run_at timestamptz NOT NULL DEFAULT now(),
  locked_at timestamptz,
  locked_by varchar(100),
  attempts integer NOT NULL DEFAULT 0,
  max_attempts integer NOT NULL DEFAULT 4,
  last_error text,
  created_at timestamptz NOT NULL DEFAULT now(),
  completed_at timestamptz
);

CREATE TABLE IF NOT EXISTS public.doi_audit_log (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  registration_id uuid REFERENCES public.doi_registrations(id) ON DELETE SET NULL,
  action varchar(50) NOT NULL,
  request_payload jsonb,
  response_status integer,
  response_body text,
  error_details text,
  created_at timestamptz NOT NULL DEFAULT now(),
  created_by uuid REFERENCES auth.users(id)
);

-- ============================================================================
-- 5) Feature 015/010: Analytics Views + RPCs（用于仪表盘）
-- ============================================================================

CREATE OR REPLACE VIEW public.view_submission_trends AS
SELECT
  date_trunc('month', m.created_at)::date AS month,
  COUNT(*)::int AS submission_count,
  COUNT(*) FILTER (WHERE m.status = 'accepted')::int AS acceptance_count
FROM public.manuscripts m
WHERE m.created_at >= date_trunc('month', CURRENT_DATE - INTERVAL '11 months')
GROUP BY date_trunc('month', m.created_at)
ORDER BY month ASC;

CREATE OR REPLACE VIEW public.view_status_pipeline AS
SELECT
  m.status AS stage,
  COUNT(*)::int AS count
FROM public.manuscripts m
WHERE m.status IN ('submitted', 'under_review', 'revision', 'in_production')
GROUP BY m.status
ORDER BY
  CASE m.status
    WHEN 'submitted' THEN 1
    WHEN 'under_review' THEN 2
    WHEN 'revision' THEN 3
    WHEN 'in_production' THEN 4
  END;

CREATE OR REPLACE VIEW public.view_decision_distribution AS
SELECT
  m.status AS decision,
  COUNT(*)::int AS count
FROM public.manuscripts m
WHERE m.status IN ('accepted', 'rejected', 'desk_reject', 'revision')
  AND m.created_at >= date_trunc('year', CURRENT_DATE)
GROUP BY m.status;
