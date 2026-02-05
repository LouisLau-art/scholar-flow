from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException

from app.core.doi_generator import generate_mock_doi
from app.lib.api_client import supabase_admin


def _is_missing_column_error(error_text: str) -> bool:
    if not error_text:
        return False
    lowered = error_text.lower()
    return (
        "column" in lowered
        or "published_at" in lowered
        or "final_pdf_path" in lowered
        or "doi" in lowered
    )


def _load_manuscript_for_publish(manuscript_id: str) -> dict[str, Any]:
    try:
        resp = (
            supabase_admin.table("manuscripts")
            .select("id,status,final_pdf_path")
            .eq("id", manuscript_id)
            .single()
            .execute()
        )
        return getattr(resp, "data", None) or {}
    except Exception as e:
        # 兼容：未迁移 final_pdf_path 的环境（MVP/云端迁移未同步）
        error_text = str(e)
        if _is_missing_column_error(error_text):
            resp = (
                supabase_admin.table("manuscripts")
                .select("id,status")
                .eq("id", manuscript_id)
                .single()
                .execute()
            )
            return getattr(resp, "data", None) or {}
        raise


def _load_invoice_for_manuscript(manuscript_id: str) -> dict[str, Any] | None:
    try:
        inv_resp = (
            supabase_admin.table("invoices")
            .select("id,amount,status,confirmed_at")
            .eq("manuscript_id", manuscript_id)
            .limit(1)
            .execute()
        )
        rows = getattr(inv_resp, "data", None) or []
        return rows[0] if rows else None
    except Exception:
        return None


def publish_manuscript(*, manuscript_id: str) -> dict[str, Any]:
    """
    Feature 024: Post-Acceptance 发布（强制门禁）

    Gate:
    - Payment: amount>0 && status!=paid -> 403
    - Production: (可选) final_pdf_path 为空 -> 400（若 schema 缺失则降级不拦）
    """
    ms = _load_manuscript_for_publish(manuscript_id)
    if not ms:
        raise HTTPException(status_code=404, detail="Manuscript not found")

    invoice = _load_invoice_for_manuscript(manuscript_id)
    if invoice is None:
        if (ms.get("status") or "").lower() in {"approved", "pending_payment"}:
            raise HTTPException(status_code=403, detail="Payment Required: Invoice is unpaid.")
    else:
        try:
            amount = float(invoice.get("amount") or 0)
        except Exception:
            amount = 0
        status = (invoice.get("status") or "unpaid").lower()
        if amount > 0 and status != "paid":
            raise HTTPException(status_code=403, detail="Payment Required: Invoice is unpaid.")

    # Production gate（默认关闭，MVP 提速）：
    # - 仅当 PRODUCTION_GATE_ENABLED=1/true/yes 时启用
    # - 且仅在 schema 存在时拦截（字段不存在则降级不拦截）
    # 默认开启（测试/生产更安全）；如需提速可显式设置 PRODUCTION_GATE_ENABLED=0
    enabled = (os.getenv("PRODUCTION_GATE_ENABLED") or "1").strip().lower() in {
        "1",
        "true",
        "yes",
        "y",
        "on",
    }
    if enabled and "final_pdf_path" in ms:
        if not (ms.get("final_pdf_path") or "").strip():
            raise HTTPException(status_code=400, detail="Production PDF required.")

    doi = generate_mock_doi(manuscript_id=manuscript_id)
    update_data = {
        "status": "published",
        "published_at": datetime.now(timezone.utc).isoformat(),
        "doi": doi,
    }

    try:
        resp = (
            supabase_admin.table("manuscripts")
            .update(update_data)
            .eq("id", manuscript_id)
            .execute()
        )
        data = getattr(resp, "data", None) or []
        if not data:
            raise HTTPException(status_code=404, detail="Manuscript not found")
        return data[0]
    except Exception as e:
        error_text = str(e)
        print(f"[Publish] update error: {error_text}")
        if _is_missing_column_error(error_text):
            resp = (
                supabase_admin.table("manuscripts")
                .update({"status": update_data["status"]})
                .eq("id", manuscript_id)
                .execute()
            )
            data = getattr(resp, "data", None) or []
            if not data:
                raise HTTPException(status_code=404, detail="Manuscript not found")
            return data[0]
        raise HTTPException(status_code=500, detail="Failed to publish manuscript")
