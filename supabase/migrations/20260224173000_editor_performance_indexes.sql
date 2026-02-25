-- Feature 001: Editor performance index tuning for process/workspace hot paths.
-- 目标：
-- 1) 降低 manuscripts 在多状态筛选 + 按 updated_at 排序场景的扫描成本
-- 2) 加速按 owner/editor/assistant_editor/journal 组合过滤
-- 3) 提升标题 ILIKE 搜索性能（pg_trgm）

CREATE EXTENSION IF NOT EXISTS pg_trgm WITH SCHEMA public;

CREATE INDEX IF NOT EXISTS idx_manuscripts_status_updated_created
ON public.manuscripts (status, updated_at DESC, created_at DESC);

DO $$
BEGIN
  IF EXISTS (
    SELECT 1
    FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'manuscripts' AND column_name = 'journal_id'
  ) THEN
    EXECUTE '
      CREATE INDEX IF NOT EXISTS idx_manuscripts_journal_status_updated_created
      ON public.manuscripts (journal_id, status, updated_at DESC, created_at DESC)
    ';
  END IF;
END $$;

DO $$
BEGIN
  IF EXISTS (
    SELECT 1
    FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'manuscripts' AND column_name = 'owner_id'
  ) THEN
    EXECUTE '
      CREATE INDEX IF NOT EXISTS idx_manuscripts_owner_status_updated_created
      ON public.manuscripts (owner_id, status, updated_at DESC, created_at DESC)
    ';
  END IF;
END $$;

DO $$
BEGIN
  IF EXISTS (
    SELECT 1
    FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'manuscripts' AND column_name = 'editor_id'
  ) THEN
    EXECUTE '
      CREATE INDEX IF NOT EXISTS idx_manuscripts_editor_status_updated_created
      ON public.manuscripts (editor_id, status, updated_at DESC, created_at DESC)
    ';
  END IF;
END $$;

DO $$
BEGIN
  IF EXISTS (
    SELECT 1
    FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'manuscripts' AND column_name = 'assistant_editor_id'
  ) THEN
    EXECUTE '
      CREATE INDEX IF NOT EXISTS idx_manuscripts_ae_status_updated_created
      ON public.manuscripts (assistant_editor_id, status, updated_at DESC, created_at DESC)
    ';
  END IF;
END $$;

DO $$
BEGIN
  IF EXISTS (
    SELECT 1
    FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'manuscripts' AND column_name = 'pre_check_status'
  ) THEN
    EXECUTE '
      CREATE INDEX IF NOT EXISTS idx_manuscripts_precheck_status_updated_created
      ON public.manuscripts (pre_check_status, updated_at DESC, created_at DESC)
      WHERE status = ''pre_check''
    ';
  END IF;
END $$;

DO $$
BEGIN
  IF EXISTS (
    SELECT 1
    FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'manuscripts' AND column_name = 'title'
  ) THEN
    EXECUTE '
      CREATE INDEX IF NOT EXISTS idx_manuscripts_title_trgm
      ON public.manuscripts
      USING gin (title gin_trgm_ops)
    ';
  END IF;
END $$;

