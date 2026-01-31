import pytest
from uuid import uuid4
from httpx import AsyncClient, ASGITransport

from main import app


class _FakeResp:
    def __init__(self, data=None, count=None):
        self.data = data
        self.count = count


class _FakeQuery:
    def __init__(self, table_name: str, state: dict):
        self._table = table_name
        self._state = state
        self._filters = []
        self._status_filter = None
        self._count = None

    def select(self, _cols="*", count=None):
        self._count = count
        return self

    def eq(self, col, val):
        if col == "status":
            self._status_filter = val
        self._filters.append((col, val))
        return self

    def order(self, _col, desc=False):
        _ = desc
        return self

    def range(self, _start, _end):
        return self

    def insert(self, payload):
        self._state.setdefault("_pending_insert", {})[self._table] = payload
        return self

    def execute(self):
        pending = (self._state.get("_pending_insert") or {}).pop(self._table, None)
        if pending is not None:
            if self._table == "doi_tasks":
                # 让返回值符合 DOITask 模型要求
                row = {
                    "id": "cccccccc-cccc-4ccc-cccc-cccccccccccc",
                    **pending,
                    "run_at": "2026-01-30T00:00:00Z",
                    "created_at": "2026-01-30T00:00:00Z",
                    "locked_at": None,
                    "locked_by": None,
                    "completed_at": None,
                    "max_attempts": pending.get("max_attempts", 4),
                    "last_error": None,
                }
                self._state.setdefault("doi_tasks", []).append(row)
                return _FakeResp(data=[row], count=1)
            return _FakeResp(data=[pending], count=1)

        if self._table != "doi_tasks":
            return _FakeResp(data=[], count=0)

        items = list(self._state.get("doi_tasks", []))
        if self._status_filter:
            items = [x for x in items if x.get("status") == self._status_filter]
        return _FakeResp(data=items, count=len(items))


class _FakeSupabase:
    def __init__(self):
        self._state = {"doi_tasks": []}

    def table(self, name: str):
        return _FakeQuery(name, self._state)


@pytest.mark.asyncio
async def test_doi_register_and_get_status(monkeypatch):
    from app.services.doi_service import DOIService

    DOIService._registrations_by_article_id.clear()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        article_id = str(uuid4())
        res = await ac.post(
            "/api/v1/doi/register",
            json={"article_id": article_id},
        )
        assert res.status_code == 201
        body = res.json()
        assert body["status"] == "pending"

        article_id = body["article_id"]
        res2 = await ac.get(f"/api/v1/doi/{article_id}")
        assert res2.status_code == 200
        assert res2.json()["status"] == "pending"


@pytest.mark.asyncio
async def test_doi_tasks_endpoints(monkeypatch):
    from app.api.v1 import doi as doi_module

    fake = _FakeSupabase()
    monkeypatch.setattr(doi_module, "supabase", fake)

    # seed one task
    fake._state["doi_tasks"].append(
        {
            "id": "aaaaaaaa-aaaa-4aaa-aaaa-aaaaaaaaaaaa",
            "registration_id": "bbbbbbbb-bbbb-4bbb-bbbb-bbbbbbbbbbbb",
            "task_type": "register",
            "status": "pending",
            "priority": 0,
            "run_at": "2026-01-30T00:00:00Z",
            "attempts": 0,
            "max_attempts": 4,
            "locked_at": None,
            "locked_by": None,
            "created_at": "2026-01-30T00:00:00Z",
            "completed_at": None,
        }
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get("/api/v1/doi/tasks")
        assert res.status_code == 200
        assert res.json()["total"] == 1

        res = await ac.get("/api/v1/doi/tasks?status=pending")
        assert res.status_code == 200
        assert res.json()["items"][0]["id"] == "aaaaaaaa-aaaa-4aaa-aaaa-aaaaaaaaaaaa"

        res = await ac.get("/api/v1/doi/tasks/failed")
        assert res.status_code == 200
        assert res.json()["total"] == 0


@pytest.mark.asyncio
async def test_doi_retry_creates_task(monkeypatch):
    from app.services.doi_service import DOIService

    DOIService._registrations_by_article_id.clear()

    from app.api.v1 import doi as doi_module

    fake = _FakeSupabase()
    monkeypatch.setattr(doi_module, "supabase", fake)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 先创建 registration（存根服务会写入进程内存）
        article_id = str(uuid4())
        res = await ac.post(
            "/api/v1/doi/register",
            json={"article_id": article_id},
        )
        assert res.status_code == 201
        article_id = res.json()["article_id"]

        # retry
        res2 = await ac.post(f"/api/v1/doi/{article_id}/retry")
        assert res2.status_code == 200
        body = res2.json()
        assert body["task_type"] == "register"
        assert body["status"] == "pending"


@pytest.mark.asyncio
async def test_doi_get_status_404_when_missing(monkeypatch):
    from app.services.doi_service import DOIService

    DOIService._registrations_by_article_id.clear()

    missing_id = str(uuid4())
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get(f"/api/v1/doi/{missing_id}")
        assert res.status_code == 404


@pytest.mark.asyncio
async def test_doi_retry_404_when_missing(monkeypatch):
    from app.services.doi_service import DOIService

    DOIService._registrations_by_article_id.clear()

    missing_id = str(uuid4())
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.post(f"/api/v1/doi/{missing_id}/retry")
        assert res.status_code == 404


@pytest.mark.asyncio
async def test_doi_retry_400_when_already_registered(monkeypatch):
    from app.services.doi_service import DOIService
    from app.models.doi import DOIRegistrationStatus
    from app.api.v1 import doi as doi_module

    DOIService._registrations_by_article_id.clear()

    # 不需要走 supabase（因为应该在 status 检查处直接失败）
    monkeypatch.setattr(doi_module, "supabase", _FakeSupabase())

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        article_id = str(uuid4())
        res = await ac.post("/api/v1/doi/register", json={"article_id": article_id})
        assert res.status_code == 201

        DOIService._registrations_by_article_id[article_id].status = DOIRegistrationStatus.REGISTERED

        res2 = await ac.post(f"/api/v1/doi/{article_id}/retry")
        assert res2.status_code == 400


@pytest.mark.asyncio
async def test_doi_retry_500_when_insert_returns_empty(monkeypatch):
    from app.services.doi_service import DOIService
    from app.api.v1 import doi as doi_module

    DOIService._registrations_by_article_id.clear()

    class _EmptyInsertQuery(_FakeQuery):
        def execute(self):
            pending = (self._state.get("_pending_insert") or {}).pop(self._table, None)
            if pending is not None:
                return _FakeResp(data=[], count=0)
            return super().execute()

    class _EmptyInsertSupabase(_FakeSupabase):
        def table(self, name: str):
            return _EmptyInsertQuery(name, self._state)

    monkeypatch.setattr(doi_module, "supabase", _EmptyInsertSupabase())

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        article_id = str(uuid4())
        res = await ac.post("/api/v1/doi/register", json={"article_id": article_id})
        assert res.status_code == 201

        res2 = await ac.post(f"/api/v1/doi/{article_id}/retry")
        assert res2.status_code == 500
