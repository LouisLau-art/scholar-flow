from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from app.core.auth_utils import get_current_user
from app.core.roles import require_any_role
from app.lib.api_client import supabase_admin

router = APIRouter(prefix="/invoices", tags=["Invoices"])


@router.post("/{invoice_id}/pay")
async def mark_invoice_paid(
    invoice_id: UUID,
    _current_user: dict = Depends(get_current_user),
    _profile: dict = Depends(require_any_role(["editor", "admin"])),
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

