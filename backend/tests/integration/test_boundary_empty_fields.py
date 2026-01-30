import pytest
from httpx import AsyncClient

# === 边界条件: 空值 ===

@pytest.mark.asyncio
async def test_create_manuscript_with_null_fields(client: AsyncClient, auth_token: str):
    """验证空字段返回 422"""
    response = await client.post(
        "/api/v1/manuscripts",
        json={
            "title": None,
            "abstract": None,
            "author_id": "00000000-0000-0000-0000-000000000000",
        },
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert response.status_code == 422
