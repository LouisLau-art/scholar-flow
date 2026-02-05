import pytest
from httpx import AsyncClient
from unittest.mock import MagicMock, patch

@pytest.mark.asyncio
async def test_get_latest_articles_success(client: AsyncClient):
    fake_manuscripts = [
        {
            "id": "00000000-0000-0000-0000-000000000001",
            "title": "Test Article",
            "abstract": "Abstract content",
            "published_at": "2026-02-05T12:00:00Z",
            "author_id": "00000000-0000-0000-0000-000000000010",
        }
    ]
    fake_profiles = [
        {
            "id": "00000000-0000-0000-0000-000000000010",
            "full_name": "Author One",
            "email": "author@example.com",
        }
    ]
    
    with patch("app.api.v1.portal.supabase_admin") as mock_supabase:
        manuscripts_table = MagicMock()
        manuscripts_table.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = (
            fake_manuscripts
        )

        profiles_table = MagicMock()
        profiles_table.select.return_value.in_.return_value.execute.return_value.data = fake_profiles

        def table_side_effect(name: str):
            if name == "manuscripts":
                return manuscripts_table
            if name == "user_profiles":
                return profiles_table
            return MagicMock()

        mock_supabase.table.side_effect = table_side_effect
        
        resp = await client.get("/api/v1/portal/articles/latest")
        
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["title"] == "Test Article"
    assert data[0]["authors"] == ["Author One"]

@pytest.mark.asyncio
async def test_get_latest_articles_limit_validation(client: AsyncClient):
    resp = await client.get("/api/v1/portal/articles/latest?limit=100")
    assert resp.status_code == 422 # ge=1, le=50
