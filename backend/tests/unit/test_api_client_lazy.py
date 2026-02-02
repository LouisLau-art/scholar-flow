import pytest

import app.lib.api_client as api_client


def test_lazy_clients_raise_clear_error_when_missing_url(monkeypatch):
    monkeypatch.setattr(api_client, "url", "")
    monkeypatch.setattr(api_client, "key", "k")
    api_client.supabase._client = None  # type: ignore[attr-defined]

    with pytest.raises(RuntimeError, match="SUPABASE_URL is required"):
        api_client.supabase.table("any")  # type: ignore[union-attr]


def test_lazy_clients_raise_clear_error_when_missing_key(monkeypatch):
    monkeypatch.setattr(api_client, "url", "https://example.supabase.co")
    monkeypatch.setattr(api_client, "key", "")
    api_client.supabase._client = None  # type: ignore[attr-defined]

    with pytest.raises(RuntimeError, match="SUPABASE_ANON_KEY or SUPABASE_KEY is required"):
        api_client.supabase.table("any")  # type: ignore[union-attr]


def test_lazy_admin_client_requires_service_or_anon_key(monkeypatch):
    monkeypatch.setattr(api_client, "url", "https://example.supabase.co")
    monkeypatch.setattr(api_client, "key", "")
    monkeypatch.setattr(api_client, "service_role_key", "")
    api_client.supabase_admin._client = None  # type: ignore[attr-defined]

    with pytest.raises(RuntimeError, match="SUPABASE_SERVICE_ROLE_KEY"):
        api_client.supabase_admin.table("any")  # type: ignore[union-attr]

