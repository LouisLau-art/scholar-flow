-- Feature 028: Workflow and UI Standardization
-- 目标：
-- 1) 引入统一的稿件生命周期状态枚举（manuscript_status）
-- 2) 在 manuscripts 上新增 invoice_metadata（JSONB）用于票据信息编辑
--
-- 注意：
-- - 现网历史版本中 manuscripts.status 可能是 TEXT 且包含旧状态（submitted/pending_decision/revision_requested...）。
-- - 该迁移会将旧状态映射到新状态，避免 cast 失败。

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'manuscript_status') THEN
    CREATE TYPE public.manuscript_status AS ENUM (
      'pre_check',
      'under_review',
      'major_revision',
      'minor_revision',
      'resubmitted',
      'decision',
      'decision_done',
      'approved',
      'layout',
      'english_editing',
      'proofreading',
      'published',
      'rejected'
    );
  END IF;
END $$;

ALTER TABLE public.manuscripts
  ADD COLUMN IF NOT EXISTS invoice_metadata jsonb NOT NULL DEFAULT '{}'::jsonb;

-- 将 status 从 TEXT 迁移为 ENUM（若 status 已经是 enum，则该语句会失败；用异常捕获兜底）
DO $$
BEGIN
  BEGIN
    ALTER TABLE public.manuscripts
      ALTER COLUMN status TYPE public.manuscript_status
      USING (
        CASE lower(status::text)
          WHEN 'draft' THEN 'pre_check'::public.manuscript_status
          WHEN 'submitted' THEN 'pre_check'::public.manuscript_status
          WHEN 'pending_quality' THEN 'pre_check'::public.manuscript_status
          WHEN 'under_review' THEN 'under_review'::public.manuscript_status
          WHEN 'pending_decision' THEN 'decision'::public.manuscript_status
          WHEN 'decision' THEN 'decision'::public.manuscript_status
          WHEN 'decision_done' THEN 'decision_done'::public.manuscript_status
          WHEN 'revision_requested' THEN 'minor_revision'::public.manuscript_status
          WHEN 'returned_for_revision' THEN 'minor_revision'::public.manuscript_status
          WHEN 'major_revision' THEN 'major_revision'::public.manuscript_status
          WHEN 'minor_revision' THEN 'minor_revision'::public.manuscript_status
          WHEN 'resubmitted' THEN 'resubmitted'::public.manuscript_status
          WHEN 'approved' THEN 'approved'::public.manuscript_status
          WHEN 'layout' THEN 'layout'::public.manuscript_status
          WHEN 'english_editing' THEN 'english_editing'::public.manuscript_status
          WHEN 'proofreading' THEN 'proofreading'::public.manuscript_status
          WHEN 'published' THEN 'published'::public.manuscript_status
          WHEN 'rejected' THEN 'rejected'::public.manuscript_status
          ELSE 'pre_check'::public.manuscript_status
        END
      );
  EXCEPTION
    WHEN undefined_column THEN
      -- 在某些早期环境中 manuscripts.status 可能不存在（极少见）；忽略
      NULL;
    WHEN invalid_parameter_value THEN
      -- 如果 status 已是 enum 或者类型不兼容，保守忽略（由后端做状态校验）
      NULL;
    WHEN datatype_mismatch THEN
      NULL;
  END;
END $$;

ALTER TABLE public.manuscripts
  ALTER COLUMN status SET DEFAULT 'pre_check';

