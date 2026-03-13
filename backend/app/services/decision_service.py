from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException

from app.api.v1.editor_common import resolve_author_notification_target
from app.core.journal_scope import ensure_manuscript_scope_access
from app.core.mail import email_service
from app.core.role_matrix import can_perform_action
from app.lib.api_client import supabase_admin
from app.models.decision import (
    DecisionSubmitRequest,
    ReviewStageExitRequest,
    get_workflow_decision_bucket,
    is_academic_recommendation_value,
)
from app.models.manuscript import ManuscriptStatus, normalize_status
from app.services.first_decision_request_email import send_first_decision_request_email
from app.services.reviewer_assignment_cancellation_email import (
    send_reviewer_assignment_cancellation_email,
    should_send_reviewer_assignment_cancellation_email,
)
from app.services.decision_service_attachments import DecisionServiceAttachmentMixin
from app.services.decision_service_letters import DecisionServiceLettersMixin
from app.services.decision_service_transitions import DecisionServiceTransitionsMixin
from app.services.editorial_service import EditorialService
from app.services.notification_service import NotificationService
from app.services.revision_service import RevisionService


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _decode_attachment_ref(raw: str) -> tuple[str, str]:
    text = str(raw or "").strip()
    if "|" in text:
        attachment_id, path = text.split("|", 1)
        return attachment_id.strip(), path.strip()
    # 兼容旧数据：若只存了 path，则用 path 作为 id 占位
    return text, text


class DecisionService(
    DecisionServiceAttachmentMixin,
    DecisionServiceLettersMixin,
    DecisionServiceTransitionsMixin,
):
    """
    Feature 041: Final Decision Workspace service.

    中文注释:
    - 聚合稿件 + 审稿报告 + 草稿，避免前端多次请求拼装。
    - 决策草稿采用乐观锁（updated_at）。
    - 最终决策写入 decision_letters 并触发状态流转与通知。
    """

    def __init__(self) -> None:
        self.client = supabase_admin
        self.editorial = EditorialService()
        self.notification = NotificationService()

    def _roles(self, profile_roles: list[str] | None) -> set[str]:
        return {str(r).strip().lower() for r in (profile_roles or []) if str(r).strip()}

    def _can_decision_action(self, *, action: str, roles: set[str]) -> bool:
        """
        决策权限兼容口径：
        - 常规按 action 精确匹配；
        - submit_final 默认包含 record_first（EIC/Admin 不应出现“全灰不可编辑”）。
        """
        if can_perform_action(action=action, roles=roles):
            return True
        if action == "decision:record_first" and can_perform_action(
            action="decision:submit_final",
            roles=roles,
        ):
            return True
        return False

    def _get_submission_mode(self, roles: set[str]) -> str:
        """
        中文注释：
        - 内部编辑（ME/AE/Admin）进入 decision workspace 时属于执行模式；
        - academic_editor / editor_in_chief 单独进入时属于 recommendation-only；
        - 若用户同时具备内部+学术角色，内部执行语义优先。
        """
        if roles.intersection({"admin", "managing_editor", "assistant_editor"}):
            return "execute"
        if roles.intersection({"academic_editor", "editor_in_chief"}):
            return "recommendation"
        return "execute"

    def _get_manuscript(self, manuscript_id: str) -> dict[str, Any]:
        select_candidates = [
            # 首选：完整字段（含 version + assistant_editor_id）
            "id,title,abstract,status,file_path,version,author_id,editor_id,assistant_editor_id,academic_editor_id,journal_id,updated_at",
            # 兼容：旧 schema 缺少 version
            "id,title,abstract,status,file_path,author_id,editor_id,assistant_editor_id,academic_editor_id,journal_id,updated_at",
            # 兼容：更旧 schema 缺少 version + assistant_editor_id + academic_editor_id
            "id,title,abstract,status,file_path,author_id,editor_id,journal_id,updated_at",
            # 兼容：极旧 schema 缺少 journal_id
            "id,title,abstract,status,file_path,author_id,editor_id,updated_at",
        ]
        resp = None
        last_error: Exception | None = None
        for select_fields in select_candidates:
            try:
                resp = (
                    self.client.table("manuscripts")
                    .select(select_fields)
                    .eq("id", manuscript_id)
                    .single()
                    .execute()
                )
                last_error = None
                break
            except Exception as err:
                last_error = err
                # 只有列缺失才尝试下一档 schema；其他错误直接抛出。
                if "column" not in str(err).lower():
                    raise
                continue

        if last_error is not None:
            raise HTTPException(status_code=404, detail="Manuscript not found") from last_error
        row = getattr(resp, "data", None) or None
        if not row:
            raise HTTPException(status_code=404, detail="Manuscript not found")
        if row.get("version") is None:
            row["version"] = 1
        row.setdefault("assistant_editor_id", None)
        row.setdefault("academic_editor_id", None)
        row.setdefault("journal_id", None)
        return row

    def _ensure_editor_access(
        self, *, manuscript: dict[str, Any], user_id: str, roles: set[str]
    ) -> None:
        # 中文注释：
        # - admin 保留跨稿件兜底权限；
        # - academic_editor / editor_in_chief 在决策链路上都必须绑定到当前稿件。
        if "admin" in roles:
            return
        assigned_editor_id = str(manuscript.get("editor_id") or "")
        if assigned_editor_id and assigned_editor_id == str(user_id):
            return
        assigned_ae_id = str(manuscript.get("assistant_editor_id") or "")
        if assigned_ae_id and assigned_ae_id == str(user_id):
            return
        assigned_academic_id = str(manuscript.get("academic_editor_id") or "")
        if assigned_academic_id and assigned_academic_id == str(user_id):
            return
        raise HTTPException(status_code=403, detail="Forbidden")

    def _ensure_author_or_internal_access(
        self, *, manuscript: dict[str, Any], user_id: str, roles: set[str]
    ) -> bool:
        """
        返回值表示是否为内部角色（managing_editor/admin/eic）。
        """
        if roles.intersection({"admin", "managing_editor", "editor_in_chief"}):
            return True
        if str(manuscript.get("author_id") or "") == str(user_id):
            return False
        raise HTTPException(status_code=403, detail="Forbidden")

    def _ensure_internal_decision_access(
        self,
        *,
        manuscript: dict[str, Any],
        manuscript_id: str,
        user_id: str,
        roles: set[str],
        action: str,
    ) -> None:
        """
        统一的决策权限入口（角色动作 + journal scope + assigned editor）。

        中文注释:
        - route 层已经做过一次校验，这里再做 service 层防线，避免旁路调用绕过；
        - 仅对内部编辑入口生效，作者入口仍走 _ensure_author_or_internal_access。
        """
        if not self._can_decision_action(action=action, roles=roles):
            raise HTTPException(status_code=403, detail=f"Insufficient permission for action: {action}")
        self._ensure_editor_access(manuscript=manuscript, user_id=user_id, roles=roles)

        # 中文注释:
        # - assistant_editor 采用“已分配稿件可访问”策略，不强制绑定 journal scope；
        # - managing_editor/editor_in_chief/admin 继续走 journal scope 强约束。
        # 注意：用户可能同时拥有多个角色（例如 assistant_editor + managing_editor）。
        # 对于“记录 First Decision 草稿/附件”等非最终决策动作，只要其作为 AE 被分配到该稿件，
        # 就应该放行，以避免因缺少 journal scope 导致 AE 工作台/决策工作台被错误阻断。
        assigned_ae_id = str(manuscript.get("assistant_editor_id") or "").strip()
        if action != "decision:submit_final" and assigned_ae_id and assigned_ae_id == str(user_id).strip():
            return

        if "assistant_editor" in roles and not roles.intersection({"admin", "managing_editor", "editor_in_chief"}):
            return

        ensure_manuscript_scope_access(
            manuscript_id=manuscript_id,
            user_id=str(user_id),
            roles=list(roles),
            allow_admin_bypass=True,
        )

    def _safe_insert_audit_log(
        self,
        *,
        manuscript_id: str,
        from_status: str,
        to_status: str,
        changed_by: str,
        comment: str,
        payload: dict[str, Any] | None,
    ) -> None:
        now = _utc_now_iso()
        base_row: dict[str, Any] = {
            "manuscript_id": manuscript_id,
            "from_status": from_status,
            "to_status": to_status,
            "comment": comment,
            "changed_by": changed_by,
            "created_at": now,
        }
        rows: list[dict[str, Any]] = []
        if payload is not None:
            row = dict(base_row)
            row["payload"] = payload
            rows.append(row)
        rows.append(dict(base_row))
        row_without_fk = dict(base_row)
        row_without_fk["changed_by"] = None
        if payload is not None:
            row_without_fk["payload"] = {**payload, "changed_by_raw": changed_by}
        rows.append(row_without_fk)
        rows.append({"manuscript_id": manuscript_id, "from_status": from_status, "to_status": to_status, "comment": comment, "changed_by": None, "created_at": now})

        for row in rows:
            try:
                self.client.table("status_transition_logs").insert(row).execute()
                return
            except Exception:
                continue

    def _get_latest_review_stage_exit_request(self, manuscript_id: str) -> dict[str, Any] | None:
        """
        读取最近一次 review_stage_exit 审计 payload，给 decision workspace 展示 AE 推荐结论。
        """
        try:
            rows = (
                self.client.table("status_transition_logs")
                .select("payload,comment,created_at,changed_by")
                .eq("manuscript_id", manuscript_id)
                .order("created_at", desc=True)
                .limit(20)
                .execute()
                .data
                or []
            )
        except Exception:
            return None

        for row in rows:
            payload = row.get("payload") if isinstance(row, dict) else None
            if not isinstance(payload, dict):
                continue
            if str(payload.get("action") or "").strip().lower() != "review_stage_exit":
                continue
            target_stage = str(payload.get("target_stage") or "").strip().lower()
            if target_stage not in {
                ManuscriptStatus.DECISION.value,
                ManuscriptStatus.DECISION_DONE.value,
                "first",
                "final",
                ManuscriptStatus.MAJOR_REVISION.value,
                ManuscriptStatus.MINOR_REVISION.value,
            }:
                continue
            return {
                "target_stage": target_stage,
                "requested_outcome": payload.get("requested_outcome"),
                "recipient_emails": payload.get("recipient_emails")
                if isinstance(payload.get("recipient_emails"), list)
                else [],
                "note": str(row.get("comment") or ""),
                "changed_at": row.get("created_at"),
                "changed_by": row.get("changed_by"),
            }
        return None

    def _get_latest_decision_recommendation(self, manuscript_id: str) -> dict[str, Any] | None:
        """
        读取最近一次学术 recommendation 提交，供编辑部执行时参考。
        """
        try:
            rows = (
                self.client.table("status_transition_logs")
                .select("payload,comment,created_at,changed_by")
                .eq("manuscript_id", manuscript_id)
                .order("created_at", desc=True)
                .limit(20)
                .execute()
                .data
                or []
            )
        except Exception:
            return None

        for row in rows:
            payload = row.get("payload") if isinstance(row, dict) else None
            if not isinstance(payload, dict):
                continue
            if str(payload.get("action") or "").strip().lower() != "decision_recommendation_submitted":
                continue
            attachment_payload = payload.get("attachment_paths")
            raw_attachment_paths = attachment_payload if isinstance(attachment_payload, list) else []
            attachments: list[dict[str, Any]] = []
            for raw_ref in raw_attachment_paths:
                attachment_id, path = _decode_attachment_ref(str(raw_ref))
                attachments.append(
                    {
                        "id": attachment_id,
                        "path": path,
                        "name": path.split("/")[-1] if path else attachment_id,
                        "signed_url": self._signed_url("decision-attachments", path) if path else None,
                    }
                )
            return {
                "decision": payload.get("decision"),
                "workflow_decision": payload.get("workflow_decision"),
                "decision_stage": payload.get("decision_stage"),
                "content": str(payload.get("content") or row.get("comment") or ""),
                "attachments": attachments,
                "changed_at": row.get("created_at"),
                "changed_by": row.get("changed_by"),
            }
        return None

    def _signed_url(self, bucket: str, path: str, expires_in: int = 60 * 10) -> str | None:
        p = str(path or "").strip()
        if not p:
            return None
        try:
            # 中文注释:
            # - UAT/开发环境可能还没跑 storage bucket migration，导致 create_signed_url 直接失败。
            # - 这里做一次性兜底创建，避免“只因为缺桶就 500”。
            self._ensure_bucket(bucket, public=False)
            signed = self.client.storage.from_(bucket).create_signed_url(p, expires_in)
            return (signed or {}).get("signedUrl") or (signed or {}).get("signedURL")
        except Exception:
            return None

    def _ensure_bucket(self, bucket: str, *, public: bool = False) -> None:
        storage = getattr(self.client, "storage", None)
        if not storage or not hasattr(storage, "get_bucket") or not hasattr(storage, "create_bucket"):
            return
        try:
            storage.get_bucket(bucket)
        except Exception:
            try:
                storage.create_bucket(bucket, options={"public": bool(public)})
            except Exception:
                return

    def _resolve_review_stage_assignment_state(self, row: dict[str, Any]) -> str:
        status_raw = normalize_status(str(row.get("status") or "")) or ""
        if status_raw == "cancelled" or row.get("cancelled_at"):
            return "cancelled"
        if status_raw == "declined" or row.get("declined_at"):
            return "declined"
        if status_raw in {"completed", "submitted"} or row.get("submitted_at"):
            return "submitted"
        if status_raw in {"accepted", "agree", "agreed"} or row.get("accepted_at"):
            return "accepted"
        if status_raw == "opened" or row.get("opened_at"):
            return "opened"
        if status_raw == "invited" or row.get("invited_at"):
            return "invited"
        return "selected"

    def _build_review_stage_report_fallback(self, assignments: list[dict[str, Any]], reports: list[dict[str, Any]]) -> dict[str, str]:
        """
        中文注释:
        - 云端有些环境的 review_assignments 还没有 submitted_at，Exit Review Stage 会误把“已提交报告”的 reviewer
          当成 accepted pending。
        - review_reports 目前没有 assignment_id，无法做绝对精确映射。
        - 这里仅在“当前轮该 reviewer 只有一个 assignment”时做保守 fallback；多 assignment 场景不猜。
        """
        reviewer_assignment_counts: dict[str, int] = {}
        for row in assignments:
            reviewer_id = str(row.get("reviewer_id") or "").strip()
            if not reviewer_id:
                continue
            reviewer_assignment_counts[reviewer_id] = reviewer_assignment_counts.get(reviewer_id, 0) + 1

        submitted_report_at_by_reviewer: dict[str, str] = {}
        for row in reports:
            reviewer_id = str(row.get("reviewer_id") or "").strip()
            created_at = str(row.get("created_at") or "").strip()
            if reviewer_id and created_at and reviewer_id not in submitted_report_at_by_reviewer:
                submitted_report_at_by_reviewer[reviewer_id] = created_at

        fallback_by_assignment_id: dict[str, str] = {}
        for row in assignments:
            assignment_id = str(row.get("id") or "").strip()
            reviewer_id = str(row.get("reviewer_id") or "").strip()
            if not assignment_id or not reviewer_id:
                continue
            if row.get("submitted_at"):
                continue
            if reviewer_assignment_counts.get(reviewer_id, 0) != 1:
                continue
            submitted_at = submitted_report_at_by_reviewer.get(reviewer_id)
            if submitted_at:
                fallback_by_assignment_id[assignment_id] = submitted_at

        return fallback_by_assignment_id

    def _list_current_round_review_assignments(
        self,
        *,
        manuscript_id: str,
        manuscript_version: int | None,
    ) -> list[dict[str, Any]]:
        select_variants = [
            "id, reviewer_id, round_number, status, created_at, invited_at, opened_at, accepted_at, declined_at, submitted_at, cancelled_at",
            "id, reviewer_id, round_number, status, created_at, invited_at, opened_at, accepted_at, declined_at, cancelled_at",
            "id, reviewer_id, round_number, status, created_at, invited_at, opened_at, accepted_at, declined_at",
            "id, reviewer_id, round_number, status, created_at, invited_at, opened_at, accepted_at",
            "id, reviewer_id, round_number, status, created_at, invited_at, opened_at",
            "id, reviewer_id, round_number, status, created_at, invited_at",
            "id, reviewer_id, round_number, status, created_at",
        ]
        rows: list[dict[str, Any]] = []
        last_error: Exception | None = None
        for select_clause in select_variants:
            try:
                resp = (
                    self.client.table("review_assignments")
                    .select(select_clause)
                    .eq("manuscript_id", manuscript_id)
                    .order("created_at", desc=True)
                    .execute()
                )
                rows = getattr(resp, "data", None) or []
                last_error = None
                break
            except Exception as exc:
                last_error = exc
                if "column" not in str(exc).lower() and "does not exist" not in str(exc).lower():
                    raise
                continue
        if last_error is not None:
            raise last_error
        if not rows:
            return []

        target_round: int | None = None
        if manuscript_version is not None and any(
            int(item.get("round_number") or 1) == int(manuscript_version) for item in rows
        ):
            target_round = int(manuscript_version)
        else:
            try:
                target_round = max(int(item.get("round_number") or 1) for item in rows)
            except Exception:
                target_round = None

        if target_round is None:
            return rows
        return [
            item
            for item in rows
            if int(item.get("round_number") or 1) == target_round
        ]

    def _cancel_assignment_for_stage_exit(
        self,
        *,
        assignment_id: str,
        changed_by: str,
        reason: str,
        via: str,
    ) -> None:
        now_iso = _utc_now_iso()
        payload = {
            "status": "cancelled",
            "cancelled_at": now_iso,
            "cancelled_by": changed_by,
            "cancel_reason": reason,
            "cancel_via": via,
        }
        fallback_payload = {"status": "cancelled"}
        try:
            self.client.table("review_assignments").update(payload).eq("id", assignment_id).execute()
        except Exception as exc:
            lowered = str(exc).lower()
            if "cancelled_" not in lowered and "cancel_reason" not in lowered and "cancel_via" not in lowered:
                raise
            self.client.table("review_assignments").update(fallback_payload).eq("id", assignment_id).execute()

    def _send_cancellation_email_for_stage_exit(
        self,
        *,
        assignment: dict[str, Any],
        manuscript: dict[str, Any],
        cancel_reason: str,
        cancelled_by: str | None = None,
    ) -> dict[str, Any]:
        try:
            return send_reviewer_assignment_cancellation_email(
                assignment=assignment,
                manuscript=manuscript,
                cancel_reason=cancel_reason,
                cancelled_by=cancelled_by,
            )
        except Exception as exc:
            return {
                "status": "failed",
                "error_message": str(exc),
            }

    def _send_first_decision_request_emails(
        self,
        *,
        manuscript: dict[str, Any],
        recipient_emails: list[str],
        requested_outcome: str,
        requested_by: str,
        ae_note: str,
    ) -> tuple[list[str], list[str]]:
        sent_recipients: list[str] = []
        failed_recipients: list[str] = []
        for recipient_email in recipient_emails:
            try:
                result = send_first_decision_request_email(
                    manuscript=manuscript,
                    recipient_email=recipient_email,
                    requested_outcome=requested_outcome,
                    requested_by=requested_by,
                    ae_note=ae_note,
                )
            except Exception:
                result = {
                    "status": "failed",
                    "recipient": recipient_email,
                }
            status = str(result.get("status") or "").strip().lower()
            recipient = str(result.get("recipient") or recipient_email).strip().lower()
            if not recipient:
                continue
            if status == "sent":
                sent_recipients.append(recipient)
            else:
                failed_recipients.append(recipient)
        return sent_recipients, failed_recipients

    def _send_direct_revision_request_email(
        self,
        *,
        manuscript: dict[str, Any],
        decision_type: str,
        requested_by: str,
        editor_comment: str,
        revision_id: str | None,
        round_number: int | None,
    ) -> tuple[str | None, str | None]:
        target = resolve_author_notification_target(
            manuscript=manuscript,
            manuscript_id=str(manuscript.get("id") or ""),
            supabase_client=self.client,
        )
        recipient_email = str(target.get("recipient_email") or "").strip().lower()
        if not recipient_email:
            return None, None

        recipient_name = str(target.get("recipient_name") or "Author").strip() or "Author"
        manuscript_id = str(manuscript.get("id") or "").strip()
        manuscript_title = str(manuscript.get("title") or "").strip() or "Manuscript"
        decision_type_value = str(decision_type or "").strip().lower()
        decision_label = (
            "Major Revision Requested"
            if decision_type_value == "major"
            else "Minor Revision Requested"
        )
        requested_by_name = "Editorial Team"
        try:
            profile = (
                self.client.table("user_profiles")
                .select("full_name,email")
                .eq("id", str(requested_by or "").strip())
                .single()
                .execute()
            )
            profile_data = getattr(profile, "data", None) or {}
            requested_by_name = (
                str(profile_data.get("full_name") or "").strip()
                or str(profile_data.get("email") or "").strip()
                or "Editorial Team"
            )
        except Exception:
            requested_by_name = "Editorial Team"

        frontend_base_url = (
            os.environ.get("FRONTEND_BASE_URL")
            or os.environ.get("FRONTEND_ORIGIN")
            or "http://localhost:3000"
        )
        revision_url = f"{str(frontend_base_url).strip().rstrip('/')}/submit-revision/{manuscript_id}"
        revision_token = str(revision_id or f"round-{int(round_number or 0)}").strip() or "revision"
        idempotency_key = f"direct-revision-request/{revision_token}/{recipient_email}"
        delivery = email_service.send_inline_email(
            to_email=recipient_email,
            cc_emails=list(target.get("cc_recipients") or []),
            reply_to_emails=list(target.get("reply_to_recipients") or []),
            template_key="direct_revision_request",
            subject_template="[{{ manuscript_title }}] {{ decision_label }}",
            body_html_template=(
                "<p>Dear {{ recipient_name }},</p>"
                "<p>The manuscript <strong>{{ manuscript_title }}</strong> now requires "
                "<strong>{{ decision_label }}</strong>.</p>"
                "<p>Revision round: <strong>{{ round_number_label }}</strong><br/>"
                "Requested by: <strong>{{ requested_by_name }}</strong></p>"
                "<p>Editor note: {{ editor_comment or 'Please review the revision request in the portal.' }}</p>"
                "<p>Submit your revision here: <a href=\"{{ revision_url }}\">{{ revision_url }}</a></p>"
            ),
            body_text_template=(
                "Dear {{ recipient_name }}, the manuscript \"{{ manuscript_title }}\" now requires "
                "{{ decision_label }}. Revision round: {{ round_number_label }}. "
                "Requested by: {{ requested_by_name }}. "
                "Editor note: {{ editor_comment or 'Please review the revision request in the portal.' }}. "
                "Submit your revision here: {{ revision_url }}."
            ),
            context={
                "recipient_name": recipient_name,
                "manuscript_title": manuscript_title,
                "decision_label": decision_label,
                "round_number_label": str(round_number or 1),
                "requested_by_name": requested_by_name,
                "editor_comment": str(editor_comment or "").strip(),
                "revision_url": revision_url,
            },
            idempotency_key=idempotency_key,
            tags=[
                {"name": "scene", "value": "decision_workflow"},
                {"name": "event", "value": "direct_revision_request"},
                {"name": "manuscript_id", "value": manuscript_id},
                {"name": "decision_type", "value": decision_type_value or "minor"},
            ],
            headers={
                "X-SF-Manuscript-ID": manuscript_id,
                "X-SF-Event-Type": "direct_revision_request",
            },
            audit_context={
                "manuscript_id": manuscript_id or None,
                "actor_user_id": str(requested_by or "").strip() or None,
                "scene": "decision_workflow",
                "event_type": "direct_revision_request",
                "idempotency_key": idempotency_key,
            },
        )
        status = str(delivery.get("status") or "").strip().lower()
        if status == "sent":
            return recipient_email, None
        return None, recipient_email

    def exit_review_stage(
        self,
        *,
        manuscript_id: str,
        user_id: str,
        profile_roles: list[str] | None,
        request: ReviewStageExitRequest,
    ) -> dict[str, Any]:
        manuscript = self._get_manuscript(manuscript_id)
        roles = self._roles(profile_roles)
        self._ensure_internal_decision_access(
            manuscript=manuscript,
            manuscript_id=manuscript_id,
            user_id=user_id,
            roles=roles,
            action="decision:record_first",
        )

        current_status = normalize_status(str(manuscript.get("status") or "")) or ""
        if current_status not in {
            ManuscriptStatus.UNDER_REVIEW.value,
            ManuscriptStatus.RESUBMITTED.value,
        }:
            raise HTTPException(
                status_code=422,
                detail="Review-stage exit is only allowed in under_review/resubmitted stage",
            )

        assignments = self._list_current_round_review_assignments(
            manuscript_id=manuscript_id,
            manuscript_version=int(manuscript.get("version") or 1),
        )
        submitted_report_fallback: dict[str, str] = {}
        if assignments and any(not row.get("submitted_at") for row in assignments):
            submitted_report_fallback = self._build_review_stage_report_fallback(
                assignments,
                self._list_submitted_reports(manuscript_id),
            )

        def _state_for_exit(row: dict[str, Any]) -> str:
            assignment_id = str(row.get("id") or "").strip()
            submitted_at = submitted_report_fallback.get(assignment_id)
            if not submitted_at:
                return self._resolve_review_stage_assignment_state(row)
            augmented_row = dict(row)
            augmented_row["submitted_at"] = submitted_at
            return self._resolve_review_stage_assignment_state(augmented_row)

        accepted_pending = [
            row
            for row in assignments
            if _state_for_exit(row) == "accepted"
        ]
        auto_cancel_candidates = [
            row
            for row in assignments
            if _state_for_exit(row) in {"selected", "invited", "opened"}
        ]

        resolution_map: dict[str, dict[str, str]] = {}
        for item in list(request.accepted_pending_resolutions or []):
            assignment_id = str(item.assignment_id or "").strip()
            if assignment_id:
                resolution_map[assignment_id] = {
                    "action": str(item.action or "").strip().lower(),
                    "reason": str(item.reason or "").strip(),
                }

        accepted_pending_ids = {str(row.get("id") or "").strip() for row in accepted_pending if row.get("id")}
        unresolved_ids = sorted(
            assignment_id for assignment_id in accepted_pending_ids if assignment_id not in resolution_map
        )
        if unresolved_ids:
            raise HTTPException(
                status_code=422,
                detail="All accepted-but-not-submitted reviewers must be explicitly handled before leaving under_review",
            )

        waiting_ids = sorted(
            assignment_id
            for assignment_id, item in resolution_map.items()
            if assignment_id in accepted_pending_ids and item.get("action") == "wait"
        )
        if waiting_ids:
            raise HTTPException(
                status_code=409,
                detail="Review-stage exit is blocked because some accepted reviewers are marked to continue waiting",
            )

        auto_cancelled_ids: list[str] = []
        manually_cancelled_ids: list[str] = []
        cancellation_email_sent_assignment_ids: list[str] = []
        cancellation_email_failed_assignment_ids: list[str] = []
        stage_note = str(request.note or "").strip()
        target_label = str(request.target_stage or "").strip().lower().replace("_", " ")

        for row in auto_cancel_candidates:
            assignment_id = str(row.get("id") or "").strip()
            if not assignment_id:
                continue
            state = _state_for_exit(row)
            reason = (
                stage_note
                or f"Review stage exited to {target_label}; {state} reviewer assignment closed automatically"
            )
            self._cancel_assignment_for_stage_exit(
                assignment_id=assignment_id,
                changed_by=user_id,
                reason=reason,
                via="auto_stage_exit",
            )
            auto_cancelled_ids.append(assignment_id)
            if should_send_reviewer_assignment_cancellation_email(row):
                email_result = self._send_cancellation_email_for_stage_exit(
                    assignment=row,
                    manuscript=manuscript,
                    cancel_reason=reason,
                    cancelled_by=user_id,
                )
                if str(email_result.get("status") or "").strip().lower() == "sent":
                    cancellation_email_sent_assignment_ids.append(assignment_id)
                else:
                    cancellation_email_failed_assignment_ids.append(assignment_id)

        for row in accepted_pending:
            assignment_id = str(row.get("id") or "").strip()
            if not assignment_id:
                continue
            resolution = resolution_map.get(assignment_id) or {}
            action = str(resolution.get("action") or "").strip().lower()
            if action != "cancel":
                continue
            reason = resolution.get("reason") or stage_note or (
                f"Review stage exited to {target_label} by editor decision"
            )
            self._cancel_assignment_for_stage_exit(
                assignment_id=assignment_id,
                changed_by=user_id,
                reason=str(reason).strip(),
                via="post_acceptance_cleanup",
            )
            manually_cancelled_ids.append(assignment_id)
            email_result = self._send_cancellation_email_for_stage_exit(
                assignment=row,
                manuscript=manuscript,
                cancel_reason=str(reason).strip(),
                cancelled_by=user_id,
            )
            if str(email_result.get("status") or "").strip().lower() == "sent":
                cancellation_email_sent_assignment_ids.append(assignment_id)
            else:
                cancellation_email_failed_assignment_ids.append(assignment_id)

        remaining_pending_ids = sorted(
            assignment_id
            for assignment_id in accepted_pending_ids
            if assignment_id not in set(manually_cancelled_ids)
        )
        if remaining_pending_ids:
            raise HTTPException(
                status_code=409,
                detail="Accepted reviewers remain active; stay in under_review or cancel them before proceeding",
            )

        target_stage = str(request.target_stage or "").strip().lower()
        exit_note = stage_note or (
            "review stage exited by editor decision"
        )
        transition_payload = {
            "action": "review_stage_exit",
            "source": "editor_detail",
            "reason": "editor_exit_review_stage",
            "target_stage": target_stage,
            "requested_outcome": request.requested_outcome,
            "recipient_emails": request.recipient_emails,
            "auto_cancelled_assignment_ids": auto_cancelled_ids,
            "manually_cancelled_assignment_ids": manually_cancelled_ids,
            "before": {"status": current_status},
        }
        first_decision_email_sent_recipients: list[str] = []
        first_decision_email_failed_recipients: list[str] = []
        author_revision_email_sent_recipient: str | None = None
        author_revision_email_failed_recipient: str | None = None

        if target_stage == "first":
            updated = self.editorial.update_status(
                manuscript_id=manuscript_id,
                to_status=ManuscriptStatus.DECISION.value,
                changed_by=user_id,
                comment=exit_note,
                allow_skip=False,
                payload={**transition_payload, "after": {"status": ManuscriptStatus.DECISION.value}},
            )
            new_status = str(updated.get("status") or ManuscriptStatus.DECISION.value)
            first_decision_email_sent_recipients, first_decision_email_failed_recipients = (
                self._send_first_decision_request_emails(
                    manuscript=manuscript,
                    recipient_emails=request.recipient_emails,
                    requested_outcome=str(request.requested_outcome or ""),
                    requested_by=user_id,
                    ae_note=exit_note,
                )
            )
        elif target_stage == "final":
            if current_status != ManuscriptStatus.DECISION.value:
                self.editorial.update_status(
                    manuscript_id=manuscript_id,
                    to_status=ManuscriptStatus.DECISION.value,
                    changed_by=user_id,
                    comment="review stage exit auto step",
                    allow_skip=False,
                )
            updated = self.editorial.update_status(
                manuscript_id=manuscript_id,
                to_status=ManuscriptStatus.DECISION_DONE.value,
                changed_by=user_id,
                comment=exit_note,
                allow_skip=False,
                payload={**transition_payload, "after": {"status": ManuscriptStatus.DECISION_DONE.value}},
            )
            new_status = str(updated.get("status") or ManuscriptStatus.DECISION_DONE.value)
        elif target_stage in {
            ManuscriptStatus.MAJOR_REVISION.value,
            ManuscriptStatus.MINOR_REVISION.value,
        }:
            decision_type = (
                "major"
                if target_stage == ManuscriptStatus.MAJOR_REVISION.value
                else "minor"
            )
            revision_result = RevisionService().create_revision_request(
                manuscript_id=manuscript_id,
                decision_type=decision_type,
                editor_comment=exit_note,
            )
            if not revision_result.get("success"):
                raise HTTPException(
                    status_code=400,
                    detail=str(revision_result.get("error") or "Failed to create revision request"),
                )
            revision_data = revision_result.get("data") if isinstance(revision_result.get("data"), dict) else {}
            new_status = str(revision_data.get("manuscript_status") or target_stage)
            self._safe_insert_audit_log(
                manuscript_id=manuscript_id,
                from_status=current_status,
                to_status=new_status,
                changed_by=user_id,
                comment=exit_note,
                payload={**transition_payload, "after": {"status": new_status}},
            )
            try:
                self.notification.create_notification(
                    user_id=str(manuscript.get("author_id") or ""),
                    manuscript_id=manuscript_id,
                    type="decision",
                    title="Revision Requested",
                    content=f"Editor has requested a {decision_type} revision for '{str(manuscript.get('title') or 'Manuscript')}'.",
                )
            except Exception:
                pass
            author_revision_email_sent_recipient, author_revision_email_failed_recipient = (
                self._send_direct_revision_request_email(
                    manuscript=manuscript,
                    decision_type=decision_type,
                    requested_by=user_id,
                    editor_comment=exit_note,
                    revision_id=str(revision_data.get("revision", {}).get("id") or "").strip() or None,
                    round_number=int(revision_data.get("round_number") or 0) or None,
                )
            )
        else:
            raise HTTPException(status_code=422, detail="Invalid review-stage exit target")

        return {
            "manuscript_status": new_status,
            "target_stage": target_stage,
            "auto_cancelled_assignment_ids": auto_cancelled_ids,
            "manually_cancelled_assignment_ids": manually_cancelled_ids,
            "remaining_pending_assignment_ids": remaining_pending_ids,
            "cancellation_email_sent_assignment_ids": cancellation_email_sent_assignment_ids,
            "cancellation_email_failed_assignment_ids": cancellation_email_failed_assignment_ids,
            "first_decision_email_sent_recipients": first_decision_email_sent_recipients,
            "first_decision_email_failed_recipients": first_decision_email_failed_recipients,
            "author_revision_email_sent_recipient": author_revision_email_sent_recipient,
            "author_revision_email_failed_recipient": author_revision_email_failed_recipient,
        }

    def get_decision_context(
        self, *, manuscript_id: str, user_id: str, profile_roles: list[str] | None
    ) -> dict[str, Any]:
        manuscript = self._get_manuscript(manuscript_id)
        roles = self._roles(profile_roles)
        submission_mode = self._get_submission_mode(roles)
        self._ensure_internal_decision_access(
            manuscript=manuscript,
            manuscript_id=manuscript_id,
            user_id=user_id,
            roles=roles,
            action="decision:record_first",
        )

        status = normalize_status(str(manuscript.get("status") or "")) or ""
        if status not in {
            ManuscriptStatus.DECISION.value,
            ManuscriptStatus.DECISION_DONE.value,
        }:
            raise HTTPException(status_code=400, detail=f"Decision workspace unavailable in status: {status}")

        reports = self._list_submitted_reports(manuscript_id)
        can_record_first = self._can_decision_action(action="decision:record_first", roles=roles)
        can_submit_final = can_perform_action(action="decision:submit_final", roles=roles)
        has_submitted_author_revision = self._has_submitted_author_revision(manuscript_id)
        is_final_status_allowed = status in {
            ManuscriptStatus.DECISION.value,
            ManuscriptStatus.DECISION_DONE.value,
        }

        final_blocking_reasons: list[str] = []
        if not is_final_status_allowed:
            final_blocking_reasons.append(
                "Decision submission is only allowed in decision/decision_done stage"
            )

        draft = None
        if submission_mode == "execute":
            draft = self._get_latest_letter(
                manuscript_id=manuscript_id,
                editor_id=user_id,
                status="draft",
                manuscript_version=int(manuscript.get("version") or 1),
            )
        review_stage_exit_request = self._get_latest_review_stage_exit_request(manuscript_id)
        latest_decision_recommendation = self._get_latest_decision_recommendation(manuscript_id)
        template_content = self._build_template(reports)

        draft_payload: dict[str, Any] | None = None
        if draft:
            draft_attachments: list[dict[str, str]] = []
            for raw_ref in list(draft.get("attachment_paths") or []):
                attachment_id, path = _decode_attachment_ref(str(raw_ref))
                draft_attachments.append(
                    {
                        "id": attachment_id,
                        "path": path,
                        "name": path.split("/")[-1] if path else attachment_id,
                        "signed_url": self._signed_url("decision-attachments", path) if path else None,
                    }
                )
            draft_payload = {
                "id": draft.get("id"),
                "content": draft.get("content") or "",
                "decision": draft.get("decision"),
                "status": draft.get("status"),
                "last_updated_at": draft.get("updated_at"),
                "attachments": draft_attachments,
            }

        return {
            "manuscript": {
                "id": manuscript.get("id"),
                "title": manuscript.get("title"),
                "abstract": manuscript.get("abstract"),
                # 兼容：隐藏 legacy pending_decision 等历史状态，统一返回归一化后的 status。
                "status": status or manuscript.get("status"),
                "version": manuscript.get("version") or 1,
                "pdf_url": self._signed_url("manuscripts", str(manuscript.get("file_path") or "")),
            },
            "reports": reports,
            "draft": draft_payload,
            "review_stage_exit_request": review_stage_exit_request,
            "latest_decision_recommendation": latest_decision_recommendation,
            "templates": [
                {"id": "default", "name": "Default Decision Template", "content": template_content}
            ],
            "permissions": {
                "can_record_first": can_record_first,
                "can_submit_final": can_submit_final,
                "can_submit": len(reports) > 0 or submission_mode == "recommendation",
                "can_submit_final_now": can_submit_final and len(final_blocking_reasons) == 0,
                "final_blocking_reasons": final_blocking_reasons,
                "has_submitted_author_revision": has_submitted_author_revision,
                "is_read_only": False,
                "submission_mode": submission_mode,
            },
        }

    def submit_decision(
        self,
        *,
        manuscript_id: str,
        user_id: str,
        profile_roles: list[str] | None,
        request: DecisionSubmitRequest,
    ) -> dict[str, Any]:
        manuscript = self._get_manuscript(manuscript_id)
        roles = self._roles(profile_roles)
        submission_mode = self._get_submission_mode(roles)
        action = "decision:submit_final" if request.is_final else "decision:record_first"
        self._ensure_internal_decision_access(
            manuscript=manuscript,
            manuscript_id=manuscript_id,
            user_id=user_id,
            roles=roles,
            action=action,
        )

        requested_decision = str(request.decision).strip().lower()
        try:
            workflow_decision = get_workflow_decision_bucket(requested_decision)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail="Invalid decision") from exc

        if request.decision_stage == "final" and workflow_decision == "add_reviewer":
            raise HTTPException(
                status_code=422,
                detail="Add reviewer is only allowed in first decision stage",
            )
        if (
            submission_mode != "recommendation"
            and request.decision_stage == "first"
            and workflow_decision == "accept"
        ):
            raise HTTPException(
                status_code=422,
                detail="First decision does not allow accept; route manuscript to final decision instead",
            )

        content = str(request.content or "").strip()
        if submission_mode == "recommendation":
            if not request.is_final:
                raise HTTPException(
                    status_code=422,
                    detail="Recommendation submission does not support draft save",
                )
            if not is_academic_recommendation_value(requested_decision):
                raise HTTPException(
                    status_code=422,
                    detail="Recommendation submission requires one of the five academic recommendation values",
                )

        if submission_mode != "recommendation" and request.is_final and workflow_decision != "add_reviewer" and not content:
            raise HTTPException(status_code=422, detail="Decision letter content is required")

        current_status = normalize_status(str(manuscript.get("status") or "")) or ManuscriptStatus.PRE_CHECK.value
        if request.decision_stage == "first":
            if current_status != ManuscriptStatus.DECISION.value:
                raise HTTPException(
                    status_code=422,
                    detail="Exit review stage first; first decision is only available in decision stage",
                )
            if not request.is_final and workflow_decision == "add_reviewer":
                raise HTTPException(
                    status_code=422,
                    detail="Add reviewer is a workflow action and cannot be saved as a draft",
                )
        elif request.decision_stage == "final":
            if not request.is_final:
                raise HTTPException(
                    status_code=422,
                    detail="Final decision stage does not support draft save; submit the decision instead",
                )
            if current_status not in {
                ManuscriptStatus.DECISION.value,
                ManuscriptStatus.DECISION_DONE.value,
            }:
                raise HTTPException(
                    status_code=422,
                    detail="Exit review stage first; final decision submission is only available in decision/decision_done stage",
                )
            if workflow_decision == "accept" and current_status != ManuscriptStatus.DECISION_DONE.value:
                raise HTTPException(
                    status_code=422,
                    detail="Accept is only allowed in final decision queue (decision_done)",
                )
        else:
            raise HTTPException(status_code=422, detail="Invalid decision stage")

        if submission_mode == "recommendation":
            now_iso = _utc_now_iso()
            self._safe_insert_audit_log(
                manuscript_id=manuscript_id,
                from_status=current_status,
                to_status=current_status,
                changed_by=user_id,
                comment=content or f"{request.decision_stage or 'decision'} recommendation submitted",
                payload={
                    "action": "decision_recommendation_submitted",
                    "decision": requested_decision,
                    "workflow_decision": workflow_decision,
                    "decision_stage": request.decision_stage,
                    "source": "decision_workspace",
                    "reason": "editor_submit_decision_recommendation",
                    "execution_required": True,
                    "content": content,
                    "attachment_paths": list(request.attachment_paths or []),
                },
            )
            return {
                "decision_letter_id": None,
                "status": None,
                "manuscript_status": current_status,
                "updated_at": now_iso,
            }

        draft = self._get_latest_letter(
            manuscript_id=manuscript_id,
            editor_id=user_id,
            status="draft",
            manuscript_version=int(manuscript.get("version") or 1),
        )
        row: dict[str, Any] | None = None
        if not request.is_final:
            row = self._save_letter(
                existing=draft,
                manuscript_id=manuscript_id,
                manuscript_version=int(manuscript.get("version") or 1),
                editor_id=user_id,
                content=content,
                decision=workflow_decision,
                status="draft",
                attachment_paths=list(request.attachment_paths or []),
                last_updated_at=request.last_updated_at,
            )
        elif request.decision_stage == "first" and workflow_decision != "add_reviewer":
            # 中文注释:
            # - first decision 提交时只允许复用当前 draft；不再“更新最近任意 letter”，
            #   避免覆盖后续 final decision 或历史 committed letter。
            row = self._save_letter(
                existing=draft,
                manuscript_id=manuscript_id,
                manuscript_version=int(manuscript.get("version") or 1),
                editor_id=user_id,
                content=content,
                decision=workflow_decision,
                status="final",
                attachment_paths=list(request.attachment_paths or []),
                last_updated_at=request.last_updated_at,
            )
        elif request.decision_stage == "final":
            # 中文注释:
            # - final decision 始终新建一条 committed letter，保留 first decision 历史。
            row = self._save_letter(
                existing=None,
                manuscript_id=manuscript_id,
                manuscript_version=int(manuscript.get("version") or 1),
                editor_id=user_id,
                content=content,
                decision=workflow_decision,
                status="final",
                attachment_paths=list(request.attachment_paths or []),
                last_updated_at=request.last_updated_at,
            )
        new_status = current_status

        if request.is_final and request.decision_stage == "final":
            transition_payload = {
                "action": "final_decision_workspace",
                "decision": requested_decision,
                "workflow_decision": workflow_decision,
                "decision_stage": "final",
                "source": "decision_workspace",
                "reason": "editor_submit_final_decision",
                "decision_letter": {
                    "id": row.get("id") if row else None,
                    "status": row.get("status") if row else None,
                    "content": row.get("content") if row else content,
                    "attachment_paths": row.get("attachment_paths") if row else list(request.attachment_paths or []),
                },
            }
            new_status = self._transition_for_final_decision(
                manuscript_id=manuscript_id,
                current_status=current_status,
                decision=workflow_decision,
                changed_by=user_id,
                transition_payload=transition_payload,
            )
            if draft and str(draft.get("id") or "").strip():
                self._delete_letter_by_id(letter_id=str(draft.get("id") or ""))
            self._notify_author(
                manuscript=manuscript, manuscript_id=manuscript_id, decision=requested_decision
            )
        elif request.is_final and request.decision_stage == "first":
            transition_payload = {
                "action": "first_decision_workspace",
                "decision": requested_decision,
                "workflow_decision": workflow_decision,
                "decision_stage": "first",
                "source": "decision_workspace",
                "reason": "editor_submit_first_decision",
            }
            if row is not None:
                transition_payload["decision_letter"] = {
                    "id": row.get("id"),
                    "status": row.get("status"),
                    "content": row.get("content"),
                    "attachment_paths": row.get("attachment_paths") or [],
                }
            new_status = self._transition_for_first_decision(
                manuscript_id=manuscript_id,
                current_status=current_status,
                decision=workflow_decision,
                changed_by=user_id,
                transition_payload=transition_payload,
            )
            if workflow_decision == "add_reviewer" and draft and str(draft.get("id") or "").strip():
                self._delete_letter_by_id(letter_id=str(draft.get("id") or ""))
            if workflow_decision != "add_reviewer":
                self._notify_author(
                    manuscript=manuscript,
                    manuscript_id=manuscript_id,
                    decision=requested_decision,
                )
        else:
            self._safe_insert_audit_log(
                manuscript_id=manuscript_id,
                from_status=current_status,
                to_status=new_status,
                changed_by=user_id,
                comment="first decision saved",
                payload={
                    "action": "first_decision_workspace",
                    "decision_stage": "first",
                    "source": "decision_workspace",
                    "reason": "editor_save_first_decision",
                    "decision": requested_decision,
                    "workflow_decision": workflow_decision,
                    "before": {"status": current_status},
                    "after": {"status": current_status},
                    "decision_letter": {
                        "id": row.get("id") if row else None,
                        "status": row.get("status") if row else None,
                        "attachment_paths": row.get("attachment_paths") if row else [],
                    },
                },
            )

        return {
            "decision_letter_id": row.get("id") if row else None,
            "status": row.get("status") if row else None,
            "manuscript_status": new_status,
            "updated_at": row.get("updated_at") if row else None,
        }
