from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from app.core.auth_utils import get_current_user
from app.core.roles import get_current_profile, require_any_role
from app.lib.api_client import supabase_admin
from app.services.invoice_pdf_service import (
    generate_and_store_invoice_pdf,
    get_invoice_pdf_signed_url,
)

router = APIRouter(prefix="/invoices", tags=["Invoices"])


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
