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
async def test_my_history_forbidden_for_other_user(client: AsyncClient, auth_token: str, monkeypatch):
    monkeypatch.setenv("ADMIN_EMAILS", "test@example.com")
    headers = {"Authorization": f"Bearer {auth_token}"}

    resp = await client.get(
        "/api/v1/reviews/my-history?user_id=11111111-1111-1111-1111-111111111111",
        headers=headers,
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_my_history_ok_for_self(client: AsyncClient, auth_token: str, monkeypatch):
    monkeypatch.setenv("ADMIN_EMAILS", "test@example.com")
    headers = {"Authorization": f"Bearer {auth_token}"}

    mock = MagicMock()
    mock.table.return_value = mock
    mock.select.return_value = mock
    mock.eq.return_value = mock
    mock.order.return_value = mock
    mock.limit.return_value = mock
    mock.in_.return_value = mock

    assignments_resp = MagicMock()
    assignments_resp.data = [
        {
            "id": "assign-1",
            "manuscript_id": "ms-1",
            "reviewer_id": "00000000-0000-0000-0000-000000000000",
            "status": "completed",
            "created_at": "2026-03-11T08:00:00+00:00",
            "round_number": 1,
        }
    ]
    manuscripts_resp = MagicMock()
    manuscripts_resp.data = [
        {
            "id": "ms-1",
            "title": "History Manuscript",
            "abstract": "History abstract",
            "status": "decision",
        }
    ]
    reports_resp = MagicMock()
    reports_resp.data = [
        {
            "manuscript_id": "ms-1",
            "reviewer_id": "00000000-0000-0000-0000-000000000000",
            "status": "completed",
            "comments_for_author": "Strong paper",
            "confidential_comments_to_editor": "Minor concerns",
            "attachment_path": None,
            "created_at": "2026-03-11T09:00:00+00:00",
            "updated_at": "2026-03-11T09:00:00+00:00",
        }
    ]
    email_logs_resp = MagicMock()
    email_logs_resp.data = []
    mock.execute.side_effect = [assignments_resp, manuscripts_resp, reports_resp, email_logs_resp]

    with patch("app.api.v1.reviews.supabase_admin", mock):
        resp = await client.get(
            "/api/v1/reviews/my-history?user_id=00000000-0000-0000-0000-000000000000",
            headers=headers,
        )

    assert resp.status_code == 200
    payload = resp.json()
    assert payload.get("success") is True
    assert payload["data"][0]["assignment_state"] == "submitted"
    assert payload["data"][0]["manuscript_title"] == "History Manuscript"
    assert payload["data"][0]["comments_for_author"] == "Strong paper"


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
            "accepted_at": "2026-03-06T00:00:00Z",
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
        assert resp.json()["data"]["redirect_url"] == f"/reviewer/workspace/{assignment_id}"
        assert "sf_review_magic=" in (resp.headers.get("set-cookie") or "")


@pytest.mark.asyncio
async def test_reviewer_workspace_session_redirects_to_invite_when_not_yet_accepted(
    client: AsyncClient, auth_token: str, monkeypatch
):
    monkeypatch.setenv("ADMIN_EMAILS", "test@example.com")
    headers = {"Authorization": f"Bearer {auth_token}"}

    assignment_id = "11111111-1111-1111-1111-111111111111"
    mock = _mock_supabase_with_data(
        {
            "id": assignment_id,
            "reviewer_id": "00000000-0000-0000-0000-000000000000",
            "manuscript_id": "22222222-2222-2222-2222-222222222222",
            "status": "pending",
            "accepted_at": None,
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
        assert resp.json()["data"]["redirect_url"] == f"/review/invite?assignment_id={assignment_id}"


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


@pytest.mark.asyncio
async def test_reviewer_workspace_session_forbidden_when_assignment_cancelled(
    client: AsyncClient, auth_token: str, monkeypatch
):
    monkeypatch.setenv("ADMIN_EMAILS", "test@example.com")
    headers = {"Authorization": f"Bearer {auth_token}"}

    assignment_id = "11111111-1111-1111-1111-111111111112"
    mock = _mock_supabase_with_data(
        {
            "id": assignment_id,
            "reviewer_id": "00000000-0000-0000-0000-000000000000",
            "manuscript_id": "22222222-2222-2222-2222-222222222222",
            "status": "cancelled",
        }
    )
    mock.single.return_value = mock

    with patch("app.api.v1.reviews.supabase_admin", mock):
        resp = await client.post(
            f"/api/v1/reviewer/assignments/{assignment_id}/session",
            headers=headers,
        )
        assert resp.status_code == 403
        assert resp.json()["detail"] == "Invitation revoked"
