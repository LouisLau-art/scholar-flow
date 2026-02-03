-- Feature 023: KPI Owner Binding (Internal Owner / Invited By)
-- 目标:
-- 1) 将历史字段 kpi_owner_id 统一为 owner_id（可空，FK -> auth.users）
-- 2) 更新 editor_kpi_stats 视图按 owner_id 统计

DO $$
DECLARE
  has_owner boolean;
  has_kpi boolean;
BEGIN
  SELECT EXISTS (
    SELECT 1
    FROM information_schema.columns
    WHERE table_schema='public' AND table_name='manuscripts' AND column_name='owner_id'
  ) INTO has_owner;

  SELECT EXISTS (
    SELECT 1
    FROM information_schema.columns
    WHERE table_schema='public' AND table_name='manuscripts' AND column_name='kpi_owner_id'
  ) INTO has_kpi;

  -- 兼容历史：若只有 kpi_owner_id，则重命名为 owner_id
  IF has_kpi AND NOT has_owner THEN
    EXECUTE 'ALTER TABLE public.manuscripts RENAME COLUMN kpi_owner_id TO owner_id';
    has_owner := true;
    has_kpi := false;
  END IF;

  -- 兜底：若两者都不存在（极少数环境），则新增 owner_id
  IF NOT has_owner AND NOT has_kpi THEN
    EXECUTE 'ALTER TABLE public.manuscripts ADD COLUMN owner_id uuid REFERENCES auth.users(id)';
    has_owner := true;
  END IF;

  -- 视图更新（按 owner_id 统计 KPI）
  EXECUTE 'DROP VIEW IF EXISTS public.editor_kpi_stats';

  IF has_owner THEN
    EXECUTE $v$
      CREATE VIEW public.editor_kpi_stats AS
      SELECT
          owner_id,
          COUNT(*) as processed_count,
          AVG(EXTRACT(EPOCH FROM (updated_at - created_at))/3600) as avg_process_hours
      FROM public.manuscripts
      WHERE status != 'draft'
      GROUP BY owner_id
    $v$;
  ELSIF has_kpi THEN
    -- 理论上不会到这里（上面已重命名），但保留作为容错
    EXECUTE $v$
      CREATE VIEW public.editor_kpi_stats AS
      SELECT
          kpi_owner_id as owner_id,
          COUNT(*) as processed_count,
          AVG(EXTRACT(EPOCH FROM (updated_at - created_at))/3600) as avg_process_hours
      FROM public.manuscripts
      WHERE status != 'draft'
      GROUP BY kpi_owner_id
    $v$;
  END IF;
END $$;

