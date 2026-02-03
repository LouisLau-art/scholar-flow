import pytest
from types import SimpleNamespace
from uuid import uuid4

from httpx import AsyncClient

from main import app
from app.core.roles import get_current_profile


@pytest.fixture
def override_profile():
    """
    覆盖 get_current_profile，避免测试依赖真实 Supabase user_profiles。
    """

    def _set(profile: dict):
        app.dependency_overrides[get_current_profile] = lambda: profile

    yield _set
    app.dependency_overrides.pop(get_current_profile, None)


class _DummyQuery:
    def __init__(self, data):
        self._data = data

    def update(self, *_args, **_kwargs):
        return self

    def eq(self, *_args, **_kwargs):
        return self

    def execute(self):
        return SimpleNamespace(data=self._data)


class _DummySupabaseAdmin:
    def __init__(self, data):
        self._data = data

    def table(self, name: str):
        assert name == "manuscripts"
        return _DummyQuery(self._data)


@pytest.mark.asyncio
async def test_update_manuscript_owner_requires_editor_or_admin(
    client: AsyncClient, auth_token: str, override_profile
):
    override_profile({"id": str(uuid4()), "email": "author@example.com", "roles": ["author"]})

    manuscript_id = str(uuid4())
    res = await client.patch(
        f"/api/v1/manuscripts/{manuscript_id}",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={"owner_id": str(uuid4())},
    )
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_update_manuscript_owner_rejects_non_staff_owner(
    client: AsyncClient, auth_token: str, override_profile, monkeypatch: pytest.MonkeyPatch
):
    override_profile({"id": str(uuid4()), "email": "editor@example.com", "roles": ["editor"]})

    def _bad(_owner_id):
        raise ValueError("owner_id must be editor/admin")

    monkeypatch.setattr("app.api.v1.manuscripts.validate_internal_owner_id", _bad)

    manuscript_id = str(uuid4())
    res = await client.patch(
        f"/api/v1/manuscripts/{manuscript_id}",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={"owner_id": str(uuid4())},
    )
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_update_manuscript_owner_success(
    client: AsyncClient, auth_token: str, override_profile, monkeypatch: pytest.MonkeyPatch
):
    override_profile({"id": str(uuid4()), "email": "editor@example.com", "roles": ["editor"]})

    owner_id = str(uuid4())
    manuscript_id = str(uuid4())

    monkeypatch.setattr("app.api.v1.manuscripts.validate_internal_owner_id", lambda _id: {"id": owner_id, "roles": ["editor"]})
    monkeypatch.setattr(
        "app.api.v1.manuscripts.supabase_admin",
        _DummySupabaseAdmin([{"id": manuscript_id, "owner_id": owner_id}]),
    )

    res = await client.patch(
        f"/api/v1/manuscripts/{manuscript_id}",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={"owner_id": owner_id},
    )

    assert res.status_code == 200
    payload = res.json()
    assert payload["success"] is True
    assert payload["data"]["owner_id"] == owner_id

