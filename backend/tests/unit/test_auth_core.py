import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from jose import jwt


@pytest.mark.asyncio
async def test_core_auth_get_current_user_hs256_decode(monkeypatch):
    from app.core import auth as auth_module

    monkeypatch.setattr(auth_module, "SUPABASE_JWT_SECRET", "secret")
    payload = {"sub": "user-1", "email": "u@example.com", "aud": "authenticated"}
    token = jwt.encode(payload, "secret", algorithm="HS256")

    async def _fake_roles(_user_id: str):
        return ["editor"]

    monkeypatch.setattr(auth_module, "_get_user_roles", _fake_roles)

    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    user = await auth_module.get_current_user(creds)
    assert user["id"] == "user-1"
    assert user["email"] == "u@example.com"
    assert "editor" in user["roles"]


@pytest.mark.asyncio
async def test_core_auth_get_current_user_missing_sub_rejected(monkeypatch):
    from app.core import auth as auth_module

    monkeypatch.setattr(auth_module, "SUPABASE_JWT_SECRET", "secret")
    token = jwt.encode({"email": "u@example.com", "aud": "authenticated"}, "secret", algorithm="HS256")
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

    with pytest.raises(HTTPException) as exc:
        await auth_module.get_current_user(creds)
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_core_auth_require_roles_allows_and_denies(monkeypatch):
    from app.core import auth as auth_module

    async def _fake_user():
        return {"id": "u", "roles": ["author", "editor"]}

    dep = auth_module.require_roles(["editor"])
    user = await dep(current_user=await _fake_user())
    assert user["id"] == "u"

    dep2 = auth_module.require_roles(["admin"])
    with pytest.raises(HTTPException) as exc:
        await dep2(current_user=await _fake_user())
    assert exc.value.status_code == 403

