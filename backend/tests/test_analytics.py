"""
Analytics API 单元测试
功能: 测试分析仪表盘 API 端点

中文注释:
- 测试 KPI 汇总、趋势、地理分布、导出端点
- 使用 Mock 模拟 Supabase 响应
"""

import pytest
from unittest.mock import MagicMock, patch
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock

from app.models.analytics import (
    PipelineData,
    DecisionData,
    GeoData,
    KPISummary,
    SLAAlertItem,
    StageDurationItem,
    TrendData,
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

    def test_stage_duration_item_valid(self):
        item = StageDurationItem(stage="decision", avg_days=5.2, sample_size=12)
        assert item.stage == "decision"
        assert item.sample_size == 12

    def test_sla_alert_item_valid(self):
        item = SLAAlertItem(
            manuscript_id="m-1",
            title="Test Manuscript",
            status="under_review",
            overdue_tasks_count=2,
            max_overdue_days=4.5,
            severity="medium",
        )
        assert item.manuscript_id == "m-1"
        assert item.severity == "medium"


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

    @pytest.mark.asyncio
    async def test_get_editor_efficiency_ranking(self, mock_supabase_client):
        from app.services.analytics_service import AnalyticsService

        mock_response = MagicMock()
        mock_response.data = [
            {
                "editor_id": "e-1",
                "editor_name": "ME A",
                "editor_email": "me-a@example.com",
                "handled_count": 18,
                "avg_first_decision_days": 6.4,
            }
        ]
        mock_supabase_client.rpc.return_value.execute.return_value = mock_response

        service = AnalyticsService(supabase_client=mock_supabase_client)
        rows = await service.get_editor_efficiency_ranking(limit=5, journal_ids=["j-1"])

        assert len(rows) == 1
        assert rows[0].editor_id == "e-1"
        assert rows[0].handled_count == 18
        mock_supabase_client.rpc.assert_called_with(
            "get_editor_efficiency_ranking",
            {"limit_count": 5, "journal_ids": ["j-1"]},
        )

    @pytest.mark.asyncio
    async def test_get_stage_duration_breakdown(self, mock_supabase_client):
        from app.services.analytics_service import AnalyticsService

        mock_response = MagicMock()
        mock_response.data = [
            {"stage": "pre_check", "avg_days": 1.8, "sample_size": 20},
            {"stage": "under_review", "avg_days": 12.3, "sample_size": 15},
            {"stage": "decision", "avg_days": 3.5, "sample_size": 11},
            {"stage": "production", "avg_days": 6.0, "sample_size": 6},
        ]
        mock_supabase_client.rpc.return_value.execute.return_value = mock_response

        service = AnalyticsService(supabase_client=mock_supabase_client)
        rows = await service.get_stage_duration_breakdown(journal_ids=["j-2"])

        assert len(rows) == 4
        assert rows[0].stage == "pre_check"
        assert rows[2].avg_days == 3.5
        mock_supabase_client.rpc.assert_called_with(
            "get_stage_duration_breakdown",
            {"journal_ids": ["j-2"]},
        )

    @pytest.mark.asyncio
    async def test_get_sla_alerts_with_severity(self, mock_supabase_client):
        from app.services.analytics_service import AnalyticsService

        mock_response = MagicMock()
        mock_response.data = [
            {
                "manuscript_id": "m-low",
                "title": "Low",
                "status": "under_review",
                "overdue_tasks_count": 1,
                "max_overdue_days": 1.2,
            },
            {
                "manuscript_id": "m-high",
                "title": "High",
                "status": "decision",
                "overdue_tasks_count": 3,
                "max_overdue_days": 8.0,
            },
        ]
        mock_supabase_client.rpc.return_value.execute.return_value = mock_response

        service = AnalyticsService(supabase_client=mock_supabase_client)
        rows = await service.get_sla_alerts(limit=10, journal_ids=None)

        assert len(rows) == 2
        assert rows[0].severity == "low"
        assert rows[1].severity == "high"
        mock_supabase_client.rpc.assert_called_with(
            "get_sla_overdue_manuscripts",
            {"limit_count": 10, "journal_ids": None},
        )

    @pytest.mark.asyncio
    async def test_missing_management_rpc_degrades_to_empty(self, mock_supabase_client):
        from app.services.analytics_service import AnalyticsService

        mock_supabase_client.rpc.side_effect = RuntimeError(
            'function public.get_stage_duration_breakdown does not exist'
        )
        service = AnalyticsService(supabase_client=mock_supabase_client)

        rows = await service.get_stage_duration_breakdown()
        assert rows == []


class TestAnalyticsAPI:
    """测试 Analytics API 端点"""

    @pytest.fixture
    def mock_auth(self):
        """模拟认证"""
        with patch("app.core.auth.get_current_user") as mock:
            mock.return_value = {
                "id": "test-user-id",
                "email": "editor@test.com",
                "roles": ["managing_editor"],
            }
            yield mock

    @pytest.fixture
    def mock_analytics_service(self):
        """模拟 AnalyticsService"""
        with patch("app.services.analytics_service.get_analytics_service") as mock:
            service = MagicMock()
            mock.return_value = service
            yield service

    def test_management_endpoint_requires_role(self):
        from app.api.v1.analytics import router
        from app.core.auth import get_current_user
        from app.services.analytics_service import get_analytics_service

        app = FastAPI()
        app.include_router(router, prefix="/api/v1")
        app.dependency_overrides[get_current_user] = lambda: {
            "id": "u-author",
            "email": "author@example.com",
            "roles": ["author"],
        }
        app.dependency_overrides[get_analytics_service] = lambda: MagicMock()

        client = TestClient(app)
        resp = client.get("/api/v1/analytics/management")
        assert resp.status_code == 403
        assert "Insufficient role" in str(resp.json().get("detail", ""))

    def test_management_endpoint_returns_payload(self):
        from app.api.v1.analytics import router
        from app.core.auth import get_current_user
        from app.services.analytics_service import get_analytics_service

        app = FastAPI()
        app.include_router(router, prefix="/api/v1")

        fake_service = MagicMock()
        fake_service.get_editor_efficiency_ranking = AsyncMock(
            return_value=[
                {
                    "editor_id": "e1",
                    "editor_name": "ME A",
                    "editor_email": "me-a@example.com",
                    "handled_count": 12,
                    "avg_first_decision_days": 5.4,
                }
            ]
        )
        fake_service.get_stage_duration_breakdown = AsyncMock(
            return_value=[
                {"stage": "pre_check", "avg_days": 2.1, "sample_size": 8},
                {"stage": "under_review", "avg_days": 9.5, "sample_size": 8},
                {"stage": "decision", "avg_days": 3.0, "sample_size": 8},
                {"stage": "production", "avg_days": 6.2, "sample_size": 4},
            ]
        )
        fake_service.get_sla_alerts = AsyncMock(
            return_value=[
                {
                    "manuscript_id": "m1",
                    "title": "M1",
                    "status": "under_review",
                    "journal_id": "j1",
                    "journal_title": "Journal A",
                    "editor_id": "e1",
                    "editor_name": "ME A",
                    "owner_id": None,
                    "owner_name": None,
                    "overdue_tasks_count": 2,
                    "max_overdue_days": 4.2,
                    "earliest_due_at": None,
                    "severity": "medium",
                }
            ]
        )

        app.dependency_overrides[get_current_user] = lambda: {
            "id": "u-me",
            "email": "me@example.com",
            "roles": ["managing_editor"],
        }
        app.dependency_overrides[get_analytics_service] = lambda: fake_service

        client = TestClient(app)
        resp = client.get("/api/v1/analytics/management?ranking_limit=5&sla_limit=10")
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert len(body["editor_ranking"]) == 1
        assert len(body["stage_durations"]) == 4
        assert len(body["sla_alerts"]) == 1
        fake_service.get_editor_efficiency_ranking.assert_awaited_once_with(
            limit=5,
            journal_ids=None,
        )
        fake_service.get_sla_alerts.assert_awaited_once_with(
            limit=10,
            journal_ids=None,
        )
