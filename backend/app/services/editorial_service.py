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
    payload: dict[str, Any] | None
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
        base_row: dict[str, Any] = {
            "manuscript_id": manuscript_id,
            "from_status": log.from_status,
            "to_status": log.to_status,
            "comment": log.comment,
            "changed_by": log.changed_by,
            "created_at": log.created_at,
        }

        def _try_insert(row: dict[str, Any]) -> None:
            self.client.table("status_transition_logs").insert(row).execute()

        payload = log.payload
        candidates: list[dict[str, Any]] = []

        # 1) 原始写入（含 changed_by + payload）
        row1 = dict(base_row)
        if payload is not None:
            row1["payload"] = payload
        candidates.append(row1)

        # 2) 若 payload 列不存在，则去掉 payload 再写一次
        row2 = dict(base_row)
        candidates.append(row2)

        # 3) 若 changed_by 外键约束失败（测试 token / dev bypass 可能出现），用 changed_by=NULL 降级写入。
        if log.changed_by:
            downgraded_payload = dict(payload) if isinstance(payload, dict) else {}
            downgraded_payload.setdefault("changed_by_raw", log.changed_by)

            row3 = dict(base_row)
            row3["changed_by"] = None
            if downgraded_payload:
                row3["payload"] = downgraded_payload
            candidates.append(row3)

            # 4) 同上，但去掉 payload（防止 payload 列不存在）
            row4 = dict(base_row)
            row4["changed_by"] = None
            candidates.append(row4)

        last_err: Exception | None = None
        for row in candidates:
            try:
                _try_insert(row)
                return
            except Exception as e:
                last_err = e
                continue

        # 中文注释: 迁移未跑/权限不足/外键约束等问题，不应阻断主流程（MVP 提速）。
        if last_err is not None:
            print(f"[Workflow] transition log insert failed (ignored): {last_err}")

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
        payload: dict[str, Any] | None = None,
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
                payload=payload,
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
        before_meta: dict[str, Any] = {}
        meta: dict[str, Any] = {}
        try:
            raw_meta = ms.get("invoice_metadata") or {}
            if isinstance(raw_meta, dict):
                before_meta = dict(raw_meta)
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
                payload={
                    "action": "update_invoice_info",
                    "before": before_meta,
                    "after": meta,
                },
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
