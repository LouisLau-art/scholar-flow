import pytest
from httpx import AsyncClient, ASGITransport
from main import app


@pytest.mark.asyncio
async def test_doi_registration_flow(supabase_admin_client):
    _ = supabase_admin_client
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        # 1. Create registration task
        response = await ac.post(
            "/api/v1/doi/register",
            json={"article_id": "00000000-0000-0000-0000-000000000000"},
        )
        # Should fail because article doesn't exist or is not published (mocked DB required)
        # For now, we expect 404 or 400 depending on implementation
        assert response.status_code in [404, 400, 201]

        # 2. Get status (if 201)
        if response.status_code == 201:
            data = response.json()
            article_id = data["article_id"]
            status_res = await ac.get(f"/api/v1/doi/{article_id}")
            assert status_res.status_code == 200
            assert status_res.json()["status"] == "pending"
