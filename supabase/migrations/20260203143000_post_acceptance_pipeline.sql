-- Feature 024: Post-Acceptance Pipeline (录用后出版流水线)
-- 目标：
-- 1) manuscripts 增加 production/publish 所需字段：final_pdf_path / published_at / doi
-- 2) doi 唯一性（仅在非空时约束）

ALTER TABLE public.manuscripts
  ADD COLUMN IF NOT EXISTS final_pdf_path TEXT;

ALTER TABLE public.manuscripts
  ADD COLUMN IF NOT EXISTS published_at TIMESTAMPTZ;

ALTER TABLE public.manuscripts
  ADD COLUMN IF NOT EXISTS doi TEXT;

-- 兼容：使用 partial unique index，避免 NULL 触发唯一性冲突
CREATE UNIQUE INDEX IF NOT EXISTS manuscripts_doi_unique
  ON public.manuscripts (doi)
  WHERE doi IS NOT NULL;

CREATE INDEX IF NOT EXISTS manuscripts_published_at_idx
  ON public.manuscripts (published_at DESC);

