-- ============================================================================
-- Analytics Dashboard: Views and RPCs
-- 功能: 为主编/编辑提供 KPI 指标、投稿趋势、状态流水线、地理分布数据
-- 创建日期: 2026-01-30
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 1. 扩展 user_profiles 表添加 country 字段（用于地理分布统计）
-- ----------------------------------------------------------------------------
ALTER TABLE public.user_profiles
ADD COLUMN IF NOT EXISTS country TEXT;

COMMENT ON COLUMN public.user_profiles.country IS '用户所在国家，用于地理分布统计';

-- ----------------------------------------------------------------------------
-- 2. view_submission_trends: 过去 12 个月的投稿和接受趋势
-- 说明: 按月聚合投稿数量和接受数量，用于趋势折线图
-- ----------------------------------------------------------------------------
CREATE OR REPLACE VIEW public.view_submission_trends AS
SELECT
    date_trunc('month', m.created_at)::date AS month,
    COUNT(*)::int AS submission_count,
    COUNT(*) FILTER (WHERE m.status = 'accepted')::int AS acceptance_count
FROM public.manuscripts m
WHERE m.created_at >= date_trunc('month', CURRENT_DATE - INTERVAL '11 months')
GROUP BY date_trunc('month', m.created_at)
ORDER BY month ASC;

COMMENT ON VIEW public.view_submission_trends IS '过去 12 个月的投稿和接受趋势数据';

-- ----------------------------------------------------------------------------
-- 3. view_status_pipeline: 当前活跃稿件的状态分布
-- 说明: 排除草稿和最终状态（accepted/rejected），用于漏斗图
-- 活跃状态定义: submitted, under_review, revision, in_production
-- ----------------------------------------------------------------------------
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

COMMENT ON VIEW public.view_status_pipeline IS '当前活跃稿件按状态分布（流水线/漏斗图）';

-- ----------------------------------------------------------------------------
-- 4. get_journal_kpis(): 核心 KPI 指标 RPC
-- 返回: 
--   - new_submissions_month: 本月新投稿数
--   - total_pending: 待处理稿件总数
--   - avg_first_decision_days: 平均首次决定时间（天），排除 Desk Reject
--   - yearly_acceptance_rate: 年度接受率（排除 Desk Reject）
--   - apc_revenue_month: 本月 APC 收入
--   - apc_revenue_year: 本年度 APC 收入
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.get_journal_kpis()
RETURNS JSON
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    result JSON;
    v_new_submissions_month INT;
    v_total_pending INT;
    v_avg_first_decision_days NUMERIC;
    v_yearly_acceptance_rate NUMERIC;
    v_apc_revenue_month NUMERIC;
    v_apc_revenue_year NUMERIC;
    v_start_of_month DATE;
    v_start_of_year DATE;
BEGIN
    v_start_of_month := date_trunc('month', CURRENT_DATE)::date;
    v_start_of_year := date_trunc('year', CURRENT_DATE)::date;

    -- 本月新投稿数
    SELECT COUNT(*)::int INTO v_new_submissions_month
    FROM public.manuscripts
    WHERE created_at >= v_start_of_month;

    -- 待处理稿件总数（活跃状态）
    SELECT COUNT(*)::int INTO v_total_pending
    FROM public.manuscripts
    WHERE status IN ('submitted', 'under_review', 'revision');

    -- 平均首次决定时间（排除 desk_reject，使用 updated_at 作为决定时间的近似值）
    -- 注意：如果有 first_decision_at 字段，应使用该字段
    SELECT COALESCE(
        AVG(
            EXTRACT(EPOCH FROM (updated_at - created_at)) / 86400
        )::numeric(10,1),
        0
    ) INTO v_avg_first_decision_days
    FROM public.manuscripts
    WHERE status IN ('accepted', 'rejected', 'revision', 'under_review')
      AND status != 'desk_reject'
      AND updated_at > created_at;

    -- 年度接受率（排除 desk_reject）
    -- 公式: accepted / (accepted + rejected)，仅计算已决定的稿件
    SELECT COALESCE(
        (
            COUNT(*) FILTER (WHERE status = 'accepted')::numeric /
            NULLIF(COUNT(*) FILTER (WHERE status IN ('accepted', 'rejected')), 0)
        )::numeric(10,4),
        0
    ) INTO v_yearly_acceptance_rate
    FROM public.manuscripts
    WHERE created_at >= v_start_of_year
      AND status != 'desk_reject';

    -- 本月 APC 收入（已支付/已确认的账单）
    SELECT COALESCE(SUM(amount), 0)::numeric(12,2) INTO v_apc_revenue_month
    FROM public.invoices
    WHERE (status = 'paid' OR status = 'confirmed')
      AND (confirmed_at >= v_start_of_month OR created_at >= v_start_of_month);

    -- 本年度 APC 收入
    SELECT COALESCE(SUM(amount), 0)::numeric(12,2) INTO v_apc_revenue_year
    FROM public.invoices
    WHERE (status = 'paid' OR status = 'confirmed')
      AND (confirmed_at >= v_start_of_year OR created_at >= v_start_of_year);

    -- 构建 JSON 结果
    result := json_build_object(
        'new_submissions_month', v_new_submissions_month,
        'total_pending', v_total_pending,
        'avg_first_decision_days', v_avg_first_decision_days,
        'yearly_acceptance_rate', v_yearly_acceptance_rate,
        'apc_revenue_month', v_apc_revenue_month,
        'apc_revenue_year', v_apc_revenue_year
    );

    RETURN result;
END;
$$;

COMMENT ON FUNCTION public.get_journal_kpis() IS '返回期刊核心 KPI 指标，用于主编仪表盘';

-- ----------------------------------------------------------------------------
-- 5. get_author_geography(): 作者国家分布 RPC
-- 返回: 按国家聚合的投稿数量，用于水平条形图
-- 说明: 仅统计有国家信息的作者，返回 Top 10
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.get_author_geography()
RETURNS TABLE(country TEXT, submission_count INT)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    RETURN QUERY
    SELECT
        up.country,
        COUNT(DISTINCT m.id)::int AS submission_count
    FROM public.manuscripts m
    INNER JOIN public.user_profiles up ON m.author_id = up.id
    WHERE up.country IS NOT NULL AND up.country != ''
    GROUP BY up.country
    ORDER BY submission_count DESC
    LIMIT 10;
END;
$$;

COMMENT ON FUNCTION public.get_author_geography() IS '返回 Top 10 作者国家分布，用于地理图表';

-- ----------------------------------------------------------------------------
-- 6. view_decision_distribution: 决定分布（用于饼图/环形图）
-- 说明: 统计今年各类决定的数量分布
-- ----------------------------------------------------------------------------
CREATE OR REPLACE VIEW public.view_decision_distribution AS
SELECT
    m.status AS decision,
    COUNT(*)::int AS count
FROM public.manuscripts m
WHERE m.status IN ('accepted', 'rejected', 'desk_reject', 'revision')
  AND m.created_at >= date_trunc('year', CURRENT_DATE)
GROUP BY m.status;

COMMENT ON VIEW public.view_decision_distribution IS '年度决定分布（接受/拒绝/修改）';

-- ----------------------------------------------------------------------------
-- 7. 授权：允许认证用户访问这些 Views 和 RPCs
-- ----------------------------------------------------------------------------
GRANT SELECT ON public.view_submission_trends TO authenticated;
GRANT SELECT ON public.view_status_pipeline TO authenticated;
GRANT SELECT ON public.view_decision_distribution TO authenticated;
GRANT EXECUTE ON FUNCTION public.get_journal_kpis() TO authenticated;
GRANT EXECUTE ON FUNCTION public.get_author_geography() TO authenticated;
