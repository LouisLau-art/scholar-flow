import pytest
import asyncio
from httpx import AsyncClient
from unittest.mock import MagicMock, patch

# === 并发请求: 数据一致性 ===

def _mock_supabase_with_data(data=None):
    mock = MagicMock()
    mock.table.return_value = mock
    mock.select.return_value = mock
    mock.order.return_value = mock
    mock.eq.return_value = mock
    response = MagicMock()
    response.data = data or []
    response.error = None
    mock.execute.return_value = response
    return mock

@pytest.mark.asyncio
async def test_concurrent_consistent_list_responses(client: AsyncClient):
    """验证并发读取列表保持一致"""
    dataset = [
        {"id": "m-1", "title": "Paper 1", "status": "submitted"},
        {"id": "m-2", "title": "Paper 2", "status": "under_review"},
    ]
    mock = _mock_supabase_with_data(dataset)

    with patch("app.lib.api_client.supabase", mock), \
         patch("app.api.v1.manuscripts.supabase", mock):
        async def fetch():
            return await client.get("/api/v1/manuscripts")

        results = await asyncio.gather(*[fetch() for _ in range(5)])

        assert all(r.status_code == 200 for r in results)
        assert all(r.json().get("data") == dataset for r in results)
