"""
Analytics 聚合测试
功能: 测试趋势和地理分布数据聚合

中文注释:
- 测试 view_submission_trends 视图查询
- 测试 get_author_geography RPC
- 测试空数据处理
"""

import pytest
from unittest.mock import MagicMock

from app.models.analytics import TrendData, GeoData, PipelineData, DecisionData


class TestTrendAggregation:
    """测试投稿趋势聚合"""

    @pytest.fixture
    def mock_supabase_client(self):
        """创建模拟的 Supabase 客户端"""
        return MagicMock()

    @pytest.mark.asyncio
    async def test_get_submission_trends_with_data(self, mock_supabase_client):
        """测试有数据时的趋势查询"""
        from app.services.analytics_service import AnalyticsService

        mock_response = MagicMock()
        mock_response.data = [
            {"month": "2026-01-01", "submission_count": 15, "acceptance_count": 3},
            {"month": "2025-12-01", "submission_count": 12, "acceptance_count": 2},
            {"month": "2025-11-01", "submission_count": 10, "acceptance_count": 1},
        ]
        mock_supabase_client.table.return_value.select.return_value.execute.return_value = mock_response

        service = AnalyticsService(supabase_client=mock_supabase_client)
        result = await service.get_submission_trends()

        assert len(result) == 3
        assert result[0].submission_count == 15
        assert result[0].acceptance_count == 3

    @pytest.mark.asyncio
    async def test_get_submission_trends_empty(self, mock_supabase_client):
        """测试空数据时的趋势查询"""
        from app.services.analytics_service import AnalyticsService

        mock_response = MagicMock()
        mock_response.data = []
        mock_supabase_client.table.return_value.select.return_value.execute.return_value = mock_response

        service = AnalyticsService(supabase_client=mock_supabase_client)
        result = await service.get_submission_trends()

        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_get_status_pipeline(self, mock_supabase_client):
        """测试状态流水线查询"""
        from app.services.analytics_service import AnalyticsService

        mock_response = MagicMock()
        mock_response.data = [
            {"stage": "submitted", "count": 10},
            {"stage": "under_review", "count": 8},
            {"stage": "revision", "count": 5},
        ]
        mock_supabase_client.table.return_value.select.return_value.execute.return_value = mock_response

        service = AnalyticsService(supabase_client=mock_supabase_client)
        result = await service.get_status_pipeline()

        assert len(result) == 3
        assert result[0].stage == "submitted"
        assert result[0].count == 10

    @pytest.mark.asyncio
    async def test_get_decision_distribution(self, mock_supabase_client):
        """测试决定分布查询"""
        from app.services.analytics_service import AnalyticsService

        mock_response = MagicMock()
        mock_response.data = [
            {"decision": "accepted", "count": 15},
            {"decision": "rejected", "count": 8},
            {"decision": "revision", "count": 12},
        ]
        mock_supabase_client.table.return_value.select.return_value.execute.return_value = mock_response

        service = AnalyticsService(supabase_client=mock_supabase_client)
        result = await service.get_decision_distribution()

        assert len(result) == 3
        assert result[0].decision == "accepted"


class TestGeoAggregation:
    """测试地理分布聚合"""

    @pytest.fixture
    def mock_supabase_client(self):
        """创建模拟的 Supabase 客户端"""
        return MagicMock()

    @pytest.mark.asyncio
    async def test_get_author_geography_with_data(self, mock_supabase_client):
        """测试有数据时的地理分布查询"""
        from app.services.analytics_service import AnalyticsService

        mock_response = MagicMock()
        mock_response.data = [
            {"country": "China", "submission_count": 50},
            {"country": "USA", "submission_count": 30},
            {"country": "UK", "submission_count": 20},
            {"country": "Germany", "submission_count": 15},
            {"country": "Japan", "submission_count": 12},
        ]
        mock_supabase_client.rpc.return_value.execute.return_value = mock_response

        service = AnalyticsService(supabase_client=mock_supabase_client)
        result = await service.get_author_geography()

        assert len(result) == 5
        assert result[0].country == "China"
        assert result[0].submission_count == 50
        mock_supabase_client.rpc.assert_called_once_with("get_author_geography")

    @pytest.mark.asyncio
    async def test_get_author_geography_empty(self, mock_supabase_client):
        """测试无地理数据时"""
        from app.services.analytics_service import AnalyticsService

        mock_response = MagicMock()
        mock_response.data = []
        mock_supabase_client.rpc.return_value.execute.return_value = mock_response

        service = AnalyticsService(supabase_client=mock_supabase_client)
        result = await service.get_author_geography()

        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_get_author_geography_top_10(self, mock_supabase_client):
        """测试地理分布只返回 Top 10"""
        from app.services.analytics_service import AnalyticsService

        # SQL RPC 已限制返回 10 条，这里模拟 10 条数据
        mock_response = MagicMock()
        mock_response.data = [
            {"country": f"Country{i}", "submission_count": 100 - i * 10}
            for i in range(10)
        ]
        mock_supabase_client.rpc.return_value.execute.return_value = mock_response

        service = AnalyticsService(supabase_client=mock_supabase_client)
        result = await service.get_author_geography()

        assert len(result) == 10
        assert result[0].submission_count == 100
        assert result[9].submission_count == 10
