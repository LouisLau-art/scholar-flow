-- ============================================================================
-- Feature 047: Analytics Management Insights
-- 目标：
-- 1) 编辑效率排行（处理量 + 平均首次决定耗时）
-- 2) 阶段耗时分解（pre_check / under_review / decision / production）
-- 3) 超 SLA 稿件预警（基于 internal_tasks 逾期）
-- 备注：
-- - 所有函数支持可选 journal_ids 过滤，便于后端 journal-scope 裁剪。
-- - 使用 SECURITY DEFINER，统一由后端服务调用。
-- ============================================================================

CREATE OR REPLACE FUNCTION public.get_editor_efficiency_ranking(
  limit_count int DEFAULT 10,
  journal_ids uuid[] DEFAULT NULL
)
RETURNS TABLE(
  editor_id uuid,
  editor_name text,
  editor_email text,
  handled_count int,
  avg_first_decision_days numeric
)
LANGUAGE sql
SECURITY DEFINER
AS $$
WITH manuscript_scope AS (
  SELECT
    m.id AS manuscript_id,
    COALESCE(m.editor_id, m.owner_id) AS editor_id,
    m.created_at
  FROM public.manuscripts m
  WHERE COALESCE(m.editor_id, m.owner_id) IS NOT NULL
    AND (journal_ids IS NULL OR m.journal_id = ANY(journal_ids))
),
first_decision AS (
  SELECT
    l.manuscript_id,
    MIN(l.created_at) AS first_decision_at
  FROM public.status_transition_logs l
  WHERE l.to_status IN ('decision_done', 'major_revision', 'minor_revision', 'approved', 'rejected')
  GROUP BY l.manuscript_id
),
scored AS (
  SELECT
    ms.editor_id,
    ms.manuscript_id,
    EXTRACT(EPOCH FROM (fd.first_decision_at - ms.created_at)) / 86400.0 AS first_decision_days
  FROM manuscript_scope ms
  JOIN first_decision fd ON fd.manuscript_id = ms.manuscript_id
)
SELECT
  s.editor_id,
  COALESCE(NULLIF(TRIM(up.full_name), ''), up.email, 'Unknown Editor') AS editor_name,
  up.email AS editor_email,
  COUNT(*)::int AS handled_count,
  COALESCE(
    AVG(s.first_decision_days) FILTER (WHERE s.first_decision_days >= 0),
    0
  )::numeric(10,2) AS avg_first_decision_days
FROM scored s
LEFT JOIN public.user_profiles up ON up.id = s.editor_id
GROUP BY s.editor_id, up.full_name, up.email
ORDER BY handled_count DESC, avg_first_decision_days ASC, editor_name ASC
LIMIT GREATEST(COALESCE(limit_count, 10), 1);
$$;

COMMENT ON FUNCTION public.get_editor_efficiency_ranking(int, uuid[]) IS
'Analytics: 编辑效率排行（处理量 + 平均首次决定耗时）';


CREATE OR REPLACE FUNCTION public.get_stage_duration_breakdown(
  journal_ids uuid[] DEFAULT NULL
)
RETURNS TABLE(
  stage text,
  avg_days numeric,
  sample_size int
)
LANGUAGE sql
SECURITY DEFINER
AS $$
WITH manuscript_scope AS (
  SELECT
    m.id AS manuscript_id,
    m.created_at
  FROM public.manuscripts m
  WHERE (journal_ids IS NULL OR m.journal_id = ANY(journal_ids))
),
events AS (
  SELECT
    l.manuscript_id,
    MIN(l.created_at) FILTER (WHERE l.from_status = 'pre_check') AS precheck_end_at,
    MIN(l.created_at) FILTER (WHERE l.to_status = 'under_review') AS review_start_at,
    MIN(l.created_at) FILTER (WHERE l.from_status = 'under_review') AS review_end_at,
    MIN(l.created_at) FILTER (WHERE l.to_status = 'decision') AS decision_start_at,
    MIN(l.created_at) FILTER (WHERE l.to_status IN ('approved', 'rejected', 'major_revision', 'minor_revision')) AS decision_end_at,
    MIN(l.created_at) FILTER (WHERE l.to_status = 'approved') AS production_start_at,
    MIN(l.created_at) FILTER (WHERE l.to_status = 'published') AS production_end_at
  FROM public.status_transition_logs l
  GROUP BY l.manuscript_id
),
durations AS (
  SELECT
    ms.manuscript_id,
    EXTRACT(EPOCH FROM (e.precheck_end_at - ms.created_at)) / 86400.0 AS pre_check_days,
    EXTRACT(EPOCH FROM (e.review_end_at - e.review_start_at)) / 86400.0 AS under_review_days,
    EXTRACT(EPOCH FROM (e.decision_end_at - e.decision_start_at)) / 86400.0 AS decision_days,
    EXTRACT(EPOCH FROM (e.production_end_at - e.production_start_at)) / 86400.0 AS production_days
  FROM manuscript_scope ms
  LEFT JOIN events e ON e.manuscript_id = ms.manuscript_id
),
flat AS (
  SELECT 'pre_check'::text AS stage, pre_check_days AS days FROM durations
  UNION ALL
  SELECT 'under_review'::text AS stage, under_review_days AS days FROM durations
  UNION ALL
  SELECT 'decision'::text AS stage, decision_days AS days FROM durations
  UNION ALL
  SELECT 'production'::text AS stage, production_days AS days FROM durations
)
SELECT
  stage,
  COALESCE(
    AVG(days) FILTER (WHERE days IS NOT NULL AND days >= 0),
    0
  )::numeric(10,2) AS avg_days,
  COUNT(*) FILTER (WHERE days IS NOT NULL AND days >= 0)::int AS sample_size
FROM flat
GROUP BY stage
ORDER BY
  CASE stage
    WHEN 'pre_check' THEN 1
    WHEN 'under_review' THEN 2
    WHEN 'decision' THEN 3
    WHEN 'production' THEN 4
    ELSE 99
  END;
$$;

COMMENT ON FUNCTION public.get_stage_duration_breakdown(uuid[]) IS
'Analytics: 流程阶段耗时分解（pre_check / under_review / decision / production）';


CREATE OR REPLACE FUNCTION public.get_sla_overdue_manuscripts(
  limit_count int DEFAULT 20,
  journal_ids uuid[] DEFAULT NULL
)
RETURNS TABLE(
  manuscript_id uuid,
  title text,
  status text,
  journal_id uuid,
  journal_title text,
  editor_id uuid,
  editor_name text,
  owner_id uuid,
  owner_name text,
  overdue_tasks_count int,
  max_overdue_days numeric,
  earliest_due_at timestamptz
)
LANGUAGE sql
SECURITY DEFINER
AS $$
WITH overdue AS (
  SELECT
    t.manuscript_id,
    COUNT(*)::int AS overdue_tasks_count,
    COALESCE(
      MAX(EXTRACT(EPOCH FROM (NOW() - t.due_at)) / 86400.0),
      0
    )::numeric(10,2) AS max_overdue_days,
    MIN(t.due_at) AS earliest_due_at
  FROM public.internal_tasks t
  WHERE t.status <> 'done'
    AND t.due_at < NOW()
  GROUP BY t.manuscript_id
)
SELECT
  m.id AS manuscript_id,
  COALESCE(NULLIF(TRIM(m.title), ''), m.id::text) AS title,
  m.status::text AS status,
  m.journal_id,
  j.title AS journal_title,
  m.editor_id,
  COALESCE(NULLIF(TRIM(ep.full_name), ''), ep.email, NULL) AS editor_name,
  m.owner_id,
  COALESCE(NULLIF(TRIM(op.full_name), ''), op.email, NULL) AS owner_name,
  o.overdue_tasks_count,
  o.max_overdue_days,
  o.earliest_due_at
FROM overdue o
JOIN public.manuscripts m ON m.id = o.manuscript_id
LEFT JOIN public.journals j ON j.id = m.journal_id
LEFT JOIN public.user_profiles ep ON ep.id = m.editor_id
LEFT JOIN public.user_profiles op ON op.id = m.owner_id
WHERE m.status::text NOT IN ('published', 'rejected')
  AND (journal_ids IS NULL OR m.journal_id = ANY(journal_ids))
ORDER BY
  o.overdue_tasks_count DESC,
  o.max_overdue_days DESC,
  m.updated_at DESC
LIMIT GREATEST(COALESCE(limit_count, 20), 1);
$$;

COMMENT ON FUNCTION public.get_sla_overdue_manuscripts(int, uuid[]) IS
'Analytics: 超 SLA 稿件预警（基于 internal_tasks 逾期任务）';


GRANT EXECUTE ON FUNCTION public.get_editor_efficiency_ranking(int, uuid[]) TO authenticated;
GRANT EXECUTE ON FUNCTION public.get_stage_duration_breakdown(uuid[]) TO authenticated;
GRANT EXECUTE ON FUNCTION public.get_sla_overdue_manuscripts(int, uuid[]) TO authenticated;
