import pytest
from unittest.mock import MagicMock


def _mk_supabase_chain(select_data=None, insert_data=None):
    mock = MagicMock()
    mock.table.return_value = mock
    mock.select.return_value = mock
    mock.eq.return_value = mock
    mock.update.return_value = mock
    mock.insert.return_value = mock

    select_resp = MagicMock()
    select_resp.data = select_data if select_data is not None else []

    insert_resp = MagicMock()
    insert_resp.data = insert_data if insert_data is not None else []

    # get_current_profile 会先 select().execute()，如无记录再 insert().execute()
    mock.execute.side_effect = [select_resp, insert_resp]
    return mock


@pytest.mark.asyncio
async def test_get_current_profile_creates_default_author(monkeypatch):
    monkeypatch.delenv("ADMIN_EMAILS", raising=False)
    from app.core import roles as roles_mod

    user_id = "00000000-0000-0000-0000-000000000000"
    user = {"id": user_id, "email": "test@example.com"}

    supabase = _mk_supabase_chain(
        select_data=[],
        insert_data=[{"id": user_id, "email": "test@example.com", "roles": ["author"]}],
    )
    monkeypatch.setattr(roles_mod, "supabase", supabase)

    profile = await roles_mod.get_current_profile(user)
    assert profile["id"] == user_id
    assert profile["roles"] == ["author"]


@pytest.mark.asyncio
async def test_get_current_profile_admin_email_elevates_and_merges(monkeypatch):
    monkeypatch.setenv("ADMIN_EMAILS", "test@example.com")
    from app.core import roles as roles_mod

    user_id = "00000000-0000-0000-0000-000000000000"
    user = {"id": user_id, "email": "test@example.com"}

    mock = MagicMock()
    mock.table.return_value = mock
    mock.select.return_value = mock
    mock.eq.return_value = mock
    mock.update.return_value = mock

    select_resp = MagicMock()
    select_resp.data = [{"id": user_id, "email": "test@example.com", "roles": ["author"]}]
    update_resp = MagicMock()
    update_resp.data = [{"id": user_id, "roles": ["admin", "editor", "reviewer", "author"]}]
    mock.execute.side_effect = [select_resp, update_resp]

    monkeypatch.setattr(roles_mod, "supabase", mock)

    profile = await roles_mod.get_current_profile(user)
    assert "admin" in profile["roles"]
    assert "editor" in profile["roles"]
    assert "reviewer" in profile["roles"]


@pytest.mark.asyncio
async def test_get_current_profile_falls_back_on_error(monkeypatch):
    monkeypatch.setenv("ADMIN_EMAILS", "test@example.com")
    from app.core import roles as roles_mod

    user = {"id": "00000000-0000-0000-0000-000000000000", "email": "test@example.com"}

    bad = MagicMock()
    bad.table.side_effect = RuntimeError("boom")
    monkeypatch.setattr(roles_mod, "supabase", bad)

    profile = await roles_mod.get_current_profile(user)
    assert profile["id"] == user["id"]
    assert "admin" in profile["roles"]


@pytest.mark.asyncio
async def test_require_any_role_allows(monkeypatch):
    from app.core.roles import require_any_role

    dep = require_any_role(["editor"])
    profile = await dep(profile={"roles": ["editor"]})
    assert profile["roles"] == ["editor"]

