from types import SimpleNamespace
from uuid import UUID

import pytest
from fastapi import HTTPException

from app.core.config import CrossrefConfig
from app.models.doi import DOIRegistrationStatus
from app.services.doi_service import DOIService


class _DummyUpdateQuery:
    def __init__(self):
        self._rows = [{"id": "m-1"}]

    def update(self, *_args, **_kwargs):
        return self

    def eq(self, *_args, **_kwargs):
        return self

    def execute(self):
        return SimpleNamespace(data=self._rows)


class _DummyClient:
    def table(self, name):
        assert name == "manuscripts"
        return _DummyUpdateQuery()


def test_generate_doi_defaults_without_config():
    svc = DOIService()
    assert svc.generate_doi(2026, 1) == "10.12345/sf.2026.00001"


def test_generate_doi_uses_config_prefix():
    cfg = CrossrefConfig(
        depositor_email="x@example.com",
        depositor_password="pw",
        doi_prefix="10.99999",
        api_url="https://example.com",
        journal_title="J",
        journal_issn=None,
    )
    svc = DOIService(config=cfg)
    assert svc.generate_doi(2026, 2) == "10.99999/sf.2026.00002"


@pytest.mark.asyncio
async def test_create_registration_requires_published(monkeypatch):
    svc = DOIService()
    monkeypatch.setattr(
        svc,
        "_load_manuscript",
        lambda _id: {"id": _id, "status": "under_review", "created_at": "2026-01-01T00:00:00+00:00"},
    )

    with pytest.raises(HTTPException) as exc:
        await svc.create_registration(UUID("00000000-0000-0000-0000-000000000123"))
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_get_registration_returns_none_for_unknown_id(monkeypatch):
    svc = DOIService()
    monkeypatch.setattr(svc, "_load_registration_row", lambda **_kwargs: None)
    assert await svc.get_registration(UUID("11111111-1111-1111-1111-111111111111")) is None


@pytest.mark.asyncio
async def test_retry_registration_rejects_registered(monkeypatch):
    svc = DOIService()

    async def _get_registration(_article_id):
        return SimpleNamespace(id=UUID(int=1), status=DOIRegistrationStatus.REGISTERED)

    monkeypatch.setattr(svc, "get_registration", _get_registration)

    with pytest.raises(HTTPException) as exc:
        await svc.retry_registration(UUID(int=1))
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_register_doi_updates_to_registered(monkeypatch):
    cfg = CrossrefConfig(
        depositor_email="x@example.com",
        depositor_password="pw",
        doi_prefix="10.99999",
        api_url="https://example.com",
        journal_title="J",
        journal_issn=None,
    )
    svc = DOIService(config=cfg, client=_DummyClient())

    registration_state = {
        "id": "00000000-0000-0000-0000-000000000001",
        "article_id": "00000000-0000-0000-0000-000000000002",
        "doi": "10.99999/sf.2026.00001",
        "status": "pending",
        "attempts": 0,
        "crossref_batch_id": None,
        "error_message": None,
        "created_at": "2026-01-01T00:00:00+00:00",
        "registered_at": None,
        "updated_at": "2026-01-01T00:00:00+00:00",
    }

    def _fake_load_registration_by_id(*, registration_id: str):
        assert registration_id == "00000000-0000-0000-0000-000000000001"
        return dict(registration_state)

    def _fake_update_registration(_registration_id: str, updates: dict):
        registration_state.update(updates)
        return dict(registration_state)

    monkeypatch.setattr(svc, "_load_registration_by_id", _fake_load_registration_by_id)
    monkeypatch.setattr(svc, "_update_registration", _fake_update_registration)
    monkeypatch.setattr(
        svc,
        "_load_manuscript",
        lambda _id: {
            "id": _id,
            "status": "published",
            "title": "A",
            "created_at": "2026-01-01T00:00:00+00:00",
            "published_at": "2026-01-01T00:00:00+00:00",
        },
    )
    monkeypatch.setattr(
        svc,
        "_build_crossref_article_data",
        lambda _m, doi: {"doi": doi, "title": "A", "authors": [{"full_name": "Author"}]},
    )
    monkeypatch.setattr(svc, "_create_batch_id", lambda _aid: "batch-1")
    monkeypatch.setattr(svc, "_log_audit", lambda **_kwargs: None)

    class _DummyCrossref:
        def generate_xml(self, *_args, **_kwargs):
            return b"<xml/>"

        async def submit_deposit(self, *_args, **_kwargs):
            return "<batch_id>crossref-batch-42</batch_id>"

    svc.crossref = _DummyCrossref()

    result = await svc.register_doi(UUID("00000000-0000-0000-0000-000000000001"))
    assert result.status == DOIRegistrationStatus.REGISTERED
    assert result.crossref_batch_id == "crossref-batch-42"


@pytest.mark.asyncio
async def test_process_due_tasks_handles_failure(monkeypatch):
    svc = DOIService()

    calls = {"count": 0, "handled": 0}

    def _fake_claim_next_task():
        if calls["count"] == 0:
            calls["count"] += 1
            return {
                "id": "task-1",
                "task_type": "register",
                "registration_id": "00000000-0000-0000-0000-000000000001",
                "attempts": 1,
                "max_attempts": 4,
            }
        return None

    async def _fake_register(_registration_id):
        raise RuntimeError("boom")

    async def _fake_handle_failure(_task, _error):
        calls["handled"] += 1

    monkeypatch.setattr(svc, "_claim_next_task", _fake_claim_next_task)
    monkeypatch.setattr(svc, "register_doi", _fake_register)
    monkeypatch.setattr(svc, "_handle_task_failure", _fake_handle_failure)

    result = await svc.process_due_tasks(limit=5)
    assert result["processed_count"] == 1
    assert result["items"][0]["status"] == "failed"
    assert calls["handled"] == 1
