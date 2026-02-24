from __future__ import annotations

from datetime import datetime, timezone
from io import BytesIO
from typing import Literal

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse

from app.api.v1.editor_common import (
    ConfirmInvoicePaidPayload,
    require_action_or_403 as _require_action_or_403,
)
from app.core.auth_utils import get_current_user
from app.core.journal_scope import ensure_manuscript_scope_access
from app.core.role_matrix import can_perform_action
from app.core.roles import require_any_role
from app.lib.api_client import supabase_admin
from app.services.editor_service import EditorService, FinanceListFilters

# 与 editor.py 保持一致：这些角色可进入 Editor Command Center。
EDITOR_SCOPE_COMPAT_ROLES = [
    "admin",
    "managing_editor",
    "assistant_editor",
    "production_editor",
    "editor_in_chief",
]

router = APIRouter(tags=["Editor Command Center"])


@router.get("/finance/invoices")
async def get_finance_invoices(
    status: Literal["all", "unpaid", "paid", "waived"] = Query("all", description="状态筛选"),
    q: str | None = Query(None, max_length=100, description="关键词（invoice number / manuscript title）"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_by: Literal["updated_at", "amount", "status"] = Query("updated_at"),
    sort_order: Literal["asc", "desc"] = Query("desc"),
    _profile: dict = Depends(require_any_role(["managing_editor", "admin"])),
):
    """
    Feature 046: Finance 页面真实账单列表（内部角色）。
    """
    try:
        result = EditorService().list_finance_invoices(
            filters=FinanceListFilters(
                status=status,
                q=q,
                page=page,
                page_size=page_size,
                sort_by=sort_by,
                sort_order=sort_order,
            )
        )
        return {"success": True, "data": result["rows"], "meta": result["meta"]}
    except HTTPException:
        raise
    except Exception as e:
        print(f"[Finance] list invoices failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch finance invoices")


@router.get("/finance/invoices/export")
async def export_finance_invoices_csv(
    status: Literal["all", "unpaid", "paid", "waived"] = Query("all", description="状态筛选"),
    q: str | None = Query(None, max_length=100, description="关键词（invoice number / manuscript title）"),
    sort_by: Literal["updated_at", "amount", "status"] = Query("updated_at"),
    sort_order: Literal["asc", "desc"] = Query("desc"),
    _profile: dict = Depends(require_any_role(["managing_editor", "admin"])),
):
    """
    Feature 046: 导出 Finance 当前筛选结果（CSV）。
    """
    try:
        result = EditorService().export_finance_invoices_csv(
            filters=FinanceListFilters(
                status=status,
                q=q,
                page=1,
                page_size=100,
                sort_by=sort_by,
                sort_order=sort_order,
            )
        )
        csv_text = result.get("csv_text", "")
        snapshot_at = str(result.get("snapshot_at") or datetime.now(timezone.utc).isoformat())
        empty = bool(result.get("empty"))
        filename = f"finance_invoices_{status}_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}.csv"
        headers = {
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Export-Snapshot-At": snapshot_at,
            "X-Export-Empty": "1" if empty else "0",
        }
        return StreamingResponse(
            BytesIO(csv_text.encode("utf-8")),
            media_type="text/csv",
            headers=headers,
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"[Finance] export invoices failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to export finance invoices")


@router.post("/invoices/confirm")
async def confirm_invoice_paid(
    current_user: dict = Depends(get_current_user),
    profile: dict = Depends(require_any_role(EDITOR_SCOPE_COMPAT_ROLES)),
    payload: ConfirmInvoicePaidPayload = Body(...),
):
    """
    MVP：财务确认到账（把 invoices.status 置为 paid）。

    中文注释:
    - 支付渠道/自动对账后续再做；MVP 先提供一个“人工确认到账”入口。
    - Publish 时会做 Payment Gate 检查：amount>0 且 status!=paid -> 禁止发布。
    """
    # 中文注释:
    # - ME 在生产链路中需要执行人工到账确认；
    # - 因此此处接受 invoice:update_info（ME）或 invoice:override_apc（EIC/Admin）任一动作权限。
    roles = profile.get("roles") or []
    if not (
        can_perform_action(action="invoice:update_info", roles=roles)
        or can_perform_action(action="invoice:override_apc", roles=roles)
    ):
        _require_action_or_403(action="invoice:confirm_paid", roles=roles)
    try:
        manuscript_id = str(payload.manuscript_id or "").strip()
        if not manuscript_id:
            raise HTTPException(status_code=422, detail="manuscript_id is required")

        ensure_manuscript_scope_access(
            manuscript_id=manuscript_id,
            user_id=str(current_user.get("id") or ""),
            roles=profile.get("roles") or [],
            allow_admin_bypass=True,
        )

        expected_status = str(payload.expected_status or "").strip().lower() or None
        source = str(payload.source or "unknown").strip().lower() or "unknown"

        inv_resp = (
            supabase_admin.table("invoices")
            .select("id, amount, status, confirmed_at")
            .eq("manuscript_id", manuscript_id)
            .limit(1)
            .execute()
        )
        inv_rows = getattr(inv_resp, "data", None) or []
        if not inv_rows:
            raise HTTPException(status_code=404, detail="Invoice not found")
        inv = inv_rows[0]

        previous_status = str(inv.get("status") or "").strip().lower() or "unpaid"
        if expected_status and previous_status != expected_status:
            raise HTTPException(status_code=409, detail="Invoice status changed by another operation")

        if previous_status == "paid":
            confirmed_at = str(inv.get("confirmed_at") or datetime.now(timezone.utc).isoformat())
            return {
                "success": True,
                "data": {
                    "invoice_id": inv["id"],
                    "manuscript_id": manuscript_id,
                    "previous_status": previous_status,
                    "current_status": "paid",
                    "confirmed_at": confirmed_at,
                    "already_paid": True,
                    "conflict": False,
                    "source": source,
                },
            }

        confirmed_at = datetime.now(timezone.utc).isoformat()
        update_query = supabase_admin.table("invoices").update({"status": "paid", "confirmed_at": confirmed_at}).eq("id", inv["id"])
        if expected_status:
            update_query = update_query.eq("status", expected_status)
        upd_resp = update_query.execute()
        upd_rows = getattr(upd_resp, "data", None) or []
        if expected_status and not upd_rows:
            raise HTTPException(status_code=409, detail="Invoice status changed by another operation")

        EditorService()._safe_insert_transition_log(
            manuscript_id=manuscript_id,
            from_status=f"invoice:{previous_status}",
            to_status="invoice:paid",
            changed_by=str(current_user.get("id") or ""),
            comment="finance invoice confirmed paid",
            payload={
                "action": "finance_invoice_confirm_paid",
                "invoice_id": str(inv.get("id") or ""),
                "before_status": previous_status,
                "after_status": "paid",
                "source": source,
            },
            created_at=confirmed_at,
        )

        return {
            "success": True,
            "data": {
                "invoice_id": inv["id"],
                "manuscript_id": manuscript_id,
                "previous_status": previous_status,
                "current_status": "paid",
                "confirmed_at": confirmed_at,
                "already_paid": False,
                "conflict": False,
                "source": source,
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"[Financial] confirm invoice failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to confirm invoice")
