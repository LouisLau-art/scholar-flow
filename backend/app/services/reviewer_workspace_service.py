from __future__ import annotations

import logging
import re
import secrets
from datetime import datetime, timezone
from typing import Any, Dict
from uuid import UUID

from postgrest.exceptions import APIError

from app.lib.api_client import supabase_admin
from app.schemas.review import ReviewSubmission, WorkspaceData

logger = logging.getLogger("scholarflow.reviewer_workspace")


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_iso_datetime(raw: Any) -> datetime | None:
    text = str(raw or "").strip()
    if not text:
        return None
    try:
        dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except Exception:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _derive_invite_state(assignment: Dict[str, Any]) -> str:
    status = str(assignment.get("status") or "").lower()
    if status == "completed":
        return "submitted"
    if status == "accepted":
        return "accepted"
    if status == "declined" or assignment.get("declined_at"):
        return "declined"
    if assignment.get("accepted_at"):
        return "accepted"
    return "invited"


class ReviewerWorkspaceService:
    """
    Reviewer workspace domain service:
    - Strict assignment ownership checks
    - Aggregate manuscript + draft review report for workspace
    - Handle attachment upload and final submission
    """

    def __init__(self, *, client: Any | None = None) -> None:
        self.client = client or supabase_admin

    def _get_assignment_for_reviewer(self, *, assignment_id: UUID, reviewer_id: UUID) -> Dict[str, Any]:
        select_variants = [
            "id, manuscript_id, reviewer_id, status, due_at, invited_at, opened_at, accepted_at, declined_at, submitted_at, decline_reason",
            "id, manuscript_id, reviewer_id, status, due_at, invited_at, opened_at, accepted_at, declined_at, decline_reason",
            "id, manuscript_id, reviewer_id, status, due_at, accepted_at, declined_at",
            "id, manuscript_id, reviewer_id, status, due_at",
        ]
        last_error: Exception | None = None
        assignment: Dict[str, Any] = {}
        for cols in select_variants:
            try:
                resp = (
                    self.client.table("review_assignments")
                    .select(cols)
                    .eq("id", str(assignment_id))
                    .single()
                    .execute()
                )
                assignment = getattr(resp, "data", None) or {}
                last_error = None
                break
            except Exception as e:
                last_error = e
                continue
        if last_error and not assignment:
            raise last_error
        if not assignment:
            raise ValueError("Assignment not found")
        if str(assignment.get("reviewer_id") or "") != str(reviewer_id):
            raise PermissionError("Assignment does not belong to current reviewer")
        return assignment

    def _ensure_invitation_accepted(
        self,
        *,
        assignment_id: UUID,
        assignment: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        中文注释:
        - UAT/外部 reviewer 场景下，流程应尽量“点开就能开始 review”，避免被卡在 accept 页；
        - 云端 schema 可能缺 invited_at/opened_at/accepted_at 等字段，更新失败时做多档降级；
        - 若两档写入都失败，必须显式报错，避免出现“内存态 accepted、数据库仍 invited”的不一致。
        """
        state = _derive_invite_state(assignment)
        if state != "invited":
            return assignment

        now_iso = _utc_now_iso()
        first_error: Exception | None = None
        # 1) 最完整写入：pending + accepted_at + opened_at
        try:
            self.client.table("review_assignments").update(
                {"status": "pending", "accepted_at": now_iso, "opened_at": now_iso}
            ).eq("id", str(assignment_id)).execute()
            assignment["status"] = "pending"
            assignment["accepted_at"] = now_iso
            assignment["opened_at"] = assignment.get("opened_at") or now_iso
            return assignment
        except Exception as e:
            first_error = e

        # 2) 降级：仅写 status=accepted（兼容缺失时间戳列的环境）
        try:
            self.client.table("review_assignments").update({"status": "accepted"}).eq(
                "id", str(assignment_id)
            ).execute()
        except Exception as e:
            logger.error(
                "[ReviewerWorkspace] failed to persist invitation acceptance (assignment_id=%s): first=%r, fallback=%r",
                assignment_id,
                first_error,
                e,
            )
            raise RuntimeError("Failed to persist invitation acceptance") from e

        assignment["status"] = "accepted"
        assignment["accepted_at"] = assignment.get("accepted_at") or now_iso
        assignment["opened_at"] = assignment.get("opened_at") or now_iso
        return assignment

    def _extract_signed_url(self, signed: Any) -> str | None:
        if isinstance(signed, dict):
            value = signed.get("signedURL") or signed.get("signedUrl") or signed.get("signed_url")
            if value:
                return value
        getter = getattr(signed, "get", lambda _k, _d=None: None)
        value = getter("signedURL") or getter("signedUrl") or getter("signed_url")
        if value:
            return value
        data = getattr(signed, "data", None)
        if isinstance(data, dict):
            value = data.get("signedURL") or data.get("signedUrl") or data.get("signed_url")
            if value:
                return value
        return None

    def _get_signed_url(self, *, bucket: str, file_path: str, expires_in: int = 60 * 5) -> str:
        # 中文注释: Reviewer 端统一走短时效 signed URL，避免泄露私有对象路径。
        signed = self.client.storage.from_(bucket).create_signed_url(file_path, expires_in)
        value = self._extract_signed_url(signed)
        if value:
            return value
        raise ValueError("Failed to generate signed URL")

    def _list_review_reports(self, *, manuscript_id: str, reviewer_id: str) -> list[dict[str, Any]]:
        select_variants = [
            "id,status,comments_for_author,content,confidential_comments_to_editor,recommendation,attachment_path,created_at,updated_at",
            "id,status,comments_for_author,content,confidential_comments_to_editor,attachment_path,created_at",
            "id,status,content,attachment_path,created_at",
        ]
        for cols in select_variants:
            try:
                rr = (
                    self.client.table("review_reports")
                    .select(cols)
                    .eq("manuscript_id", manuscript_id)
                    .eq("reviewer_id", reviewer_id)
                    .order("created_at", desc=True)
                    .execute()
                )
                return getattr(rr, "data", None) or []
            except Exception:
                continue
        return []

    def _load_manuscript(self, *, manuscript_id: str) -> dict[str, Any]:
        select_variants = [
            "id,title,abstract,file_path,dataset_url,source_code_url,cover_letter_path",
            "id,title,abstract,file_path,cover_letter_path",
            "id,title,abstract,file_path",
        ]
        for cols in select_variants:
            try:
                ms_resp = (
                    self.client.table("manuscripts")
                    .select(cols)
                    .eq("id", manuscript_id)
                    .single()
                    .execute()
                )
                return getattr(ms_resp, "data", None) or {}
            except Exception:
                continue
        return {}

    def _build_attachment_items(self, *, report_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        seen: set[str] = set()
        items: list[dict[str, Any]] = []
        for row in report_rows:
            path = str(row.get("attachment_path") or "").strip()
            if not path or path in seen:
                continue
            seen.add(path)
            filename = path.rsplit("/", 1)[-1] or "attachment"
            signed_url: str | None
            try:
                signed_url = self._get_signed_url(bucket="review-attachments", file_path=path, expires_in=60 * 5)
            except Exception:
                signed_url = None
            items.append({"path": path, "filename": filename, "signed_url": signed_url})
        return items

    def _sanitize_text(self, raw: Any) -> str:
        text = str(raw or "").strip()
        if not text:
            return ""
        # 中文注释: response_letter 可能是富文本 HTML，这里做轻量去标签，避免时间线展示过于噪声。
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text

    def _load_author_response_events(self, *, manuscript_id: str) -> list[dict[str, Any]]:
        try:
            resp = (
                self.client.table("revisions")
                .select("id,round_number,response_letter,submitted_at,created_at,status")
                .eq("manuscript_id", manuscript_id)
                .order("round_number", desc=True)
                .execute()
            )
            rows = getattr(resp, "data", None) or []
        except Exception:
            return []

        out: list[dict[str, Any]] = []
        for row in rows:
            letter = self._sanitize_text(row.get("response_letter"))
            if not letter:
                continue
            ts_raw = row.get("submitted_at") or row.get("created_at")
            ts = _parse_iso_datetime(ts_raw)
            if ts is None:
                continue
            round_number = row.get("round_number")
            out.append(
                {
                    "id": f"author-revision-{row.get('id')}",
                    "timestamp": ts,
                    "actor": "author",
                    "channel": "public",
                    "title": f"Author resubmission note (Round {round_number})"
                    if round_number is not None
                    else "Author resubmission note",
                    "message": letter,
                }
            )
        return out

    def _load_reviewer_notification_events(self, *, manuscript_id: str, reviewer_id: str) -> list[dict[str, Any]]:
        try:
            resp = (
                self.client.table("notifications")
                .select("id,type,content,created_at")
                .eq("manuscript_id", manuscript_id)
                .eq("user_id", reviewer_id)
                .order("created_at", desc=True)
                .limit(20)
                .execute()
            )
            rows = getattr(resp, "data", None) or []
        except Exception:
            return []

        out: list[dict[str, Any]] = []
        for row in rows:
            ts = _parse_iso_datetime(row.get("created_at"))
            if ts is None:
                continue
            out.append(
                {
                    "id": f"notification-{row.get('id')}",
                    "timestamp": ts,
                    "actor": "editor",
                    "channel": "system",
                    "title": str(row.get("type") or "notification").replace("_", " ").title(),
                    "message": self._sanitize_text(row.get("content")),
                }
            )
        return out

    def _build_assignment_events(self, *, assignment: dict[str, Any]) -> list[dict[str, Any]]:
        events: list[dict[str, Any]] = []
        mapping = [
            ("invited_at", "system", "system", "Invitation sent"),
            ("opened_at", "reviewer", "system", "Invitation opened"),
            ("accepted_at", "reviewer", "system", "Invitation accepted"),
            ("submitted_at", "reviewer", "system", "Review submitted"),
            ("declined_at", "reviewer", "system", "Invitation declined"),
        ]
        for key, actor, channel, title in mapping:
            ts = _parse_iso_datetime(assignment.get(key))
            if ts is None:
                continue
            events.append(
                {
                    "id": f"assignment-{key}-{assignment.get('id')}",
                    "timestamp": ts,
                    "actor": actor,
                    "channel": channel,
                    "title": title,
                    "message": None,
                }
            )

        due_dt = _parse_iso_datetime(assignment.get("due_at"))
        if due_dt is not None:
            events.append(
                {
                    "id": f"assignment-due-{assignment.get('id')}",
                    "timestamp": due_dt,
                    "actor": "system",
                    "channel": "system",
                    "title": "Review due date",
                    "message": f"Please submit before {due_dt.strftime('%Y-%m-%d %H:%M UTC')}.",
                }
            )
        return events

    def _build_report_events(self, *, report_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        events: list[dict[str, Any]] = []
        for row in report_rows:
            ts = _parse_iso_datetime(row.get("updated_at")) or _parse_iso_datetime(row.get("created_at"))
            if ts is None:
                continue
            public_note = self._sanitize_text(row.get("comments_for_author") or row.get("content"))
            confidential_note = self._sanitize_text(row.get("confidential_comments_to_editor"))
            if public_note:
                events.append(
                    {
                        "id": f"report-public-{row.get('id')}",
                        "timestamp": ts,
                        "actor": "reviewer",
                        "channel": "public",
                        "title": "Your comment to authors",
                        "message": public_note,
                    }
                )
            if confidential_note:
                events.append(
                    {
                        "id": f"report-private-{row.get('id')}",
                        "timestamp": ts,
                        "actor": "reviewer",
                        "channel": "private",
                        "title": "Your confidential note to editor",
                        "message": confidential_note,
                    }
                )
        return events

    def get_workspace_data(self, *, assignment_id: UUID, reviewer_id: UUID) -> WorkspaceData:
        assignment = self._get_assignment_for_reviewer(assignment_id=assignment_id, reviewer_id=reviewer_id)
        assignment = self._ensure_invitation_accepted(assignment_id=assignment_id, assignment=assignment)
        state = _derive_invite_state(assignment)
        if state == "declined":
            raise PermissionError("Invitation has been declined")
        if state == "invited":
            raise PermissionError("Please accept invitation first")
        manuscript_id = str(assignment["manuscript_id"])

        manuscript = self._load_manuscript(manuscript_id=manuscript_id)
        if not manuscript:
            raise ValueError("Manuscript not found")
        file_path = str(manuscript.get("file_path") or "").strip()
        if not file_path:
            raise ValueError("Manuscript PDF not found")
        pdf_url = self._get_signed_url(bucket="manuscripts", file_path=file_path, expires_in=60 * 5)

        report_rows = self._list_review_reports(manuscript_id=manuscript_id, reviewer_id=str(reviewer_id))
        report = report_rows[0] if report_rows else None
        attachments = self._build_attachment_items(report_rows=report_rows)

        cover_letter_path = str(manuscript.get("cover_letter_path") or "").strip()
        cover_letter_url: str | None = None
        if cover_letter_path:
            try:
                cover_letter_url = self._get_signed_url(bucket="manuscripts", file_path=cover_letter_path, expires_in=60 * 5)
            except Exception:
                cover_letter_url = None

        is_read_only = str(assignment.get("status") or "").lower() == "completed"
        can_submit = not is_read_only
        recommendation = report.get("recommendation") if report else None
        if recommendation is None and report and report.get("status") == "completed":
            # 兼容历史数据：老数据可能没有 recommendation 字段
            recommendation = "minor_revision"

        timeline: list[dict[str, Any]] = []
        timeline.extend(self._build_assignment_events(assignment=assignment))
        timeline.extend(self._build_report_events(report_rows=report_rows))
        timeline.extend(
            self._load_reviewer_notification_events(
                manuscript_id=manuscript_id,
                reviewer_id=str(reviewer_id),
            )
        )
        timeline.extend(self._load_author_response_events(manuscript_id=manuscript_id))
        timeline.sort(key=lambda item: item.get("timestamp"), reverse=True)

        assignment_id_value = str(assignment.get("id") or "").strip()
        try:
            UUID(assignment_id_value)
        except Exception:
            assignment_id_value = str(assignment_id)

        return WorkspaceData.model_validate(
            {
                "manuscript": {
                    "id": manuscript["id"],
                    "title": manuscript.get("title") or "Untitled",
                    "abstract": manuscript.get("abstract"),
                    "pdf_url": pdf_url,
                    "dataset_url": manuscript.get("dataset_url"),
                    "source_code_url": manuscript.get("source_code_url"),
                    "cover_letter_url": cover_letter_url,
                },
                "assignment": {
                    "id": assignment_id_value,
                    "status": assignment.get("status") or "pending",
                    "due_at": assignment.get("due_at"),
                    "invited_at": assignment.get("invited_at"),
                    "opened_at": assignment.get("opened_at"),
                    "accepted_at": assignment.get("accepted_at"),
                    "submitted_at": assignment.get("submitted_at"),
                    "decline_reason": assignment.get("decline_reason"),
                },
                "review_report": {
                    "id": report.get("id") if report else None,
                    "status": (report or {}).get("status") or "pending",
                    "comments_for_author": (report or {}).get("comments_for_author")
                    or (report or {}).get("content")
                    or "",
                    "confidential_comments_to_editor": (report or {}).get("confidential_comments_to_editor") or "",
                    "recommendation": recommendation,
                    "attachments": attachments,
                    "submitted_at": (report or {}).get("updated_at") or (report or {}).get("created_at"),
                },
                "permissions": {"can_submit": can_submit, "is_read_only": is_read_only},
                "timeline": timeline,
            }
        )

    def upload_attachment(
        self,
        *,
        assignment_id: UUID,
        reviewer_id: UUID,
        filename: str,
        content: bytes,
        content_type: str | None = None,
    ) -> str:
        self._get_assignment_for_reviewer(assignment_id=assignment_id, reviewer_id=reviewer_id)
        safe_name = (filename or "attachment").replace("/", "_")
        unique_prefix = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S") + "-" + secrets.token_hex(4)
        object_path = f"assignments/{assignment_id}/{unique_prefix}-{safe_name}"
        self.client.storage.from_("review-attachments").upload(
            object_path,
            content,
            {"content-type": content_type or "application/octet-stream"},
        )
        return object_path

    def submit_review(
        self,
        *,
        assignment_id: UUID,
        reviewer_id: UUID,
        payload: ReviewSubmission,
    ) -> Dict[str, Any]:
        assignment = self._get_assignment_for_reviewer(assignment_id=assignment_id, reviewer_id=reviewer_id)
        assignment = self._ensure_invitation_accepted(assignment_id=assignment_id, assignment=assignment)
        state = _derive_invite_state(assignment)
        if state == "submitted":
            raise ValueError("Review already submitted")
        if state == "declined":
            raise ValueError("Invitation already declined")
        if state == "invited":
            raise ValueError("Please accept invitation first")

        manuscript_id = str(assignment["manuscript_id"])
        attachment_path = payload.attachments[-1] if payload.attachments else None
        recommendation = str(payload.recommendation or "minor_revision").strip() or "minor_revision"
        report_payload = {
            "manuscript_id": manuscript_id,
            "reviewer_id": str(reviewer_id),
            "status": "completed",
            "comments_for_author": payload.comments_for_author,
            "confidential_comments_to_editor": payload.confidential_comments_to_editor or None,
            "recommendation": recommendation,
            "attachment_path": attachment_path,
            "content": payload.comments_for_author,
            "score": 5,
        }

        existing = (
            self.client.table("review_reports")
            .select("id")
            .eq("manuscript_id", manuscript_id)
            .eq("reviewer_id", str(reviewer_id))
            .limit(1)
            .execute()
        )
        rows = getattr(existing, "data", None) or []
        if rows:
            try:
                self.client.table("review_reports").update(report_payload).eq("id", rows[0]["id"]).execute()
            except APIError as e:
                # 中文注释: 兼容历史 schema（缺字段 recommendation）避免直接 500。
                if "recommendation" not in str(e).lower():
                    raise
                fallback_payload = {k: v for k, v in report_payload.items() if k != "recommendation"}
                self.client.table("review_reports").update(fallback_payload).eq("id", rows[0]["id"]).execute()
        else:
            try:
                self.client.table("review_reports").insert(report_payload).execute()
            except APIError as e:
                if "recommendation" not in str(e).lower():
                    raise
                fallback_payload = {k: v for k, v in report_payload.items() if k != "recommendation"}
                self.client.table("review_reports").insert(fallback_payload).execute()

        self.client.table("review_assignments").update({"status": "completed"}).eq("id", str(assignment_id)).execute()

        # 当该稿件所有 assignment 都 completed 时，推进到 decision
        pending = (
            self.client.table("review_assignments")
            .select("id")
            .eq("manuscript_id", manuscript_id)
            .neq("status", "completed")
            .execute()
        )
        if not (getattr(pending, "data", None) or []):
            try:
                # 首选：仅在 under_review/resubmitted/decision 时推进，避免把已进入 production 的稿件回滚。
                self.client.table("manuscripts").update({"status": "decision"}).eq("id", manuscript_id).in_(
                    "status",
                    ["under_review", "resubmitted", "decision"],
                ).execute()
                # 兼容：历史环境可能仍存在 pending_decision（TEXT）状态；enum 环境会报错，忽略即可。
                try:
                    self.client.table("manuscripts").update({"status": "decision"}).eq("id", manuscript_id).eq(
                        "status", "pending_decision"
                    ).execute()
                except Exception as e:
                    logger.debug("Advance manuscript fallback from pending_decision skipped: %s", e)
            except Exception as e:
                # 中文注释：审稿提交优先，不应因“推进 decision 失败”导致 reviewer 端 500。
                logger.warning("[ReviewerSubmit] advance manuscript to decision failed (ignored): %s", e)

        return {"success": True, "status": "completed"}
