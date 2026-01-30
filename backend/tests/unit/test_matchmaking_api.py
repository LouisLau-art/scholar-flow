import pytest
from httpx import AsyncClient
from unittest.mock import MagicMock, patch


def auth_headers(token: str | None) -> dict[str, str]:
    if not token:
        return {}
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_matchmaking_requires_auth(client: AsyncClient):
    resp = await client.post("/api/v1/matchmaking/analyze", json={"title": "t"})
    assert resp.status_code in {401, 403}


@pytest.mark.asyncio
async def test_matchmaking_invalid_token_401(client: AsyncClient, invalid_token: str):
    resp = await client.post(
        "/api/v1/matchmaking/analyze",
        headers=auth_headers(invalid_token),
        json={"title": "t"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_matchmaking_non_editor_forbidden(client: AsyncClient, auth_token: str, monkeypatch):
    # 不设置 ADMIN_EMAILS -> 默认 roles=['author']，应当被 RBAC 拒绝
    monkeypatch.delenv("ADMIN_EMAILS", raising=False)

    # 避免测试跑到真实 Supabase：强制触发 get_current_profile 的降级路径
    from app.core import roles as roles_mod

    bad = MagicMock()
    bad.table.side_effect = RuntimeError("boom")
    monkeypatch.setattr(roles_mod, "supabase", bad)

    resp = await client.post(
        "/api/v1/matchmaking/analyze",
        headers=auth_headers(auth_token),
        json={"title": "t"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_matchmaking_validation_422(client: AsyncClient, auth_token: str, monkeypatch):
    monkeypatch.setenv("ADMIN_EMAILS", "test@example.com")
    from app.core import roles as roles_mod

    bad = MagicMock()
    bad.table.side_effect = RuntimeError("boom")
    monkeypatch.setattr(roles_mod, "supabase", bad)

    resp = await client.post(
        "/api/v1/matchmaking/analyze",
        headers=auth_headers(auth_token),
        json={},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_matchmaking_success_returns_recommendations(client: AsyncClient, auth_token: str, monkeypatch):
    monkeypatch.setenv("ADMIN_EMAILS", "test@example.com")

    # 避免真实 Supabase：走 get_current_profile 的异常降级（仍然具备 editor/admin/reviewer）
    from app.core import roles as roles_mod

    bad = MagicMock()
    bad.table.side_effect = RuntimeError("boom")
    monkeypatch.setattr(roles_mod, "supabase", bad)

    fake_result = {
        "recommendations": [
            {
                "reviewer_id": "00000000-0000-0000-0000-000000000111",
                "name": "Dr. Expert",
                "email": "expert@example.com",
                "match_score": 0.88,
            }
        ],
        "insufficient_data": False,
        "message": None,
    }

    with patch("app.api.v1.matchmaking.MatchmakingService") as svc:
        svc.return_value.analyze.return_value = fake_result
        resp = await client.post(
            "/api/v1/matchmaking/analyze",
            headers=auth_headers(auth_token),
            json={"manuscript_id": "00000000-0000-0000-0000-000000000999"},
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["data"]["recommendations"][0]["match_score"] == 0.88

