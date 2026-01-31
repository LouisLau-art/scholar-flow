import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from starlette.requests import Request


@pytest.mark.asyncio
async def test_public_endpoints_smoke(client):
    res = await client.get("/api/v1/public/topics")
    assert res.status_code == 200
    body = res.json()
    assert body["success"] is True
    assert isinstance(body["data"], list)

    res2 = await client.get("/api/v1/public/announcements")
    assert res2.status_code == 200
    body2 = res2.json()
    assert body2["success"] is True
    assert isinstance(body2["data"], list)


@pytest.mark.asyncio
async def test_coverage_endpoint_404_when_report_missing(monkeypatch):
    from app.api.v1 import coverage as coverage_api

    monkeypatch.setattr(
        coverage_api,
        "get_coverage_summary",
        lambda: {"backend": None, "frontend": None},
    )

    with pytest.raises(HTTPException) as exc:
        await coverage_api.get_coverage(current_user={"id": "user-1"})

    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_notifications_mark_read_404_when_not_found(monkeypatch):
    from app.api.v1 import notifications as notifications_api

    class _StubNotificationService:
        def mark_read(self, access_token: str, notification_id: str):
            _ = access_token
            _ = notification_id
            return None

    monkeypatch.setattr(notifications_api, "NotificationService", _StubNotificationService)

    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="t")
    with pytest.raises(HTTPException) as exc:
        await notifications_api.mark_notification_read(
            id="n1", _current_user={"id": "user-1"}, credentials=creds
        )

    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_require_admin_bearer_key_error_paths(monkeypatch):
    from app.core import security as security_module

    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="k")

    monkeypatch.setattr(security_module, "get_admin_api_key", lambda: None)
    with pytest.raises(HTTPException) as exc:
        await security_module.require_admin_bearer_key(credentials=creds)
    assert exc.value.status_code == 401
    assert "not configured" in str(exc.value.detail).lower()

    monkeypatch.setattr(security_module, "get_admin_api_key", lambda: "expected")
    with pytest.raises(HTTPException) as exc2:
        await security_module.require_admin_bearer_key(credentials=creds)
    assert exc2.value.status_code == 401
    assert "invalid" in str(exc2.value.detail).lower()


@pytest.mark.asyncio
async def test_exception_handler_middleware_returns_json_for_errors():
    from fastapi import FastAPI
    from app.core.middleware import ExceptionHandlerMiddleware

    mw = ExceptionHandlerMiddleware(app=FastAPI())
    request = Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/boom",
            "headers": [],
            "query_string": b"",
            "client": ("test", 123),
            "server": ("test", 80),
            "scheme": "http",
        }
    )

    async def _raise_http(_req):
        raise HTTPException(status_code=418, detail="teapot")

    res = await mw.dispatch(request, _raise_http)
    assert res.status_code == 418
    assert b"teapot" in res.body

    async def _raise_generic(_req):
        raise RuntimeError("boom")

    res2 = await mw.dispatch(request, _raise_generic)
    assert res2.status_code == 500
    assert b"server_error" in res2.body
