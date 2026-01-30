import pytest
from httpx import AsyncClient

# === Auth 逻辑与权限测试 ===

@pytest.mark.asyncio
async def test_protected_route_without_token(client: AsyncClient):
    """验证受保护路由在无 Token 时返回 401"""
    # 假设 /api/v1/user/profile 是受保护的
    response = await client.get("/api/v1/user/profile")
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_auth_middleware_token_decoding(client: AsyncClient):
    """验证伪造 Token 会被拦截"""
    headers = {"Authorization": "Bearer invalid-token"}
    response = await client.get("/api/v1/user/profile", headers=headers)
    assert response.status_code == 401
    assert "Token 验证失败" in response.json()["detail"]

@pytest.mark.asyncio
async def test_protected_route_with_expired_token(client: AsyncClient, expired_token: str):
    """验证过期 Token 会被拦截"""
    headers = {"Authorization": f"Bearer {expired_token}"}
    response = await client.get("/api/v1/user/profile", headers=headers)
    assert response.status_code == 401
    assert "Token 验证失败" in response.json()["detail"]
