from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.services.production_service import ProductionService


class _FakeSupabaseAdmin:
    def __init__(self, *, manuscript: dict, invoices: list[dict] | None):
        self._manuscript = manuscript
        self._invoices = invoices

    def table(self, name: str):
        return _FakeQuery(self, name)


class _FakeQuery:
    def __init__(self, parent: _FakeSupabaseAdmin, name: str):
        self.parent = parent
        self.name = name
        self._single = False

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

    def execute(self):
        if self.name == "manuscripts" and self._single:
            return SimpleNamespace(data=self.parent._manuscript)
        if self.name == "invoices":
            return SimpleNamespace(data=self.parent._invoices or [])
        return SimpleNamespace(data=[])


@dataclass
class _FakeEditorial:
    last_args: dict | None = None

    def update_status(self, **kwargs):
        self.last_args = kwargs
        # mimic supabase update return row
        return {"id": kwargs["manuscript_id"], "status": kwargs["to_status"]}


def test_advance_from_approved_to_layout(monkeypatch):
    from app.services import production_service as prod_mod

    fake_admin = _FakeSupabaseAdmin(manuscript={"id": "m1", "status": "approved"}, invoices=None)
    monkeypatch.setattr(prod_mod, "supabase_admin", fake_admin)

    editorial = _FakeEditorial()
    svc = ProductionService(editorial=editorial)
    out = svc.advance(manuscript_id="m1", changed_by="u1")

    assert out.previous_status == "approved"
    assert out.new_status == "layout"
    assert (editorial.last_args or {}).get("to_status") == "layout"


def test_revert_from_proofreading_to_english_editing(monkeypatch):
    from app.services import production_service as prod_mod

    fake_admin = _FakeSupabaseAdmin(manuscript={"id": "m1", "status": "proofreading"}, invoices=None)
    monkeypatch.setattr(prod_mod, "supabase_admin", fake_admin)

    editorial = _FakeEditorial()
    svc = ProductionService(editorial=editorial)
    out = svc.revert(manuscript_id="m1", changed_by="u1")

    assert out.previous_status == "proofreading"
    assert out.new_status == "english_editing"


def test_publish_blocks_when_invoice_unpaid(monkeypatch):
    from app.services import production_service as prod_mod

    fake_admin = _FakeSupabaseAdmin(
        manuscript={"id": "m1", "status": "proofreading", "final_pdf_path": "production/m1/final.pdf"},
        invoices=[{"amount": 100, "status": "unpaid"}],
    )
    monkeypatch.setattr(prod_mod, "supabase_admin", fake_admin)

    svc = ProductionService(editorial=_FakeEditorial())
    with pytest.raises(HTTPException) as exc:
        svc.advance(manuscript_id="m1", changed_by="u1")
    assert exc.value.status_code == 403


def test_publish_blocks_when_production_gate_enabled_and_pdf_missing(monkeypatch):
    from app.services import production_service as prod_mod

    fake_admin = _FakeSupabaseAdmin(
        manuscript={"id": "m1", "status": "proofreading", "final_pdf_path": ""},
        invoices=[{"amount": 100, "status": "paid"}],
    )
    monkeypatch.setattr(prod_mod, "supabase_admin", fake_admin)
    monkeypatch.setenv("PRODUCTION_GATE_ENABLED", "1")

    svc = ProductionService(editorial=_FakeEditorial())
    with pytest.raises(HTTPException) as exc:
        svc.advance(manuscript_id="m1", changed_by="u1")
    assert exc.value.status_code == 400


def test_publish_succeeds_and_passes_extra_updates(monkeypatch):
    from app.services import production_service as prod_mod

    fake_admin = _FakeSupabaseAdmin(
        manuscript={"id": "m1", "status": "proofreading", "final_pdf_path": "production/m1/final.pdf"},
        invoices=[{"amount": 100, "status": "paid"}],
    )
    monkeypatch.setattr(prod_mod, "supabase_admin", fake_admin)
    monkeypatch.setenv("PRODUCTION_GATE_ENABLED", "1")

    editorial = _FakeEditorial()
    svc = ProductionService(editorial=editorial)
    out = svc.advance(manuscript_id="m1", changed_by="u1")

    assert out.new_status == "published"
    args = editorial.last_args or {}
    assert args.get("to_status") == "published"
    extra = args.get("extra_updates") or {}
    assert "published_at" in extra
    assert "doi" in extra


def test_advance_rejects_non_post_acceptance_status(monkeypatch):
    from app.services import production_service as prod_mod

    fake_admin = _FakeSupabaseAdmin(manuscript={"id": "m1", "status": "decision"}, invoices=None)
    monkeypatch.setattr(prod_mod, "supabase_admin", fake_admin)

    svc = ProductionService(editorial=_FakeEditorial())
    with pytest.raises(HTTPException) as exc:
        svc.advance(manuscript_id="m1", changed_by="u1")
    assert exc.value.status_code == 400
