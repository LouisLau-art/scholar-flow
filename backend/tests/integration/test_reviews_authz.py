import pytest
from httpx import AsyncClient
from unittest.mock import MagicMock, patch


def _mock_supabase_with_data(data=None):
    mock = MagicMock()
    mock.table.return_value = mock
    mock.select.return_value = mock
    mock.eq.return_value = mock
    resp = MagicMock()
    resp.data = data or []
    mock.execute.return_value = resp
    return mock


@pytest.mark.asyncio
async def test_my_tasks_forbidden_for_other_user(client: AsyncClient, auth_token: str, monkeypatch):
    monkeypatch.setenv("ADMIN_EMAILS", "test@example.com")
    headers = {"Authorization": f"Bearer {auth_token}"}
    mock = _mock_supabase_with_data([])

    with patch("app.api.v1.reviews.supabase", mock), patch("app.lib.api_client.supabase", mock):
        resp = await client.get(
            "/api/v1/reviews/my-tasks?user_id=11111111-1111-1111-1111-111111111111",
            headers=headers,
        )
        assert resp.status_code == 403


@pytest.mark.asyncio
async def test_my_tasks_ok_for_self(client: AsyncClient, auth_token: str, monkeypatch):
    monkeypatch.setenv("ADMIN_EMAILS", "test@example.com")
    headers = {"Authorization": f"Bearer {auth_token}"}
    mock = _mock_supabase_with_data([{"id": "a-1"}])

    with patch("app.api.v1.reviews.supabase", mock), patch("app.lib.api_client.supabase", mock):
        resp = await client.get(
            "/api/v1/reviews/my-tasks?user_id=00000000-0000-0000-0000-000000000000",
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json().get("success") is True

