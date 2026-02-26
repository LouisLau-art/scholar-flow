from __future__ import annotations

import logging
from typing import Any, Iterable
from uuid import UUID

from fastapi import HTTPException

from app.core.journal_scope import get_user_scope_journal_ids, is_scope_enforcement_enabled
from app.core.role_matrix import normalize_roles
from app.models.manuscript import ManuscriptStatus, PreCheckStatus, normalize_status

logger = logging.getLogger("scholarflow.editor_precheck_workspace")


class EditorServicePrecheckWorkspaceDecisionMixin:
    def submit_technical_check(
        self,
        manuscript_id: UUID,
        ae_id: UUID,
        *,
        decision: str,
        comment: str | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        """
        AE technical check:
        - pass -> under_review（跳过 academic pre-check）
        - academic -> pre_check/academic（送 EIC 预审，可选）
        - revision -> minor_revision
        """
        manuscript_id_str = str(manuscript_id)
        ae_id_str = str(ae_id)
        normalized_decision = str(decision or "").strip().lower()
        if normalized_decision not in {"pass", "revision", "academic"}:
            raise HTTPException(status_code=422, detail="decision must be pass, academic or revision")
        comment_clean = (comment or "").strip() or None
        if normalized_decision == "revision" and not comment_clean:
            raise HTTPException(status_code=422, detail="comment is required for revision")

        ms = self._get_manuscript(manuscript_id_str)
        status = normalize_status(str(ms.get("status") or ""))
        pre = self._normalize_precheck_status(ms.get("pre_check_status"))
        owner_ae = str(ms.get("assistant_editor_id") or "")

        if status != ManuscriptStatus.PRE_CHECK.value:
            if normalized_decision == "revision" and status == ManuscriptStatus.MINOR_REVISION.value:
                return dict(ms)
            if normalized_decision == "pass" and status == ManuscriptStatus.UNDER_REVIEW.value:
                return dict(ms)
            if (
                normalized_decision == "academic"
                and status == ManuscriptStatus.PRE_CHECK.value
                and pre == PreCheckStatus.ACADEMIC.value
            ):
                return dict(ms)
            raise HTTPException(status_code=409, detail="Technical check conflict: manuscript state changed")

        if pre != PreCheckStatus.TECHNICAL.value:
            raise HTTPException(status_code=409, detail=f"Technical check only allowed in technical stage, current={pre}")

        if owner_ae != ae_id_str:
            raise HTTPException(status_code=403, detail="Only assigned assistant editor can submit technical check")

        if normalized_decision == "academic":
            now = self._now()
            data = {
                "pre_check_status": PreCheckStatus.ACADEMIC.value,
                "updated_at": now,
            }
            q = (
                self.client.table("manuscripts")
                .update(data)
                .eq("id", manuscript_id_str)
                .eq("status", ManuscriptStatus.PRE_CHECK.value)
                .eq("pre_check_status", PreCheckStatus.TECHNICAL.value)
                .eq("assistant_editor_id", ae_id_str)
            )
            resp = q.execute()
            rows = getattr(resp, "data", None) or []
            if not rows:
                latest = self._get_manuscript(manuscript_id_str)
                latest_status = normalize_status(str(latest.get("status") or ""))
                latest_pre = self._normalize_precheck_status(latest.get("pre_check_status"))
                latest_ae = str(latest.get("assistant_editor_id") or "")
                if (
                    latest_status == ManuscriptStatus.PRE_CHECK.value
                    and latest_pre == PreCheckStatus.ACADEMIC.value
                    and latest_ae == ae_id_str
                ):
                    return self._map_precheck_row(latest)
                raise HTTPException(status_code=409, detail="Technical check conflict: manuscript state changed")

            updated = rows[0]
            self._safe_insert_transition_log(
                manuscript_id=manuscript_id_str,
                from_status=ManuscriptStatus.PRE_CHECK.value,
                to_status=ManuscriptStatus.PRE_CHECK.value,
                changed_by=ae_id_str,
                comment=comment_clean or "technical check sent to academic queue",
                payload={
                    "action": "precheck_technical_to_academic",
                    "pre_check_from": PreCheckStatus.TECHNICAL.value,
                    "pre_check_to": PreCheckStatus.ACADEMIC.value,
                    "assistant_editor_before": owner_ae or None,
                    "assistant_editor_after": owner_ae or None,
                    "decision": "academic",
                    "idempotency_key": idempotency_key,
                },
                created_at=now,
            )
            return self._map_precheck_row(updated)

        if normalized_decision == "pass":
            updated = self.editorial.update_status(
                manuscript_id=manuscript_id_str,
                to_status=ManuscriptStatus.UNDER_REVIEW.value,
                changed_by=ae_id_str,
                comment=comment_clean or "technical check passed, moved to under_review",
                allow_skip=False,
                extra_updates={"pre_check_status": None},
                payload={
                    "action": "precheck_technical_to_under_review",
                    "pre_check_from": PreCheckStatus.TECHNICAL.value,
                    "pre_check_to": None,
                    "assistant_editor_before": owner_ae or None,
                    "assistant_editor_after": owner_ae or None,
                    "decision": "pass",
                    "idempotency_key": idempotency_key,
                },
            )
            return updated

        updated = self.editorial.update_status(
            manuscript_id=manuscript_id_str,
            to_status=ManuscriptStatus.MINOR_REVISION.value,
            changed_by=ae_id_str,
            comment=comment_clean,
            allow_skip=False,
            payload={
                "action": "precheck_technical_revision",
                "pre_check_from": PreCheckStatus.TECHNICAL.value,
                "pre_check_to": None,
                "assistant_editor_before": owner_ae or None,
                "assistant_editor_after": owner_ae or None,
                "decision": "revision",
                "idempotency_key": idempotency_key,
            },
        )
        return updated

    def get_academic_queue(
        self,
        *,
        viewer_user_id: UUID | str,
        viewer_roles: Iterable[str] | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> list[dict[str, Any]]:
        """
        EIC Academic Queue: Status=PRE_CHECK, PreCheckStatus=ACADEMIC
        """
        normalized_roles = set(normalize_roles(viewer_roles))
        q = (
            self.client.table("manuscripts")
            .select("*")
            .eq("status", ManuscriptStatus.PRE_CHECK.value)
            .eq("pre_check_status", PreCheckStatus.ACADEMIC.value)
            .order("updated_at", desc=True)
            .order("created_at", desc=True)
            .range((page - 1) * page_size, page * page_size - 1)
        )
        resp = q.execute()
        rows = getattr(resp, "data", None) or []
        out = self._enrich_precheck_rows(rows)

        if "admin" not in normalized_roles:
            scoped_journal_ids = get_user_scope_journal_ids(
                user_id=str(viewer_user_id),
                roles=normalized_roles,
            )
            has_global_scope_role = bool({"managing_editor", "editor_in_chief"} & normalized_roles)
            if scoped_journal_ids:
                out = [
                    row
                    for row in out
                    if str(row.get("journal_id") or "").strip() in scoped_journal_ids
                ]
            elif has_global_scope_role or is_scope_enforcement_enabled():
                return []

        return out

    def get_final_decision_queue(
        self,
        *,
        viewer_user_id: UUID | str,
        viewer_roles: Iterable[str] | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> list[dict[str, Any]]:
        """
        EIC Final Decision Queue:
        - 常规展示 status in decision / decision_done（终审阶段）
        - 额外展示“已有 first decision 草稿”的 under_review / resubmitted 稿件，
          便于 EIC 从 AE 草稿接手终审。
        """
        normalized_roles = set(normalize_roles(viewer_roles))
        decision_stage_statuses = {
            ManuscriptStatus.DECISION.value,
            ManuscriptStatus.DECISION_DONE.value,
        }
        q = (
            self.client.table("manuscripts")
            .select("id,title,status,updated_at,journal_id,journals(title,slug),assistant_editor_id,owner_id")
            .in_(
                "status",
                [
                    ManuscriptStatus.UNDER_REVIEW.value,
                    ManuscriptStatus.RESUBMITTED.value,
                    ManuscriptStatus.DECISION.value,
                    ManuscriptStatus.DECISION_DONE.value,
                ],
            )
            .order("updated_at", desc=True)
            .order("created_at", desc=True)
            .range((page - 1) * page_size, page * page_size - 1)
        )
        resp = q.execute()
        rows = getattr(resp, "data", None) or []

        if "admin" not in normalized_roles:
            scoped_journal_ids = get_user_scope_journal_ids(
                user_id=str(viewer_user_id),
                roles=normalized_roles,
            )
            has_global_scope_role = bool({"managing_editor", "editor_in_chief"} & normalized_roles)
            if scoped_journal_ids:
                rows = [
                    row
                    for row in rows
                    if str(row.get("journal_id") or "").strip() in scoped_journal_ids
                ]
            elif has_global_scope_role or is_scope_enforcement_enabled():
                return []

        manuscript_ids = [str(row.get("id") or "").strip() for row in rows if str(row.get("id") or "").strip()]
        latest_draft_map: dict[str, dict[str, Any]] = {}
        if manuscript_ids:
            try:
                draft_resp = (
                    self.client.table("decision_letters")
                    .select("id,manuscript_id,editor_id,decision,status,updated_at")
                    .eq("status", "draft")
                    .in_("manuscript_id", manuscript_ids)
                    .order("updated_at", desc=True)
                    .execute()
                )
                for row in (getattr(draft_resp, "data", None) or []):
                    mid = str(row.get("manuscript_id") or "").strip()
                    if mid and mid not in latest_draft_map:
                        latest_draft_map[mid] = row
            except Exception as e:
                logger.warning("[FinalDecisionQueue] load draft decision letters failed (ignored): %s", e)

        for row in rows:
            draft = latest_draft_map.get(str(row.get("id") or "").strip())
            if draft:
                row["latest_first_decision_draft"] = {
                    "id": draft.get("id"),
                    "editor_id": draft.get("editor_id"),
                    "decision": draft.get("decision"),
                    "updated_at": draft.get("updated_at"),
                }
            else:
                row["latest_first_decision_draft"] = None

        filtered_rows: list[dict[str, Any]] = []
        for row in rows:
            status = normalize_status(str(row.get("status") or ""))
            has_draft = row.get("latest_first_decision_draft") is not None
            if status in decision_stage_statuses or has_draft:
                filtered_rows.append(row)
        return filtered_rows

    def submit_academic_check(
        self,
        manuscript_id: UUID,
        decision: str,
        comment: str | None = None,
        *,
        changed_by: UUID | str | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        """
        EIC academic check:
        - review -> under_review
        - decision_phase -> decision
        """
        manuscript_id_str = str(manuscript_id)
        actor = str(changed_by) if changed_by else None
        d = str(decision or "").strip().lower()
        if d not in {"review", "decision_phase"}:
            raise HTTPException(status_code=422, detail="decision must be review or decision_phase")
        to_status = ManuscriptStatus.UNDER_REVIEW.value if d == "review" else ManuscriptStatus.DECISION.value

        ms = self._get_manuscript(manuscript_id_str)
        status = normalize_status(str(ms.get("status") or ""))
        pre = self._normalize_precheck_status(ms.get("pre_check_status"))
        if status != ManuscriptStatus.PRE_CHECK.value:
            if status == to_status:
                return ms
            raise HTTPException(status_code=409, detail="Academic check conflict: manuscript state changed")
        if pre != PreCheckStatus.ACADEMIC.value:
            raise HTTPException(status_code=409, detail=f"Academic check only allowed in academic stage, current={pre}")

        payload_action = "precheck_academic_to_review" if d == "review" else "precheck_academic_to_decision"
        updated = self.editorial.update_status(
            manuscript_id=manuscript_id_str,
            to_status=to_status,
            changed_by=actor,
            comment=(comment or "").strip() or None,
            allow_skip=False,
            extra_updates={"pre_check_status": None},
            payload={
                "action": payload_action,
                "pre_check_from": PreCheckStatus.ACADEMIC.value,
                "pre_check_to": None,
                "assistant_editor_before": str(ms.get("assistant_editor_id") or "") or None,
                "assistant_editor_after": str(ms.get("assistant_editor_id") or "") or None,
                "decision": d,
                "idempotency_key": idempotency_key,
            },
        )
        return updated
