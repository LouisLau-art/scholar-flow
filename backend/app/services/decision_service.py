from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from fastapi import HTTPException

from app.core.journal_scope import ensure_manuscript_scope_access
from app.core.role_matrix import can_perform_action
from app.lib.api_client import supabase_admin
from app.models.decision import DecisionSubmitRequest
from app.models.manuscript import ManuscriptStatus, normalize_status
from app.services.editorial_service import EditorialService
from app.services.notification_service import NotificationService


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_iso(value: object) -> datetime | None:
    if isinstance(value, datetime):
        return value
    if not isinstance(value, str):
        return None
    raw = value.strip()
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except Exception:
        return None


def _safe_file_name(filename: str) -> str:
    return filename.replace("/", "_").replace("\\", "_")


def _encode_attachment_ref(attachment_id: str, object_path: str) -> str:
    return f"{attachment_id}|{object_path}"


def _decode_attachment_ref(raw: str) -> tuple[str, str]:
    text = str(raw or "").strip()
    if "|" in text:
        attachment_id, path = text.split("|", 1)
        return attachment_id.strip(), path.strip()
    # 兼容旧数据：若只存了 path，则用 path 作为 id 占位
    return text, text


class DecisionService:
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

    def _get_manuscript(self, manuscript_id: str) -> dict[str, Any]:
        select_candidates = [
            # 首选：完整字段（含 version + assistant_editor_id）
            "id,title,abstract,status,file_path,version,author_id,editor_id,assistant_editor_id,updated_at",
            # 兼容：旧 schema 缺少 version
            "id,title,abstract,status,file_path,author_id,editor_id,assistant_editor_id,updated_at",
            # 兼容：更旧 schema 缺少 version + assistant_editor_id
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
        return row

    def _ensure_editor_access(
        self, *, manuscript: dict[str, Any], user_id: str, roles: set[str]
    ) -> None:
        # admin / editor_in_chief 可跨稿件访问；
        # managing_editor 按 editor_id 绑定访问，assistant_editor 按 assistant_editor_id 绑定访问。
        if roles.intersection({"admin", "editor_in_chief"}):
            return
        assigned_editor_id = str(manuscript.get("editor_id") or "")
        if assigned_editor_id and assigned_editor_id == str(user_id):
            return
        assigned_ae_id = str(manuscript.get("assistant_editor_id") or "")
        if assigned_ae_id and assigned_ae_id == str(user_id):
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
        if not can_perform_action(action=action, roles=roles):
            raise HTTPException(status_code=403, detail=f"Insufficient permission for action: {action}")
        ensure_manuscript_scope_access(
            manuscript_id=manuscript_id,
            user_id=str(user_id),
            roles=list(roles),
            allow_admin_bypass=True,
        )
        self._ensure_editor_access(manuscript=manuscript, user_id=user_id, roles=roles)

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

    def _signed_url(self, bucket: str, path: str, expires_in: int = 60 * 10) -> str | None:
        p = str(path or "").strip()
        if not p:
            return None
        try:
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

    def _list_submitted_reports(self, manuscript_id: str) -> list[dict[str, Any]]:
        resp = (
            self.client.table("review_reports")
            .select(
                "id,reviewer_id,status,score,comments_for_author,content,confidential_comments_to_editor,attachment_path,created_at"
            )
            .eq("manuscript_id", manuscript_id)
            .order("created_at", desc=True)
            .execute()
        )
        rows = getattr(resp, "data", None) or []
        submitted = [
            row
            for row in rows
            if str(row.get("status") or "").strip().lower()
            in {"submitted", "completed", "done"}
        ]

        reviewer_ids = sorted(
            {str(r.get("reviewer_id") or "") for r in submitted if r.get("reviewer_id")}
        )
        reviewer_map: dict[str, dict[str, Any]] = {}
        if reviewer_ids:
            try:
                p = (
                    self.client.table("user_profiles")
                    .select("id,full_name,email")
                    .in_("id", reviewer_ids)
                    .execute()
                )
                for item in (getattr(p, "data", None) or []):
                    rid = str(item.get("id") or "")
                    if rid:
                        reviewer_map[rid] = item
            except Exception:
                reviewer_map = {}

        normalized: list[dict[str, Any]] = []
        for idx, row in enumerate(submitted, start=1):
            rid = str(row.get("reviewer_id") or "")
            prof = reviewer_map.get(rid) or {}
            comments_for_author = str(
                row.get("comments_for_author") or row.get("content") or ""
            ).strip()
            attachment_path = str(row.get("attachment_path") or "").strip()
            attachment_id, _ = _decode_attachment_ref(attachment_path)
            normalized.append(
                {
                    "id": row.get("id"),
                    "reviewer_id": row.get("reviewer_id"),
                    "reviewer_name": prof.get("full_name") or f"Reviewer {idx}",
                    "reviewer_email": prof.get("email"),
                    "status": row.get("status"),
                    "score": row.get("score"),
                    "comments_for_author": comments_for_author,
                    "confidential_comments_to_editor": row.get(
                        "confidential_comments_to_editor"
                    ),
                    "attachment": (
                        {
                            "id": attachment_id,
                            "path": attachment_path,
                            "signed_url": self._signed_url("review-attachments", attachment_path),
                        }
                        if attachment_path
                        else None
                    ),
                    "created_at": row.get("created_at"),
                }
            )
        return normalized

    def _build_template(self, reports: list[dict[str, Any]]) -> str:
        parts: list[str] = [
            "Dear Author,",
            "",
            "Thank you for submitting your manuscript. Please find the editorial decision below.",
            "",
        ]
        for idx, report in enumerate(reports, start=1):
            comments = str(report.get("comments_for_author") or "").strip()
            parts.append(f"Reviewer {idx}:")
            parts.append(comments or "(No public comment provided)")
            parts.append("")
        parts.extend(
            [
                "Best regards,",
                "Editorial Office",
            ]
        )
        return "\n".join(parts)

    def _get_latest_letter(
        self, *, manuscript_id: str, editor_id: str, status: str | None = None
    ) -> dict[str, Any] | None:
        try:
            query = (
                self.client.table("decision_letters")
                .select(
                    "id,manuscript_id,manuscript_version,editor_id,content,decision,status,attachment_paths,created_at,updated_at"
                )
                .eq("manuscript_id", manuscript_id)
                .eq("editor_id", editor_id)
            )
            if status:
                query = query.eq("status", status)
            resp = query.order("updated_at", desc=True).limit(1).execute()
            rows = getattr(resp, "data", None) or []
            return rows[0] if rows else None
        except Exception as e:
            if "decision_letters" in str(e).lower() and "does not exist" in str(e).lower():
                raise HTTPException(
                    status_code=500, detail="DB not migrated: decision_letters table missing"
                ) from e
            raise

    def _save_letter(
        self,
        *,
        existing: dict[str, Any] | None,
        manuscript_id: str,
        manuscript_version: int,
        editor_id: str,
        content: str,
        decision: str,
        status: str,
        attachment_paths: list[str],
        last_updated_at: datetime | None,
    ) -> dict[str, Any]:
        now = _utc_now_iso()

        def _is_conflict(existing_row: dict[str, Any]) -> bool:
            if last_updated_at is None:
                return False
            db_updated = _parse_iso(existing_row.get("updated_at"))
            if db_updated is None:
                return False
            # 中文注释: 使用毫秒级比较，避免数据库微秒截断导致误判
            return int(db_updated.timestamp() * 1000) != int(last_updated_at.timestamp() * 1000)

        if existing:
            if _is_conflict(existing):
                raise HTTPException(
                    status_code=409,
                    detail="Draft conflict: letter has been modified by another session",
                )
            payload = {
                "content": content,
                "decision": decision,
                "status": status,
                "manuscript_version": manuscript_version,
                "attachment_paths": attachment_paths,
                "updated_at": now,
            }
            resp = (
                self.client.table("decision_letters")
                .update(payload)
                .eq("id", existing["id"])
                .execute()
            )
            rows = getattr(resp, "data", None) or []
            if not rows:
                raise HTTPException(status_code=500, detail="Failed to update decision letter")
            return rows[0]

        payload = {
            "manuscript_id": manuscript_id,
            "manuscript_version": manuscript_version,
            "editor_id": editor_id,
            "content": content,
            "decision": decision,
            "status": status,
            "attachment_paths": attachment_paths,
            "created_at": now,
            "updated_at": now,
        }
        resp = self.client.table("decision_letters").insert(payload).execute()
        rows = getattr(resp, "data", None) or []
        if not rows:
            raise HTTPException(status_code=500, detail="Failed to create decision letter")
        return rows[0]

    def _transition_for_final_decision(
        self,
        *,
        manuscript_id: str,
        current_status: str,
        decision: str,
        changed_by: str,
        transition_payload: dict[str, Any],
    ) -> str:
        norm = normalize_status(current_status) or ManuscriptStatus.PRE_CHECK.value
        comment = f"final_decision:{decision}"
        target_status = (
            ManuscriptStatus.REJECTED.value
            if decision == "reject"
            else ManuscriptStatus.APPROVED.value
            if decision == "accept"
            else ManuscriptStatus.MAJOR_REVISION.value
            if decision == "major_revision"
            else ManuscriptStatus.MINOR_REVISION.value
        )
        audit_payload = dict(transition_payload or {})
        audit_payload.setdefault("source", "decision_workspace")
        audit_payload.setdefault("reason", "editor_submit_final_decision")
        audit_payload["decision_stage"] = "final"
        audit_payload["before"] = {"status": norm}
        audit_payload["after"] = {"status": target_status}

        if decision == "reject":
            if norm == ManuscriptStatus.RESUBMITTED.value:
                self.editorial.update_status(
                    manuscript_id=manuscript_id,
                    to_status=ManuscriptStatus.DECISION.value,
                    changed_by=changed_by,
                    comment="decision workspace auto step",
                    allow_skip=False,
                )
                self.editorial.update_status(
                    manuscript_id=manuscript_id,
                    to_status=ManuscriptStatus.DECISION_DONE.value,
                    changed_by=changed_by,
                    comment="decision workspace auto step",
                    allow_skip=False,
                )
            elif norm == ManuscriptStatus.DECISION.value:
                self.editorial.update_status(
                    manuscript_id=manuscript_id,
                    to_status=ManuscriptStatus.DECISION_DONE.value,
                    changed_by=changed_by,
                    comment="decision workspace auto step",
                    allow_skip=False,
                )
            elif norm != ManuscriptStatus.DECISION_DONE.value:
                raise HTTPException(
                    status_code=422,
                    detail="Final reject only allowed in resubmitted/decision/decision_done stage",
                )
            updated = self.editorial.update_status(
                manuscript_id=manuscript_id,
                to_status=ManuscriptStatus.REJECTED.value,
                changed_by=changed_by,
                comment=comment,
                allow_skip=False,
                payload=audit_payload,
            )
            return str(updated.get("status") or ManuscriptStatus.REJECTED.value)

        if decision == "accept":
            if norm == ManuscriptStatus.RESUBMITTED.value:
                self.editorial.update_status(
                    manuscript_id=manuscript_id,
                    to_status=ManuscriptStatus.DECISION.value,
                    changed_by=changed_by,
                    comment="decision workspace auto step",
                    allow_skip=False,
                )
                self.editorial.update_status(
                    manuscript_id=manuscript_id,
                    to_status=ManuscriptStatus.DECISION_DONE.value,
                    changed_by=changed_by,
                    comment="decision workspace auto step",
                    allow_skip=False,
                )
            elif norm == ManuscriptStatus.DECISION.value:
                self.editorial.update_status(
                    manuscript_id=manuscript_id,
                    to_status=ManuscriptStatus.DECISION_DONE.value,
                    changed_by=changed_by,
                    comment="decision workspace auto step",
                    allow_skip=False,
                )
            elif norm != ManuscriptStatus.DECISION_DONE.value:
                raise HTTPException(
                    status_code=422,
                    detail="Final accept only allowed in resubmitted/decision/decision_done stage",
                )
            updated = self.editorial.update_status(
                manuscript_id=manuscript_id,
                to_status=ManuscriptStatus.APPROVED.value,
                changed_by=changed_by,
                comment=comment,
                allow_skip=False,
                payload=audit_payload,
            )
            return str(updated.get("status") or ManuscriptStatus.APPROVED.value)

        # major/minor revision
        to_status = (
            ManuscriptStatus.MAJOR_REVISION.value
            if decision == "major_revision"
            else ManuscriptStatus.MINOR_REVISION.value
        )
        try:
            updated = self.editorial.update_status(
                manuscript_id=manuscript_id,
                to_status=to_status,
                changed_by=changed_by,
                comment=comment,
                allow_skip=False,
                payload=audit_payload,
            )
        except HTTPException:
            updated = self.editorial.update_status(
                manuscript_id=manuscript_id,
                to_status=to_status,
                changed_by=changed_by,
                comment=comment,
                allow_skip=True,
                payload=audit_payload,
            )
        return str(updated.get("status") or to_status)

    def _notify_author(self, *, manuscript: dict[str, Any], manuscript_id: str, decision: str) -> None:
        author_id = str(manuscript.get("author_id") or "").strip()
        if not author_id:
            return
        title = str(manuscript.get("title") or "Manuscript")
        decision_label = {
            "accept": "Accepted",
            "reject": "Rejected",
            "major_revision": "Major Revision Requested",
            "minor_revision": "Minor Revision Requested",
        }.get(decision, "Updated")
        self.notification.create_notification(
            user_id=author_id,
            manuscript_id=manuscript_id,
            type="decision",
            title="Final Decision Updated",
            content=f"Decision for '{title}': {decision_label}.",
        )

    def get_decision_context(
        self, *, manuscript_id: str, user_id: str, profile_roles: list[str] | None
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

        status = normalize_status(str(manuscript.get("status") or "")) or ""
        if status not in {
            ManuscriptStatus.UNDER_REVIEW.value,
            ManuscriptStatus.RESUBMITTED.value,
            ManuscriptStatus.DECISION.value,
            ManuscriptStatus.DECISION_DONE.value,
            ManuscriptStatus.MAJOR_REVISION.value,
            ManuscriptStatus.MINOR_REVISION.value,
        }:
            raise HTTPException(status_code=400, detail=f"Decision workspace unavailable in status: {status}")

        reports = self._list_submitted_reports(manuscript_id)
        draft = self._get_latest_letter(
            manuscript_id=manuscript_id,
            editor_id=user_id,
            status="draft",
        )
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
                "status": manuscript.get("status"),
                "version": manuscript.get("version") or 1,
                "pdf_url": self._signed_url("manuscripts", str(manuscript.get("file_path") or "")),
            },
            "reports": reports,
            "draft": draft_payload,
            "templates": [
                {"id": "default", "name": "Default Decision Template", "content": template_content}
            ],
            "permissions": {
                "can_submit": len(reports) > 0,
                "is_read_only": False,
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
        action = "decision:submit_final" if request.is_final else "decision:record_first"
        self._ensure_internal_decision_access(
            manuscript=manuscript,
            manuscript_id=manuscript_id,
            user_id=user_id,
            roles=roles,
            action=action,
        )

        decision = str(request.decision).strip().lower()
        if decision not in {"accept", "reject", "major_revision", "minor_revision"}:
            raise HTTPException(status_code=422, detail="Invalid decision")

        content = str(request.content or "").strip()
        if request.is_final and not content:
            raise HTTPException(status_code=422, detail="Final decision letter content is required")

        reports = self._list_submitted_reports(manuscript_id)
        if request.is_final and len(reports) == 0:
            raise HTTPException(
                status_code=422, detail="At least one submitted review report is required"
            )

        existing = self._get_latest_letter(manuscript_id=manuscript_id, editor_id=user_id, status=None)
        row = self._save_letter(
            existing=existing,
            manuscript_id=manuscript_id,
            manuscript_version=int(manuscript.get("version") or 1),
            editor_id=user_id,
            content=content,
            decision=decision,
            status="final" if request.is_final else "draft",
            attachment_paths=list(request.attachment_paths or []),
            last_updated_at=request.last_updated_at,
        )

        current_status = normalize_status(str(manuscript.get("status") or "")) or ManuscriptStatus.PRE_CHECK.value
        if request.is_final:
            if current_status not in {
                ManuscriptStatus.RESUBMITTED.value,
                ManuscriptStatus.DECISION.value,
                ManuscriptStatus.DECISION_DONE.value,
            }:
                raise HTTPException(
                    status_code=422,
                    detail=(
                        "Final decision is only allowed after author resubmission "
                        "(status must be resubmitted/decision/decision_done)"
                    ),
                )
            try:
                rev = (
                    self.client.table("revisions")
                    .select("id,status,submitted_at")
                    .eq("manuscript_id", manuscript_id)
                    .order("submitted_at", desc=True)
                    .limit(1)
                    .execute()
                )
                rev_rows = getattr(rev, "data", None) or []
                latest = rev_rows[0] if rev_rows else None
                has_submitted_revision = bool(
                    latest
                    and (
                        str(latest.get("status") or "").strip().lower() == "submitted"
                        or bool(latest.get("submitted_at"))
                    )
                )
            except Exception:
                has_submitted_revision = False
            if not has_submitted_revision:
                raise HTTPException(
                    status_code=422,
                    detail="Final decision requires at least one submitted author revision",
                )
        new_status = current_status

        if request.is_final:
            transition_payload = {
                "action": "final_decision_workspace",
                "decision": decision,
                "decision_stage": "final",
                "source": "decision_workspace",
                "reason": "editor_submit_final_decision",
                "decision_letter": {
                    "id": row.get("id"),
                    "status": row.get("status"),
                    "content": row.get("content"),
                    "attachment_paths": row.get("attachment_paths") or [],
                },
            }
            new_status = self._transition_for_final_decision(
                manuscript_id=manuscript_id,
                current_status=current_status,
                decision=decision,
                changed_by=user_id,
                transition_payload=transition_payload,
            )
            self._notify_author(
                manuscript=manuscript, manuscript_id=manuscript_id, decision=decision
            )
        else:
            # 中文注释: first decision 仅记录草稿审计事件，不触发状态流转。
            self._safe_insert_audit_log(
                manuscript_id=manuscript_id,
                from_status=current_status,
                to_status=current_status,
                changed_by=user_id,
                comment="first decision saved",
                payload={
                    "action": "first_decision_workspace",
                    "decision_stage": "first",
                    "source": "decision_workspace",
                    "reason": "editor_save_first_decision",
                    "decision": decision,
                    "before": {"status": current_status},
                    "after": {"status": current_status},
                    "decision_letter": {
                        "id": row.get("id"),
                        "status": row.get("status"),
                        "attachment_paths": row.get("attachment_paths") or [],
                    },
                },
            )

        return {
            "decision_letter_id": row.get("id"),
            "status": row.get("status"),
            "manuscript_status": new_status,
            "updated_at": row.get("updated_at"),
        }

    def upload_attachment(
        self,
        *,
        manuscript_id: str,
        user_id: str,
        profile_roles: list[str] | None,
        filename: str,
        content: bytes,
        content_type: str | None = None,
    ) -> dict[str, str]:
        manuscript = self._get_manuscript(manuscript_id)
        roles = self._roles(profile_roles)
        self._ensure_internal_decision_access(
            manuscript=manuscript,
            manuscript_id=manuscript_id,
            user_id=user_id,
            roles=roles,
            action="decision:record_first",
        )

        if not content:
            raise HTTPException(status_code=400, detail="Attachment cannot be empty")
        if len(content) > 25 * 1024 * 1024:
            raise HTTPException(status_code=413, detail="Attachment too large (max 25MB)")

        self._ensure_bucket("decision-attachments", public=False)
        attachment_id = str(uuid4())
        safe_name = _safe_file_name(filename or "decision-attachment")
        object_path = f"decision_letters/{manuscript_id}/{attachment_id}_{safe_name}"

        try:
            self.client.storage.from_("decision-attachments").upload(
                object_path,
                content,
                {"content-type": content_type or "application/octet-stream"},
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to upload attachment: {e}") from e

        return {
            "attachment_id": attachment_id,
            "path": object_path,
            "ref": _encode_attachment_ref(attachment_id, object_path),
        }

    def _find_attachment(
        self, *, manuscript_id: str, attachment_id: str
    ) -> dict[str, Any] | None:
        try:
            resp = (
                self.client.table("decision_letters")
                .select("id,status,editor_id,attachment_paths")
                .eq("manuscript_id", manuscript_id)
                .execute()
            )
        except Exception as e:
            if "decision_letters" in str(e).lower() and "does not exist" in str(e).lower():
                raise HTTPException(
                    status_code=500, detail="DB not migrated: decision_letters table missing"
                ) from e
            raise

        rows = getattr(resp, "data", None) or []
        for row in rows:
            for ref in list(row.get("attachment_paths") or []):
                ref_id, path = _decode_attachment_ref(str(ref))
                if ref_id == attachment_id:
                    return {
                        "decision_letter_id": row.get("id"),
                        "status": row.get("status"),
                        "editor_id": row.get("editor_id"),
                        "path": path,
                    }
        return None

    def get_attachment_signed_url_for_editor(
        self,
        *,
        manuscript_id: str,
        attachment_id: str,
        user_id: str,
        profile_roles: list[str] | None,
    ) -> str:
        manuscript = self._get_manuscript(manuscript_id)
        roles = self._roles(profile_roles)
        self._ensure_internal_decision_access(
            manuscript=manuscript,
            manuscript_id=manuscript_id,
            user_id=user_id,
            roles=roles,
            action="decision:record_first",
        )
        found = self._find_attachment(manuscript_id=manuscript_id, attachment_id=attachment_id)
        if not found:
            raise HTTPException(status_code=404, detail="Attachment not found")
        signed = self._signed_url("decision-attachments", found["path"])
        if not signed:
            raise HTTPException(status_code=500, detail="Failed to sign attachment URL")
        return signed

    def get_attachment_signed_url_for_author(
        self,
        *,
        manuscript_id: str,
        attachment_id: str,
        user_id: str,
        profile_roles: list[str] | None,
    ) -> str:
        manuscript = self._get_manuscript(manuscript_id)
        roles = self._roles(profile_roles)
        is_internal = self._ensure_author_or_internal_access(
            manuscript=manuscript,
            user_id=user_id,
            roles=roles,
        )
        found = self._find_attachment(manuscript_id=manuscript_id, attachment_id=attachment_id)
        if not found:
            raise HTTPException(status_code=404, detail="Attachment not found")
        if not is_internal and str(found.get("status") or "").lower() != "final":
            raise HTTPException(status_code=403, detail="Attachment is not visible before final decision")
        signed = self._signed_url("decision-attachments", found["path"])
        if not signed:
            raise HTTPException(status_code=500, detail="Failed to sign attachment URL")
        return signed
