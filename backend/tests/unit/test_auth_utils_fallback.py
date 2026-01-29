from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from jose import jwt

from app.core import auth_utils


def _make_jwt_like_token(header: dict, payload: dict) -> str:
    """
    构造一个符合 JWT 三段结构的字符串即可触发 jose 的 header 解析；
    signature 部分使用占位即可（不会被验证，因为我们走 fallback 分支）。
    """
    import base64
    import json

    def b64url(obj: dict) -> str:
        raw = json.dumps(obj, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("utf-8")

    # signature 段需要是合法的 base64url，否则 jose 解析 header 时会报 padding 错误
    sig = base64.urlsafe_b64encode(b"sig").rstrip(b"=").decode("utf-8")
    return f"{b64url(header)}.{b64url(payload)}.{sig}"


@pytest.mark.asyncio
async def test_get_current_user_fallback_success(monkeypatch):
    token = _make_jwt_like_token(
        header={"alg": "RS256", "typ": "JWT"},
        payload={"sub": "user-1", "email": "u@example.com", "aud": "authenticated"},
    )

    fake_supabase = SimpleNamespace(
        auth=SimpleNamespace(
            get_user=lambda _token: SimpleNamespace(
                user=SimpleNamespace(id="user-1", email="u@example.com")
            )
        )
    )
    monkeypatch.setattr(auth_utils, "supabase", fake_supabase)

    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    user = await auth_utils.get_current_user(creds)

    assert user["id"] == "user-1"
    assert user["email"] == "u@example.com"


@pytest.mark.asyncio
async def test_get_current_user_fallback_failure_raises_401(monkeypatch):
    token = _make_jwt_like_token(
        header={"alg": "RS256", "typ": "JWT"},
        payload={"sub": "user-1", "email": "u@example.com", "aud": "authenticated"},
    )

    def boom(_token):
        raise RuntimeError("boom")

    fake_supabase = SimpleNamespace(auth=SimpleNamespace(get_user=boom))
    monkeypatch.setattr(auth_utils, "supabase", fake_supabase)

    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    with pytest.raises(HTTPException) as exc:
        await auth_utils.get_current_user(creds)

    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_missing_sub_rejected(monkeypatch):
    # 走 HS256 本地 decode 分支，但 payload 缺少 sub，应返回 401
    secret = "mock-secret-replace-later"
    monkeypatch.setattr(auth_utils, "SUPABASE_JWT_SECRET", secret)

    token = jwt.encode({"email": "u@example.com", "aud": "authenticated"}, secret, algorithm="HS256")
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

    with pytest.raises(HTTPException) as exc:
        await auth_utils.get_current_user(creds)

    assert exc.value.status_code == 401
