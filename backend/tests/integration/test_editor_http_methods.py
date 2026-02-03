import pytest
from httpx import AsyncClient
from unittest.mock import MagicMock, patch

# === API 方法覆盖测试: Editor ===

class _MockResponse:
    def __init__(self, data):
        self.data = data
        self.error = None


class _SupabaseMock:
    """
    生成支持链式调用的 Supabase Mock

    中文注释:
    - editor.py 里会对 .single().execute() 期待 dict（response.data 为 dict）
    - 其他 execute() 多为 list（response.data 为 list）
    """

    def __init__(self, *, list_data=None, single_data=None):
        self._list_data = list_data or []
        self._single_data = single_data or {}
        self._next_single = False

    def table(self, *_args, **_kwargs):
        return self

    def select(self, *_args, **_kwargs):
        return self

    def order(self, *_args, **_kwargs):
        return self

    def eq(self, *_args, **_kwargs):
        return self

    def in_(self, *_args, **_kwargs):
        return self

    def or_(self, *_args, **_kwargs):
        return self

    def limit(self, *_args, **_kwargs):
        return self

    def update(self, *_args, **_kwargs):
        return self

    def upsert(self, *_args, **_kwargs):
        return self

    def insert(self, *_args, **_kwargs):
        return self

    def delete(self, *_args, **_kwargs):
        return self

    def single(self, *_args, **_kwargs):
        self._next_single = True
        return self

    def execute(self, *_args, **_kwargs):
        if self._next_single:
            self._next_single = False
            return _MockResponse(self._single_data)
        return _MockResponse(self._list_data)

@pytest.mark.asyncio
async def test_editor_pipeline_methods(client: AsyncClient, auth_token: str, monkeypatch):
    """验证 /editor/pipeline 仅支持 GET"""
    monkeypatch.setenv("ADMIN_EMAILS", "test@example.com")
    headers = {"Authorization": f"Bearer {auth_token}"}
    mock = _SupabaseMock(list_data=[], single_data={})

    with patch("app.lib.api_client.supabase", mock), \
         patch("app.lib.api_client.supabase_admin", mock), \
         patch("app.api.v1.editor.supabase", mock), \
         patch("app.api.v1.editor.supabase_admin", mock):
        get_resp = await client.get("/api/v1/editor/pipeline", headers=headers)
        assert get_resp.status_code == 200

        post_resp = await client.post("/api/v1/editor/pipeline", headers=headers)
        assert post_resp.status_code == 405

@pytest.mark.asyncio
async def test_editor_available_reviewers_methods(client: AsyncClient, auth_token: str, monkeypatch):
    """验证 /editor/available-reviewers 仅支持 GET"""
    monkeypatch.setenv("ADMIN_EMAILS", "test@example.com")
    headers = {"Authorization": f"Bearer {auth_token}"}
    mock = _SupabaseMock(list_data=[], single_data={})

    with patch("app.lib.api_client.supabase", mock), \
         patch("app.lib.api_client.supabase_admin", mock), \
         patch("app.api.v1.editor.supabase", mock), \
         patch("app.api.v1.editor.supabase_admin", mock):
        get_resp = await client.get("/api/v1/editor/available-reviewers", headers=headers)
        assert get_resp.status_code == 200

        post_resp = await client.post("/api/v1/editor/available-reviewers", headers=headers)
        assert post_resp.status_code == 405

@pytest.mark.asyncio
async def test_editor_decision_methods(client: AsyncClient, auth_token: str, monkeypatch):
    """验证 /editor/decision 仅支持 POST"""
    monkeypatch.setenv("ADMIN_EMAILS", "test@example.com")
    headers = {"Authorization": f"Bearer {auth_token}"}
    mock = _SupabaseMock(
        list_data=[{"id": "decision-1"}],
        single_data={"author_id": "00000000-0000-0000-0000-000000000000", "title": "Test"},
    )

    with patch("app.lib.api_client.supabase", mock), \
         patch("app.lib.api_client.supabase_admin", mock), \
         patch("app.api.v1.editor.supabase", mock), \
         patch("app.api.v1.editor.supabase_admin", mock):
        get_resp = await client.get("/api/v1/editor/decision", headers=headers)
        assert get_resp.status_code == 405

        post_resp = await client.post(
            "/api/v1/editor/decision",
            json={
                "manuscript_id": "00000000-0000-0000-0000-000000000000",
                "decision": "accept",
                "apc_amount": 1500,
            },
            headers=headers,
        )
        assert post_resp.status_code == 200


@pytest.mark.asyncio
async def test_editor_publish_methods(client: AsyncClient, auth_token: str, monkeypatch):
    """验证 /editor/publish 仅支持 POST，且需要 editor/admin 角色"""
    monkeypatch.setenv("ADMIN_EMAILS", "test@example.com")
    headers = {"Authorization": f"Bearer {auth_token}"}
    mock = _SupabaseMock(
        list_data=[{"id": "m-1", "status": "published"}],
        single_data={"id": "m-1", "status": "approved"},
    )

    with patch("app.lib.api_client.supabase", mock), \
         patch("app.lib.api_client.supabase_admin", mock), \
         patch("app.api.v1.editor.supabase", mock), \
         patch("app.api.v1.editor.supabase_admin", mock), \
         patch("app.services.post_acceptance_service.supabase_admin", mock):
        get_resp = await client.get("/api/v1/editor/publish", headers=headers)
        assert get_resp.status_code == 405

        post_resp = await client.post(
            "/api/v1/editor/publish",
            json={"manuscript_id": "00000000-0000-0000-0000-000000000000"},
            headers=headers,
        )
        assert post_resp.status_code == 200
