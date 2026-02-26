from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from app.models.manuscript import ManuscriptStatus, PreCheckStatus, normalize_status

logger = logging.getLogger("scholarflow.editor_precheck_workspace")


class EditorServicePrecheckWorkspaceViewMixin:
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
