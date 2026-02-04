from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID

from fastapi import HTTPException

from app.lib.api_client import supabase_admin
from app.models.manuscript import ManuscriptStatus, normalize_status


@dataclass(frozen=True)
class StatusTransition:
    from_status: str
    to_status: str
    changed_by: str | None
    comment: str | None
    created_at: str


class EditorialService:
    """
    Feature 028：统一的稿件状态机与审计日志写入服务。

    中文注释:
    - 遵循章程：核心状态流转逻辑必须显性可见，避免散落在 API 层/前端。
    - 该服务使用 service_role（supabase_admin）读写，以兼容云端 RLS 环境。
    """

    def __init__(self) -> None:
        self.client = supabase_admin

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def _insert_transition_log(self, log: StatusTransition, manuscript_id: str) -> None:
        """
        写入 status_transition_logs（若云端未应用该迁移，失败则降级忽略）。
        """
        try:
            self.client.table("status_transition_logs").insert(
                {
                    "manuscript_id": manuscript_id,
                    "from_status": log.from_status,
                    "to_status": log.to_status,
                    "comment": log.comment,
                    "changed_by": log.changed_by,
                    "created_at": log.created_at,
                }
            ).execute()
        except Exception as e:
            # 中文注释: 迁移未跑/列缺失时，不应阻断主流程（MVP 提速）。
            print(f"[Workflow] transition log insert failed (ignored): {e}")

    def get_manuscript(self, manuscript_id: str) -> dict[str, Any]:
        try:
            resp = (
                self.client.table("manuscripts")
                .select("id,status,updated_at,invoice_metadata,owner_id,editor_id")
                .eq("id", manuscript_id)
                .single()
                .execute()
            )
            data = getattr(resp, "data", None) or None
        except Exception as e:
            # PostgREST single() 0 行会抛异常；这里统一转为 404
            raise HTTPException(status_code=404, detail="Manuscript not found") from e
        if not data:
            raise HTTPException(status_code=404, detail="Manuscript not found")
        return data

    def update_status(
        self,
        *,
        manuscript_id: str,
        to_status: str,
        changed_by: str | None,
        comment: str | None = None,
        allow_skip: bool = False,
        extra_updates: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        更新稿件状态并写入 transition log。

        allow_skip:
        - editor: False（默认不允许跳过关键阶段）
        - admin: True（可允许灵活跳转）
        """
        ms = self.get_manuscript(manuscript_id)
        from_status = str(ms.get("status") or "")

        to_norm = normalize_status(to_status)
        if to_norm is None:
            raise HTTPException(status_code=422, detail="Invalid status")

        from_norm = normalize_status(from_status) or ManuscriptStatus.PRE_CHECK.value

        if not allow_skip:
            allowed = ManuscriptStatus.allowed_next(from_norm)
            if to_norm not in allowed:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid transition: {from_norm} -> {to_norm}. Allowed: {sorted(allowed)}",
                )

        now = self._now()
        update_payload: dict[str, Any] = {"status": to_norm, "updated_at": now}
        if extra_updates:
            update_payload.update(extra_updates)
        try:
            upd = (
                self.client.table("manuscripts")
                .update(update_payload)
                .eq("id", manuscript_id)
                .execute()
            )
            rows = getattr(upd, "data", None) or []
            if not rows:
                raise HTTPException(status_code=404, detail="Manuscript not found")
            updated = rows[0]
        except HTTPException:
            raise
        except Exception as e:
            print(f"[Workflow] update_status failed: {e}")
            raise HTTPException(status_code=500, detail="Failed to update status") from e

        self._insert_transition_log(
            StatusTransition(
                from_status=from_norm,
                to_status=to_norm,
                changed_by=changed_by,
                comment=comment,
                created_at=now,
            ),
            manuscript_id=manuscript_id,
        )
        return updated

    def update_invoice_info(
        self,
        *,
        manuscript_id: str,
        authors: Optional[str] = None,
        affiliation: Optional[str] = None,
        apc_amount: Optional[float] = None,
        funding_info: Optional[str] = None,
        changed_by: str | None,
    ) -> dict[str, Any]:
        ms = self.get_manuscript(manuscript_id)
        meta: dict[str, Any] = {}
        try:
            raw_meta = ms.get("invoice_metadata") or {}
            if isinstance(raw_meta, dict):
                meta = dict(raw_meta)
        except Exception:
            meta = {}

        def set_if_not_none(key: str, value: Any) -> None:
            if value is not None:
                meta[key] = value

        set_if_not_none("authors", authors)
        set_if_not_none("affiliation", affiliation)
        set_if_not_none("apc_amount", apc_amount)
        set_if_not_none("funding_info", funding_info)

        now = self._now()
        try:
            resp = (
                self.client.table("manuscripts")
                .update({"invoice_metadata": meta, "updated_at": now})
                .eq("id", manuscript_id)
                .execute()
            )
            rows = getattr(resp, "data", None) or []
            if not rows:
                raise HTTPException(status_code=404, detail="Manuscript not found")
            updated = rows[0]
        except HTTPException:
            raise
        except Exception as e:
            print(f"[Workflow] update_invoice_info failed: {e}")
            raise HTTPException(status_code=500, detail="Failed to update invoice info") from e

        # 中文注释：发票信息的变更也写入状态流转日志，便于审计（to_status=from_status）
        self._insert_transition_log(
            StatusTransition(
                from_status=str(ms.get("status") or ""),
                to_status=str(ms.get("status") or ""),
                changed_by=changed_by,
                comment="invoice_metadata updated",
                created_at=now,
            ),
            manuscript_id=manuscript_id,
        )
        return updated


async def process_quality_check(
    manuscript_id: UUID,
    passed: bool,
    owner_id: UUID,
    revision_notes: Optional[str] = None,
):
    """
    处理编辑质检逻辑（兼容历史接口）。

    028 约定:
    - 质检通过：pre_check -> under_review
    - 质检不通过：进入 minor_revision（等同“退回作者补材料/改格式”）
    """
    svc = EditorialService()
    to_status = ManuscriptStatus.UNDER_REVIEW.value if passed else ManuscriptStatus.MINOR_REVISION.value
    updated = svc.update_status(
        manuscript_id=str(manuscript_id),
        to_status=to_status,
        changed_by=str(owner_id),
        comment=revision_notes,
        allow_skip=False,
        extra_updates={"owner_id": str(owner_id)},
    )
    return {"id": updated.get("id"), "status": updated.get("status"), "owner_id": updated.get("owner_id")}


async def handle_plagiarism_result(manuscript_id: UUID, score: float):
    """
    处理查重结果并执行拦截预警（历史占位逻辑，MVP 默认关闭）。
    """
    if score > 0.3:
        print(f"检测到高重复率风险: {manuscript_id}, 得分: {score}")
        return "high_similarity"
    return "pre_check"
