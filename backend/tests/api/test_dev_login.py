from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


@pytest.mark.unit
def test_dev_login_disabled_by_default(monkeypatch):
    monkeypatch.delenv("GO_ENV", raising=False)
    resp = client.get("/api/v1/auth/dev-login?email=test@example.com")
    assert resp.status_code == 404


@pytest.mark.unit
def test_dev_login_redirects_with_tokens(monkeypatch):
    monkeypatch.setenv("GO_ENV", "dev")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "anon-key")
    monkeypatch.setenv("FRONTEND_ORIGIN", "http://localhost:3000")

    import app.api.v1.auth as auth_api

    # Mock: admin.generate_link -> properties.email_otp
    mock_admin = MagicMock()
    mock_admin.auth.admin.generate_link.return_value = SimpleNamespace(properties={"email_otp": "otp-123"})
    monkeypatch.setattr(auth_api, "supabase_admin", mock_admin)

    # Mock: anon client verify_otp -> session tokens
    mock_anon = MagicMock()
    mock_anon.auth.verify_otp.return_value = SimpleNamespace(
        session=SimpleNamespace(access_token="acc-1", refresh_token="ref-1")
    )
    monkeypatch.setattr(auth_api, "create_client", lambda *_args, **_kwargs: mock_anon)

    resp = client.get(
        "/api/v1/auth/dev-login?email=test@example.com&next=/dashboard",
        follow_redirects=False,
    )
    assert resp.status_code in (302, 307)
    assert resp.headers["location"].startswith("http://localhost:3000/auth/callback?")
    assert "access_token=acc-1" in resp.headers["location"]
    assert "refresh_token=ref-1" in resp.headers["location"]
    assert "next=%2Fdashboard" in resp.headers["location"]
