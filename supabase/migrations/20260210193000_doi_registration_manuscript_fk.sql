-- GAP-P2-01: DOI/Crossref 真对接的 schema 兼容修复
-- 目标：让 doi_registrations.article_id 与 manuscripts 对齐，避免历史 articles 外键导致注册失败

DO $$
DECLARE
  con_name text;
BEGIN
  IF to_regclass('public.doi_registrations') IS NULL THEN
    RAISE NOTICE 'skip: public.doi_registrations not found';
    RETURN;
  END IF;

  FOR con_name IN
    SELECT c.conname
    FROM pg_constraint c
    WHERE c.conrelid = 'public.doi_registrations'::regclass
      AND c.contype = 'f'
      AND c.confrelid = to_regclass('public.articles')
  LOOP
    EXECUTE format(
      'ALTER TABLE public.doi_registrations DROP CONSTRAINT IF EXISTS %I',
      con_name
    );
  END LOOP;
END $$;

DO $$
BEGIN
  IF to_regclass('public.doi_registrations') IS NULL THEN
    RETURN;
  END IF;

  IF to_regclass('public.manuscripts') IS NULL THEN
    RAISE NOTICE 'skip: public.manuscripts not found';
    RETURN;
  END IF;

  IF NOT EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conrelid = 'public.doi_registrations'::regclass
      AND conname = 'doi_registrations_article_id_manuscript_fkey'
  ) THEN
    ALTER TABLE public.doi_registrations
      ADD CONSTRAINT doi_registrations_article_id_manuscript_fkey
      FOREIGN KEY (article_id)
      REFERENCES public.manuscripts(id)
      ON DELETE CASCADE
      NOT VALID;
  END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_doi_registrations_status_updated
  ON public.doi_registrations (status, updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_doi_tasks_status_run_at
  ON public.doi_tasks (status, run_at ASC);
