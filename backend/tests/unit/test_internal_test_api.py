import os
import pytest
from httpx import AsyncClient, ASGITransport

from main import app


class _FakeSupabaseResponse:
    def __init__(self, data=None, count=None):
        self.data = data
        self.count = count


class _FakeTable:
    def __init__(self, name: str, store: dict):
        self._name = name
        self._store = store
        self._pending = None

    def upsert(self, payload, on_conflict=None):
        _ = on_conflict
        self._pending = ("upsert", payload)
        return self

    def insert(self, payload):
        self._pending = ("insert", payload)
        return self

    def select(self, _cols="*"):
        return self

    def single(self):
        return self

    def execute(self):
        op, payload = self._pending or ("noop", None)
        if self._name == "journals" and op in {"upsert", "insert"}:
            journal_id = "aaaaaaaa-aaaa-4aaa-aaaa-aaaaaaaaaaaa"
            return _FakeSupabaseResponse(
                data={
                    "id": journal_id,
                    "slug": payload.get("slug"),
                    "title": payload.get("title"),
                }
            )
        if self._name == "manuscripts" and op == "insert":
            items = []
            for idx, row in enumerate(payload):
                items.append(
                    {
                        "id": f"bbbbbbbb-bbbb-4bbb-bbbb-bbbbbbbbbbb{idx}",
                        "title": row.get("title"),
                        "status": row.get("status"),
                    }
                )
            return _FakeSupabaseResponse(data=items)
        return _FakeSupabaseResponse(data={})


class _FakeAuthAdmin:
    def __init__(self):
        self._users = set()

    def get_user_by_id(self, uid: str):
        if uid not in self._users:
            raise Exception("not found")
        return {"id": uid}

    def create_user(self, attributes: dict):
        uid = attributes.get("id")
        if uid:
            self._users.add(uid)
        return {"id": uid}


class _FakeSupabaseAdmin:
    def __init__(self):
        self.auth = type("Auth", (), {"admin": _FakeAuthAdmin()})()
        self._store = {}

    def table(self, name: str):
        return _FakeTable(name, self._store)


@pytest.mark.asyncio
async def test_internal_reset_db_forbidden_when_disabled(monkeypatch):
    monkeypatch.delenv("ENABLE_TEST_ENDPOINTS", raising=False)
    monkeypatch.delenv("GO_ENV", raising=False)
    monkeypatch.delenv("ENV", raising=False)
    monkeypatch.setenv("ADMIN_API_KEY", "k")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.post("/api/v1/internal/reset-db", headers={"Authorization": "Bearer k"})
        assert res.status_code == 403


@pytest.mark.asyncio
async def test_internal_reset_db_requires_test_db_url(monkeypatch):
    monkeypatch.setenv("ENABLE_TEST_ENDPOINTS", "true")
    monkeypatch.setenv("ADMIN_API_KEY", "k")
    monkeypatch.delenv("TEST_DB_URL", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_DB_URL", raising=False)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.post("/api/v1/internal/reset-db", headers={"Authorization": "Bearer k"})
        assert res.status_code == 500
        assert "TEST_DB_URL" in res.text


@pytest.mark.asyncio
async def test_internal_reset_db_success(monkeypatch):
    monkeypatch.setenv("ENABLE_TEST_ENDPOINTS", "true")
    monkeypatch.setenv("ADMIN_API_KEY", "k")
    monkeypatch.setenv("TEST_DB_URL", "postgres://example.invalid/db")

    from app.api.v1 import internal as internal_module

    monkeypatch.setattr(internal_module, "_truncate_public_tables", lambda _url: ["manuscripts", "journals"])

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.post("/api/v1/internal/reset-db", headers={"Authorization": "Bearer k"})
        assert res.status_code == 200
        body = res.json()
        assert body["message"] == "Database reset complete."
        assert "manuscripts" in body["tables_truncated"]


@pytest.mark.asyncio
async def test_internal_seed_db_success(monkeypatch):
    monkeypatch.setenv("ENABLE_TEST_ENDPOINTS", "true")
    monkeypatch.setenv("ADMIN_API_KEY", "k")

    from app.api.v1 import internal as internal_module

    monkeypatch.setattr(internal_module, "supabase_admin", _FakeSupabaseAdmin())

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.post("/api/v1/internal/seed-db", headers={"Authorization": "Bearer k"})
        assert res.status_code == 200
        body = res.json()
        assert body["message"] == "Database seeded successfully."
        assert body["summary"]["manuscripts_created"] >= 1


def test_internal_get_test_db_url_prefers_test_db_url(monkeypatch):
    from app.api.v1.internal import _get_test_db_url

    monkeypatch.setenv("TEST_DB_URL", "postgres://test")
    monkeypatch.setenv("DATABASE_URL", "postgres://db")
    monkeypatch.setenv("SUPABASE_DB_URL", "postgres://sb")
    assert _get_test_db_url() == "postgres://test"

    monkeypatch.delenv("TEST_DB_URL", raising=False)
    assert _get_test_db_url() == "postgres://db"

    monkeypatch.delenv("DATABASE_URL", raising=False)
    assert _get_test_db_url() == "postgres://sb"


def test_internal_truncate_public_tables_filters_spatial_ref_sys(monkeypatch):
    from app.api.v1 import internal as internal_module

    executed = {"truncate_called": False}

    class _Cursor:
        def __init__(self):
            self._stage = 0

        def execute(self, query):
            # 第一次：拉表名；第二次：TRUNCATE
            if self._stage == 0:
                self._stage = 1
                return
            executed["truncate_called"] = True
            executed["truncate_query"] = str(query)

        def fetchall(self):
            return [("manuscripts",), ("spatial_ref_sys",), ("journals",)]

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    class _Conn:
        def set_session(self, autocommit=True):
            _ = autocommit

        def cursor(self):
            return _Cursor()

        def close(self):
            return

    monkeypatch.setattr(internal_module.psycopg2, "connect", lambda _url: _Conn())

    tables = internal_module._truncate_public_tables("postgres://example.invalid/db")
    assert "spatial_ref_sys" not in tables
    assert set(tables) == {"manuscripts", "journals"}
    assert executed["truncate_called"] is True
