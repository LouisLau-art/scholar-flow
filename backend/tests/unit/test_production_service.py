from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.services.production_service import ProductionService


class _FakeSupabaseAdmin:
    def __init__(
        self,
        *,
        manuscript: dict,
        invoices: list[dict] | None,
        manuscript_error: Exception | None = None,
        invoice_error: Exception | None = None,
    ):
        self._manuscript = manuscript
        self._invoices = invoices
        self._manuscript_error = manuscript_error
        self._invoice_error = invoice_error

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
            if self.parent._manuscript_error is not None:
                raise self.parent._manuscript_error
            return SimpleNamespace(data=self.parent._manuscript)
        if self.name == "invoices":
            if self.parent._invoice_error is not None:
                raise self.parent._invoice_error
            return SimpleNamespace(data=self.parent._invoices or [])
        return SimpleNamespace(data=[])


@dataclass
class _FakeEditorial:
    last_args: dict | None = None

    def update_status(self, **kwargs):
        self.last_args = kwargs
        # mimic supabase update return row
        return {"id": kwargs["manuscript_id"], "status": kwargs["to_status"]}


@dataclass
class _FakeWorkspace:
    gate_result: dict | None = None
    last_manuscript_id: str | None = None

    def assert_publish_gate_ready(self, *, manuscript_id: str):
        self.last_manuscript_id = manuscript_id
        return self.gate_result


@pytest.mark.parametrize("status", ["approved", "proofreading", "english_editing", "decision"])
def test_advance_rejects_unsupported_direct_publish_status(monkeypatch, status: str):
    from app.services import production_service as prod_mod

    fake_admin = _FakeSupabaseAdmin(manuscript={"id": "m1", "status": status}, invoices=None)
    monkeypatch.setattr(prod_mod, "supabase_admin", fake_admin)

    editorial = _FakeEditorial()
    svc = ProductionService(editorial=editorial)
    with pytest.raises(HTTPException) as exc:
        svc.advance(manuscript_id="m1", changed_by="u1")

    assert exc.value.status_code == 400
    assert "only allows advance to published" in exc.value.detail


def test_revert_rejects_direct_status_revert(monkeypatch):
    from app.services import production_service as prod_mod

    fake_admin = _FakeSupabaseAdmin(manuscript={"id": "m1", "status": "proofreading"}, invoices=None)
    monkeypatch.setattr(prod_mod, "supabase_admin", fake_admin)

    editorial = _FakeEditorial()
    svc = ProductionService(editorial=editorial)
    with pytest.raises(HTTPException) as exc:
        svc.revert(manuscript_id="m1", changed_by="u1")

    assert exc.value.status_code == 400
    assert "no longer supported" in exc.value.detail


def test_publish_blocks_when_invoice_unpaid(monkeypatch):
    from app.services import production_service as prod_mod

    fake_admin = _FakeSupabaseAdmin(
        manuscript={"id": "m1", "status": "approved_for_publish", "final_pdf_path": "production/m1/final.pdf"},
        invoices=[{"amount": 100, "status": "unpaid"}],
    )
    monkeypatch.setattr(prod_mod, "supabase_admin", fake_admin)

    svc = ProductionService(editorial=_FakeEditorial(), workspace=_FakeWorkspace())
    with pytest.raises(HTTPException) as exc:
        svc.advance(manuscript_id="m1", changed_by="u1")
    assert exc.value.status_code == 403


def test_publish_blocks_when_production_gate_enabled_and_pdf_missing(monkeypatch):
    from app.services import production_service as prod_mod

    fake_admin = _FakeSupabaseAdmin(
        manuscript={"id": "m1", "status": "approved_for_publish", "final_pdf_path": ""},
        invoices=[{"amount": 100, "status": "paid"}],
    )
    monkeypatch.setattr(prod_mod, "supabase_admin", fake_admin)
    monkeypatch.setenv("PRODUCTION_GATE_ENABLED", "1")

    svc = ProductionService(editorial=_FakeEditorial(), workspace=_FakeWorkspace(gate_result={"id": "cycle-1"}))
    with pytest.raises(HTTPException) as exc:
        svc.advance(manuscript_id="m1", changed_by="u1")
    assert exc.value.status_code == 400


def test_publish_succeeds_and_passes_extra_updates(monkeypatch):
    from app.services import production_service as prod_mod

    fake_admin = _FakeSupabaseAdmin(
        manuscript={"id": "m1", "status": "approved_for_publish", "final_pdf_path": "production/m1/final.pdf"},
        invoices=[{"amount": 100, "status": "paid"}],
    )
    monkeypatch.setattr(prod_mod, "supabase_admin", fake_admin)
    monkeypatch.setenv("PRODUCTION_GATE_ENABLED", "1")

    editorial = _FakeEditorial()
    workspace = _FakeWorkspace(gate_result={"id": "cycle-1"})
    svc = ProductionService(editorial=editorial, workspace=workspace)
    out = svc.advance(manuscript_id="m1", changed_by="u1")

    assert out.new_status == "published"
    args = editorial.last_args or {}
    assert args.get("to_status") == "published"
    extra = args.get("extra_updates") or {}
    assert "published_at" in extra
    assert "doi" in extra
    assert workspace.last_manuscript_id == "m1"


def test_publish_raises_503_when_invoice_schema_missing(monkeypatch):
    from app.services import production_service as prod_mod

    fake_admin = _FakeSupabaseAdmin(
        manuscript={"id": "m1", "status": "approved_for_publish", "final_pdf_path": "production/m1/final.pdf"},
        invoices=None,
        invoice_error=RuntimeError('Could not find the table "public.invoices" in the schema cache (PGRST205)'),
    )
    monkeypatch.setattr(prod_mod, "supabase_admin", fake_admin)

    svc = ProductionService(editorial=_FakeEditorial(), workspace=_FakeWorkspace(gate_result={"id": "cycle-1"}))
    with pytest.raises(HTTPException) as exc:
        svc.advance(manuscript_id="m1", changed_by="u1")

    assert exc.value.status_code == 503
    assert str(exc.value.detail).startswith("Production SOP schema not migrated:")


def test_publish_raises_503_when_final_pdf_column_missing_and_gate_enabled(monkeypatch):
    from app.services import production_service as prod_mod

    fake_admin = _FakeSupabaseAdmin(
        manuscript={},
        invoices=[{"amount": 100, "status": "paid"}],
        manuscript_error=RuntimeError('column "final_pdf_path" does not exist'),
    )
    monkeypatch.setattr(prod_mod, "supabase_admin", fake_admin)
    monkeypatch.setenv("PRODUCTION_GATE_ENABLED", "1")

    svc = ProductionService(editorial=_FakeEditorial(), workspace=_FakeWorkspace(gate_result={"id": "cycle-1"}))
    with pytest.raises(HTTPException) as exc:
        svc.advance(manuscript_id="m1", changed_by="u1")

    assert exc.value.status_code == 503
    assert str(exc.value.detail).startswith("Production SOP schema not migrated:")
