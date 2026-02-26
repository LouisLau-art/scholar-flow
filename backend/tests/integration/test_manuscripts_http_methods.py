import pytest
from httpx import AsyncClient
from unittest.mock import MagicMock, patch

# === API 方法覆盖测试: Manuscripts ===

def _mock_supabase_with_data(data=None):
    """生成支持链式调用的 Supabase Mock"""
    mock = MagicMock()
    mock.table.return_value = mock
    mock.select.return_value = mock
    mock.order.return_value = mock
    mock.eq.return_value = mock
    mock.or_.return_value = mock
    mock.single.return_value = mock
    mock.insert.return_value = mock
    mock.update.return_value = mock
    resp = MagicMock()
    resp.data = data or []
    mock.execute.return_value = resp
    return mock

@pytest.mark.asyncio
async def test_manuscripts_collection_methods(client: AsyncClient, auth_token: str):
    """验证 /manuscripts GET/POST 可用, 其他方法返回 405"""
    headers = {"Authorization": f"Bearer {auth_token}"}
    mock = _mock_supabase_with_data([])

    with patch("app.lib.api_client.supabase", mock), \
         patch("app.api.v1.manuscripts.supabase", mock):
        get_resp = await client.get("/api/v1/manuscripts", headers=headers)
        assert get_resp.status_code == 200

        post_resp = await client.post(
            "/api/v1/manuscripts",
            json={
                "title": "Test1",
                "abstract": "This is a sufficiently long abstract for validation rules.",
                "author_id": "00000000-0000-0000-0000-000000000000"
            },
            headers=headers,
        )
        assert post_resp.status_code == 200

        for method in ("put", "delete", "patch"):
            resp = await getattr(client, method)("/api/v1/manuscripts", headers=headers)
            assert resp.status_code == 405

@pytest.mark.asyncio
async def test_manuscripts_upload_methods(client: AsyncClient, auth_token: str):
    """验证 /manuscripts/upload 仅支持 POST"""
    headers = {"Authorization": f"Bearer {auth_token}"}
    mock = _mock_supabase_with_data([])

    with patch("app.lib.api_client.supabase", mock), \
         patch("app.api.v1.manuscripts.supabase", mock):
        get_resp = await client.get("/api/v1/manuscripts/upload", headers=headers)
        assert get_resp.status_code == 405

        # 仅验证方法不合法, 这里不做真实文件上传
        post_resp = await client.post("/api/v1/manuscripts/upload", headers=headers)
        assert post_resp.status_code in (400, 422)

@pytest.mark.asyncio
async def test_manuscripts_search_methods(client: AsyncClient, auth_token: str):
    """验证 /manuscripts/search 仅支持 GET"""
    headers = {"Authorization": f"Bearer {auth_token}"}
    mock = _mock_supabase_with_data([])

    with patch("app.lib.api_client.supabase", mock), \
         patch("app.api.v1.manuscripts.supabase", mock):
        get_resp = await client.get("/api/v1/manuscripts/search?q=AI", headers=headers)
        assert get_resp.status_code == 200

        post_resp = await client.post("/api/v1/manuscripts/search", headers=headers)
        assert post_resp.status_code == 405
