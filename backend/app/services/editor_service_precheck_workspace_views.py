from __future__ import annotations

import logging
from types import SimpleNamespace
from typing import Any
from uuid import UUID

from fastapi import HTTPException

from app.core.journal_scope import ensure_manuscript_scope_access
from app.core.role_matrix import normalize_roles
from app.models.manuscript import ManuscriptStatus, PreCheckStatus, normalize_status

logger = logging.getLogger("scholarflow.editor_precheck_workspace")


class EditorServicePrecheckWorkspaceViewMixin:
    def list_academic_editor_candidates(
        self,
        *,
        manuscript_id: UUID | str,
        viewer_user_id: str,
        viewer_roles: list[str] | None,
        search: str | None = None,
    ) -> list[dict[str, Any]]:
        manuscript_id_str = str(manuscript_id)
        manuscript = self._get_manuscript(manuscript_id_str)
        normalized_viewer_roles = set(normalize_roles(viewer_roles or []))
        viewer_id_str = str(viewer_user_id or "").strip()
        pure_assistant_editor = (
            "assistant_editor" in normalized_viewer_roles
            and not bool({"admin", "managing_editor", "editor_in_chief"} & normalized_viewer_roles)
        )
        assigned_ae_id = str(manuscript.get("assistant_editor_id") or "").strip()
        if pure_assistant_editor and assigned_ae_id != viewer_id_str:
            raise HTTPException(status_code=403, detail="Only the assigned assistant editor can view academic editor candidates")
        ensure_manuscript_scope_access(
            manuscript_id=manuscript_id_str,
            user_id=viewer_id_str,
            roles=viewer_roles or [],
            allow_admin_bypass=True,
        )
        journal_id = str(manuscript.get("journal_id") or "").strip()
        bound_academic_editor_id = str(manuscript.get("academic_editor_id") or "").strip()
        allowed_roles = {"academic_editor", "editor_in_chief"}

        candidate_ids: set[str] = set()
        if journal_id:
            try:
                scope_resp = (
                    self.client.table("journal_role_scopes")
                    .select("user_id,role")
                    .eq("journal_id", journal_id)
                    .eq("is_active", True)
                    .in_("role", sorted(allowed_roles))
                    .execute()
                )
                for row in (getattr(scope_resp, "data", None) or []):
                    user_id = str(row.get("user_id") or "").strip()
                    if user_id:
                        candidate_ids.add(user_id)
            except Exception as e:
                logger.warning("[AcademicEditors] load journal role scopes failed, fallback to role query: %s", e)

        if candidate_ids:
            profile_resp = (
                self.client.table("user_profiles")
                .select("id,email,full_name,roles")
                .in_("id", sorted(candidate_ids))
                .execute()
            )
        else:
            profile_resp = SimpleNamespace(data=[])

        candidates: list[dict[str, Any]] = []
        seen_ids: set[str] = set()
        for row in (getattr(profile_resp, "data", None) or []):
            row_id = str(row.get("id") or "").strip()
            if not row_id:
                continue
            role_set = normalize_roles(row.get("roles") or [])
            if not role_set.intersection(allowed_roles):
                continue
            seen_ids.add(row_id)
            candidates.append(row)

        if bound_academic_editor_id and bound_academic_editor_id not in seen_ids:
            try:
                bound_resp = (
                    self.client.table("user_profiles")
                    .select("id,email,full_name,roles")
                    .eq("id", bound_academic_editor_id)
                    .single()
                    .execute()
                )
                bound_row = getattr(bound_resp, "data", None) or {}
                bound_id = str(bound_row.get("id") or "").strip()
                if bound_id:
                    candidates.append(bound_row)
                    seen_ids.add(bound_id)
            except Exception as e:
                logger.warning("[AcademicEditors] load bound academic editor failed (ignored): %s", e)

        keyword = str(search or "").strip().lower()
        if keyword:
            candidates = [
                row
                for row in candidates
                if keyword in str(row.get("email") or "").lower()
                or keyword in str(row.get("full_name") or "").lower()
            ]

        candidates.sort(
            key=lambda row: (
                0 if str(row.get("id") or "").strip() == bound_academic_editor_id else 1,
                0 if "editor_in_chief" in normalize_roles(row.get("roles") or []) else 1,
                0 if str(row.get("full_name") or "").strip() else 1,
                str(row.get("full_name") or row.get("email") or "").lower(),
            )
        )
        return candidates

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
        if status == ManuscriptStatus.REVISION_BEFORE_REVIEW.value:
            return "awaiting_author"
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
            ManuscriptStatus.REVISION_BEFORE_REVIEW.value,
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
        precheck_enriched = (
            self._enrich_precheck_rows(
                precheck_rows,
                include_timeline=False,
                include_assignee_profiles=False,
            )
            if precheck_rows
            else []
        )
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
                row["academic_recommendation"] = precheck_override.get("academic_recommendation")
                row["academic_recommendation_comment"] = precheck_override.get("academic_recommendation_comment")

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

        out = self._apply_process_visibility_scope(
            rows=out,
            viewer_user_id=viewer_user_id,
            viewer_roles=viewer_roles,
        )

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
                logger.warning("[MEWorkspace] load profiles failed (ignored): %s", e)

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
            if isinstance(row.get("current_assignee"), dict) and ae_id:
                row["current_assignee"] = {
                    "id": ae_id,
                    "full_name": (profile_map.get(ae_id) or {}).get("full_name"),
                    "email": (profile_map.get(ae_id) or {}).get("email"),
                }
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
                    logger.warning("[AEWorkspace] legacy pending_decision query failed (ignored): %s", e)
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
        precheck_enriched = (
            self._enrich_precheck_rows(
                precheck_rows,
                include_timeline=False,
                include_assignee_profiles=False,
            )
            if precheck_rows
            else []
        )
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
                row["academic_recommendation"] = precheck_override.get("academic_recommendation")
                row["academic_recommendation_comment"] = precheck_override.get("academic_recommendation_comment")

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
                logger.warning("[AEWorkspace] load owner profiles failed (ignored): %s", e)

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
