from __future__ import annotations

from types import SimpleNamespace
from uuid import UUID

import pytest

from app.services import invoice_pdf_service


class _FakeStorageBucket:
    def __init__(self, parent):
        self.parent = parent

    def upload(self, path, content, opts):
        self.parent.upload_calls.append((path, content, opts))
        return {"ok": True}

    def create_signed_url(self, path, expires_in):
        return {"signedUrl": f"https://signed.example/{path}?e={expires_in}"}


class _FakeStorage:
    def __init__(self, parent):
        self.parent = parent

    def from_(self, *_args, **_kwargs):
        return _FakeStorageBucket(self.parent)


class _FakeSupabaseAdmin:
    def __init__(self):
        self.invoice = {
            "id": "11111111-1111-1111-1111-111111111111",
            "manuscript_id": "22222222-2222-2222-2222-222222222222",
            "amount": 1234.5,
            "status": "unpaid",
            "confirmed_at": None,
            "invoice_number": "",
            "pdf_path": "",
        }
        self.manuscript = {
            "id": self.invoice["manuscript_id"],
            "title": "Test Manuscript",
            "author_id": "33333333-3333-3333-3333-333333333333",
        }
        self.profile = {"full_name": "Test Author", "email": "author@example.com"}
        self.update_calls: list[tuple[str, dict]] = []
        self.upload_calls: list[tuple[str, bytes, dict]] = []
        self.storage = _FakeStorage(self)

    def table(self, name: str):
        return _FakeQuery(self, name)


class _FakeQuery:
    def __init__(self, parent: _FakeSupabaseAdmin, name: str):
        self.parent = parent
        self.name = name
        self._single = False
        self._update_payload: dict | None = None

    def select(self, *_args, **_kwargs):
        return self

    def eq(self, *_args, **_kwargs):
        return self

    def limit(self, *_args, **_kwargs):
        return self

    def single(self, *_args, **_kwargs):
        self._single = True
        return self

    def update(self, payload: dict):
        self._update_payload = payload
        return self

    def execute(self):
        if self.name == "invoices" and self._single:
            return SimpleNamespace(data=self.parent.invoice)
        if self.name == "manuscripts" and self._single:
            return SimpleNamespace(data=self.parent.manuscript)
        if self.name == "user_profiles" and self._single:
            return SimpleNamespace(data=self.parent.profile)
        if self.name == "invoices" and self._update_payload is not None:
            self.parent.update_calls.append((self.name, self._update_payload))
            return SimpleNamespace(data=[self.parent.invoice])
        return SimpleNamespace(data=[])


def _fake_upload_bytes(*_args, **_kwargs):
    return None


def _fake_pdf_bytes(_html: str) -> bytes:
    # Minimal PDF header to validate downstream behavior without depending on WeasyPrint binary deps
    return b"%PDF-1.4\n%Fake\n"


def test_generate_invoice_pdf_updates_fields_without_touching_payment_status(monkeypatch):
    fake = _FakeSupabaseAdmin()
    monkeypatch.setattr(invoice_pdf_service, "supabase_admin", fake)
    monkeypatch.setattr(invoice_pdf_service, "upload_bytes", _fake_upload_bytes)
    monkeypatch.setattr(invoice_pdf_service, "_html_to_pdf_bytes", _fake_pdf_bytes)

    result = invoice_pdf_service.generate_and_store_invoice_pdf(
        invoice_id=UUID(fake.invoice["id"])
    )

    assert result.pdf_error is None
    assert result.invoice_number
    assert result.invoice_number.startswith("INV-")
    assert result.pdf_path == f"{fake.invoice['manuscript_id']}/{fake.invoice['id']}.pdf"

    # Ensure we never mutate payment status in invoice updates
    assert fake.update_calls, "Expected invoice update"
    payloads = [p for _name, p in fake.update_calls]
    for payload in payloads:
        assert "status" not in payload
        assert "confirmed_at" not in payload


@pytest.mark.parametrize("bad_amount", ["nope", None])
def test_generate_invoice_pdf_handles_amount_parse_errors(monkeypatch, bad_amount):
    fake = _FakeSupabaseAdmin()
    fake.invoice["amount"] = bad_amount
    monkeypatch.setattr(invoice_pdf_service, "supabase_admin", fake)
    monkeypatch.setattr(invoice_pdf_service, "upload_bytes", _fake_upload_bytes)
    monkeypatch.setattr(invoice_pdf_service, "_html_to_pdf_bytes", _fake_pdf_bytes)

    result = invoice_pdf_service.generate_and_store_invoice_pdf(
        invoice_id=UUID(fake.invoice["id"])
    )
    assert result.pdf_error is None

