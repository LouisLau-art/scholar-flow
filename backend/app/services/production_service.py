from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Final

from fastapi import HTTPException

from app.core.doi_generator import generate_mock_doi
from app.lib.api_client import supabase_admin
from app.services.editorial_service import EditorialService
from app.services.production_workspace_service import ProductionWorkspaceService


POST_ACCEPTANCE_CHAIN: Final[list[str]] = [
    "approved",
    "layout",
    "english_editing",
    "proofreading",
    "published",
]

_NEXT: Final[dict[str, str]] = {
    "approved": "layout",
    "layout": "english_editing",
    "english_editing": "proofreading",
    "proofreading": "published",
}

_PREV: Final[dict[str, str]] = {
    "layout": "approved",
    "english_editing": "layout",
    "proofreading": "english_editing",
}


def _is_truthy_env(name: str, default: str = "0") -> bool:
    return (os.getenv(name, default) or "").strip().lower() in {
        "1",
        "true",
        "yes",
        "y",
        "on",
    }


def _is_missing_column_error(error_text: str) -> bool:
    if not error_text:
        return False
    lowered = error_text.lower()
    return (
        "column" in lowered
        or "published_at" in lowered
        or "final_pdf_path" in lowered
        or "doi" in lowered
        or "schema cache" in lowered
    )


@dataclass(frozen=True)
class ProductionResult:
    previous_status: str
    new_status: str
    manuscript: dict[str, Any]


class ProductionService:
    """
    Feature 031：录用后出版流水线（Post-Acceptance Workflow）。

    中文注释:
    - 本服务只处理 approved/layout/english_editing/proofreading/published 这一段链路。
    - Published 必须显式执行 Payment Gate（+ 可选 Production Gate）。
    """

    def __init__(
        self,
        *,
        editorial: EditorialService | None = None,
        workspace: ProductionWorkspaceService | None = None,
    ) -> None:
        self.editorial = editorial or EditorialService()
        self.client = supabase_admin
        self.workspace = workspace or ProductionWorkspaceService()
        if hasattr(self.workspace, "client"):
            self.workspace.client = self.client

    def _load_invoice(self, manuscript_id: str) -> dict[str, Any] | None:
        try:
            inv = (
                self.client.table("invoices")
                .select("id, amount, status, confirmed_at")
                .eq("manuscript_id", manuscript_id)
                .limit(1)
                .execute()
            )
            rows = getattr(inv, "data", None) or []
            return rows[0] if rows else None
        except Exception:
            return None

    def _load_manuscript_for_gate(self, manuscript_id: str) -> dict[str, Any]:
        """
        Gate 只需要 status + final_pdf_path（若列不存在要降级兼容）。
        """
        try:
            resp = (
                self.client.table("manuscripts")
                .select("id, status, final_pdf_path, doi, published_at")
                .eq("id", manuscript_id)
                .single()
                .execute()
            )
            return getattr(resp, "data", None) or {}
        except Exception as e:
            if _is_missing_column_error(str(e)):
                resp = (
                    self.client.table("manuscripts")
                    .select("id, status")
                    .eq("id", manuscript_id)
                    .single()
                    .execute()
                )
                return getattr(resp, "data", None) or {}
            raise

    def _payment_gate(self, manuscript_id: str, ms_status: str) -> None:
        """
        Payment Gate（强制）：
        - amount > 0 且 status 不在 (paid, waived) -> 403
        - 若 invoice 缺失但 manuscript 已在 post-acceptance（approved+）-> 403
        """
        invoice = self._load_invoice(manuscript_id)
        if invoice is None:
            if (ms_status or "").lower() in {"approved", "layout", "english_editing", "proofreading"}:
                raise HTTPException(status_code=403, detail="Payment Required: Invoice is unpaid.")
            return

        try:
            amount = float(invoice.get("amount") or 0)
        except Exception:
            amount = 0
        status = (invoice.get("status") or "unpaid").lower()
        if amount > 0 and status not in {"paid", "waived"}:
            raise HTTPException(status_code=403, detail="Payment Required: Invoice is unpaid.")

    def _production_gate(self, ms: dict[str, Any]) -> None:
        """
        Production Gate（可选）：
        - PRODUCTION_GATE_ENABLED=true 时启用
        - 仅当 schema 存在 final_pdf_path 时拦截（字段缺失则降级不拦截）
        """
        # 默认开启（测试/生产更安全）；如需提速可显式设置 PRODUCTION_GATE_ENABLED=0
        if not _is_truthy_env("PRODUCTION_GATE_ENABLED", "1"):
            return
        if "final_pdf_path" not in ms:
            return
        if not (ms.get("final_pdf_path") or "").strip():
            raise HTTPException(status_code=400, detail="Production PDF required.")

    def advance(
        self,
        *,
        manuscript_id: str,
        changed_by: str | None,
        allow_skip: bool = False,
    ) -> ProductionResult:
        ms = self._load_manuscript_for_gate(manuscript_id)
        if not ms:
            raise HTTPException(status_code=404, detail="Manuscript not found")

        current = (ms.get("status") or "").strip().lower()
        if current not in _NEXT:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported production advance from status '{current}'.",
            )

        nxt = _NEXT[current]
        if nxt != "published":
            updated = self.editorial.update_status(
                manuscript_id=manuscript_id,
                to_status=nxt,
                changed_by=changed_by,
                comment="production advance",
                allow_skip=allow_skip,
            )
            return ProductionResult(previous_status=current, new_status=nxt, manuscript=updated)

        # Publish：必须过门禁 + 填充 doi/published_at（尽力写入，缺列则降级为仅 status）
        self._payment_gate(manuscript_id, current)
        # Feature 042：发布前应绑定到“已核准生产轮次”（严格模式可通过环境变量控制）
        self.workspace.assert_publish_gate_ready(manuscript_id=manuscript_id)
        self._production_gate(ms)

        now = datetime.now(timezone.utc).isoformat()
        doi = generate_mock_doi(manuscript_id=manuscript_id)
        try:
            updated = self.editorial.update_status(
                manuscript_id=manuscript_id,
                to_status="published",
                changed_by=changed_by,
                comment="publish",
                allow_skip=allow_skip,
                extra_updates={"published_at": now, "doi": doi},
            )
        except HTTPException as e:
            # 兼容云端 schema 未同步（published_at/doi 缺列）
            cause = getattr(e, "__cause__", None)
            if e.status_code == 500 and _is_missing_column_error(str(cause) if cause else str(e)):
                updated = self.editorial.update_status(
                    manuscript_id=manuscript_id,
                    to_status="published",
                    changed_by=changed_by,
                    comment="publish (degraded)",
                    allow_skip=allow_skip,
                )
            else:
                raise

        return ProductionResult(previous_status=current, new_status="published", manuscript=updated)

    def revert(
        self,
        *,
        manuscript_id: str,
        changed_by: str | None,
        allow_skip: bool = False,
    ) -> ProductionResult:
        ms = self._load_manuscript_for_gate(manuscript_id)
        if not ms:
            raise HTTPException(status_code=404, detail="Manuscript not found")

        current = (ms.get("status") or "").strip().lower()
        if current not in _PREV:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported production revert from status '{current}'.",
            )
        prev = _PREV[current]
        updated = self.editorial.update_status(
            manuscript_id=manuscript_id,
            to_status=prev,
            changed_by=changed_by,
            comment="production revert",
            allow_skip=allow_skip,
        )
        return ProductionResult(previous_status=current, new_status=prev, manuscript=updated)
