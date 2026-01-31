import pytest
from httpx import AsyncClient, ASGITransport

from main import app


class _StubAnalyticsService:
    async def get_kpi_summary(self):
        return {
            "new_submissions_month": 1,
            "total_pending": 2,
            "avg_first_decision_days": 3.4,
            "yearly_acceptance_rate": 0.12,
            "apc_revenue_month": 0,
            "apc_revenue_year": 0,
        }

    async def get_submission_trends(self):
        return [{"month": "2026-01-01", "submission_count": 1, "acceptance_count": 0}]

    async def get_status_pipeline(self):
        return [{"stage": "submitted", "count": 1}]

    async def get_decision_distribution(self):
        return [{"decision": "accepted", "count": 1}]

    async def get_author_geography(self):
        return [{"country": "US", "submission_count": 1}]


@pytest.mark.asyncio
async def test_analytics_endpoints_success(monkeypatch):
    from app.core import auth as auth_module
    from app.services import analytics_service as analytics_module

    async def _fake_user():
        return {"id": "u", "email": "e@example.com", "roles": ["admin"]}

    app.dependency_overrides[auth_module.get_current_user] = _fake_user
    app.dependency_overrides[analytics_module.get_analytics_service] = lambda: _StubAnalyticsService()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get("/api/v1/analytics/summary")
        assert res.status_code == 200
        assert res.json()["kpi"]["total_pending"] == 2

        res = await ac.get("/api/v1/analytics/trends")
        assert res.status_code == 200
        body = res.json()
        assert body["trends"][0]["submission_count"] == 1
        assert body["pipeline"][0]["stage"] == "submitted"

        res = await ac.get("/api/v1/analytics/geo")
        assert res.status_code == 200
        assert res.json()["countries"][0]["country"] == "US"

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_analytics_export_xlsx_and_csv(monkeypatch):
    from app.core import auth as auth_module
    from app.services import analytics_service as analytics_module
    from app.core import export_service as export_module
    import io

    async def _fake_user():
        return {"id": "u", "email": "e@example.com", "roles": ["admin"]}

    class _StubExportService:
        def __init__(self, _svc):
            pass

        async def generate_xlsx(self):
            return io.BytesIO(b"xlsx")

        async def generate_csv(self):
            return io.BytesIO(b"csv")

    app.dependency_overrides[auth_module.get_current_user] = _fake_user
    app.dependency_overrides[analytics_module.get_analytics_service] = lambda: _StubAnalyticsService()
    monkeypatch.setattr(export_module, "ExportService", _StubExportService)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get("/api/v1/analytics/export?format=xlsx")
        assert res.status_code == 200
        assert res.headers["content-disposition"].endswith("analytics_report.xlsx")

        res = await ac.get("/api/v1/analytics/export?format=csv")
        assert res.status_code == 200
        assert res.headers["content-disposition"].endswith("analytics_report.csv")

    app.dependency_overrides.clear()
