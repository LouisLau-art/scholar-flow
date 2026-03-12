-- Feature: pre-check technical return should not reuse minor_revision
-- 目标：
-- 1) 为 manuscripts.status 增加 revision_before_review
-- 2) 增加 AE SLA / 作者修回相关时间字段
-- 3) 区分“外审前技术退回”和正常学术修回

DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'manuscript_status') THEN
    BEGIN
      ALTER TYPE public.manuscript_status ADD VALUE IF NOT EXISTS 'revision_before_review' AFTER 'pre_check';
    EXCEPTION
      WHEN duplicate_object THEN
        NULL;
    END;
  END IF;
END $$;

ALTER TABLE public.manuscripts
  ADD COLUMN IF NOT EXISTS initial_submitted_at timestamptz,
  ADD COLUMN IF NOT EXISTS latest_author_resubmitted_at timestamptz,
  ADD COLUMN IF NOT EXISTS ae_sla_started_at timestamptz;

UPDATE public.manuscripts
SET initial_submitted_at = COALESCE(initial_submitted_at, created_at, updated_at, now())
WHERE initial_submitted_at IS NULL;

UPDATE public.manuscripts
SET ae_sla_started_at = COALESCE(ae_sla_started_at, updated_at, created_at, now())
WHERE ae_sla_started_at IS NULL
  AND status = 'pre_check'
  AND COALESCE(pre_check_status, 'intake') = 'technical'
  AND assistant_editor_id IS NOT NULL;
