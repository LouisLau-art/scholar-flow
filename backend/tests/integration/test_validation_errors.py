import pytest
from httpx import AsyncClient

# === 参数验证错误测试 ===

@pytest.mark.asyncio
async def test_create_manuscript_title_too_long(client: AsyncClient, auth_token: str):
    """验证标题超长返回 422"""
    response = await client.post(
        "/api/v1/manuscripts",
        json={
            "title": "T" * 501,
            "abstract": "Valid abstract",
            "author_id": "00000000-0000-0000-0000-000000000000",
        },
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert response.status_code == 422

@pytest.mark.asyncio
async def test_create_manuscript_abstract_too_long(client: AsyncClient, auth_token: str):
    """验证摘要超长返回 422"""
    response = await client.post(
        "/api/v1/manuscripts",
        json={
            "title": "Valid Title",
            "abstract": "A" * 5001,
            "author_id": "00000000-0000-0000-0000-000000000000",
        },
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert response.status_code == 422
