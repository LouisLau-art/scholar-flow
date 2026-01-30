"""
Analytics 数据模型 (Pydantic v2)
功能: 定义分析仪表盘所需的数据结构

中文注释:
- KPISummary: 核心 KPI 指标，对应 get_journal_kpis() RPC 返回
- TrendData: 投稿趋势数据，对应 view_submission_trends 视图
- GeoData: 地理分布数据，对应 get_author_geography() RPC 返回
- PipelineData: 状态流水线数据，对应 view_status_pipeline 视图
- DecisionData: 决定分布数据，对应 view_decision_distribution 视图
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import date


class KPISummary(BaseModel):
    """
    核心 KPI 指标汇总
    用于仪表盘顶部的 4 个 KPI 卡片
    """

    new_submissions_month: int = Field(..., ge=0, description="本月新投稿数")
    total_pending: int = Field(..., ge=0, description="待处理稿件总数")
    avg_first_decision_days: float = Field(
        ..., ge=0, description="平均首次决定时间（天）"
    )
    yearly_acceptance_rate: float = Field(
        ..., ge=0, le=1, description="年度接受率（0-1）"
    )
    apc_revenue_month: float = Field(..., ge=0, description="本月 APC 收入（USD）")
    apc_revenue_year: float = Field(..., ge=0, description="本年度 APC 收入（USD）")


class TrendData(BaseModel):
    """
    投稿趋势数据点
    用于折线图展示过去 12 个月的投稿和接受趋势
    """

    month: date = Field(..., description="月份（每月第一天）")
    submission_count: int = Field(..., ge=0, description="该月投稿数")
    acceptance_count: int = Field(..., ge=0, description="该月接受数")


class GeoData(BaseModel):
    """
    作者地理分布数据
    用于水平条形图展示 Top 10 国家
    """

    country: str = Field(..., min_length=1, description="国家名称")
    submission_count: int = Field(..., ge=0, description="来自该国的投稿数")


class PipelineData(BaseModel):
    """
    状态流水线数据
    用于漏斗图展示当前活跃稿件状态分布
    """

    stage: str = Field(..., description="状态阶段")
    count: int = Field(..., ge=0, description="处于该阶段的稿件数")


class DecisionData(BaseModel):
    """
    决定分布数据
    用于饼图/环形图展示年度决定分布
    """

    decision: str = Field(..., description="决定类型")
    count: int = Field(..., ge=0, description="该类型的决定数量")


class AnalyticsSummaryResponse(BaseModel):
    """
    GET /api/v1/analytics/summary 响应模型
    """

    kpi: KPISummary


class TrendsResponse(BaseModel):
    """
    GET /api/v1/analytics/trends 响应模型
    """

    trends: list[TrendData]
    pipeline: list[PipelineData]
    decisions: list[DecisionData]


class GeoResponse(BaseModel):
    """
    GET /api/v1/analytics/geo 响应模型
    """

    countries: list[GeoData]
