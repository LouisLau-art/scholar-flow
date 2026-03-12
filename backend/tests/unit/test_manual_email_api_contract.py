from __future__ import annotations

from typing import Any
from uuid import UUID

import pytest
from httpx import AsyncClient
from unittest.mock import MagicMock, patch


class _Resp:
    def __init__(self, data: Any):
        self.data = data
        self.error = None


class _Table:
    def __init__(self, client: "_Client", name: str):
        self._client = client
        self._name = name
        self._pending_insert_payload = None
        self._pending_update_payload = None

    def select(self, *_args, **_kwargs):
        return self

    def eq(self, *_args, **_kwargs):
        return self

    def limit(self, *_args, **_kwargs):
        return self

    def single(self):
        return self

    def insert(self, payload=None, *_args, **_kwargs):
        self._pending_insert_payload = payload
        return self

    def update(self, payload=None, *_args, **_kwargs):
        self._pending_update_payload = payload
        return self

    def execute(self):
        if self._pending_insert_payload is not None:
            self._client._insert_calls.setdefault(self._name, []).append(self._pending_insert_payload)
            self._pending_insert_payload = None
        if self._pending_update_payload is not None:
            self._client._update_calls.setdefault(self._name, []).append(self._pending_update_payload)
            self._pending_update_payload = None
        return _Resp(self._client._pop(self._name))


class _StorageBucket:
    def __init__(self, content: bytes):
        self._content = content

    def download(self, _path: str):
        return self._content


class _Storage:
    def __init__(self, content: bytes):
        self._content = content

    def from_(self, _bucket: str):
        return _StorageBucket(self._content)


class _Client:
    def __init__(self, responses: dict[str, list[Any]], *, storage_bytes: bytes = b"%PDF-1.4 mock"):
        self._responses = responses
        self._insert_calls: dict[str, list[Any]] = {}
        self._update_calls: dict[str, list[Any]] = {}
        self.storage = _Storage(storage_bytes)

    def table(self, name: str):
        return _Table(self, name)

    def _pop(self, name: str):
        queue = self._responses.get(name) or []
        if not queue:
            return []
        return queue.pop(0)


@pytest.mark.asyncio
async def test_invoice_email_preview_returns_resolved_recipients_and_attachment_manifest(
    client: AsyncClient,
    auth_token: str,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("ADMIN_EMAILS", "test@example.com")
    invoice_id = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaa11")
    manuscript_id = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbb111")

    supabase_admin = _Client(
        {
            "invoices": [
                {
                    "id": str(invoice_id),
                    "manuscript_id": str(manuscript_id),
                    "amount": 1200,
                    "status": "unpaid",
                    "invoice_number": "INV-2026-TEST",
                    "pdf_path": f"{manuscript_id}/{invoice_id}.pdf",
                    "pdf_generated_at": "2026-03-12T10:00:00Z",
                    "pdf_error": None,
                },
            ],
            "manuscripts": [
                {
                    "id": str(manuscript_id),
                    "title": "Invoice Contract Manuscript",
                    "author_id": "author-1",
                    "journal_id": "journal-1",
                    "submission_email": "login@example.org",
                    "author_contacts": [
                        {"name": "Corr Author", "email": "corr@example.org", "is_corresponding": True},
                        {"name": "Co Author", "email": "co@example.org", "is_corresponding": False},
                    ],
                }
            ],
            "journals": [
                {"title": "Journal One", "public_editorial_email": "office@example.org"},
            ],
        }
    )

    with patch("app.api.v1.invoices.supabase_admin", supabase_admin):
        resp = await client.post(
            f"/api/v1/invoices/{invoice_id}/email/preview",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={},
        )

    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["resolved_recipients"]["to"] == ["corr@example.org"]
    assert data["resolved_recipients"]["cc"] == ["co@example.org", "office@example.org"]
    assert data["reply_to"] == ["office@example.org"]
    assert data["attachments"] == [
        {
            "filename": "INV-2026-TEST.pdf",
            "content_type": "application/pdf",
        }
    ]
    assert data["delivery_mode"] == "manual"
    assert data["can_send"] is True


@pytest.mark.asyncio
async def test_invoice_email_send_uses_pdf_attachment_and_resolved_recipients(
    client: AsyncClient,
    auth_token: str,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("ADMIN_EMAILS", "test@example.com")
    invoice_id = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaa12")
    manuscript_id = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbb112")

    supabase_admin = _Client(
        {
            "invoices": [
                {
                    "id": str(invoice_id),
                    "manuscript_id": str(manuscript_id),
                    "amount": 900,
                    "status": "unpaid",
                    "invoice_number": "INV-2026-SEND",
                    "pdf_path": f"{manuscript_id}/{invoice_id}.pdf",
                    "pdf_generated_at": "2026-03-12T10:00:00Z",
                    "pdf_error": None,
                },
            ],
            "manuscripts": [
                {
                    "id": str(manuscript_id),
                    "title": "Invoice Send Manuscript",
                    "author_id": "author-1",
                    "journal_id": "journal-1",
                    "submission_email": "login@example.org",
                    "author_contacts": [
                        {"name": "Corr Author", "email": "corr@example.org", "is_corresponding": True},
                        {"name": "Co Author", "email": "co@example.org", "is_corresponding": False},
                    ],
                }
            ],
            "journals": [
                {"title": "Journal One", "public_editorial_email": "office@example.org"},
            ],
        }
    )
    send_mock = MagicMock(
        return_value={
            "ok": True,
            "status": "sent",
            "subject": "Invoice for Invoice Send Manuscript",
            "provider_id": "re_invoice_123",
            "error_message": None,
        }
    )

    with (
        patch("app.api.v1.invoices.supabase_admin", supabase_admin),
        patch("app.api.v1.invoices.email_service.send_rendered_email", send_mock),
    ):
        resp = await client.post(
            f"/api/v1/invoices/{invoice_id}/email/send",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={},
        )

    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["delivery_status"] == "sent"
    send_kwargs = send_mock.call_args.kwargs
    assert send_kwargs["to_emails"] == ["corr@example.org"]
    assert send_kwargs["cc_emails"] == ["co@example.org", "office@example.org"]
    assert send_kwargs["reply_to_emails"] == ["office@example.org"]
    assert send_kwargs["attachments"][0]["filename"] == "INV-2026-SEND.pdf"
    assert send_kwargs["attachments"][0]["content_type"] == "application/pdf"


@pytest.mark.asyncio
async def test_invoice_email_mark_external_sent_logs_external_delivery(
    client: AsyncClient,
    auth_token: str,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("ADMIN_EMAILS", "test@example.com")
    invoice_id = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaa13")
    manuscript_id = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbb113")

    supabase_admin = _Client(
        {
            "invoices": [
                {
                    "id": str(invoice_id),
                    "manuscript_id": str(manuscript_id),
                    "amount": 900,
                    "status": "unpaid",
                    "invoice_number": "INV-2026-EXT",
                    "pdf_path": f"{manuscript_id}/{invoice_id}.pdf",
                    "pdf_generated_at": "2026-03-12T10:00:00Z",
                    "pdf_error": None,
                },
            ],
            "manuscripts": [
                {
                    "id": str(manuscript_id),
                    "title": "Invoice External Manuscript",
                    "author_id": "author-1",
                    "journal_id": "journal-1",
                    "submission_email": "login@example.org",
                    "author_contacts": [
                        {"name": "Corr Author", "email": "corr@example.org", "is_corresponding": True},
                        {"name": "Co Author", "email": "co@example.org", "is_corresponding": False},
                    ],
                }
            ],
            "journals": [
                {"title": "Journal One", "public_editorial_email": "office@example.org"},
            ],
        }
    )
    log_mock = MagicMock()

    with (
        patch("app.api.v1.invoices.supabase_admin", supabase_admin),
        patch("app.api.v1.invoices.email_service.log_attempt", log_mock),
    ):
        resp = await client.post(
            f"/api/v1/invoices/{invoice_id}/email/mark-external-sent",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={"channel": "gmail_web"},
        )

    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["communication_status"] == "external_sent"
    assert data["recipient"] == "corr@example.org"
    log_kwargs = log_mock.call_args.kwargs
    assert log_kwargs["provider"] == "gmail_web"
    assert log_kwargs["to_recipients"] == ["corr@example.org"]
    assert log_kwargs["cc_recipients"] == ["co@example.org", "office@example.org"]
    assert log_kwargs["reply_to_recipients"] == ["office@example.org"]
    assert log_kwargs["audit_context"]["communication_status"] == "external_sent"
