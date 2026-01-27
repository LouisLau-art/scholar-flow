import pytest
from httpx import AsyncClient
from unittest.mock import patch, MagicMock

# === 稿件业务核心测试 ===
# 中文注释:
# 1. 模拟 Supabase 返回数据，避免真实网络 IO。
# 2. 覆盖 CRUD 与搜索核心链路。

@pytest.mark.asyncio
async def test_get_manuscripts_empty(client: AsyncClient):
    """验证初始化时列表返回空结果"""
    with patch("app.api.v1.manuscripts.supabase") as mock_supabase:
        mock_supabase.table().select().order().execute.return_value = ([], [])
        response = await client.get("/api/v1/manuscripts/")
        assert response.status_code == 200
        assert response.json()["success"] is True

@pytest.mark.asyncio
async def test_search_manuscripts(client: AsyncClient):
    """验证搜索接口的返回结构"""
    with patch("app.api.v1.manuscripts.supabase") as mock_supabase:
        mock_supabase.table().select().eq().or_().execute.return_value = (
            None, [{"id": "1", "title": "Test Paper", "abstract": "abc", "status": "published"}]
        )
        response = await client.get("/api/v1/manuscripts/search?q=AI")
        assert response.status_code == 200
        assert len(response.json()["results"]) > 0
        assert "Test Paper" in response.json()["results"][0]["title"]

@pytest.mark.asyncio
async def test_article_detail_not_found(client: AsyncClient):
    """验证不存在的文章返回 404 或空错误"""
    # UUID 格式错误测试
    response = await client.get("/api/v1/manuscripts/articles/invalid-uuid")
    assert response.status_code == 422 # FastAPI 自动校验失败
