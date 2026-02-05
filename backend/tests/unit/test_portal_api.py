import pytest
from httpx import AsyncClient
from unittest.mock import MagicMock, patch

@pytest.mark.asyncio
async def test_get_latest_articles_success(client: AsyncClient):
    fake_data = [
        {
            "id": "00000000-0000-0000-0000-000000000001",
            "title": "Test Article",
            "authors": ["Author One"],
            "abstract": "Abstract content",
            "published_at": "2026-02-05T12:00:00Z"
        }
    ]
    
    with patch("app.api.v1.portal.supabase_admin") as mock_supabase:
        mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = fake_data
        
        resp = await client.get("/api/v1/portal/articles/latest")
        
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["title"] == "Test Article"

@pytest.mark.asyncio
async def test_get_latest_articles_limit_validation(client: AsyncClient):
    resp = await client.get("/api/v1/portal/articles/latest?limit=100")
    assert resp.status_code == 422 # ge=1, le=50
