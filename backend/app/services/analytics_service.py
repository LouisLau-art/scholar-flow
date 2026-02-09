"""
Analytics Service - 分析服务层
功能: 封装 Supabase RPC 和 View 调用，提供分析数据访问

中文注释:
- 使用 Supabase-py v2 客户端执行 RPC 和 View 查询
- 所有数据库聚合逻辑在 PostgreSQL 中执行，Python 层仅做数据转发
- 遵循章程: 核心计算逻辑放在 SQL 层，服务层保持简单
"""

import os
from typing import Literal, Optional, cast

from supabase import Client, create_client

from app.models.analytics import (
    DecisionData,
    EditorEfficiencyItem,
    GeoData,
    KPISummary,
    PipelineData,
    SLAAlertItem,
    StageDurationItem,
    TrendData,
)

StageName = Literal["pre_check", "under_review", "decision", "production"]


def get_supabase_client() -> Client:
    """
    获取 Supabase 客户端实例
    中文注释: 使用环境变量配置，确保安全
    """
    url = os.environ.get("SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
    if not url or not key:
        raise ValueError("SUPABASE_URL 和 SUPABASE_SERVICE_ROLE_KEY 环境变量必须设置")
    return create_client(url, key)


class AnalyticsService:
    """
    分析数据服务类
    封装所有分析相关的数据库操作
    """

    def __init__(self, supabase_client: Optional[Client] = None):
        """
        初始化服务
        中文注释: 允许注入客户端以便测试
        """
        self._client = supabase_client

    @property
    def client(self) -> Client:
        """延迟初始化 Supabase 客户端"""
        if self._client is None:
            self._client = get_supabase_client()
        return self._client

    def _is_missing_rpc_error(self, error: Exception | str) -> bool:
        text = str(error or "").lower()
        return "function" in text and "does not exist" in text

    def _to_sla_severity(self, *, overdue_tasks_count: int, max_overdue_days: float) -> str:
        """
        SLA 风险等级规则（显性）：
        - high: 逾期任务 >=3 或最长逾期 >=7 天
        - medium: 逾期任务 >=2 或最长逾期 >=3 天
        - low: 其余
        """
        if overdue_tasks_count >= 3 or max_overdue_days >= 7:
            return "high"
        if overdue_tasks_count >= 2 or max_overdue_days >= 3:
            return "medium"
        return "low"

    async def get_kpi_summary(self) -> KPISummary:
        """
        获取 KPI 汇总数据
        调用 get_journal_kpis() RPC

        中文注释:
        - RPC 返回 JSON，直接解析为 KPISummary 模型
        - 所有计算逻辑在 PostgreSQL 中完成
        """
        response = self.client.rpc("get_journal_kpis").execute()

        if response.data is None:
            # 返回空数据时的默认值
            return KPISummary(
                new_submissions_month=0,
                total_pending=0,
                avg_first_decision_days=0,
                yearly_acceptance_rate=0,
                apc_revenue_month=0,
                apc_revenue_year=0,
            )

        data = response.data
        return KPISummary(
            new_submissions_month=data.get("new_submissions_month", 0),
            total_pending=data.get("total_pending", 0),
            avg_first_decision_days=data.get("avg_first_decision_days", 0),
            yearly_acceptance_rate=data.get("yearly_acceptance_rate", 0),
            apc_revenue_month=data.get("apc_revenue_month", 0),
            apc_revenue_year=data.get("apc_revenue_year", 0),
        )

    async def get_submission_trends(self) -> list[TrendData]:
        """
        获取投稿趋势数据
        查询 view_submission_trends 视图

        中文注释: 返回过去 12 个月的投稿和接受趋势
        """
        response = self.client.table("view_submission_trends").select("*").execute()

        if not response.data:
            return []

        return [
            TrendData(
                month=row["month"],
                submission_count=row["submission_count"],
                acceptance_count=row["acceptance_count"],
            )
            for row in response.data
        ]

    async def get_status_pipeline(self) -> list[PipelineData]:
        """
        获取状态流水线数据
        查询 view_status_pipeline 视图

        中文注释: 返回当前活跃稿件的状态分布
        """
        response = self.client.table("view_status_pipeline").select("*").execute()

        if not response.data:
            return []

        return [
            PipelineData(
                stage=row["stage"],
                count=row["count"],
            )
            for row in response.data
        ]

    async def get_decision_distribution(self) -> list[DecisionData]:
        """
        获取决定分布数据
        查询 view_decision_distribution 视图

        中文注释: 返回年度决定分布（接受/拒绝/修改）
        """
        response = self.client.table("view_decision_distribution").select("*").execute()

        if not response.data:
            return []

        return [
            DecisionData(
                decision=row["decision"],
                count=row["count"],
            )
            for row in response.data
        ]

    async def get_author_geography(self) -> list[GeoData]:
        """
        获取作者地理分布数据
        调用 get_author_geography() RPC

        中文注释: 返回 Top 10 国家的投稿数
        """
        response = self.client.rpc("get_author_geography").execute()

        if not response.data:
            return []

        return [
            GeoData(
                country=row["country"],
                submission_count=row["submission_count"],
            )
            for row in response.data
        ]

    async def get_editor_efficiency_ranking(
        self,
        *,
        limit: int = 10,
        journal_ids: list[str] | None = None,
    ) -> list[EditorEfficiencyItem]:
        """
        获取编辑效率排行（处理量 + 平均首次决定耗时）。
        """
        params = {
            "limit_count": int(max(1, limit)),
            "journal_ids": journal_ids or None,
        }
        try:
            response = self.client.rpc("get_editor_efficiency_ranking", params).execute()
        except Exception as e:
            if self._is_missing_rpc_error(e):
                return []
            raise

        rows = response.data or []
        return [
            EditorEfficiencyItem(
                editor_id=str(row.get("editor_id") or ""),
                editor_name=str(row.get("editor_name") or "Unknown Editor"),
                editor_email=row.get("editor_email"),
                handled_count=int(row.get("handled_count") or 0),
                avg_first_decision_days=float(row.get("avg_first_decision_days") or 0),
            )
            for row in rows
            if row.get("editor_id")
        ]

    async def get_stage_duration_breakdown(
        self,
        *,
        journal_ids: list[str] | None = None,
    ) -> list[StageDurationItem]:
        """
        获取阶段耗时分解（预审/外审/终审/生产）。
        """
        params = {
            "journal_ids": journal_ids or None,
        }
        try:
            response = self.client.rpc("get_stage_duration_breakdown", params).execute()
        except Exception as e:
            if self._is_missing_rpc_error(e):
                return []
            raise

        rows = response.data or []
        out: list[StageDurationItem] = []
        for row in rows:
            stage = str(row.get("stage") or "").strip()
            if stage not in {"pre_check", "under_review", "decision", "production"}:
                continue
            stage_value = cast(StageName, stage)
            out.append(
                StageDurationItem(
                    stage=stage_value,
                    avg_days=float(row.get("avg_days") or 0),
                    sample_size=int(row.get("sample_size") or 0),
                )
            )
        return out

    async def get_sla_alerts(
        self,
        *,
        limit: int = 20,
        journal_ids: list[str] | None = None,
    ) -> list[SLAAlertItem]:
        """
        获取超 SLA 稿件预警列表。
        """
        params = {
            "limit_count": int(max(1, limit)),
            "journal_ids": journal_ids or None,
        }
        try:
            response = self.client.rpc("get_sla_overdue_manuscripts", params).execute()
        except Exception as e:
            if self._is_missing_rpc_error(e):
                return []
            raise

        rows = response.data or []
        out: list[SLAAlertItem] = []
        for row in rows:
            manuscript_id = str(row.get("manuscript_id") or "")
            if not manuscript_id:
                continue
            overdue_tasks_count = int(row.get("overdue_tasks_count") or 0)
            max_overdue_days = float(row.get("max_overdue_days") or 0)
            out.append(
                SLAAlertItem(
                    manuscript_id=manuscript_id,
                    title=str(row.get("title") or manuscript_id),
                    status=str(row.get("status") or ""),
                    journal_id=str(row.get("journal_id") or "") or None,
                    journal_title=row.get("journal_title"),
                    editor_id=str(row.get("editor_id") or "") or None,
                    editor_name=row.get("editor_name"),
                    owner_id=str(row.get("owner_id") or "") or None,
                    owner_name=row.get("owner_name"),
                    overdue_tasks_count=overdue_tasks_count,
                    max_overdue_days=max_overdue_days,
                    earliest_due_at=row.get("earliest_due_at"),
                    severity=self._to_sla_severity(
                        overdue_tasks_count=overdue_tasks_count,
                        max_overdue_days=max_overdue_days,
                    ),
                )
            )
        return out


# 单例服务实例（可选，用于依赖注入）
_analytics_service: Optional[AnalyticsService] = None


def get_analytics_service() -> AnalyticsService:
    """
    获取 AnalyticsService 单例
    中文注释: 用于 FastAPI 依赖注入
    """
    global _analytics_service
    if _analytics_service is None:
        _analytics_service = AnalyticsService()
    return _analytics_service
