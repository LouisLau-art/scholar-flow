"""
Analytics 导出功能测试
功能: 测试 XLSX/CSV 报告生成

中文注释:
- 测试 ExportService 生成文件
- 验证文件格式和内容
"""

import pytest
from unittest.mock import MagicMock, AsyncMock
from io import BytesIO
from datetime import date

from app.models.analytics import (
    KPISummary,
    TrendData,
    GeoData,
    PipelineData,
)


class TestExportService:
    """测试导出服务"""

    @pytest.fixture
    def mock_analytics_service(self):
        """创建模拟的 AnalyticsService"""
        service = MagicMock()

        # 模拟 KPI 数据
        service.get_kpi_summary = AsyncMock(
            return_value=KPISummary(
                new_submissions_month=10,
                total_pending=25,
                avg_first_decision_days=24.5,
                yearly_acceptance_rate=0.18,
                apc_revenue_month=15000.0,
                apc_revenue_year=120000.0,
            )
        )

        # 模拟趋势数据
        service.get_submission_trends = AsyncMock(
            return_value=[
                TrendData(
                    month=date(2026, 1, 1), submission_count=10, acceptance_count=2
                ),
                TrendData(
                    month=date(2025, 12, 1), submission_count=8, acceptance_count=1
                ),
            ]
        )

        # 模拟地理数据
        service.get_author_geography = AsyncMock(
            return_value=[
                GeoData(country="China", submission_count=50),
                GeoData(country="USA", submission_count=30),
            ]
        )

        # 模拟流水线数据
        service.get_status_pipeline = AsyncMock(
            return_value=[
                PipelineData(stage="submitted", count=10),
                PipelineData(stage="under_review", count=8),
            ]
        )

        return service

    @pytest.mark.asyncio
    async def test_generate_xlsx(self, mock_analytics_service):
        """测试生成 XLSX 文件"""
        from app.core.export_service import ExportService

        export_service = ExportService(mock_analytics_service)
        result = await export_service.generate_xlsx()

        # 验证返回的是 BytesIO 对象
        assert isinstance(result, BytesIO)

        # 验证文件不为空
        result.seek(0, 2)  # 移动到末尾
        file_size = result.tell()
        assert file_size > 0

        # 验证文件头是有效的 XLSX 格式 (PK zip header)
        result.seek(0)
        header = result.read(4)
        assert header == b"PK\x03\x04"

    @pytest.mark.asyncio
    async def test_generate_csv(self, mock_analytics_service):
        """测试生成 CSV 文件"""
        from app.core.export_service import ExportService

        export_service = ExportService(mock_analytics_service)
        result = await export_service.generate_csv()

        # 验证返回的是 BytesIO 对象
        assert isinstance(result, BytesIO)

        # 读取 CSV 内容
        result.seek(0)
        content = result.read().decode("utf-8")

        # 验证包含 KPI 数据
        assert "本月新投稿" in content
        assert "待处理稿件" in content
        assert "10" in content  # new_submissions_month 值

    @pytest.mark.asyncio
    async def test_xlsx_contains_kpi_sheet(self, mock_analytics_service):
        """测试 XLSX 包含 KPI Summary sheet"""
        from app.core.export_service import ExportService
        import pandas as pd

        export_service = ExportService(mock_analytics_service)
        result = await export_service.generate_xlsx()

        # 使用 pandas 读取生成的 Excel 文件
        result.seek(0)

        # 读取所有 sheet 名称
        excel_file = pd.ExcelFile(result)
        sheet_names = excel_file.sheet_names

        assert "KPI Summary" in sheet_names

        # 验证 KPI Summary sheet 内容
        kpi_df = pd.read_excel(excel_file, sheet_name="KPI Summary")
        assert len(kpi_df) == 6  # 6 个 KPI 指标

    @pytest.mark.asyncio
    async def test_xlsx_contains_trends_sheet(self, mock_analytics_service):
        """测试 XLSX 包含 Trends sheet"""
        from app.core.export_service import ExportService
        import pandas as pd

        export_service = ExportService(mock_analytics_service)
        result = await export_service.generate_xlsx()

        result.seek(0)
        excel_file = pd.ExcelFile(result)

        assert "Trends" in excel_file.sheet_names

        trends_df = pd.read_excel(excel_file, sheet_name="Trends")
        assert len(trends_df) == 2  # 2 条趋势数据

    @pytest.mark.asyncio
    async def test_xlsx_contains_geo_sheet(self, mock_analytics_service):
        """测试 XLSX 包含 Geo Distribution sheet"""
        from app.core.export_service import ExportService
        import pandas as pd

        export_service = ExportService(mock_analytics_service)
        result = await export_service.generate_xlsx()

        result.seek(0)
        excel_file = pd.ExcelFile(result)

        assert "Geo Distribution" in excel_file.sheet_names

        geo_df = pd.read_excel(excel_file, sheet_name="Geo Distribution")
        assert len(geo_df) == 2  # 2 个国家

    @pytest.mark.asyncio
    async def test_export_with_empty_data(self, mock_analytics_service):
        """测试空数据时的导出"""
        from app.core.export_service import ExportService

        # 清空趋势和地理数据
        mock_analytics_service.get_submission_trends = AsyncMock(return_value=[])
        mock_analytics_service.get_author_geography = AsyncMock(return_value=[])
        mock_analytics_service.get_status_pipeline = AsyncMock(return_value=[])

        export_service = ExportService(mock_analytics_service)
        result = await export_service.generate_xlsx()

        # 即使数据为空，也应该生成有效的 XLSX 文件
        assert isinstance(result, BytesIO)
        result.seek(0, 2)
        assert result.tell() > 0
