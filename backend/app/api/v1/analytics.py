"""
Analytics API Router
功能: 提供分析仪表盘的 REST API 端点

中文注释:
- /summary: 返回 KPI 汇总数据
- /trends: 返回投稿趋势、状态流水线、决定分布
- /geo: 返回作者地理分布
- /export: 导出分析报告（XLSX/CSV）

安全要求:
- 所有端点需要 JWT 认证
- 仅限 EIC/ME 角色访问 (RBAC)
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse

from app.models.analytics import (
    AnalyticsSummaryResponse,
    TrendsResponse,
    GeoResponse,
)
from app.services.analytics_service import AnalyticsService, get_analytics_service
from app.core.auth import get_current_user

# 配置日志（用于审计）
logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/analytics",
    tags=["Analytics"],
    responses={401: {"description": "未授权"}, 403: {"description": "权限不足"}},
)


@router.get(
    "/summary",
    response_model=AnalyticsSummaryResponse,
    summary="获取 KPI 汇总",
    description="返回期刊核心 KPI 指标，包括投稿数、待处理数、平均决定时间、接受率、APC 收入",
)
async def get_summary(
    current_user: dict = Depends(get_current_user),
    analytics_service: AnalyticsService = Depends(get_analytics_service),
):
    """
    获取 KPI 汇总数据

    中文注释:
    - 需要认证，仅限编辑角色访问
    - 记录访问日志用于审计
    """
    # 审计日志
    logger.info(
        f"Analytics summary accessed by user {current_user.get('id', 'unknown')} "
        f"(roles: {current_user.get('roles', [])})"
    )

    try:
        kpi = await analytics_service.get_kpi_summary()
        return AnalyticsSummaryResponse(kpi=kpi)
    except Exception as e:
        logger.error(f"Failed to fetch KPI summary: {e}")
        raise HTTPException(status_code=500, detail="获取 KPI 数据失败")


@router.get(
    "/trends",
    response_model=TrendsResponse,
    summary="获取趋势数据",
    description="返回投稿趋势（12个月）、状态流水线、决定分布",
)
async def get_trends(
    current_user: dict = Depends(get_current_user),
    analytics_service: AnalyticsService = Depends(get_analytics_service),
):
    """
    获取趋势和分布数据

    中文注释:
    - 合并多个视图数据，减少前端请求次数
    - 用于趋势折线图、漏斗图、饼图
    """
    logger.info(
        f"Analytics trends accessed by user {current_user.get('id', 'unknown')}"
    )

    try:
        trends = await analytics_service.get_submission_trends()
        pipeline = await analytics_service.get_status_pipeline()
        decisions = await analytics_service.get_decision_distribution()

        return TrendsResponse(
            trends=trends,
            pipeline=pipeline,
            decisions=decisions,
        )
    except Exception as e:
        logger.error(f"Failed to fetch trends data: {e}")
        raise HTTPException(status_code=500, detail="获取趋势数据失败")


@router.get(
    "/geo",
    response_model=GeoResponse,
    summary="获取地理分布",
    description="返回 Top 10 作者国家分布",
)
async def get_geo(
    current_user: dict = Depends(get_current_user),
    analytics_service: AnalyticsService = Depends(get_analytics_service),
):
    """
    获取地理分布数据

    中文注释:
    - 返回 Top 10 国家的投稿数
    - 用于水平条形图
    """
    logger.info(f"Analytics geo accessed by user {current_user.get('id', 'unknown')}")

    try:
        countries = await analytics_service.get_author_geography()
        return GeoResponse(countries=countries)
    except Exception as e:
        logger.error(f"Failed to fetch geo data: {e}")
        raise HTTPException(status_code=500, detail="获取地理数据失败")


@router.get(
    "/export",
    summary="导出分析报告",
    description="下载 XLSX 或 CSV 格式的分析报告",
)
async def export_report(
    format: str = Query("xlsx", regex="^(xlsx|csv)$", description="导出格式"),
    current_user: dict = Depends(get_current_user),
    analytics_service: AnalyticsService = Depends(get_analytics_service),
):
    """
    导出分析报告

    中文注释:
    - 支持 XLSX 和 CSV 两种格式
    - 使用 Pandas 生成报告
    - 报告包含 KPI、趋势、地理分布数据
    """
    logger.info(
        f"Analytics export ({format}) requested by user {current_user.get('id', 'unknown')}"
    )

    try:
        # 动态导入 ExportService（避免启动时依赖 Pandas）
        from app.core.export_service import ExportService

        export_service = ExportService(analytics_service)

        if format == "xlsx":
            file_content = await export_service.generate_xlsx()
            media_type = (
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            filename = "analytics_report.xlsx"
        else:
            file_content = await export_service.generate_csv()
            media_type = "text/csv"
            filename = "analytics_report.csv"

        return StreamingResponse(
            file_content,
            media_type=media_type,
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )
    except Exception as e:
        logger.error(f"Failed to export report: {e}")
        raise HTTPException(status_code=500, detail="导出报告失败")
