from __future__ import annotations

from typing import Any, Iterable
from uuid import UUID

from fastapi import HTTPException

from app.core.journal_scope import get_user_scope_journal_ids, is_scope_enforcement_enabled
from app.core.role_matrix import normalize_roles
from app.models.manuscript import ManuscriptStatus, PreCheckStatus, normalize_status


class EditorServicePrecheckWorkspaceMixin:
    def _derive_ae_workspace_bucket(self, *, status: str | None, pre_check_status: str | None) -> str:
        if status == ManuscriptStatus.PRE_CHECK.value and pre_check_status == PreCheckStatus.TECHNICAL.value:
            return "technical"
        if status == ManuscriptStatus.PRE_CHECK.value and pre_check_status == PreCheckStatus.ACADEMIC.value:
            return "academic_pending"
        if status == ManuscriptStatus.UNDER_REVIEW.value:
            return "under_review"
        if status in {
            ManuscriptStatus.RESUBMITTED.value,
            ManuscriptStatus.MINOR_REVISION.value,
            ManuscriptStatus.MAJOR_REVISION.value,
        }:
            return "revision_followup"
        if status == ManuscriptStatus.DECISION.value:
            return "decision"
        return "other"

    def _derive_managing_workspace_bucket(self, *, status: str | None, pre_check_status: str | None) -> str:
        if status == ManuscriptStatus.PRE_CHECK.value:
            if pre_check_status in {None, "", PreCheckStatus.INTAKE.value}:
                return "intake"
            if pre_check_status == PreCheckStatus.TECHNICAL.value:
                return "technical_followup"
            if pre_check_status == PreCheckStatus.ACADEMIC.value:
                return "academic_pending"
            return "precheck_other"
        if status == ManuscriptStatus.UNDER_REVIEW.value:
            return "under_review"
        if status in {
            ManuscriptStatus.RESUBMITTED.value,
            ManuscriptStatus.MINOR_REVISION.value,
            ManuscriptStatus.MAJOR_REVISION.value,
        }:
            return "revision_followup"
        if status in {ManuscriptStatus.DECISION.value, ManuscriptStatus.DECISION_DONE.value}:
            return "decision"
        if status in {
            ManuscriptStatus.APPROVED.value,
            ManuscriptStatus.LAYOUT.value,
            ManuscriptStatus.ENGLISH_EDITING.value,
            ManuscriptStatus.PROOFREADING.value,
        }:
            return "production"
        return "other"

    def get_managing_workspace(
        self,
        *,
        viewer_user_id: str,
        viewer_roles: list[str] | None,
        page: int = 1,
        page_size: int = 20,
        q: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Managing Editor Workspace：
        - 聚合 ME 需要跟进的全流程稿件，并按状态输出 workspace_bucket。
        - 仅包含非终态工作流（排除 published/rejected）。
        """
        status_scope = [
            ManuscriptStatus.PRE_CHECK.value,
            ManuscriptStatus.UNDER_REVIEW.value,
            ManuscriptStatus.MINOR_REVISION.value,
            ManuscriptStatus.MAJOR_REVISION.value,
            ManuscriptStatus.RESUBMITTED.value,
            ManuscriptStatus.DECISION.value,
            ManuscriptStatus.DECISION_DONE.value,
            ManuscriptStatus.APPROVED.value,
            ManuscriptStatus.LAYOUT.value,
            ManuscriptStatus.ENGLISH_EDITING.value,
            ManuscriptStatus.PROOFREADING.value,
        ]
        selects = [
            "id,title,created_at,updated_at,status,pre_check_status,assistant_editor_id,owner_id,journal_id,journals(title,slug)",
            "id,title,created_at,updated_at,status,pre_check_status,assistant_editor_id,owner_id,journal_id",
            "id,title,created_at,updated_at,status,pre_check_status,assistant_editor_id,owner_id",
        ]
        fetch_end = max(page * page_size - 1, page_size - 1)

        rows: list[dict[str, Any]] = []
        last_error: Exception | None = None
        for select_clause in selects:
            try:
                resp = (
                    self.client.table("manuscripts")
                    .select(select_clause)
                    .in_("status", status_scope)
                    .order("updated_at", desc=True)
                    .order("created_at", desc=True)
                    .range(0, fetch_end)
                    .execute()
                )
                rows = getattr(resp, "data", None) or []
                break
            except Exception as e:
                last_error = e
                lowered = str(e).lower()
                if "journals" in lowered or "schema cache" in lowered or "pgrst" in lowered:
                    continue
                raise
        if not rows and last_error:
            lowered = str(last_error).lower()
            if "schema cache" in lowered or "could not find" in lowered:
                raise last_error

        precheck_rows = [
            row
            for row in rows
            if normalize_status(str(row.get("status") or "")) == ManuscriptStatus.PRE_CHECK.value
        ]
        precheck_enriched = self._enrich_precheck_rows(precheck_rows) if precheck_rows else []
        precheck_by_id = {
            str(item.get("id") or ""): item
            for item in precheck_enriched
            if str(item.get("id") or "").strip()
        }
        out: list[dict[str, Any]] = []
        for base_row in rows:
            row = dict(base_row)
            row_id = str(row.get("id") or "").strip()
            precheck_override = precheck_by_id.get(row_id)
            if precheck_override:
                row["pre_check_status"] = precheck_override.get("pre_check_status")
                row["current_role"] = precheck_override.get("current_role")
                row["current_assignee"] = precheck_override.get("current_assignee")
                row["assigned_at"] = precheck_override.get("assigned_at")
                row["technical_completed_at"] = precheck_override.get("technical_completed_at")
                row["academic_completed_at"] = precheck_override.get("academic_completed_at")

            normalized_status = normalize_status(str(row.get("status") or ""))
            if not normalized_status:
                continue
            normalized_precheck = self._normalize_precheck_status(row.get("pre_check_status"))
            if normalized_status == ManuscriptStatus.PRE_CHECK.value and normalized_precheck is None:
                normalized_precheck = PreCheckStatus.INTAKE.value
            row["status"] = normalized_status
            row["pre_check_status"] = normalized_precheck
            row["workspace_bucket"] = self._derive_managing_workspace_bucket(
                status=normalized_status,
                pre_check_status=normalized_precheck,
            )
            out.append(row)

        profile_ids = sorted(
            {
                str(pid)
                for row in out
                for pid in (row.get("owner_id"), row.get("assistant_editor_id"))
                if str(pid or "").strip()
            }
        )
        profile_map: dict[str, dict[str, Any]] = {}
        if profile_ids:
            try:
                prof = (
                    self.client.table("user_profiles")
                    .select("id,full_name,email")
                    .in_("id", profile_ids)
                    .execute()
                )
                for p in (getattr(prof, "data", None) or []):
                    pid = str(p.get("id") or "")
                    if pid:
                        profile_map[pid] = p
            except Exception as e:
                print(f"[MEWorkspace] load profiles failed (ignored): {e}")

        for row in out:
            oid = str(row.get("owner_id") or "")
            ae_id = str(row.get("assistant_editor_id") or "")
            row["owner"] = (
                {
                    "id": oid,
                    "full_name": (profile_map.get(oid) or {}).get("full_name"),
                    "email": (profile_map.get(oid) or {}).get("email"),
                }
                if oid
                else None
            )
            row["assistant_editor"] = (
                {
                    "id": ae_id,
                    "full_name": (profile_map.get(ae_id) or {}).get("full_name"),
                    "email": (profile_map.get(ae_id) or {}).get("email"),
                }
                if ae_id
                else None
            )
            journal = row.get("journals")
            if isinstance(journal, list):
                row["journal"] = journal[0] if journal else None
            elif isinstance(journal, dict):
                row["journal"] = journal
            else:
                row["journal"] = None

        keyword = str(q or "").strip().lower()
        if keyword:
            out = [
                row
                for row in out
                if keyword in str(row.get("title") or "").lower()
                or keyword in str(row.get("id") or "").lower()
                or keyword in str(((row.get("owner") or {}).get("full_name") or "")).lower()
                or keyword in str(((row.get("assistant_editor") or {}).get("full_name") or "")).lower()
                or keyword in str(((row.get("journal") or {}).get("title") or "")).lower()
            ]

        out = self._apply_process_visibility_scope(
            rows=out,
            viewer_user_id=viewer_user_id,
            viewer_roles=viewer_roles,
        )

        out.sort(
            key=lambda r: (
                str(r.get("updated_at") or ""),
                str(r.get("created_at") or ""),
            ),
            reverse=True,
        )
        start = max((page - 1) * page_size, 0)
        end = start + page_size
        return out[start:end]

    def get_ae_workspace(self, ae_id: UUID, page: int = 1, page_size: int = 20) -> list[dict[str, Any]]:
        """
        AE Workspace：返回 AE 在办稿件全集（仅本人分管）。

        设计约束：
        - pre_check 仅展示 technical 子阶段（由 ME 分配后待发起外审）；
        - under_review / major_revision / minor_revision / resubmitted / decision 也纳入 AE 待办；
        - 默认按 updated_at 倒序，确保最近更新稿件置顶。
        """
        status_scope = [
            ManuscriptStatus.PRE_CHECK.value,
            ManuscriptStatus.UNDER_REVIEW.value,
            ManuscriptStatus.MINOR_REVISION.value,
            ManuscriptStatus.MAJOR_REVISION.value,
            ManuscriptStatus.RESUBMITTED.value,
            ManuscriptStatus.DECISION.value,
        ]
        selects = [
            "id,title,created_at,updated_at,status,pre_check_status,assistant_editor_id,owner_id,journal_id,journals(title,slug)",
            "id,title,created_at,updated_at,status,pre_check_status,assistant_editor_id,owner_id,journal_id",
            "id,title,created_at,updated_at,status,pre_check_status,assistant_editor_id,owner_id",
            "id,title,created_at,updated_at,status,pre_check_status,assistant_editor_id",
        ]

        rows: list[dict[str, Any]] = []
        select_used: str | None = None
        last_error: Exception | None = None
        for select_clause in selects:
            try:
                q = (
                    self.client.table("manuscripts")
                    .select(select_clause)
                    .in_("status", status_scope)
                    .eq("assistant_editor_id", str(ae_id))
                    .order("updated_at", desc=True)
                    .order("created_at", desc=True)
                    .range((page - 1) * page_size, page * page_size - 1)
                )
                resp = q.execute()
                rows = getattr(resp, "data", None) or []
                select_used = select_clause
                break
            except Exception as e:
                last_error = e
                lowered = str(e).lower()
                if "journals" in lowered or "schema cache" in lowered or "pgrst" in lowered:
                    continue
                raise
        if not rows and last_error:
            lowered = str(last_error).lower()
            if "schema cache" in lowered or "could not find" in lowered:
                raise last_error

        # 兼容：历史环境可能仍存在 manuscripts.status='pending_decision'（TEXT）。
        # 注意：若 status 已迁移为 ENUM，则该过滤会触发 “invalid input value for enum”，因此必须忽略错误。
        legacy_rows: list[dict[str, Any]] = []
        if select_used:
            try:
                legacy_resp = (
                    self.client.table("manuscripts")
                    .select(select_used)
                    .eq("assistant_editor_id", str(ae_id))
                    .eq("status", "pending_decision")
                    .order("updated_at", desc=True)
                    .order("created_at", desc=True)
                    .range((page - 1) * page_size, page * page_size - 1)
                    .execute()
                )
                legacy_rows = getattr(legacy_resp, "data", None) or []
            except Exception as e:
                msg = str(e).lower()
                if "invalid input value" not in msg and "enum" not in msg and "pending_decision" not in msg:
                    print(f"[AEWorkspace] legacy pending_decision query failed (ignored): {e}")
                legacy_rows = []

        if legacy_rows:
            merged: dict[str, dict[str, Any]] = {}
            for r in rows + legacy_rows:
                mid = str(r.get("id") or "").strip()
                if not mid:
                    continue
                merged[mid] = r
            rows = list(merged.values())
            rows.sort(
                key=lambda r: (
                    str(r.get("updated_at") or ""),
                    str(r.get("created_at") or ""),
                ),
                reverse=True,
            )
            rows = rows[:page_size]

        precheck_rows = [
            row
            for row in rows
            if normalize_status(str(row.get("status") or "")) == ManuscriptStatus.PRE_CHECK.value
        ]
        precheck_enriched = self._enrich_precheck_rows(precheck_rows) if precheck_rows else []
        precheck_by_id = {
            str(item.get("id") or ""): item
            for item in precheck_enriched
            if str(item.get("id") or "").strip()
        }
        out: list[dict[str, Any]] = []
        for base_row in rows:
            row = dict(base_row)
            row_id = str(row.get("id") or "").strip()
            precheck_override = precheck_by_id.get(row_id)
            if precheck_override:
                row["pre_check_status"] = precheck_override.get("pre_check_status")
                row["current_role"] = precheck_override.get("current_role")
                row["current_assignee"] = precheck_override.get("current_assignee")
                row["assigned_at"] = precheck_override.get("assigned_at")
                row["technical_completed_at"] = precheck_override.get("technical_completed_at")
                row["academic_completed_at"] = precheck_override.get("academic_completed_at")

            normalized_status = normalize_status(str(row.get("status") or ""))
            normalized_precheck = self._normalize_precheck_status(row.get("pre_check_status"))
            if normalized_status:
                row["status"] = normalized_status
            if normalized_status == ManuscriptStatus.PRE_CHECK.value and normalized_precheck not in {
                PreCheckStatus.TECHNICAL.value,
                PreCheckStatus.ACADEMIC.value,
            }:
                continue
            row["workspace_bucket"] = self._derive_ae_workspace_bucket(
                status=normalized_status,
                pre_check_status=normalized_precheck,
            )
            out.append(row)

        owner_ids = sorted({str(r.get("owner_id") or "") for r in out if str(r.get("owner_id") or "")})
        owner_map: dict[str, dict[str, Any]] = {}
        if owner_ids:
            try:
                prof = (
                    self.client.table("user_profiles")
                    .select("id,full_name,email")
                    .in_("id", owner_ids)
                    .execute()
                )
                for p in (getattr(prof, "data", None) or []):
                    pid = str(p.get("id") or "")
                    if pid:
                        owner_map[pid] = p
            except Exception as e:
                print(f"[AEWorkspace] load owner profiles failed (ignored): {e}")

        for row in out:
            oid = str(row.get("owner_id") or "")
            row["owner"] = (
                {
                    "id": oid,
                    "full_name": (owner_map.get(oid) or {}).get("full_name"),
                    "email": (owner_map.get(oid) or {}).get("email"),
                }
                if oid
                else None
            )
            journal = row.get("journals")
            if isinstance(journal, list):
                row["journal"] = journal[0] if journal else None
            elif isinstance(journal, dict):
                row["journal"] = journal
            else:
                row["journal"] = None

        return out

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
                print(f"[FinalDecisionQueue] load draft decision letters failed (ignored): {e}")

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
