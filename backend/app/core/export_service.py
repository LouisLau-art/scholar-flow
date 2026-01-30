"""
Export Service - 导出服务
功能: 使用 Pandas 生成 XLSX 和 CSV 格式的分析报告

中文注释:
- 聚合 KPI、趋势、地理分布数据
- 生成多 Sheet 的 Excel 报告
- 生成单表 CSV 报告
"""

import io
from datetime import datetime
from typing import TYPE_CHECKING

import pandas as pd

if TYPE_CHECKING:
    from app.services.analytics_service import AnalyticsService


class ExportService:
    """
    分析报告导出服务
    """

    def __init__(self, analytics_service: "AnalyticsService"):
        """
        初始化导出服务

        中文注释: 依赖 AnalyticsService 获取数据
        """
        self.analytics_service = analytics_service

    async def generate_xlsx(self) -> io.BytesIO:
        """
        生成 XLSX 格式报告

        中文注释:
        - 多 Sheet 结构: KPI Summary, Trends, Geo Distribution
        - 使用 openpyxl 引擎
        """
        output = io.BytesIO()

        # 获取所有数据
        kpi = await self.analytics_service.get_kpi_summary()
        trends = await self.analytics_service.get_submission_trends()
        geo = await self.analytics_service.get_author_geography()
        pipeline = await self.analytics_service.get_status_pipeline()

        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            # Sheet 1: KPI Summary
            kpi_df = pd.DataFrame(
                [
                    {
                        "指标": "本月新投稿",
                        "数值": kpi.new_submissions_month,
                    },
                    {
                        "指标": "待处理稿件",
                        "数值": kpi.total_pending,
                    },
                    {
                        "指标": "平均首次决定时间（天）",
                        "数值": round(kpi.avg_first_decision_days, 1),
                    },
                    {
                        "指标": "年度接受率",
                        "数值": f"{kpi.yearly_acceptance_rate * 100:.1f}%",
                    },
                    {
                        "指标": "本月 APC 收入",
                        "数值": f"${kpi.apc_revenue_month:,.2f}",
                    },
                    {
                        "指标": "年度 APC 收入",
                        "数值": f"${kpi.apc_revenue_year:,.2f}",
                    },
                ]
            )
            kpi_df.to_excel(writer, sheet_name="KPI Summary", index=False)

            # Sheet 2: Submission Trends
            if trends:
                trends_df = pd.DataFrame(
                    [
                        {
                            "月份": t.month.isoformat()
                            if hasattr(t.month, "isoformat")
                            else str(t.month),
                            "投稿数": t.submission_count,
                            "接受数": t.acceptance_count,
                        }
                        for t in trends
                    ]
                )
                trends_df.to_excel(writer, sheet_name="Trends", index=False)

            # Sheet 3: Status Pipeline
            if pipeline:
                pipeline_df = pd.DataFrame(
                    [
                        {
                            "状态": p.stage,
                            "数量": p.count,
                        }
                        for p in pipeline
                    ]
                )
                pipeline_df.to_excel(writer, sheet_name="Pipeline", index=False)

            # Sheet 4: Geo Distribution
            if geo:
                geo_df = pd.DataFrame(
                    [
                        {
                            "国家": g.country,
                            "投稿数": g.submission_count,
                        }
                        for g in geo
                    ]
                )
                geo_df.to_excel(writer, sheet_name="Geo Distribution", index=False)

            # Sheet 5: Report Info
            info_df = pd.DataFrame(
                [
                    {
                        "报告生成时间": datetime.now().isoformat(),
                        "数据范围": "过去 12 个月",
                    }
                ]
            )
            info_df.to_excel(writer, sheet_name="Report Info", index=False)

        output.seek(0)
        return output

    async def generate_csv(self) -> io.BytesIO:
        """
        生成 CSV 格式报告

        中文注释:
        - 单表结构，包含 KPI 汇总
        - UTF-8 编码
        """
        output = io.BytesIO()

        # 获取 KPI 数据
        kpi = await self.analytics_service.get_kpi_summary()

        # 构建 DataFrame
        df = pd.DataFrame(
            [
                {
                    "指标": "本月新投稿",
                    "数值": kpi.new_submissions_month,
                },
                {
                    "指标": "待处理稿件",
                    "数值": kpi.total_pending,
                },
                {
                    "指标": "平均首次决定时间（天）",
                    "数值": round(kpi.avg_first_decision_days, 1),
                },
                {
                    "指标": "年度接受率",
                    "数值": f"{kpi.yearly_acceptance_rate * 100:.1f}%",
                },
                {
                    "指标": "本月 APC 收入",
                    "数值": f"${kpi.apc_revenue_month:,.2f}",
                },
                {
                    "指标": "年度 APC 收入",
                    "数值": f"${kpi.apc_revenue_year:,.2f}",
                },
            ]
        )

        # 写入 CSV
        csv_content = df.to_csv(index=False)
        output.write(csv_content.encode("utf-8"))
        output.seek(0)

        return output
