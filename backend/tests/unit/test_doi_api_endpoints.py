from types import SimpleNamespace
from uuid import UUID

import pytest
from fastapi import HTTPException

from app.api.v1 import doi as doi_api


class _FakeRegistration:
    def __init__(self, *, reg_id: str, status: str):
        self.id = UUID(reg_id)
        self.status = status


class _FakeDOIService:
    def __init__(self, registration):
        self._registration = registration

    async def get_registration(self, _article_id):
        return self._registration

    async def create_registration(self, _article_id):
        return self._registration


class _FakeQuery:
    def __init__(self, data=None, count=None):
        self._data = data or []
        self.count = count

    def select(self, *_args, **_kwargs):
        return self

    def eq(self, *_args, **_kwargs):
        return self

    def order(self, *_args, **_kwargs):
        return self

    def range(self, *_args, **_kwargs):
        return self

    def insert(self, *_args, **_kwargs):
        return self

    def execute(self):
        return SimpleNamespace(data=self._data, count=self.count)


class _FakeSupabase:
    def __init__(self, *, data=None, count=None):
        self._query = _FakeQuery(data=data, count=count)

    def table(self, *_args, **_kwargs):
        return self._query


@pytest.mark.asyncio
async def test_get_doi_status_not_found():
    service = _FakeDOIService(registration=None)

    with pytest.raises(HTTPException) as exc:
        await doi_api.get_doi_status(article_id=UUID(int=1), service=service)
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_retry_doi_registration_rejects_registered(monkeypatch):
    service = _FakeDOIService(registration=_FakeRegistration(reg_id="00000000-0000-0000-0000-000000000001", status="registered"))

    with pytest.raises(HTTPException) as exc:
        await doi_api.retry_doi_registration(article_id=UUID(int=1), service=service)
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_retry_doi_registration_creates_task(monkeypatch):
    service = _FakeDOIService(registration=_FakeRegistration(reg_id="00000000-0000-0000-0000-000000000001", status="failed"))
    monkeypatch.setattr(doi_api, "supabase", _FakeSupabase(data=[{"id": "task-1"}]))

    result = await doi_api.retry_doi_registration(article_id=UUID(int=1), service=service)
    assert result["id"] == "task-1"


@pytest.mark.asyncio
async def test_list_doi_tasks_returns_list(monkeypatch):
    items = [
        {
            "id": "00000000-0000-0000-0000-000000000010",
            "registration_id": "00000000-0000-0000-0000-000000000001",
            "task_type": "register",
            "status": "pending",
            "priority": 0,
            "run_at": "2026-01-01T00:00:00+00:00",
            "attempts": 0,
            "max_attempts": 4,
            "created_at": "2026-01-01T00:00:00+00:00",
        },
        {
            "id": "00000000-0000-0000-0000-000000000011",
            "registration_id": "00000000-0000-0000-0000-000000000001",
            "task_type": "register",
            "status": "pending",
            "priority": 0,
            "run_at": "2026-01-01T00:00:00+00:00",
            "attempts": 0,
            "max_attempts": 4,
            "created_at": "2026-01-01T00:00:00+00:00",
        },
    ]
    monkeypatch.setattr(
        doi_api,
        "supabase",
        _FakeSupabase(data=items, count=2),
    )

    result = await doi_api.list_doi_tasks(status="pending", limit=20, offset=0)
    assert result.total == 2
    assert len(result.items) == 2
