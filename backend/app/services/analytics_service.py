"""
Analytics Service - 分析服务层
功能: 封装 Supabase RPC 和 View 调用，提供分析数据访问

中文注释:
- 使用 Supabase-py v2 客户端执行 RPC 和 View 查询
- 所有数据库聚合逻辑在 PostgreSQL 中执行，Python 层仅做数据转发
- 遵循章程: 核心计算逻辑放在 SQL 层，服务层保持简单
"""

import os
from typing import Optional
from supabase import create_client, Client

from app.models.analytics import (
    KPISummary,
    TrendData,
    GeoData,
    PipelineData,
    DecisionData,
)


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
