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
    resp.error = None
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


@pytest.mark.asyncio
async def test_reviewer_workspace_session_ok(client: AsyncClient, auth_token: str, monkeypatch):
    monkeypatch.setenv("ADMIN_EMAILS", "test@example.com")
    headers = {"Authorization": f"Bearer {auth_token}"}

    assignment_id = "11111111-1111-1111-1111-111111111111"
    mock = _mock_supabase_with_data(
        {
            "id": assignment_id,
            "reviewer_id": "00000000-0000-0000-0000-000000000000",
            "manuscript_id": "22222222-2222-2222-2222-222222222222",
            "status": "pending",
        }
    )
    mock.single.return_value = mock

    with patch("app.api.v1.reviews.supabase_admin", mock), patch(
        "app.api.v1.reviews.create_magic_link_jwt", return_value="mock-token"
    ):
        resp = await client.post(
            f"/api/v1/reviewer/assignments/{assignment_id}/session",
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json().get("success") is True
        assert "sf_review_magic=" in (resp.headers.get("set-cookie") or "")


@pytest.mark.asyncio
async def test_reviewer_workspace_session_forbidden_on_mismatch(client: AsyncClient, auth_token: str, monkeypatch):
    monkeypatch.setenv("ADMIN_EMAILS", "test@example.com")
    headers = {"Authorization": f"Bearer {auth_token}"}

    assignment_id = "11111111-1111-1111-1111-111111111111"
    mock = _mock_supabase_with_data(
        {
            "id": assignment_id,
            "reviewer_id": "99999999-9999-9999-9999-999999999999",
            "manuscript_id": "22222222-2222-2222-2222-222222222222",
            "status": "pending",
        }
    )
    mock.single.return_value = mock

    with patch("app.api.v1.reviews.supabase_admin", mock):
        resp = await client.post(
            f"/api/v1/reviewer/assignments/{assignment_id}/session",
            headers=headers,
        )
        assert resp.status_code == 403
