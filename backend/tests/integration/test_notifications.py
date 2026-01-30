import pytest
from httpx import AsyncClient
from unittest.mock import MagicMock, patch

def auth_headers(token: str | None) -> dict[str, str]:
    if not token:
        return {}
    return {"Authorization": f"Bearer {token}"}


def _build_postgrest_chain(data):
    mock = MagicMock()
    mock.table.return_value = mock
    mock.select.return_value = mock
    mock.order.return_value = mock
    mock.limit.return_value = mock
    mock.update.return_value = mock
    mock.eq.return_value = mock
    mock.execute.return_value = MagicMock(data=data)
    return mock


@pytest.mark.asyncio
async def test_notifications_requires_auth(client: AsyncClient):
    resp = await client.get("/api/v1/notifications")
    assert resp.status_code in {401, 403}


@pytest.mark.asyncio
async def test_notifications_list_success(client: AsyncClient, auth_token: str):
    user_client = _build_postgrest_chain(
        data=[
            {
                "id": "00000000-0000-0000-0000-000000000111",
                "user_id": "00000000-0000-0000-0000-000000000000",
                "manuscript_id": None,
                "type": "system",
                "title": "Hello",
                "content": "World",
                "is_read": False,
                "created_at": "2026-01-30T00:00:00Z",
            }
        ]
    )

    with patch("app.services.notification_service.create_user_supabase_client", return_value=user_client):
        resp = await client.get("/api/v1/notifications", headers=auth_headers(auth_token))
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert len(body["data"]) == 1


@pytest.mark.asyncio
async def test_notifications_mark_read_success(client: AsyncClient, auth_token: str):
    user_client = _build_postgrest_chain(
        data=[
            {
                "id": "00000000-0000-0000-0000-000000000111",
                "is_read": True,
            }
        ]
    )
    with patch("app.services.notification_service.create_user_supabase_client", return_value=user_client):
        resp = await client.patch(
            "/api/v1/notifications/00000000-0000-0000-0000-000000000111/read",
            headers=auth_headers(auth_token),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert body["data"]["is_read"] is True
