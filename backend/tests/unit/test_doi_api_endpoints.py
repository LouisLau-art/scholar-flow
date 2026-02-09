from uuid import UUID

import pytest
from fastapi import HTTPException

from app.api.v1 import doi as doi_api
from app.models.doi import (
    DOIRegistration,
    DOIRegistrationStatus,
    DOITask,
    DOITaskList,
    DOITaskStatus,
    DOITaskType,
)


class _FakeDOIService:
    def __init__(self, registration=None, task=None, task_list=None):
        self._registration = registration
        self._task = task
        self._task_list = task_list

    async def get_registration(self, _article_id):
        return self._registration

    async def create_registration(self, _article_id):
        if self._registration is None:
            raise HTTPException(status_code=404, detail="not found")
        return self._registration

    async def retry_registration(self, _article_id):
        if self._task is None:
            raise HTTPException(status_code=404, detail="not found")
        return self._task

    async def list_tasks(self, **_kwargs):
        return self._task_list


def _make_registration(status: DOIRegistrationStatus = DOIRegistrationStatus.PENDING) -> DOIRegistration:
    return DOIRegistration(
        id=UUID("00000000-0000-0000-0000-000000000001"),
        article_id=UUID("00000000-0000-0000-0000-000000000010"),
        doi="10.12345/sf.2026.00001",
        status=status,
        attempts=0,
        crossref_batch_id=None,
        error_message=None,
        registered_at=None,
        created_at="2026-01-01T00:00:00+00:00",
        updated_at="2026-01-01T00:00:00+00:00",
    )


def _make_task() -> DOITask:
    return DOITask(
        id=UUID("00000000-0000-0000-0000-000000000020"),
        registration_id=UUID("00000000-0000-0000-0000-000000000001"),
        task_type=DOITaskType.REGISTER,
        status=DOITaskStatus.PENDING,
        priority=10,
        run_at="2026-01-01T00:00:00+00:00",
        locked_at=None,
        locked_by=None,
        attempts=0,
        max_attempts=4,
        last_error=None,
        created_at="2026-01-01T00:00:00+00:00",
        completed_at=None,
    )


@pytest.mark.asyncio
async def test_get_doi_status_not_found():
    service = _FakeDOIService(registration=None)

    with pytest.raises(HTTPException) as exc:
        await doi_api.get_doi_status(article_id=UUID(int=1), service=service)
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_register_doi_returns_registration():
    reg = _make_registration()
    service = _FakeDOIService(registration=reg)

    result = await doi_api.register_doi(
        request=doi_api.DOIRegistrationCreate(article_id=UUID(int=1)),
        service=service,
    )
    assert result.id == reg.id


@pytest.mark.asyncio
async def test_retry_doi_registration_returns_task():
    task = _make_task()
    service = _FakeDOIService(task=task)

    result = await doi_api.retry_doi_registration(article_id=UUID(int=1), service=service)
    assert result.id == task.id


@pytest.mark.asyncio
async def test_list_doi_tasks_returns_list():
    task = _make_task()
    task_list = DOITaskList(items=[task], total=1, limit=20, offset=0)
    service = _FakeDOIService(task_list=task_list)

    result = await doi_api.list_doi_tasks(status="pending", limit=20, offset=0, service=service)
    assert result.total == 1
    assert len(result.items) == 1


@pytest.mark.asyncio
async def test_list_failed_tasks_returns_list():
    task = _make_task()
    task_list = DOITaskList(items=[task], total=1, limit=20, offset=0)
    service = _FakeDOIService(task_list=task_list)

    result = await doi_api.list_failed_tasks(limit=20, offset=0, service=service)
    assert result.total == 1
