from __future__ import annotations

import pytest


@pytest.mark.integration
@pytest.mark.asyncio
async def test_platform_readiness_requires_admin_key(client, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("ADMIN_API_KEY", "test-admin")
    resp = await client.get("/api/v1/internal/platform-readiness")
    assert resp.status_code == 401


@pytest.mark.integration
@pytest.mark.asyncio
async def test_platform_readiness_reports_config_without_leaking_secrets(
    client,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(
        "app.api.v1.internal._probe_resend_sender_domain_status",
        lambda *_args, **_kwargs: (
            "passed",
            "sender 域名已在 Resend 验证：louisliu.fun",
            {
                "provider_probe": "resend",
                "sender_domain": "louisliu.fun",
                "domain_found": True,
                "domain_verified": True,
            },
        ),
    )
    monkeypatch.setenv("ADMIN_API_KEY", "test-admin")
    monkeypatch.setenv("MAGIC_LINK_JWT_SECRET", "super-secret-magic")
    monkeypatch.setenv("FRONTEND_BASE_URL", "https://scholar-flow-q1yw.vercel.app")
    monkeypatch.setenv("FRONTEND_ORIGIN", "https://scholar-flow-q1yw.vercel.app")
    monkeypatch.setenv("RESEND_API_KEY", "re_secret_live_123")
    monkeypatch.setenv("EMAIL_SENDER", "ScholarFlow <no-reply@louisliu.fun>")
    monkeypatch.setenv("SUPABASE_URL", "https://mmvulyrfsorqdpdrzbkd.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "supabase-service-role-secret")

    resp = await client.get(
        "/api/v1/internal/platform-readiness",
        headers={"X-Admin-Key": "test-admin"},
    )
    assert resp.status_code == 200, resp.text
    payload = resp.json()
    assert payload["status"] == "passed"
    checks = {item["key"]: item for item in payload["checks"]}
    assert checks["email_provider.configured"]["status"] == "passed"
    assert checks["email_sender.ready"]["status"] == "passed"
    assert checks["frontend_base_url.ready"]["status"] == "passed"
    assert checks["email_provider.configured"]["evidence"]["uses_resend"] is True
    assert checks["email_sender.ready"]["evidence"]["sender_domain"] == "louisliu.fun"
    serialized = resp.text
    assert "re_secret_live_123" not in serialized
    assert "supabase-service-role-secret" not in serialized
    assert "super-secret-magic" not in serialized


@pytest.mark.integration
@pytest.mark.asyncio
async def test_platform_readiness_flags_localhost_and_resend_dev_fallback(
    client,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("ADMIN_API_KEY", "test-admin")
    monkeypatch.delenv("MAGIC_LINK_JWT_SECRET", raising=False)
    monkeypatch.delenv("SECRET_KEY", raising=False)
    monkeypatch.setenv("FRONTEND_BASE_URL", "http://localhost:3000")
    monkeypatch.setenv("FRONTEND_ORIGIN", "http://127.0.0.1:3000")
    monkeypatch.setenv("RESEND_API_KEY", "re_secret_live_123")
    monkeypatch.setenv("EMAIL_SENDER", "ScholarFlow <onboarding@resend.dev>")
    monkeypatch.setenv("SUPABASE_URL", "https://mmvulyrfsorqdpdrzbkd.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "service-role")

    resp = await client.get(
        "/api/v1/internal/platform-readiness",
        headers={"X-Admin-Key": "test-admin"},
    )
    assert resp.status_code == 200, resp.text
    payload = resp.json()
    assert payload["status"] == "failed"
    checks = {item["key"]: item for item in payload["checks"]}
    assert checks["magic_link_secret.configured"]["status"] == "blocked"
    assert checks["frontend_base_url.ready"]["status"] == "failed"
    assert checks["frontend_origin.ready"]["status"] == "failed"
    assert checks["email_sender.ready"]["status"] == "failed"
    assert checks["email_provider.configured"]["status"] == "passed"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_platform_readiness_fails_when_resend_sender_uses_dev_fallback(
    client,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("ADMIN_API_KEY", "test-admin")
    monkeypatch.setenv("SECRET_KEY", "fallback-secret")
    monkeypatch.setenv("FRONTEND_BASE_URL", "https://scholar-flow-q1yw.vercel.app")
    monkeypatch.setenv("FRONTEND_ORIGIN", "https://scholar-flow-q1yw.vercel.app")
    monkeypatch.setenv("RESEND_API_KEY", "re_secret_live_123")
    monkeypatch.setenv("EMAIL_SENDER", "ScholarFlow <onboarding@resend.dev>")
    monkeypatch.setenv("SUPABASE_URL", "https://mmvulyrfsorqdpdrzbkd.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "service-role")

    resp = await client.get(
        "/api/v1/internal/platform-readiness",
        headers={"X-Admin-Key": "test-admin"},
    )
    assert resp.status_code == 200, resp.text
    payload = resp.json()
    assert payload["status"] == "failed"
    checks = {item["key"]: item for item in payload["checks"]}
    assert checks["email_provider.configured"]["status"] == "passed"
    assert checks["email_sender.ready"]["status"] == "failed"
    assert checks["email_sender.ready"]["evidence"]["uses_resend_dev_fallback"] is True


@pytest.mark.integration
@pytest.mark.asyncio
async def test_platform_readiness_accepts_smtp_provider(
    client,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("ADMIN_API_KEY", "test-admin")
    monkeypatch.setenv("MAGIC_LINK_JWT_SECRET", "magic-secret")
    monkeypatch.setenv("FRONTEND_BASE_URL", "https://scholar-flow-q1yw.vercel.app")
    monkeypatch.setenv("FRONTEND_ORIGIN", "https://scholar-flow-q1yw.vercel.app")
    monkeypatch.delenv("RESEND_API_KEY", raising=False)
    monkeypatch.delenv("EMAIL_SENDER", raising=False)
    monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("SMTP_FROM_EMAIL", "no-reply@example.com")
    monkeypatch.setenv("SUPABASE_URL", "https://mmvulyrfsorqdpdrzbkd.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "service-role")

    resp = await client.get(
        "/api/v1/internal/platform-readiness",
        headers={"X-Admin-Key": "test-admin"},
    )
    assert resp.status_code == 200, resp.text
    payload = resp.json()
    assert payload["status"] == "passed"
    checks = {item["key"]: item for item in payload["checks"]}
    assert checks["email_provider.configured"]["evidence"]["uses_smtp"] is True
    assert checks["email_sender.ready"]["evidence"]["provider"] == "smtp"
    assert checks["email_sender.ready"]["status"] == "passed"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_platform_readiness_blocks_secret_key_fallback_for_magic_link(
    client,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("ADMIN_API_KEY", "test-admin")
    monkeypatch.delenv("MAGIC_LINK_JWT_SECRET", raising=False)
    monkeypatch.setenv("SECRET_KEY", "fallback-secret")
    monkeypatch.delenv("RESEND_API_KEY", raising=False)
    monkeypatch.delenv("EMAIL_SENDER", raising=False)
    monkeypatch.setenv("FRONTEND_BASE_URL", "https://scholar-flow-q1yw.vercel.app")
    monkeypatch.setenv("FRONTEND_ORIGIN", "https://scholar-flow-q1yw.vercel.app")
    monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("SMTP_FROM_EMAIL", "no-reply@example.com")
    monkeypatch.setenv("SUPABASE_URL", "https://mmvulyrfsorqdpdrzbkd.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "service-role")

    resp = await client.get(
        "/api/v1/internal/platform-readiness",
        headers={"X-Admin-Key": "test-admin"},
    )
    assert resp.status_code == 200, resp.text
    payload = resp.json()
    assert payload["status"] == "blocked"
    checks = {item["key"]: item for item in payload["checks"]}
    assert checks["magic_link_secret.configured"]["status"] == "blocked"
    assert checks["magic_link_secret.configured"]["evidence"]["secret_key_fallback_configured"] is True


@pytest.mark.integration
@pytest.mark.asyncio
async def test_platform_readiness_requires_explicit_smtp_from_email(
    client,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("ADMIN_API_KEY", "test-admin")
    monkeypatch.setenv("MAGIC_LINK_JWT_SECRET", "magic-secret")
    monkeypatch.setenv("FRONTEND_BASE_URL", "https://scholar-flow-q1yw.vercel.app")
    monkeypatch.setenv("FRONTEND_ORIGIN", "https://scholar-flow-q1yw.vercel.app")
    monkeypatch.delenv("RESEND_API_KEY", raising=False)
    monkeypatch.delenv("EMAIL_SENDER", raising=False)
    monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("SMTP_USER", "mailer")
    monkeypatch.delenv("SMTP_FROM_EMAIL", raising=False)
    monkeypatch.setenv("SUPABASE_URL", "https://mmvulyrfsorqdpdrzbkd.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "service-role")

    resp = await client.get(
        "/api/v1/internal/platform-readiness",
        headers={"X-Admin-Key": "test-admin"},
    )
    assert resp.status_code == 200, resp.text
    payload = resp.json()
    assert payload["status"] == "blocked"
    checks = {item["key"]: item for item in payload["checks"]}
    assert checks["email_provider.configured"]["status"] == "passed"
    assert checks["email_sender.ready"]["status"] == "blocked"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_runtime_version_reports_current_deploy_sha(
    client,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("ADMIN_API_KEY", "test-admin")
    monkeypatch.setenv("DEPLOY_SHA", "abc123")

    resp = await client.get(
        "/api/v1/internal/runtime-version",
        headers={"X-Admin-Key": "test-admin"},
    )
    assert resp.status_code == 200, resp.text
    payload = resp.json()
    assert payload["deploy_sha"] == "abc123"
    assert payload["source"] == "huggingface-space"
