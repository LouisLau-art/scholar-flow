from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from app.core.config import SMTPConfig, get_admin_api_key
from app.core.security import require_admin_key


def test_smtp_config_from_env_none_without_host(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("SMTP_HOST", raising=False)
    assert SMTPConfig.from_env() is None


def test_smtp_config_from_env_parses_values(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("SMTP_PORT", "2525")
    monkeypatch.setenv("SMTP_USER", "user@example.com")
    monkeypatch.setenv("SMTP_PASSWORD", "pw")
    monkeypatch.setenv("SMTP_FROM_EMAIL", "no-reply@example.com")
    monkeypatch.setenv("SMTP_USE_STARTTLS", "false")

    cfg = SMTPConfig.from_env()
    assert cfg is not None
    assert cfg.host == "smtp.example.com"
    assert cfg.port == 2525
    assert cfg.user == "user@example.com"
    assert cfg.password == "pw"
    assert cfg.from_email == "no-reply@example.com"
    assert cfg.use_starttls is False


def test_get_admin_api_key_trim(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("ADMIN_API_KEY", "  secret  ")
    assert get_admin_api_key() == "secret"


@pytest.mark.asyncio
async def test_require_admin_key_rejects_when_not_configured(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("ADMIN_API_KEY", raising=False)
    with pytest.raises(HTTPException) as exc:
        await require_admin_key(x_admin_key="anything")
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_require_admin_key_rejects_invalid(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("ADMIN_API_KEY", "secret")
    with pytest.raises(HTTPException) as exc:
        await require_admin_key(x_admin_key="wrong")
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_require_admin_key_accepts_valid(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("ADMIN_API_KEY", "secret")
    await require_admin_key(x_admin_key="secret")


@pytest.mark.asyncio
async def test_internal_chase_reviews_endpoint_calls_scheduler():
    from app.api.v1 import internal as internal_api

    fake_scheduler = MagicMock()
    fake_scheduler.run.return_value = {"processed_count": 3, "emails_sent": 2}

    with patch.object(internal_api, "ChaseScheduler", return_value=fake_scheduler):
        resp = await internal_api.chase_reviews(_admin=None)
        assert resp["success"] is True
        assert resp["processed_count"] == 3
        assert resp["emails_sent"] == 2


def test_create_user_supabase_client_sets_postgrest_auth():
    from app.lib import api_client as api_client_mod

    fake = MagicMock()
    fake.postgrest = MagicMock()

    with patch.object(api_client_mod, "create_client", return_value=fake):
        client = api_client_mod.create_user_supabase_client("jwt.token.here")
        assert client is fake
        fake.postgrest.auth.assert_called_once_with("jwt.token.here")

