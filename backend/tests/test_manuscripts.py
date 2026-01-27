import pytest
from httpx import AsyncClient
from unittest.mock import patch, MagicMock

# === 稿件业务核心测试 (真实行为模拟版) ===

def get_full_mock(data_to_return):
    mock = MagicMock()
    # 模拟链式调用返回自己
    mock.table.return_value = mock
    mock.select.return_value = mock
    mock.order.return_value = mock
    mock.eq.return_value = mock
    mock.or_.return_value = mock
    mock.single.return_value = mock
    
    # 模拟 execute() 返回一个带 data 属性的对象
    mock_response = MagicMock()
    mock_response.data = data_to_return
    mock.execute.return_value = mock_response
    return mock

@pytest.mark.asyncio
async def test_get_manuscripts_empty(client: AsyncClient):
    """验证列表接口返回成功"""
    mock = get_full_mock([])
    with patch("app.lib.api_client.supabase", mock), \
         patch("app.api.v1.manuscripts.supabase", mock):
        response = await client.get("/api/v1/manuscripts")
        assert response.status_code == 200
        assert response.json()["success"] is True

@pytest.mark.asyncio
async def test_search_manuscripts(client: AsyncClient):
    """验证搜索接口的返回结构"""
    mock = get_full_mock([{"id": "1", "title": "Test Paper"}])
    with patch("app.lib.api_client.supabase", mock), \
         patch("app.api.v1.manuscripts.supabase", mock):
        response = await client.get("/api/v1/manuscripts/search?q=AI")
        assert response.status_code == 200
        assert "results" in response.json()
        assert len(response.json()["results"]) > 0
