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

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field


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


class EditorEfficiencyItem(BaseModel):
    """
    编辑效率排行项
    """

    editor_id: str = Field(..., description="编辑用户 ID")
    editor_name: str = Field(..., description="编辑姓名（缺失时兜底）")
    editor_email: str | None = Field(None, description="编辑邮箱")
    handled_count: int = Field(..., ge=0, description="已处理稿件数")
    avg_first_decision_days: float = Field(
        ..., ge=0, description="平均首次决定耗时（天）"
    )


class StageDurationItem(BaseModel):
    """
    阶段耗时分解项
    """

    stage: Literal["pre_check", "under_review", "decision", "production"] = Field(
        ..., description="流程阶段"
    )
    avg_days: float = Field(..., ge=0, description="平均耗时（天）")
    sample_size: int = Field(..., ge=0, description="样本量")


class SLAAlertItem(BaseModel):
    """
    超 SLA 稿件预警项
    """

    manuscript_id: str = Field(..., description="稿件 ID")
    title: str = Field(..., description="稿件标题")
    status: str = Field(..., description="当前稿件状态")
    journal_id: str | None = Field(None, description="期刊 ID")
    journal_title: str | None = Field(None, description="期刊标题")
    editor_id: str | None = Field(None, description="编辑 ID")
    editor_name: str | None = Field(None, description="编辑姓名")
    owner_id: str | None = Field(None, description="Owner ID")
    owner_name: str | None = Field(None, description="Owner 姓名")
    overdue_tasks_count: int = Field(..., ge=0, description="逾期任务数")
    max_overdue_days: float = Field(..., ge=0, description="最长逾期天数")
    earliest_due_at: datetime | None = Field(None, description="最早逾期截止时间")
    severity: Literal["low", "medium", "high"] = Field(..., description="风险等级")


class AnalyticsManagementResponse(BaseModel):
    """
    GET /api/v1/analytics/management 响应模型
    """

    editor_ranking: list[EditorEfficiencyItem]
    stage_durations: list[StageDurationItem]
    sla_alerts: list[SLAAlertItem]
