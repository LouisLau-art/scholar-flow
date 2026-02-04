from app.core.sentry_init import _before_send, init_sentry


def test_before_send_filters_request_body_and_sensitive_headers(monkeypatch):
    event = {
        "request": {
            "headers": {
                "Authorization": "Bearer secret",
                "Cookie": "a=b",
                "X-Test": "ok",
            },
            "data": {"password": "cleartext", "other": "value"},
            "cookies": {"a": "b"},
            "body": "raw-body",
        },
        "extra": {"password": "cleartext"},
    }

    out = _before_send(event, {})
    assert out is not None

    request = out["request"]
    assert request["data"] == "[Filtered]"
    assert request["body"] == "[Filtered]"
    assert request["cookies"] == "[Filtered]"
    assert "Authorization" not in request["headers"]
    assert "Cookie" not in request["headers"]
    assert request["headers"]["X-Test"] == "ok"
    assert out["extra"]["password"] == "[Filtered]"


def test_init_sentry_disabled_without_dsn(monkeypatch):
    monkeypatch.delenv("SENTRY_DSN", raising=False)
    monkeypatch.delenv("SENTRY_ENABLED", raising=False)
    assert init_sentry() is False

