from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.api.v1 import editor as editor_api
from app.services import post_acceptance_service


class _FakeStorageBucket:
    def upload(self, *_args, **_kwargs):
        return {"ok": True}


class _FakeStorage:
    def from_(self, *_args, **_kwargs):
        return _FakeStorageBucket()


class _FakeSupabaseAdmin:
    def __init__(self, *, manuscript=None, invoices=None, update_result=None):
        self._manuscript = manuscript or {"id": "m-1", "status": "approved"}
        self._invoices = invoices
        self._update_result = update_result or [{"id": "m-1", "status": "published", "doi": "10.1234/x"}]
        self.storage = _FakeStorage()

    def table(self, name: str):
        return _FakeQuery(self, name)


class _FakeQuery:
    def __init__(self, parent: _FakeSupabaseAdmin, name: str):
        self.parent = parent
        self.name = name
        self._single = False
        self._update_payload = None

    def select(self, *_args, **_kwargs):
        return self

    def eq(self, *_args, **_kwargs):
        return self

    def limit(self, *_args, **_kwargs):
        return self

    def order(self, *_args, **_kwargs):
        return self

    def single(self, *_args, **_kwargs):
        self._single = True
        return self

    def update(self, payload):
        self._update_payload = payload
        return self

    def execute(self):
        if self.name == "manuscripts" and self._single:
            return SimpleNamespace(data=self.parent._manuscript)
        if self.name == "invoices":
            return SimpleNamespace(data=self.parent._invoices or [])
        if self.name == "manuscripts" and self._update_payload is not None:
            return SimpleNamespace(data=self.parent._update_result)
        return SimpleNamespace(data=[])


@pytest.mark.asyncio
async def test_publish_blocks_when_invoice_unpaid(monkeypatch):
    fake = _FakeSupabaseAdmin(
        manuscript={"id": "m-1", "status": "approved"},
        invoices=[{"amount": 100, "status": "unpaid"}],
    )
    monkeypatch.setattr(post_acceptance_service, "supabase_admin", fake)
    monkeypatch.setattr(editor_api, "supabase_admin", fake)

    with pytest.raises(HTTPException) as exc:
        await editor_api.publish_manuscript_dev(
            current_user={"id": "u-1"},
            _profile={"roles": ["editor"]},
            manuscript_id="m-1",
        )

    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_publish_allows_when_invoice_paid(monkeypatch):
    fake = _FakeSupabaseAdmin(
        manuscript={"id": "m-1", "status": "approved", "final_pdf_path": "production/m-1/final.pdf"},
        invoices=[{"amount": 100, "status": "paid"}],
        update_result=[{"id": "m-1", "status": "published"}],
    )
    monkeypatch.setattr(post_acceptance_service, "supabase_admin", fake)
    monkeypatch.setattr(editor_api, "supabase_admin", fake)

    result = await editor_api.publish_manuscript_dev(
        current_user={"id": "u-1"},
        _profile={"roles": ["editor"]},
        manuscript_id="m-1",
    )

    assert result["success"] is True
    assert result["data"]["status"] == "published"


@pytest.mark.asyncio
async def test_publish_blocks_when_invoice_missing_for_approved(monkeypatch):
    fake = _FakeSupabaseAdmin(
        manuscript={"id": "m-1", "status": "approved"},
        invoices=[],
    )
    monkeypatch.setattr(post_acceptance_service, "supabase_admin", fake)
    monkeypatch.setattr(editor_api, "supabase_admin", fake)

    with pytest.raises(HTTPException) as exc:
        await editor_api.publish_manuscript_dev(
            current_user={"id": "u-1"},
            _profile={"roles": ["editor"]},
            manuscript_id="m-1",
        )

    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_accept_requires_apc_amount():
    with pytest.raises(HTTPException) as exc:
        await editor_api.submit_final_decision(
            current_user={"id": "u-1"},
            manuscript_id="m-1",
            decision="accept",
            comment="",
            apc_amount=None,
        )
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_accept_rejects_negative_apc():
    with pytest.raises(HTTPException) as exc:
        await editor_api.submit_final_decision(
            current_user={"id": "u-1"},
            manuscript_id="m-1",
            decision="accept",
            comment="",
            apc_amount=-1,
        )
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_publish_allows_when_invoice_missing_for_non_approved(monkeypatch):
    fake = _FakeSupabaseAdmin(
        manuscript={"id": "m-1", "status": "pre_check"},
        invoices=[],
        update_result=[{"id": "m-1", "status": "published"}],
    )
    monkeypatch.setattr(post_acceptance_service, "supabase_admin", fake)
    monkeypatch.setattr(editor_api, "supabase_admin", fake)

    result = await editor_api.publish_manuscript_dev(
        current_user={"id": "u-1"},
        _profile={"roles": ["editor"]},
        manuscript_id="m-1",
    )
    assert result["success"] is True
    assert result["data"]["status"] == "published"


@pytest.mark.asyncio
async def test_publish_allows_when_invoice_amount_not_numeric(monkeypatch):
    fake = _FakeSupabaseAdmin(
        manuscript={"id": "m-1", "status": "approved", "final_pdf_path": "production/m-1/final.pdf"},
        invoices=[{"amount": "not-a-number", "status": "unpaid"}],
        update_result=[{"id": "m-1", "status": "published"}],
    )
    monkeypatch.setattr(post_acceptance_service, "supabase_admin", fake)
    monkeypatch.setattr(editor_api, "supabase_admin", fake)

    result = await editor_api.publish_manuscript_dev(
        current_user={"id": "u-1"},
        _profile={"roles": ["editor"]},
        manuscript_id="m-1",
    )
    assert result["success"] is True
    assert result["data"]["status"] == "published"


@pytest.mark.asyncio
async def test_publish_blocks_when_final_pdf_missing(monkeypatch):
    fake = _FakeSupabaseAdmin(
        manuscript={"id": "m-1", "status": "approved", "final_pdf_path": ""},
        invoices=[{"amount": 100, "status": "paid"}],
        update_result=[{"id": "m-1", "status": "published"}],
    )
    monkeypatch.setattr(post_acceptance_service, "supabase_admin", fake)
    monkeypatch.setattr(editor_api, "supabase_admin", fake)
    monkeypatch.setenv("PRODUCTION_GATE_ENABLED", "1")

    with pytest.raises(HTTPException) as exc:
        await editor_api.publish_manuscript_dev(
            current_user={"id": "u-1"},
            _profile={"roles": ["editor"]},
            manuscript_id="m-1",
        )
    assert exc.value.status_code == 400
