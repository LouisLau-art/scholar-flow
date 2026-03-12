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
    def _uses_bound_academic_assignment_scope(self, roles: set[str]) -> bool:
        return bool({"academic_editor", "editor_in_chief"} & roles) and not bool({"admin", "managing_editor"} & roles)

    def submit_technical_check(
        self,
        manuscript_id: UUID,
        ae_id: UUID,
        *,
        decision: str,
        comment: str | None = None,
        academic_editor_id: UUID | str | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        """
        AE technical check:
        - pass -> under_review（跳过 academic pre-check）
        - academic -> pre_check/academic（送 EIC 预审，可选）
        - revision -> revision_before_review
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
            if normalized_decision == "revision" and status in {
                ManuscriptStatus.REVISION_BEFORE_REVIEW.value,
                ManuscriptStatus.MINOR_REVISION.value,
            }:
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
            academic_editor_id_str = str(academic_editor_id or "").strip()
            if not academic_editor_id_str:
                raise HTTPException(status_code=422, detail="academic_editor_id is required for academic routing")
            self._validate_academic_editor_assignment(
                academic_editor_id=academic_editor_id_str,
                manuscript_journal_id=str(ms.get("journal_id") or "").strip() or None,
            )
            now = self._now()
            data = {
                "pre_check_status": PreCheckStatus.ACADEMIC.value,
                "academic_editor_id": academic_editor_id_str,
                "academic_submitted_at": now,
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
                latest_academic_editor_id = str(latest.get("academic_editor_id") or "")
                if (
                    latest_status == ManuscriptStatus.PRE_CHECK.value
                    and latest_pre == PreCheckStatus.ACADEMIC.value
                    and latest_ae == ae_id_str
                    and latest_academic_editor_id == academic_editor_id_str
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
                    "academic_editor_before": str(ms.get("academic_editor_id") or "") or None,
                    "academic_editor_after": academic_editor_id_str,
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
            to_status=ManuscriptStatus.REVISION_BEFORE_REVIEW.value,
            changed_by=ae_id_str,
            comment=comment_clean,
            allow_skip=False,
            extra_updates={
                "ae_sla_started_at": str(ms.get("ae_sla_started_at") or "").strip() or self._now(),
                "pre_check_status": PreCheckStatus.TECHNICAL.value,
                "assistant_editor_id": owner_ae or None,
            },
            payload={
                "action": "precheck_technical_revision",
                "pre_check_from": PreCheckStatus.TECHNICAL.value,
                "pre_check_to": PreCheckStatus.TECHNICAL.value,
                "assistant_editor_before": owner_ae or None,
                "assistant_editor_after": owner_ae or None,
                "decision": "revision",
                "idempotency_key": idempotency_key,
            },
        )
        return updated

    def revert_technical_check(
        self,
        manuscript_id: UUID,
        actor_id: UUID | str,
        *,
        reason: str,
        actor_roles: Iterable[str] | None = None,
        source: str | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        """
        受控回退：under_review -> pre_check(technical)

        约束：
        - 仅在 under_review 阶段；
        - 最近一次进入 under_review 必须来自 precheck_technical_to_under_review；
        - 不存在进行中的 review_assignments；
        - assistant_editor 仅可操作自己分配的稿件；managing_editor/admin 可覆盖。
        """
        manuscript_id_str = str(manuscript_id)
        actor_id_str = str(actor_id)
        normalized_roles = set(normalize_roles(actor_roles))
        reason_clean = str(reason or "").strip()
        if len(reason_clean) < 10:
            raise HTTPException(status_code=422, detail="reason must be at least 10 characters")

        ms = self._get_manuscript(manuscript_id_str)
        status = normalize_status(str(ms.get("status") or ""))
        pre = self._normalize_precheck_status(ms.get("pre_check_status"))
        owner_ae = str(ms.get("assistant_editor_id") or "")

        if status == ManuscriptStatus.PRE_CHECK.value and pre == PreCheckStatus.TECHNICAL.value:
            # 幂等兜底：已经回退成功时重复提交直接返回。
            return self._map_precheck_row(ms)

        if status != ManuscriptStatus.UNDER_REVIEW.value:
            raise HTTPException(status_code=409, detail="Technical-check revert only allowed in under_review")

        has_global_override = bool({"admin", "managing_editor"} & normalized_roles)
        if not has_global_override and owner_ae != actor_id_str:
            raise HTTPException(status_code=403, detail="Only assigned assistant editor can revert technical check")

        # 约束1：最近一次进入 under_review 必须来自 precheck_technical_to_under_review。
        try:
            log_resp = (
                self.client.table("status_transition_logs")
                .select("id,created_at,payload")
                .eq("manuscript_id", manuscript_id_str)
                .eq("to_status", ManuscriptStatus.UNDER_REVIEW.value)
                .order("created_at", desc=True)
                .range(0, 0)
                .execute()
            )
            log_rows = getattr(log_resp, "data", None) or []
        except Exception as e:
            logger.warning("[RevertTechnicalCheck] load status_transition_logs failed: %s", e)
            raise HTTPException(status_code=409, detail="Cannot verify transition history for revert")

        latest_log = log_rows[0] if log_rows else None
        payload = latest_log.get("payload") if isinstance((latest_log or {}).get("payload"), dict) else {}
        latest_action = str(payload.get("action") or "").strip().lower()
        if latest_action != "precheck_technical_to_under_review":
            raise HTTPException(
                status_code=409,
                detail="Technical-check revert blocked: latest under_review source is not technical submit-check",
            )

        # 约束2：外审尚未实质开始（仅允许空集，或全部 cancelled/declined）。
        try:
            ra_resp = (
                self.client.table("review_assignments")
                .select("id,status,accepted_at,submitted_at,declined_at")
                .eq("manuscript_id", manuscript_id_str)
                .execute()
            )
            ra_rows = getattr(ra_resp, "data", None) or []
        except Exception as e:
            logger.warning("[RevertTechnicalCheck] load review_assignments failed: %s", e)
            raise HTTPException(status_code=409, detail="Cannot verify reviewer assignments for revert")

        def _is_active_assignment(row: dict[str, Any]) -> bool:
            status_raw = str(row.get("status") or "").strip().lower()
            if status_raw in {"cancelled", "declined"}:
                return False
            if row.get("declined_at") and status_raw in {"", "pending", "invited", "opened"}:
                return False
            # accepted/submitted/completed/pending/invited/opened/unknown 全部视为“已开始或不可安全回退”
            if row.get("accepted_at") or row.get("submitted_at"):
                return True
            return True

        if any(_is_active_assignment(row) for row in ra_rows):
            raise HTTPException(
                status_code=409,
                detail="Technical-check revert blocked: reviewer assignments already started",
            )

        now = self._now()
        update_payload = {
            "status": ManuscriptStatus.PRE_CHECK.value,
            "pre_check_status": PreCheckStatus.TECHNICAL.value,
            "updated_at": now,
        }
        q = (
            self.client.table("manuscripts")
            .update(update_payload)
            .eq("id", manuscript_id_str)
            .eq("status", ManuscriptStatus.UNDER_REVIEW.value)
        )
        if not has_global_override:
            q = q.eq("assistant_editor_id", actor_id_str)
        upd = q.execute()
        rows = getattr(upd, "data", None) or []
        if not rows:
            latest = self._get_manuscript(manuscript_id_str)
            latest_status = normalize_status(str(latest.get("status") or ""))
            latest_pre = self._normalize_precheck_status(latest.get("pre_check_status"))
            if latest_status == ManuscriptStatus.PRE_CHECK.value and latest_pre == PreCheckStatus.TECHNICAL.value:
                return self._map_precheck_row(latest)
            raise HTTPException(status_code=409, detail="Technical-check revert conflict: manuscript state changed")

        self._safe_insert_transition_log(
            manuscript_id=manuscript_id_str,
            from_status=ManuscriptStatus.UNDER_REVIEW.value,
            to_status=ManuscriptStatus.PRE_CHECK.value,
            changed_by=actor_id_str,
            comment=reason_clean,
            payload={
                "action": "precheck_technical_revert_from_under_review",
                "reason": reason_clean,
                "source": str(source or "ae_workspace"),
                "assistant_editor_before": owner_ae or None,
                "assistant_editor_after": owner_ae or None,
                "idempotency_key": idempotency_key,
            },
            created_at=now,
        )
        return self._map_precheck_row(rows[0])

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

        if self._uses_bound_academic_assignment_scope(normalized_roles):
            viewer_id_str = str(viewer_user_id or "").strip()
            out = [
                row for row in out if str(row.get("academic_editor_id") or "").strip() == viewer_id_str
            ]

        if "admin" not in normalized_roles:
            scoped_journal_ids = get_user_scope_journal_ids(
                user_id=str(viewer_user_id),
                roles=normalized_roles,
            )
            has_global_scope_role = bool({"managing_editor", "academic_editor", "editor_in_chief"} & normalized_roles)
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
        - 仅展示 status in decision / decision_done（终审阶段）
        - under_review / resubmitted 必须先通过 Exit Review Stage 进入决策队列
        """
        normalized_roles = set(normalize_roles(viewer_roles))
        decision_stage_statuses = {
            ManuscriptStatus.DECISION.value,
            ManuscriptStatus.DECISION_DONE.value,
        }
        q = (
            self.client.table("manuscripts")
            .select("id,title,status,updated_at,journal_id,journals(title,slug),assistant_editor_id,academic_editor_id,owner_id")
            .in_(
                "status",
                [
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

        if self._uses_bound_academic_assignment_scope(normalized_roles):
            viewer_id_str = str(viewer_user_id or "").strip()
            rows = [
                row for row in rows if str(row.get("academic_editor_id") or "").strip() == viewer_id_str
            ]

        if "admin" not in normalized_roles:
            scoped_journal_ids = get_user_scope_journal_ids(
                user_id=str(viewer_user_id),
                roles=normalized_roles,
            )
            has_global_scope_role = bool({"managing_editor", "academic_editor", "editor_in_chief"} & normalized_roles)
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
            if status in decision_stage_statuses:
                filtered_rows.append(row)
        return filtered_rows

    def submit_academic_check(
        self,
        manuscript_id: UUID,
        decision: str,
        comment: str | None = None,
        *,
        changed_by: UUID | str | None = None,
        actor_roles: Iterable[str] | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        """
        EIC / Academic Editor academic check:
        - 仅记录学术 recommendation
        - 不直接推进 manuscript 主状态
        - 后续由编辑部执行 under_review / decision 等真实流转
        """
        manuscript_id_str = str(manuscript_id)
        actor = str(changed_by) if changed_by else None
        d = str(decision or "").strip().lower()
        if d not in {"review", "decision_phase"}:
            raise HTTPException(status_code=422, detail="decision must be review or decision_phase")
        recommended_next_status = (
            ManuscriptStatus.UNDER_REVIEW.value
            if d == "review"
            else ManuscriptStatus.DECISION.value
        )

        ms = self._get_manuscript(manuscript_id_str)
        status = normalize_status(str(ms.get("status") or ""))
        pre = self._normalize_precheck_status(ms.get("pre_check_status"))
        if status != ManuscriptStatus.PRE_CHECK.value:
            raise HTTPException(status_code=409, detail="Academic check conflict: manuscript state changed")
        if pre != PreCheckStatus.ACADEMIC.value:
            raise HTTPException(status_code=409, detail=f"Academic check only allowed in academic stage, current={pre}")

        actor_id = str(actor or "").strip()
        normalized_actor_roles = set(normalize_roles(actor_roles))
        bound_academic_editor_id = str(ms.get("academic_editor_id") or "").strip()
        if (
            actor_id
            and "admin" not in normalized_actor_roles
            and bound_academic_editor_id != actor_id
        ):
            raise HTTPException(status_code=403, detail="Only the bound academic editor can submit academic check")

        now = self._now()
        comment_clean = (comment or "").strip() or None
        update_payload = {
            "academic_completed_at": now,
            "updated_at": now,
        }
        q = (
            self.client.table("manuscripts")
            .update(update_payload)
            .eq("id", manuscript_id_str)
            .eq("status", ManuscriptStatus.PRE_CHECK.value)
            .eq("pre_check_status", PreCheckStatus.ACADEMIC.value)
        )
        if actor_id and "admin" not in normalized_actor_roles:
            q = q.eq("academic_editor_id", actor_id)
        resp = q.execute()
        rows = getattr(resp, "data", None) or []
        if not rows:
            latest = self._get_manuscript(manuscript_id_str)
            latest_status = normalize_status(str(latest.get("status") or ""))
            latest_pre = self._normalize_precheck_status(latest.get("pre_check_status"))
            latest_academic_editor_id = str(latest.get("academic_editor_id") or "").strip()
            if latest_status == ManuscriptStatus.PRE_CHECK.value and latest_pre == PreCheckStatus.ACADEMIC.value:
                if "admin" in normalized_actor_roles or not actor_id or latest_academic_editor_id == actor_id:
                    mapped_latest = self._map_precheck_row(latest)
                    mapped_latest["academic_recommendation"] = d
                    mapped_latest["academic_recommendation_comment"] = comment_clean
                    return mapped_latest
            raise HTTPException(status_code=409, detail="Academic check conflict: manuscript state changed")

        updated = self._map_precheck_row(rows[0])
        updated["academic_recommendation"] = d
        updated["academic_recommendation_comment"] = comment_clean
        self._safe_insert_transition_log(
            manuscript_id=manuscript_id_str,
            from_status=ManuscriptStatus.PRE_CHECK.value,
            to_status=ManuscriptStatus.PRE_CHECK.value,
            changed_by=actor_id or None,
            comment=comment_clean,
            payload={
                "action": "precheck_academic_recommendation_submitted",
                "pre_check_from": PreCheckStatus.ACADEMIC.value,
                "pre_check_to": PreCheckStatus.ACADEMIC.value,
                "assistant_editor_before": str(ms.get("assistant_editor_id") or "") or None,
                "assistant_editor_after": str(ms.get("assistant_editor_id") or "") or None,
                "academic_editor_before": str(ms.get("academic_editor_id") or "") or None,
                "academic_editor_after": str(ms.get("academic_editor_id") or "") or None,
                "decision": d,
                "recommended_next_status": recommended_next_status,
                "execution_required": True,
                "idempotency_key": idempotency_key,
            },
            created_at=now,
        )
        return updated

    def _validate_academic_editor_assignment(
        self,
        *,
        academic_editor_id: str,
        manuscript_journal_id: str | None,
    ) -> dict[str, Any]:
        academic_editor_id_str = str(academic_editor_id or "").strip()
        if not academic_editor_id_str:
            raise HTTPException(status_code=422, detail="academic_editor_id is required")

        try:
            resp = (
                self.client.table("user_profiles")
                .select("id,full_name,email,roles")
                .eq("id", academic_editor_id_str)
                .single()
                .execute()
            )
        except Exception as e:
            raise HTTPException(status_code=422, detail="academic_editor_id profile not found") from e

        profile = getattr(resp, "data", None) or {}
        if not profile:
            raise HTTPException(status_code=422, detail="academic_editor_id profile not found")

        role_set = set(normalize_roles(profile.get("roles") or []))
        if not role_set.intersection({"academic_editor", "editor_in_chief"}):
            raise HTTPException(
                status_code=422,
                detail="academic_editor_id must have academic_editor or editor_in_chief role",
            )

        journal_id = str(manuscript_journal_id or "").strip()
        if journal_id:
            scoped_journal_ids = get_user_scope_journal_ids(
                user_id=academic_editor_id_str,
                roles=role_set,
            )
            if journal_id not in scoped_journal_ids:
                raise HTTPException(
                    status_code=422,
                    detail="academic_editor_id is not scoped to this journal",
                )

        return profile

    def bind_academic_editor(
        self,
        manuscript_id: UUID | str,
        *,
        academic_editor_id: UUID | str,
        changed_by: UUID | str | None,
        reason: str | None = None,
        source: str | None = None,
    ) -> dict[str, Any]:
        manuscript_id_str = str(manuscript_id)
        academic_editor_id_str = str(academic_editor_id or "").strip()
        changed_by_str = str(changed_by or "").strip() or None
        reason_clean = str(reason or "").strip() or None
        source_clean = str(source or "editor_manuscript_detail").strip() or "editor_manuscript_detail"

        ms = self._get_manuscript(manuscript_id_str)
        validated_profile = self._validate_academic_editor_assignment(
            academic_editor_id=academic_editor_id_str,
            manuscript_journal_id=str(ms.get("journal_id") or "").strip() or None,
        )
        before_academic_editor_id = str(ms.get("academic_editor_id") or "").strip() or None
        if before_academic_editor_id == academic_editor_id_str:
            return dict(ms)

        now = self._now()
        update_payload = {
            "academic_editor_id": academic_editor_id_str,
            "updated_at": now,
        }
        if (
            normalize_status(str(ms.get("status") or "")) == ManuscriptStatus.PRE_CHECK.value
            and self._normalize_precheck_status(ms.get("pre_check_status")) == PreCheckStatus.ACADEMIC.value
            and not str(ms.get("academic_submitted_at") or "").strip()
        ):
            update_payload["academic_submitted_at"] = now

        try:
            resp = (
                self.client.table("manuscripts")
                .update(update_payload)
                .eq("id", manuscript_id_str)
                .execute()
            )
        except Exception as e:
            logger.error("[AcademicEditorBinding] update manuscript academic_editor_id failed: %s", e)
            raise HTTPException(status_code=500, detail="Failed to bind academic editor") from e

        rows = getattr(resp, "data", None) or []
        if not rows:
            raise HTTPException(status_code=404, detail="Manuscript not found")
        updated = rows[0]
        self._safe_insert_transition_log(
            manuscript_id=manuscript_id_str,
            from_status=str(ms.get("status") or ""),
            to_status=str(updated.get("status") or ms.get("status") or ""),
            changed_by=changed_by_str,
            comment=reason_clean or "academic editor bound",
            payload={
                "action": "bind_academic_editor",
                "source": source_clean,
                "reason": reason_clean,
                "before": {"academic_editor_id": before_academic_editor_id},
                "after": {
                    "academic_editor_id": academic_editor_id_str,
                    "academic_editor_name": validated_profile.get("full_name"),
                    "academic_editor_email": validated_profile.get("email"),
                },
            },
            created_at=now,
        )
        return updated
