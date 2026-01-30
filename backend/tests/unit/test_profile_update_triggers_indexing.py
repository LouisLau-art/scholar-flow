import pytest
from httpx import AsyncClient
from unittest.mock import MagicMock, patch


def auth_headers(token: str | None) -> dict[str, str]:
    if not token:
        return {}
    return {"Authorization": f"Bearer {token}"}


def _mk_supabase_update_ok(row: dict):
    mock = MagicMock()
    mock.table.return_value = mock
    mock.update.return_value = mock
    mock.eq.return_value = mock
    mock.execute.return_value = MagicMock(data=[row])
    return mock


@pytest.mark.asyncio
async def test_profile_update_triggers_reviewer_indexing(client: AsyncClient, auth_token: str, monkeypatch):
    monkeypatch.setenv("ADMIN_EMAILS", "test@example.com")

    # 让 get_current_profile 走异常降级（仍具备 reviewer/editor/admin）
    from app.core import roles as roles_mod

    bad = MagicMock()
    bad.table.side_effect = RuntimeError("boom")
    monkeypatch.setattr(roles_mod, "supabase", bad)

    from app.api.v1 import users as users_mod

    monkeypatch.setattr(users_mod, "supabase", _mk_supabase_update_ok({"id": "u", "name": "n"}))

    with patch("app.api.v1.users.MatchmakingService") as svc:
        svc.return_value.index_reviewer.return_value = None
        resp = await client.put(
            "/api/v1/user/profile",
            headers=auth_headers(auth_token),
            json={"research_interests": "Machine Learning"},
        )

    assert resp.status_code == 200
    assert svc.return_value.index_reviewer.called


@pytest.mark.asyncio
async def test_profile_update_does_not_trigger_indexing_for_author(client: AsyncClient, auth_token: str, monkeypatch):
    monkeypatch.delenv("ADMIN_EMAILS", raising=False)

    from app.core import roles as roles_mod

    bad = MagicMock()
    bad.table.side_effect = RuntimeError("boom")
    monkeypatch.setattr(roles_mod, "supabase", bad)

    from app.api.v1 import users as users_mod

    monkeypatch.setattr(users_mod, "supabase", _mk_supabase_update_ok({"id": "u", "name": "n"}))

    with patch("app.api.v1.users.MatchmakingService") as svc:
        resp = await client.put(
            "/api/v1/user/profile",
            headers=auth_headers(auth_token),
            json={"research_interests": "ML"},
        )

    assert resp.status_code == 200
    assert not svc.return_value.index_reviewer.called

