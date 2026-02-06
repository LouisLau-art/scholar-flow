from __future__ import annotations

import secrets
import string
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from postgrest.exceptions import APIError

from app.lib.api_client import supabase_admin
from app.schemas.review import ReviewSubmission, WorkspaceData
from app.schemas.reviewer import ReviewerCreate, ReviewerUpdate


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _is_missing_column_error(err: Exception) -> bool:
    msg = str(err or "").lower()
    return "column" in msg or "does not exist" in msg or "pgrst" in msg


class ReviewerService:
    """
    Reviewer Library service:
    - Add to library: create/link auth.users + user_profiles (NO email)
    - Search/list active reviewers
    - Soft delete (deactivate)
    - Profile update
    """

    def _gen_temp_password(self, length: int = 14) -> str:
        alphabet = string.ascii_letters + string.digits
        return "".join(secrets.choice(alphabet) for _ in range(length))

    def _get_profile_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        e = (email or "").strip().lower()
        if not e:
            return None
        resp = (
            supabase_admin.table("user_profiles")
            .select("id,email,full_name,title,affiliation,homepage_url,research_interests,roles,is_reviewer_active,created_at,updated_at")
            .ilike("email", e)
            .maybe_single()
            .execute()
        )
        return getattr(resp, "data", None) or None

    def _find_auth_user_id_by_email(self, email: str) -> Optional[str]:
        """
        Best-effort fallback: list auth users and locate by email.
        NOTE: 仅在 create_user 返回“已存在”时使用，避免频繁拉取全量用户列表。
        """
        try:
            res = supabase_admin.auth.admin.list_users()
            users_list = getattr(res, "users", res)
            if not isinstance(users_list, list):
                users_list = getattr(res, "users", []) or []
            for u in users_list:
                try:
                    if (getattr(u, "email", "") or "").lower() == (email or "").lower():
                        return getattr(u, "id", None)
                except Exception:
                    continue
        except Exception as e:
            print(f"[ReviewerLibrary] list_users failed (ignored): {e}")
        return None

    def add_to_library(self, payload: ReviewerCreate) -> Dict[str, Any]:
        email = str(payload.email).strip().lower()
        now = _utc_now_iso()

        # 1) If profile exists: update metadata, ensure reviewer role, activate.
        existing = self._get_profile_by_email(email)
        if existing and existing.get("id"):
            roles: List[str] = list(existing.get("roles") or [])
            if "reviewer" not in roles:
                roles.append("reviewer")
            update_data: Dict[str, Any] = {
                "full_name": payload.full_name,
                "title": str(payload.title) if payload.title is not None else None,
                "affiliation": payload.affiliation,
                "homepage_url": str(payload.homepage_url) if payload.homepage_url is not None else None,
                "research_interests": payload.research_interests or [],
                "roles": roles,
                "is_reviewer_active": True,
                "updated_at": now,
            }
            supabase_admin.table("user_profiles").update(update_data).eq("id", str(existing["id"])).execute()
            merged = {**existing, **update_data}
            merged["id"] = existing["id"]
            return merged

        # 2) Create auth user (no email) then create profile
        user_id: Optional[str] = None
        try:
            temp_password = self._gen_temp_password()
            res = supabase_admin.auth.admin.create_user(
                {
                    "email": email,
                    "password": temp_password,
                    "email_confirm": True,
                    "user_metadata": {"full_name": payload.full_name},
                }
            )
            user = getattr(res, "user", None)
            user_id = getattr(user, "id", None) if user else None
        except Exception as e:
            msg = str(e).lower()
            if "already exists" in msg or "already registered" in msg:
                user_id = self._find_auth_user_id_by_email(email)
            else:
                raise

        if not user_id:
            raise ValueError("Failed to create/link auth user for reviewer")

        roles = ["reviewer"]
        profile_data: Dict[str, Any] = {
            "id": user_id,
            "email": email,
            "full_name": payload.full_name,
            "title": str(payload.title) if payload.title is not None else None,
            "affiliation": payload.affiliation,
            "homepage_url": str(payload.homepage_url) if payload.homepage_url is not None else None,
            "research_interests": payload.research_interests or [],
            "roles": roles,
            "is_reviewer_active": True,
            "created_at": now,
            "updated_at": now,
        }
        supabase_admin.table("user_profiles").upsert(profile_data).execute()
        return profile_data

    def deactivate(self, reviewer_id: UUID) -> Dict[str, Any]:
        now = _utc_now_iso()
        resp = (
            supabase_admin.table("user_profiles")
            .update({"is_reviewer_active": False, "updated_at": now})
            .eq("id", str(reviewer_id))
            .execute()
        )
        rows = getattr(resp, "data", None) or []
        if not rows:
            raise ValueError("Reviewer not found")
        return rows[0]

    def get_reviewer(self, reviewer_id: UUID) -> Dict[str, Any]:
        resp = (
            supabase_admin.table("user_profiles")
            .select("id,email,full_name,title,affiliation,homepage_url,research_interests,roles,is_reviewer_active,created_at,updated_at")
            .eq("id", str(reviewer_id))
            .single()
            .execute()
        )
        data = getattr(resp, "data", None) or None
        if not data:
            raise ValueError("Reviewer not found")
        return data

    def update_reviewer(self, reviewer_id: UUID, payload: ReviewerUpdate) -> Dict[str, Any]:
        now = _utc_now_iso()
        update_data: Dict[str, Any] = {"updated_at": now}
        for k, v in payload.model_dump(exclude_unset=True).items():
            if k == "homepage_url" and v is not None:
                update_data[k] = str(v)
            else:
                update_data[k] = v
        resp = supabase_admin.table("user_profiles").update(update_data).eq("id", str(reviewer_id)).execute()
        rows = getattr(resp, "data", None) or []
        if not rows:
            raise ValueError("Reviewer not found")
        return rows[0]

    def search(self, query: str = "", limit: int = 50) -> List[Dict[str, Any]]:
        q = (query or "").strip()
        base = (
            supabase_admin.table("user_profiles")
            .select("id,email,full_name,title,affiliation,homepage_url,research_interests,roles,is_reviewer_active,created_at,updated_at")
            .contains("roles", ["reviewer"])
            .eq("is_reviewer_active", True)
            .limit(limit)
        )

        if not q:
            resp = base.order("updated_at", desc=True).execute()
            return getattr(resp, "data", None) or []

        # Prefer generated column for fast search; fallback if remote schema not updated
        try:
            resp = base.ilike("reviewer_search_text", f"%{q}%").order("updated_at", desc=True).execute()
            return getattr(resp, "data", None) or []
        except Exception as e:
            if not _is_missing_column_error(e):
                raise

        # Fallback: OR across basic fields (may be slower without dedicated indexes)
        ors = ",".join(
            [
                f"full_name.ilike.%{q}%",
                f"email.ilike.%{q}%",
                f"affiliation.ilike.%{q}%",
                f"homepage_url.ilike.%{q}%",
            ]
        )
        resp = base.or_(ors).order("updated_at", desc=True).execute()
        return getattr(resp, "data", None) or []


class ReviewerWorkspaceService:
    """
    Reviewer workspace domain service:
    - Strict assignment ownership checks
    - Aggregate manuscript + draft review report for workspace
    - Handle attachment upload and final submission
    """

    def _get_assignment_for_reviewer(self, *, assignment_id: UUID, reviewer_id: UUID) -> Dict[str, Any]:
        resp = (
            supabase_admin.table("review_assignments")
            .select("id, manuscript_id, reviewer_id, status")
            .eq("id", str(assignment_id))
            .single()
            .execute()
        )
        assignment = getattr(resp, "data", None) or {}
        if not assignment:
            raise ValueError("Assignment not found")
        if str(assignment.get("reviewer_id") or "") != str(reviewer_id):
            raise PermissionError("Assignment does not belong to current reviewer")
        return assignment

    def _get_pdf_signed_url(self, file_path: str, expires_in: int = 60 * 10) -> str:
        # 中文注释: Reviewer 端仅使用短时效 signed URL，避免公开暴露原始路径。
        signed = supabase_admin.storage.from_("manuscripts").create_signed_url(file_path, expires_in)
        if isinstance(signed, dict):
            value = signed.get("signedURL") or signed.get("signed_url")
            if value:
                return value
        value = getattr(signed, "get", lambda _k, _d=None: None)("signedURL")
        if value:
            return value
        data = getattr(signed, "data", None)
        if isinstance(data, dict):
            value = data.get("signedURL") or data.get("signed_url")
            if value:
                return value
        raise ValueError("Failed to generate signed URL")

    def _get_latest_review_report(self, *, manuscript_id: str, reviewer_id: str) -> Dict[str, Any] | None:
        try:
            rr = (
                supabase_admin.table("review_reports")
                .select("id,status,comments_for_author,confidential_comments_to_editor,recommendation,attachment_path")
                .eq("manuscript_id", manuscript_id)
                .eq("reviewer_id", reviewer_id)
                .order("created_at", desc=True)
                .limit(1)
                .execute()
            )
            rows = getattr(rr, "data", None) or []
            return rows[0] if rows else None
        except Exception:
            return None

    def get_workspace_data(self, *, assignment_id: UUID, reviewer_id: UUID) -> WorkspaceData:
        assignment = self._get_assignment_for_reviewer(assignment_id=assignment_id, reviewer_id=reviewer_id)
        manuscript_id = str(assignment["manuscript_id"])

        ms_resp = (
            supabase_admin.table("manuscripts")
            .select("id,title,abstract,file_path")
            .eq("id", manuscript_id)
            .single()
            .execute()
        )
        manuscript = getattr(ms_resp, "data", None) or {}
        if not manuscript:
            raise ValueError("Manuscript not found")
        file_path = str(manuscript.get("file_path") or "").strip()
        if not file_path:
            raise ValueError("Manuscript PDF not found")
        pdf_url = self._get_pdf_signed_url(file_path)

        report = self._get_latest_review_report(manuscript_id=manuscript_id, reviewer_id=str(reviewer_id))
        attachments: list[str] = []
        if report and report.get("attachment_path"):
            attachments = [str(report["attachment_path"])]

        is_read_only = str(assignment.get("status") or "").lower() == "completed"
        can_submit = not is_read_only
        recommendation = report.get("recommendation") if report else None
        if recommendation is None and report and report.get("status") == "completed":
            # 兼容历史数据：老数据可能没有 recommendation 字段
            recommendation = "minor_revision"

        return WorkspaceData.model_validate(
            {
                "manuscript": {
                    "id": manuscript["id"],
                    "title": manuscript.get("title") or "Untitled",
                    "abstract": manuscript.get("abstract"),
                    "pdf_url": pdf_url,
                },
                "review_report": {
                    "id": report.get("id") if report else None,
                    "status": (report or {}).get("status") or "pending",
                    "comments_for_author": (report or {}).get("comments_for_author") or "",
                    "confidential_comments_to_editor": (report or {}).get("confidential_comments_to_editor") or "",
                    "recommendation": recommendation,
                    "attachments": attachments,
                },
                "permissions": {"can_submit": can_submit, "is_read_only": is_read_only},
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
        object_path = f"assignments/{assignment_id}/{safe_name}"
        supabase_admin.storage.from_("review-attachments").upload(
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
        if str(assignment.get("status") or "").lower() == "completed":
            raise ValueError("Review already submitted")

        manuscript_id = str(assignment["manuscript_id"])
        attachment_path = payload.attachments[-1] if payload.attachments else None
        report_payload = {
            "manuscript_id": manuscript_id,
            "reviewer_id": str(reviewer_id),
            "status": "completed",
            "comments_for_author": payload.comments_for_author,
            "confidential_comments_to_editor": payload.confidential_comments_to_editor or None,
            "recommendation": payload.recommendation,
            "attachment_path": attachment_path,
            "content": payload.comments_for_author,
            "score": 5,
        }

        existing = (
            supabase_admin.table("review_reports")
            .select("id")
            .eq("manuscript_id", manuscript_id)
            .eq("reviewer_id", str(reviewer_id))
            .limit(1)
            .execute()
        )
        rows = getattr(existing, "data", None) or []
        if rows:
            try:
                supabase_admin.table("review_reports").update(report_payload).eq("id", rows[0]["id"]).execute()
            except APIError as e:
                # 中文注释: 兼容历史 schema（缺字段 recommendation）避免直接 500。
                if "recommendation" not in str(e).lower():
                    raise
                fallback_payload = {k: v for k, v in report_payload.items() if k != "recommendation"}
                supabase_admin.table("review_reports").update(fallback_payload).eq("id", rows[0]["id"]).execute()
        else:
            try:
                supabase_admin.table("review_reports").insert(report_payload).execute()
            except APIError as e:
                if "recommendation" not in str(e).lower():
                    raise
                fallback_payload = {k: v for k, v in report_payload.items() if k != "recommendation"}
                supabase_admin.table("review_reports").insert(fallback_payload).execute()

        supabase_admin.table("review_assignments").update({"status": "completed"}).eq("id", str(assignment_id)).execute()

        # 当该稿件所有 assignment 都 completed 时，推进到 pending_decision
        pending = (
            supabase_admin.table("review_assignments")
            .select("id")
            .eq("manuscript_id", manuscript_id)
            .neq("status", "completed")
            .execute()
        )
        if not (getattr(pending, "data", None) or []):
            supabase_admin.table("manuscripts").update({"status": "pending_decision"}).eq("id", manuscript_id).execute()

        return {"success": True, "status": "completed"}
