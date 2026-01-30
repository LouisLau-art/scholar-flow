import pytest
from httpx import AsyncClient
from unittest.mock import MagicMock, patch

# === API 方法覆盖测试: Editor ===

def _mock_supabase_with_data(data=None):
    """生成支持链式调用的 Supabase Mock"""
    mock = MagicMock()
    mock.table.return_value = mock
    mock.select.return_value = mock
    mock.order.return_value = mock
    mock.eq.return_value = mock
    mock.update.return_value = mock
    # editor.py 中既有 tuple 返回也有 response.data 访问，统一提供 data 属性
    response = MagicMock()
    response.data = data or []
    response.error = None
    mock.execute.return_value = response
    return mock

@pytest.mark.asyncio
async def test_editor_pipeline_methods(client: AsyncClient, auth_token: str, monkeypatch):
    """验证 /editor/pipeline 仅支持 GET"""
    monkeypatch.setenv("ADMIN_EMAILS", "test@example.com")
    headers = {"Authorization": f"Bearer {auth_token}"}
    mock = _mock_supabase_with_data([])

    with patch("app.lib.api_client.supabase", mock), \
         patch("app.api.v1.editor.supabase", mock):
        get_resp = await client.get("/api/v1/editor/pipeline", headers=headers)
        assert get_resp.status_code == 200

        post_resp = await client.post("/api/v1/editor/pipeline", headers=headers)
        assert post_resp.status_code == 405

@pytest.mark.asyncio
async def test_editor_available_reviewers_methods(client: AsyncClient, auth_token: str, monkeypatch):
    """验证 /editor/available-reviewers 仅支持 GET"""
    monkeypatch.setenv("ADMIN_EMAILS", "test@example.com")
    headers = {"Authorization": f"Bearer {auth_token}"}
    mock = _mock_supabase_with_data([])

    with patch("app.lib.api_client.supabase", mock), \
         patch("app.api.v1.editor.supabase", mock):
        get_resp = await client.get("/api/v1/editor/available-reviewers", headers=headers)
        assert get_resp.status_code == 200

        post_resp = await client.post("/api/v1/editor/available-reviewers", headers=headers)
        assert post_resp.status_code == 405

@pytest.mark.asyncio
async def test_editor_decision_methods(client: AsyncClient, auth_token: str, monkeypatch):
    """验证 /editor/decision 仅支持 POST"""
    monkeypatch.setenv("ADMIN_EMAILS", "test@example.com")
    headers = {"Authorization": f"Bearer {auth_token}"}
    mock = _mock_supabase_with_data([{"id": "decision-1"}])

    with patch("app.lib.api_client.supabase", mock), \
         patch("app.api.v1.editor.supabase", mock):
        get_resp = await client.get("/api/v1/editor/decision", headers=headers)
        assert get_resp.status_code == 405

        post_resp = await client.post(
            "/api/v1/editor/decision",
            json={"manuscript_id": "00000000-0000-0000-0000-000000000000", "decision": "accept"},
            headers=headers,
        )
        assert post_resp.status_code == 200


@pytest.mark.asyncio
async def test_editor_publish_methods(client: AsyncClient, auth_token: str, monkeypatch):
    """验证 /editor/publish 仅支持 POST，且需要 editor/admin 角色"""
    monkeypatch.setenv("ADMIN_EMAILS", "test@example.com")
    headers = {"Authorization": f"Bearer {auth_token}"}
    mock = _mock_supabase_with_data([{"id": "m-1", "status": "published"}])

    with patch("app.lib.api_client.supabase", mock), \
         patch("app.api.v1.editor.supabase", mock):
        get_resp = await client.get("/api/v1/editor/publish", headers=headers)
        assert get_resp.status_code == 405

        post_resp = await client.post(
            "/api/v1/editor/publish",
            json={"manuscript_id": "00000000-0000-0000-0000-000000000000"},
            headers=headers,
        )
        assert post_resp.status_code == 200
