"""
Analytics API 单元测试
功能: 测试分析仪表盘 API 端点

中文注释:
- 测试 KPI 汇总、趋势、地理分布、导出端点
- 使用 Mock 模拟 Supabase 响应
"""

import pytest
from unittest.mock import MagicMock, patch

from app.models.analytics import (
    KPISummary,
    TrendData,
    GeoData,
    PipelineData,
    DecisionData,
)


class TestAnalyticsModels:
    """测试 Pydantic 模型"""

    def test_kpi_summary_valid(self):
        """测试 KPISummary 模型验证"""
        kpi = KPISummary(
            new_submissions_month=10,
            total_pending=25,
            avg_first_decision_days=24.5,
            yearly_acceptance_rate=0.18,
            apc_revenue_month=15000.0,
            apc_revenue_year=120000.0,
        )
        assert kpi.new_submissions_month == 10
        assert kpi.yearly_acceptance_rate == 0.18

    def test_kpi_summary_boundary_values(self):
        """测试 KPISummary 边界值"""
        kpi = KPISummary(
            new_submissions_month=0,
            total_pending=0,
            avg_first_decision_days=0,
            yearly_acceptance_rate=0,
            apc_revenue_month=0,
            apc_revenue_year=0,
        )
        assert kpi.new_submissions_month == 0
        assert kpi.yearly_acceptance_rate == 0

    def test_trend_data_valid(self):
        """测试 TrendData 模型"""
        from datetime import date

        trend = TrendData(
            month=date(2026, 1, 1),
            submission_count=15,
            acceptance_count=3,
        )
        assert trend.submission_count == 15

    def test_geo_data_valid(self):
        """测试 GeoData 模型"""
        geo = GeoData(country="China", submission_count=50)
        assert geo.country == "China"

    def test_pipeline_data_valid(self):
        """测试 PipelineData 模型"""
        pipeline = PipelineData(stage="under_review", count=12)
        assert pipeline.stage == "under_review"

    def test_decision_data_valid(self):
        """测试 DecisionData 模型"""
        decision = DecisionData(decision="accepted", count=8)
        assert decision.decision == "accepted"


class TestAnalyticsService:
    """测试 AnalyticsService"""

    @pytest.fixture
    def mock_supabase_client(self):
        """创建模拟的 Supabase 客户端"""
        client = MagicMock()
        return client

    @pytest.mark.asyncio
    async def test_get_kpi_summary(self, mock_supabase_client):
        """测试获取 KPI 汇总"""
        from app.services.analytics_service import AnalyticsService

        # 模拟 RPC 响应
        mock_response = MagicMock()
        mock_response.data = {
            "new_submissions_month": 10,
            "total_pending": 25,
            "avg_first_decision_days": 24.5,
            "yearly_acceptance_rate": 0.18,
            "apc_revenue_month": 15000.0,
            "apc_revenue_year": 120000.0,
        }
        mock_supabase_client.rpc.return_value.execute.return_value = mock_response

        service = AnalyticsService(supabase_client=mock_supabase_client)
        result = await service.get_kpi_summary()

        assert result.new_submissions_month == 10
        assert result.yearly_acceptance_rate == 0.18
        mock_supabase_client.rpc.assert_called_once_with("get_journal_kpis")

    @pytest.mark.asyncio
    async def test_get_kpi_summary_empty(self, mock_supabase_client):
        """测试空数据情况"""
        from app.services.analytics_service import AnalyticsService

        mock_response = MagicMock()
        mock_response.data = None
        mock_supabase_client.rpc.return_value.execute.return_value = mock_response

        service = AnalyticsService(supabase_client=mock_supabase_client)
        result = await service.get_kpi_summary()

        # 应返回默认值
        assert result.new_submissions_month == 0
        assert result.total_pending == 0

    @pytest.mark.asyncio
    async def test_get_submission_trends(self, mock_supabase_client):
        """测试获取投稿趋势"""
        from app.services.analytics_service import AnalyticsService

        mock_response = MagicMock()
        mock_response.data = [
            {"month": "2026-01-01", "submission_count": 10, "acceptance_count": 2},
            {"month": "2025-12-01", "submission_count": 8, "acceptance_count": 1},
        ]
        mock_supabase_client.table.return_value.select.return_value.execute.return_value = mock_response

        service = AnalyticsService(supabase_client=mock_supabase_client)
        result = await service.get_submission_trends()

        assert len(result) == 2
        assert result[0].submission_count == 10

    @pytest.mark.asyncio
    async def test_get_author_geography(self, mock_supabase_client):
        """测试获取地理分布"""
        from app.services.analytics_service import AnalyticsService

        mock_response = MagicMock()
        mock_response.data = [
            {"country": "China", "submission_count": 50},
            {"country": "USA", "submission_count": 30},
        ]
        mock_supabase_client.rpc.return_value.execute.return_value = mock_response

        service = AnalyticsService(supabase_client=mock_supabase_client)
        result = await service.get_author_geography()

        assert len(result) == 2
        assert result[0].country == "China"
        assert result[0].submission_count == 50


class TestAnalyticsAPI:
    """测试 Analytics API 端点"""

    @pytest.fixture
    def mock_auth(self):
        """模拟认证"""
        with patch("app.core.auth.get_current_user") as mock:
            mock.return_value = {
                "id": "test-user-id",
                "email": "editor@test.com",
                "roles": ["editor"],
            }
            yield mock

    @pytest.fixture
    def mock_analytics_service(self):
        """模拟 AnalyticsService"""
        with patch("app.services.analytics_service.get_analytics_service") as mock:
            service = MagicMock()
            mock.return_value = service
            yield service

    # 注意: 完整的 API 测试需要使用 TestClient 并配置 FastAPI app
    # 这里只展示模型和服务层测试
