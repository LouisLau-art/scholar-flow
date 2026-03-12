from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, EmailStr, field_validator

from app.api.v1.editor_common import resolve_author_notification_target
from app.core.auth_utils import get_current_user
from app.core.email_normalization import normalize_email
from app.core.mail import email_service
from app.core.roles import get_current_profile, require_any_role
from app.lib.api_client import supabase_admin
from app.models.email_log import EmailStatus
from app.services.invoice_pdf_service import (
    generate_and_store_invoice_pdf,
    get_invoice_pdf_signed_url,
)

router = APIRouter(prefix="/invoices", tags=["Invoices"])


class InvoiceEmailActionPayload(BaseModel):
    model_config = ConfigDict(extra="ignore")

    subject_override: str | None = None
    html_override: str | None = None
    idempotency_key: str | None = None
    channel: str | None = "other"
    to_override: list[EmailStr] | None = None
    cc_override: list[EmailStr] | None = None
    bcc_override: list[EmailStr] | None = None
    reply_to_override: list[EmailStr] | None = None

    @field_validator("subject_override", "html_override", "idempotency_key", "channel", mode="before")
    @classmethod
    def _normalize_text(cls, value: Any) -> Any:
        if value is None:
            return None
        normalized = str(value).strip()
        return normalized or None

    @field_validator("to_override", "cc_override", "bcc_override", "reply_to_override", mode="before")
    @classmethod
    def _normalize_email_list(cls, value: Any) -> list[str] | None:
        if value is None:
            return None
        raw = [value] if isinstance(value, str) else list(value)
        normalized: list[str] = []
        for item in raw:
            email = normalize_email(item)
            if email and email not in normalized:
                normalized.append(email)
        return normalized


def _normalize_email_list(emails: list[str] | None) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for item in emails or []:
        email = normalize_email(item)
        if not email or email in seen:
            continue
        seen.add(email)
        normalized.append(email)
    return normalized


def _ensure_invoice_email_context(invoice_id: UUID) -> dict[str, Any]:
    inv_resp = (
        supabase_admin.table("invoices")
        .select("id, manuscript_id, amount, status, invoice_number, pdf_path, pdf_generated_at, pdf_error")
        .eq("id", str(invoice_id))
        .single()
        .execute()
    )
    invoice = getattr(inv_resp, "data", None) or {}
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    manuscript_id = str(invoice.get("manuscript_id") or "").strip()
    if not manuscript_id:
        raise HTTPException(status_code=500, detail="Invoice missing manuscript_id")

    if not str(invoice.get("pdf_path") or "").strip() or str(invoice.get("pdf_error") or "").strip():
        result = generate_and_store_invoice_pdf(invoice_id=invoice_id)
        if result.pdf_error:
            raise HTTPException(status_code=500, detail=f"Failed to generate invoice pdf: {result.pdf_error}")
        invoice["pdf_path"] = result.pdf_path
        invoice["invoice_number"] = result.invoice_number
        invoice["pdf_generated_at"] = result.pdf_generated_at
        invoice["pdf_error"] = result.pdf_error

    ms_resp = (
        supabase_admin.table("manuscripts")
        .select("id, title, author_id, journal_id, submission_email, author_contacts")
        .eq("id", manuscript_id)
        .single()
        .execute()
    )
    manuscript = getattr(ms_resp, "data", None) or {}
    if not manuscript:
        raise HTTPException(status_code=404, detail="Manuscript not found")

    journal_title = "ScholarFlow Journal"
    journal_public_editorial_email = None
    journal_id = str(manuscript.get("journal_id") or "").strip()
    if journal_id:
        try:
            jr = (
                supabase_admin.table("journals")
                .select("title, public_editorial_email")
                .eq("id", journal_id)
                .single()
                .execute()
            )
            jr_data = getattr(jr, "data", None) or {}
            journal_title = str(jr_data.get("title") or journal_title).strip() or journal_title
            journal_public_editorial_email = normalize_email(jr_data.get("public_editorial_email"))
        except Exception:
            pass

    if journal_public_editorial_email:
        manuscript["journal_public_editorial_email"] = journal_public_editorial_email

    target = resolve_author_notification_target(
        manuscript=manuscript,
        manuscript_id=manuscript_id,
        supabase_client=supabase_admin,
    )
    if not target.get("recipient_email"):
        raise HTTPException(status_code=422, detail="No author email available for invoice delivery")

    manuscript_title = str(manuscript.get("title") or "Manuscript").strip() or "Manuscript"
    invoice_number = str(invoice.get("invoice_number") or "").strip() or f"INV-{invoice_id}"
    recipient_name = str(target.get("recipient_name") or "Author").strip() or "Author"
    amount_display = f"USD {float(invoice.get('amount') or 0):,.2f}"
    subject = f"Invoice for {manuscript_title}"
    html = (
        f"<p>Dear {recipient_name},</p>"
        f"<p>Please find attached the invoice for <strong>{manuscript_title}</strong>.</p>"
        f"<p>Journal: <strong>{journal_title}</strong><br/>"
        f"Invoice Number: <strong>{invoice_number}</strong><br/>"
        f"Amount: <strong>{amount_display}</strong></p>"
        "<p>Please contact the editorial office if any detail needs correction.</p>"
    )
    text = email_service.derive_plain_text_from_html(html)
    attachment_name = f"{invoice_number}.pdf"
    return {
        "invoice": invoice,
        "manuscript": manuscript,
        "journal_title": journal_title,
        "target": target,
        "subject": subject,
        "html": html,
        "text": text,
        "attachment_name": attachment_name,
    }


def _resolve_invoice_email_envelope(
    *,
    target: dict[str, Any],
    payload: InvoiceEmailActionPayload,
) -> dict[str, list[str]]:
    to_recipients = _normalize_email_list(payload.to_override) or _normalize_email_list(target.get("to_recipients"))
    cc_recipients = (
        _normalize_email_list(payload.cc_override)
        if payload.cc_override is not None
        else _normalize_email_list(target.get("cc_recipients"))
    )
    bcc_recipients = (
        _normalize_email_list(payload.bcc_override)
        if payload.bcc_override is not None
        else _normalize_email_list(target.get("bcc_recipients"))
    )
    reply_to_recipients = (
        _normalize_email_list(payload.reply_to_override)
        if payload.reply_to_override is not None
        else _normalize_email_list(target.get("reply_to_recipients"))
    )
    if not to_recipients:
        recipient_email = normalize_email(target.get("recipient_email"))
        if recipient_email:
            to_recipients = [recipient_email]
    return {
        "to": to_recipients,
        "cc": cc_recipients,
        "bcc": bcc_recipients,
        "reply_to": reply_to_recipients,
    }


def _download_invoice_pdf_bytes(pdf_path: str) -> bytes:
    payload = supabase_admin.storage.from_("invoices").download(pdf_path)
    if isinstance(payload, bytes):
        return payload
    if isinstance(payload, bytearray):
        return bytes(payload)
    content = getattr(payload, "content", None)
    if isinstance(content, bytes):
        return content
    raise RuntimeError("Failed to download invoice pdf bytes")


def _build_invoice_email_preview(invoice_id: UUID, payload: InvoiceEmailActionPayload) -> dict[str, Any]:
    context = _ensure_invoice_email_context(invoice_id)
    subject = str(payload.subject_override or context["subject"]).strip() or context["subject"]
    html = str(payload.html_override or context["html"]).strip() or context["html"]
    envelope = _resolve_invoice_email_envelope(target=context["target"], payload=payload)
    return {
        "invoice_id": str(invoice_id),
        "recipient_source": context["target"].get("source"),
        "resolved_recipients": envelope,
        "subject": subject,
        "html": html,
        "text": email_service.derive_plain_text_from_html(html),
        "reply_to": envelope["reply_to"],
        "attachments": [
            {
                "filename": context["attachment_name"],
                "content_type": "application/pdf",
            }
        ],
        "delivery_mode": "manual",
        "idempotency_key": str(payload.idempotency_key or f"invoice-email/{invoice_id}"),
        "can_send": True,
        "context": context,
    }


@router.post("/{invoice_id}/pay")
async def mark_invoice_paid(
    invoice_id: UUID,
    _current_user: dict = Depends(get_current_user),
    _profile: dict = Depends(require_any_role(["managing_editor", "admin"])),
):
    """
    Feature 024: 标记账单已支付（Admin/Editor）

    中文注释:
    - 生产环境应该由支付回调/对账触发；MVP 先提供人工确认入口。
    """
    try:
        inv_resp = (
            supabase_admin.table("invoices")
            .select("id,manuscript_id,amount,status,confirmed_at")
            .eq("id", str(invoice_id))
            .single()
            .execute()
        )
        inv = getattr(inv_resp, "data", None) or None
        if not inv:
            raise HTTPException(status_code=404, detail="Invoice not found")

        supabase_admin.table("invoices").update(
            {"status": "paid", "confirmed_at": datetime.now(timezone.utc).isoformat()}
        ).eq("id", str(invoice_id)).execute()

        inv["status"] = "paid"
        inv["confirmed_at"] = datetime.now(timezone.utc).isoformat()
        return {"success": True, "data": inv}
    except HTTPException:
        raise
    except Exception as e:
        print(f"[Invoices] mark paid failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to mark invoice as paid")


@router.get("/{invoice_id}/pdf-signed")
async def get_invoice_pdf_signed(
    invoice_id: UUID,
    current_user: dict = Depends(get_current_user),
    profile: dict = Depends(get_current_profile),
):
    """
    Feature 026: 获取 Invoice PDF 的 signed URL（Author / Editor / Admin）

    中文注释:
    - bucket 为私有；前端只能拿到短期 signed URL。
    - 若 pdf 尚未生成，允许在此处触发一次生成（不改变支付状态）。
    """
    user_id = str(current_user["id"])
    roles = set((profile or {}).get("roles") or [])
    is_internal = bool(roles.intersection({"admin", "managing_editor"}))

    inv_resp = (
        supabase_admin.table("invoices")
        .select("id, manuscript_id, pdf_path, pdf_error")
        .eq("id", str(invoice_id))
        .single()
        .execute()
    )
    inv = getattr(inv_resp, "data", None) or {}
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice not found")

    manuscript_id = str(inv.get("manuscript_id") or "").strip()
    if not manuscript_id:
        raise HTTPException(status_code=500, detail="Invoice missing manuscript_id")

    ms_resp = (
        supabase_admin.table("manuscripts")
        .select("id, author_id")
        .eq("id", manuscript_id)
        .single()
        .execute()
    )
    ms = getattr(ms_resp, "data", None) or {}
    if not ms:
        raise HTTPException(status_code=404, detail="Manuscript not found")

    if not (roles.intersection({"admin", "managing_editor"}) or str(ms.get("author_id") or "") == user_id):
        raise HTTPException(status_code=403, detail="Forbidden")

    pdf_path = (inv.get("pdf_path") or "").strip()
    pdf_error = (inv.get("pdf_error") or "").strip()
    if (not pdf_path) or pdf_error:
        res = generate_and_store_invoice_pdf(invoice_id=invoice_id)
        if res.pdf_error:
            print(f"[InvoicePDF] generate failed for invoice={invoice_id}: {res.pdf_error}")
            raise HTTPException(
                status_code=500,
                detail=(
                    f"Failed to generate invoice pdf: {res.pdf_error}"
                    if is_internal
                    else "Invoice PDF generation failed. Please retry later."
                ),
            )

    try:
        signed_url, expires_in = get_invoice_pdf_signed_url(invoice_id=invoice_id)
    except Exception as e:
        print(f"[InvoicePDF] signed url failed for invoice={invoice_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=(f"Invoice not available: {e}" if is_internal else "Invoice not available. Please retry later."),
        )

    return {
        "success": True,
        "data": {"invoice_id": str(invoice_id), "signed_url": signed_url, "expires_in": expires_in},
    }


@router.post("/{invoice_id}/pdf/regenerate")
async def regenerate_invoice_pdf(
    invoice_id: UUID,
    _current_user: dict = Depends(get_current_user),
    _profile: dict = Depends(require_any_role(["managing_editor", "admin"])),
):
    """
    Feature 026: Regenerate invoice PDF（Editor/Admin）

    中文注释:
    - 只允许内部角色触发，避免作者频繁重试造成资源浪费。
    - 再生成只更新 pdf 字段，不得改变支付状态。
    """
    try:
        res = generate_and_store_invoice_pdf(invoice_id=invoice_id)
        if res.pdf_error:
            raise HTTPException(status_code=500, detail=f"Failed to regenerate invoice pdf: {res.pdf_error}")
        return {
            "success": True,
            "data": {
                "invoice_id": str(invoice_id),
                "invoice_number": res.invoice_number,
                "pdf_path": res.pdf_path,
                "pdf_generated_at": res.pdf_generated_at,
                "pdf_error": res.pdf_error,
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to regenerate invoice pdf: {e}")


@router.post("/{invoice_id}/email/preview")
async def preview_invoice_email(
    invoice_id: UUID,
    payload: InvoiceEmailActionPayload | None = Body(default=None),
    _current_user: dict = Depends(get_current_user),
    _profile: dict = Depends(require_any_role(["managing_editor", "admin"])),
):
    preview = _build_invoice_email_preview(invoice_id, payload or InvoiceEmailActionPayload())
    return {"success": True, "data": {k: v for k, v in preview.items() if k != "context"}}


@router.post("/{invoice_id}/email/send")
async def send_invoice_email(
    invoice_id: UUID,
    payload: InvoiceEmailActionPayload | None = Body(default=None),
    current_user: dict = Depends(get_current_user),
    _profile: dict = Depends(require_any_role(["managing_editor", "admin"])),
):
    body = payload or InvoiceEmailActionPayload()
    preview = _build_invoice_email_preview(invoice_id, body)
    context = preview["context"]
    pdf_path = str(context["invoice"].get("pdf_path") or "").strip()
    pdf_bytes = _download_invoice_pdf_bytes(pdf_path)
    result = email_service.send_rendered_email(
        to_emails=preview["resolved_recipients"]["to"],
        cc_emails=preview["resolved_recipients"]["cc"],
        bcc_emails=preview["resolved_recipients"]["bcc"],
        reply_to_emails=preview["resolved_recipients"]["reply_to"],
        template_key="invoice_email",
        subject=preview["subject"],
        html_body=preview["html"],
        text_body=preview["text"],
        attachments=[
            {
                "filename": context["attachment_name"],
                "content": pdf_bytes,
                "content_type": "application/pdf",
            }
        ],
        idempotency_key=preview["idempotency_key"],
        audit_context={
            "manuscript_id": str(context["manuscript"].get("id") or "").strip() or None,
            "actor_user_id": str(current_user.get("id") or "").strip() or None,
            "scene": "invoice",
            "event_type": "invoice_email",
            "delivery_mode": "manual",
            "communication_status": "system_sent",
            "idempotency_key": preview["idempotency_key"],
        },
    )
    return {
        "success": True,
        "data": {
            "invoice_id": str(invoice_id),
            "recipient": preview["resolved_recipients"]["to"][0] if preview["resolved_recipients"]["to"] else None,
            "delivery_status": str(result.get("status") or EmailStatus.FAILED.value),
            "delivery_error": result.get("error_message"),
            "provider_id": result.get("provider_id"),
            "processed_at": datetime.now(timezone.utc).isoformat(),
        },
    }


@router.post("/{invoice_id}/email/resend")
async def resend_invoice_email(
    invoice_id: UUID,
    payload: InvoiceEmailActionPayload | None = Body(default=None),
    current_user: dict = Depends(get_current_user),
    _profile: dict = Depends(require_any_role(["managing_editor", "admin"])),
):
    body = payload or InvoiceEmailActionPayload()
    body.idempotency_key = body.idempotency_key or (
        f"invoice-email-resend/{invoice_id}/{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}"
    )
    return await send_invoice_email(
        invoice_id=invoice_id,
        payload=body,
        current_user=current_user,
        _profile=_profile,
    )


@router.post("/{invoice_id}/email/mark-external-sent")
async def mark_invoice_email_external_sent(
    invoice_id: UUID,
    payload: InvoiceEmailActionPayload | None = Body(default=None),
    current_user: dict = Depends(get_current_user),
    _profile: dict = Depends(require_any_role(["managing_editor", "admin"])),
):
    body = payload or InvoiceEmailActionPayload()
    preview = _build_invoice_email_preview(invoice_id, body)
    context = preview["context"]
    channel = str(body.channel or "other").strip() or "other"
    email_service.log_attempt(
        recipient=preview["resolved_recipients"]["to"][0],
        subject=preview["subject"],
        template_name="invoice_email",
        status=EmailStatus.SENT,
        provider=channel,
        to_recipients=preview["resolved_recipients"]["to"],
        cc_recipients=preview["resolved_recipients"]["cc"],
        bcc_recipients=preview["resolved_recipients"]["bcc"],
        reply_to_recipients=preview["resolved_recipients"]["reply_to"],
        attachment_manifest=[
            {
                "filename": context["attachment_name"],
                "content_type": "application/pdf",
            }
        ],
        audit_context={
            "manuscript_id": str(context["manuscript"].get("id") or "").strip() or None,
            "actor_user_id": str(current_user.get("id") or "").strip() or None,
            "scene": "invoice",
            "event_type": "invoice_email",
            "delivery_mode": "manual",
            "communication_status": "external_sent",
            "idempotency_key": preview["idempotency_key"],
        },
    )
    return {
        "success": True,
        "data": {
            "invoice_id": str(invoice_id),
            "recipient": preview["resolved_recipients"]["to"][0],
            "communication_status": "external_sent",
            "provider": channel,
            "processed_at": datetime.now(timezone.utc).isoformat(),
        },
    }
