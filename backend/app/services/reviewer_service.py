from __future__ import annotations

import secrets
import string
import os
import re
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from postgrest.exceptions import APIError

from app.lib.api_client import supabase_admin
from app.schemas.review import (
    InviteAcceptPayload,
    InviteActionWindow,
    InviteAssignmentState,
    InviteDeclinePayload,
    InviteManuscriptPreview,
    InviteTimeline,
    InviteViewData,
    ReviewSubmission,
    WorkspaceData,
)
from app.schemas.reviewer import ReviewerCreate, ReviewerUpdate


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _is_missing_column_error(err: Exception) -> bool:
    msg = str(err or "").lower()
    return "column" in msg or "does not exist" in msg or "pgrst" in msg


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


class ReviewPolicyService:
    """
    审稿邀请策略服务：
    - 冷却期（同刊同审稿人）
    - 利益冲突（作者=审稿人）
    - 逾期风险（该审稿人未完成且已逾期任务数）
    - due date 默认/窗口配置
    """

    def __init__(self) -> None:
        self.client = supabase_admin

    @staticmethod
    def _safe_int_env(name: str, default: int, *, min_value: int = 0) -> int:
        try:
            value = int((os.environ.get(name) or "").strip() or default)
        except Exception:
            value = default
        return max(min_value, value)

    def cooldown_days(self) -> int:
        return self._safe_int_env("REVIEW_INVITE_COOLDOWN_DAYS", 30, min_value=1)

    def cooldown_override_roles(self) -> list[str]:
        raw = (os.environ.get("REVIEW_INVITE_COOLDOWN_OVERRIDE_ROLES") or "admin,managing_editor").strip()
        roles = [r.strip() for r in raw.split(",") if r.strip()]
        return roles or ["admin", "managing_editor"]

    def due_window_days(self) -> tuple[int, int, int]:
        min_days = self._safe_int_env("REVIEW_INVITE_DUE_MIN_DAYS", 7, min_value=1)
        max_days = self._safe_int_env("REVIEW_INVITE_DUE_MAX_DAYS", 21, min_value=min_days)
        default_days = self._safe_int_env("REVIEW_INVITE_DUE_DEFAULT_DAYS", 10, min_value=min_days)
        if default_days > max_days:
            default_days = max_days
        return min_days, max_days, default_days

    def _load_manuscript_journal_map(self, manuscript_ids: list[str]) -> dict[str, str]:
        mids = sorted({str(x).strip() for x in manuscript_ids if str(x).strip()})
        if not mids:
            return {}
        try:
            resp = (
                self.client.table("manuscripts")
                .select("id,journal_id")
                .in_("id", mids)
                .execute()
            )
            rows = getattr(resp, "data", None) or []
        except Exception:
            rows = []
        out: dict[str, str] = {}
        for row in rows:
            mid = str(row.get("id") or "").strip()
            jid = str(row.get("journal_id") or "").strip()
            if mid and jid:
                out[mid] = jid
        return out

    def evaluate_candidates(self, *, manuscript: dict[str, Any], reviewer_ids: list[str]) -> dict[str, dict[str, Any]]:
        reviewer_ids = sorted({str(x).strip() for x in reviewer_ids if str(x).strip()})
        if not reviewer_ids:
            return {}

        manuscript_id = str(manuscript.get("id") or "").strip()
        journal_id = str(manuscript.get("journal_id") or "").strip()
        author_id = str(manuscript.get("author_id") or "").strip()

        now = datetime.now(timezone.utc)
        cooldown_days = self.cooldown_days()
        cooldown_cutoff = now - timedelta(days=cooldown_days)
        done_statuses = {"completed", "cancelled", "declined"}

        base: dict[str, dict[str, Any]] = {
            rid: {
                "can_assign": True,
                "allow_override": False,
                "cooldown_active": False,
                "conflict": False,
                "overdue_risk": False,
                "overdue_open_count": 0,
                "hits": [],
            }
            for rid in reviewer_ids
        }

        for rid in reviewer_ids:
            if author_id and rid == author_id:
                base[rid]["conflict"] = True
                base[rid]["can_assign"] = False
                base[rid]["hits"].append(
                    {
                        "code": "conflict",
                        "label": "Conflict of interest",
                        "severity": "error",
                        "blocking": True,
                        "detail": "Reviewer is the manuscript author.",
                    }
                )

        try:
            ra_resp = (
                self.client.table("review_assignments")
                .select("manuscript_id,reviewer_id,status,due_at,invited_at,created_at")
                .in_("reviewer_id", reviewer_ids)
                .order("created_at", desc=True)
                .execute()
            )
            assignment_rows = getattr(ra_resp, "data", None) or []
        except Exception:
            assignment_rows = []

        if journal_id and assignment_rows:
            related_manuscript_ids = [
                str(row.get("manuscript_id") or "").strip()
                for row in assignment_rows
                if str(row.get("manuscript_id") or "").strip() and str(row.get("manuscript_id") or "").strip() != manuscript_id
            ]
            journal_map = self._load_manuscript_journal_map(related_manuscript_ids)
        else:
            journal_map = {}

        latest_cooldown_at: dict[str, datetime] = {}
        overdue_count: dict[str, int] = {}

        for row in assignment_rows:
            rid = str(row.get("reviewer_id") or "").strip()
            if rid not in base:
                continue
            status = str(row.get("status") or "").strip().lower()
            due_dt = _parse_iso_datetime(row.get("due_at"))
            if status not in done_statuses and due_dt and due_dt < now:
                overdue_count[rid] = int(overdue_count.get(rid, 0)) + 1

            if not journal_id:
                continue
            row_mid = str(row.get("manuscript_id") or "").strip()
            if not row_mid or row_mid == manuscript_id:
                continue
            if journal_map.get(row_mid) != journal_id:
                continue

            invited_dt = _parse_iso_datetime(row.get("invited_at")) or _parse_iso_datetime(row.get("created_at"))
            if not invited_dt or invited_dt < cooldown_cutoff:
                continue
            prev = latest_cooldown_at.get(rid)
            if prev is None or invited_dt > prev:
                latest_cooldown_at[rid] = invited_dt

        for rid in reviewer_ids:
            if rid in latest_cooldown_at:
                hit_at = latest_cooldown_at[rid]
                cooldown_until = (hit_at + timedelta(days=cooldown_days)).date().isoformat()
                base[rid]["cooldown_active"] = True
                # 中文注释:
                # - 冷却期改为“提醒”而不是强制拦截（editor 仍可选择并指派）。
                # - 仅在 UI 上展示 warning badge；后端不再要求 override。
                base[rid]["can_assign"] = not base[rid]["conflict"]
                base[rid]["allow_override"] = False
                base[rid]["cooldown_last_invited_at"] = hit_at.isoformat()
                base[rid]["cooldown_until"] = cooldown_until
                base[rid]["hits"].append(
                    {
                        "code": "cooldown",
                        "label": "Cooldown active",
                        "severity": "warning",
                        "blocking": False,
                        "detail": f"Invited within {cooldown_days} days in the same journal. Cooldown until {cooldown_until}.",
                    }
                )

            od = int(overdue_count.get(rid, 0))
            if od > 0:
                base[rid]["overdue_risk"] = True
                base[rid]["overdue_open_count"] = od
                base[rid]["hits"].append(
                    {
                        "code": "overdue_risk",
                        "label": "Overdue risk",
                        "severity": "info",
                        "blocking": False,
                        "detail": f"Reviewer has {od} overdue open assignment(s).",
                    }
                )

        return base


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


class ReviewerInviteService:
    """
    Feature 037: invitation response workflow service.

    - 读取邀请态（invited/opened/accepted/declined/submitted）
    - 处理 Accept/Decline 状态流转（幂等）
    - 校验 due date 窗口
    """

    def _due_window_days(self) -> tuple[int, int]:
        min_days, max_days, _default_days = ReviewPolicyService().due_window_days()
        return min_days, max_days

    def _build_due_window(self) -> InviteActionWindow:
        min_days, max_days, default_days = ReviewPolicyService().due_window_days()
        today = datetime.now(timezone.utc).date()
        return InviteActionWindow(
            min_due_date=today + timedelta(days=min_days),
            max_due_date=today + timedelta(days=max_days),
            default_due_date=today + timedelta(days=default_days),
        )

    def _derive_invite_state(self, assignment: Dict[str, Any]) -> str:
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

    def _get_assignment_for_reviewer(self, *, assignment_id: UUID, reviewer_id: UUID) -> Dict[str, Any]:
        try:
            resp = (
                supabase_admin.table("review_assignments")
                .select(
                    "id, manuscript_id, reviewer_id, status, due_at, invited_at, opened_at, accepted_at, declined_at, decline_reason, decline_note"
                )
                .eq("id", str(assignment_id))
                .single()
                .execute()
            )
        except Exception as e:
            # 兼容未应用 037 migration 的环境
            if "column" in str(e).lower() and (
                "invited_at" in str(e).lower()
                or "accepted_at" in str(e).lower()
                or "declined_at" in str(e).lower()
            ):
                resp = (
                    supabase_admin.table("review_assignments")
                    .select("id, manuscript_id, reviewer_id, status, due_at")
                    .eq("id", str(assignment_id))
                    .single()
                    .execute()
                )
            else:
                raise
        assignment = getattr(resp, "data", None) or {}
        if not assignment:
            raise ValueError("Assignment not found")
        if str(assignment.get("reviewer_id") or "") != str(reviewer_id):
            raise PermissionError("Assignment does not belong to current reviewer")
        return assignment

    def _get_submitted_at(self, *, manuscript_id: str, reviewer_id: str) -> str | None:
        try:
            rr = (
                supabase_admin.table("review_reports")
                .select("created_at,status")
                .eq("manuscript_id", manuscript_id)
                .eq("reviewer_id", reviewer_id)
                .eq("status", "completed")
                .order("created_at", desc=True)
                .limit(1)
                .execute()
            )
            rows = getattr(rr, "data", None) or []
            return rows[0].get("created_at") if rows else None
        except Exception:
            return None

    def get_invite_view(self, *, assignment_id: UUID, reviewer_id: UUID) -> InviteViewData:
        assignment = self._get_assignment_for_reviewer(assignment_id=assignment_id, reviewer_id=reviewer_id)
        opened_at = assignment.get("opened_at")
        if not opened_at:
            now_iso = _utc_now_iso()
            try:
                supabase_admin.table("review_assignments").update({"opened_at": now_iso}).eq(
                    "id", str(assignment_id)
                ).execute()
                assignment["opened_at"] = now_iso
            except Exception:
                pass

        manuscript_id = str(assignment.get("manuscript_id") or "")
        ms_resp = (
            supabase_admin.table("manuscripts")
            .select("id,title,abstract")
            .eq("id", manuscript_id)
            .single()
            .execute()
        )
        manuscript = getattr(ms_resp, "data", None) or {}
        if not manuscript:
            raise ValueError("Manuscript not found")

        state = self._derive_invite_state(assignment)
        submitted_at = self._get_submitted_at(manuscript_id=manuscript_id, reviewer_id=str(reviewer_id))
        timeline = InviteTimeline(
            invited_at=assignment.get("invited_at"),
            opened_at=assignment.get("opened_at"),
            accepted_at=assignment.get("accepted_at"),
            declined_at=assignment.get("declined_at"),
            submitted_at=submitted_at,
        )
        assignment_state = InviteAssignmentState(
            assignment_id=UUID(str(assignment["id"])),
            manuscript_id=UUID(manuscript_id),
            reviewer_id=UUID(str(assignment["reviewer_id"])),
            status=state,
            due_at=assignment.get("due_at"),
            decline_reason=assignment.get("decline_reason"),
            decline_note=assignment.get("decline_note"),
            timeline=timeline,
        )
        window = self._build_due_window()
        return InviteViewData(
            assignment=assignment_state,
            manuscript=InviteManuscriptPreview(
                id=UUID(str(manuscript["id"])),
                title=str(manuscript.get("title") or "Untitled Manuscript"),
                abstract=manuscript.get("abstract"),
            ),
            window=window,
            can_open_workspace=state in {"accepted", "submitted"},
        )

    def accept_invitation(
        self,
        *,
        assignment_id: UUID,
        reviewer_id: UUID,
        payload: InviteAcceptPayload,
    ) -> Dict[str, Any]:
        assignment = self._get_assignment_for_reviewer(assignment_id=assignment_id, reviewer_id=reviewer_id)
        state = self._derive_invite_state(assignment)
        if state == "submitted":
            return {"status": "submitted", "idempotent": True, "due_at": assignment.get("due_at")}
        if state == "declined":
            raise ValueError("Invitation already declined")
        if state == "accepted":
            return {"status": "accepted", "idempotent": True, "due_at": assignment.get("due_at")}

        window = self._build_due_window()
        due_date = payload.due_date
        if due_date < window.min_due_date or due_date > window.max_due_date:
            raise ValueError(
                f"Due date must be between {window.min_due_date.isoformat()} and {window.max_due_date.isoformat()}"
            )

        due_at_iso = datetime.combine(due_date, datetime.min.time(), tzinfo=timezone.utc).isoformat()
        now_iso = _utc_now_iso()
        try:
            supabase_admin.table("review_assignments").update(
                {
                    "status": "pending",
                    "accepted_at": now_iso,
                    "due_at": due_at_iso,
                    "declined_at": None,
                    "decline_reason": None,
                    "decline_note": None,
                }
            ).eq("id", str(assignment_id)).execute()
        except Exception as e:
            if "column" in str(e).lower() and "accepted_at" in str(e).lower():
                supabase_admin.table("review_assignments").update(
                    {
                        "status": "accepted",
                        "due_at": due_at_iso,
                    }
                ).eq("id", str(assignment_id)).execute()
            else:
                raise
        return {"status": "accepted", "idempotent": False, "due_at": due_at_iso}

    def decline_invitation(
        self,
        *,
        assignment_id: UUID,
        reviewer_id: UUID,
        payload: InviteDeclinePayload,
    ) -> Dict[str, Any]:
        assignment = self._get_assignment_for_reviewer(assignment_id=assignment_id, reviewer_id=reviewer_id)
        state = self._derive_invite_state(assignment)
        if state == "submitted":
            raise ValueError("Review already submitted")
        if state == "accepted":
            raise ValueError("Invitation already accepted")
        if state == "declined":
            return {"status": "declined", "idempotent": True}

        now_iso = _utc_now_iso()
        try:
            supabase_admin.table("review_assignments").update(
                {
                    "status": "declined",
                    "declined_at": now_iso,
                    "decline_reason": payload.reason,
                    "decline_note": (payload.note or "").strip() or None,
                }
            ).eq("id", str(assignment_id)).execute()
        except Exception as e:
            if "column" in str(e).lower() and "declined_at" in str(e).lower():
                supabase_admin.table("review_assignments").update(
                    {
                        "status": "declined",
                    }
                ).eq("id", str(assignment_id)).execute()
            else:
                raise
        return {"status": "declined", "idempotent": False}


class ReviewerWorkspaceService:
    """
    Reviewer workspace domain service:
    - Strict assignment ownership checks
    - Aggregate manuscript + draft review report for workspace
    - Handle attachment upload and final submission
    """

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
                    supabase_admin.table("review_assignments")
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
        signed = supabase_admin.storage.from_(bucket).create_signed_url(file_path, expires_in)
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
                    supabase_admin.table("review_reports")
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
                    supabase_admin.table("manuscripts")
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
                supabase_admin.table("revisions")
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
                supabase_admin.table("notifications")
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
        state = ReviewerInviteService()._derive_invite_state(assignment)
        if state == "invited":
            # 中文注释:
            # - UAT/内测阶段允许“打开 workspace 即视为接受邀请”，避免 reviewer 被强制卡在 accept 页面。
            # - 兼容云端 schema 漂移：accepted_at/opened_at 可能缺失，缺失时退化为 status=accepted。
            now_iso = _utc_now_iso()
            try:
                supabase_admin.table("review_assignments").update(
                    {"status": "pending", "accepted_at": now_iso, "opened_at": now_iso}
                ).eq("id", str(assignment_id)).execute()
                assignment["status"] = "pending"
                assignment["accepted_at"] = now_iso
                assignment["opened_at"] = assignment.get("opened_at") or now_iso
            except Exception as e:
                if _is_missing_column_error(e):
                    try:
                        supabase_admin.table("review_assignments").update({"status": "accepted"}).eq(
                            "id", str(assignment_id)
                        ).execute()
                        assignment["status"] = "accepted"
                    except Exception:
                        pass
            state = ReviewerInviteService()._derive_invite_state(assignment)
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
        state = ReviewerInviteService()._derive_invite_state(assignment)
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

        # 当该稿件所有 assignment 都 completed 时，推进到 decision
        pending = (
            supabase_admin.table("review_assignments")
            .select("id")
            .eq("manuscript_id", manuscript_id)
            .neq("status", "completed")
            .execute()
        )
        if not (getattr(pending, "data", None) or []):
            try:
                ms_row = (
                    supabase_admin.table("manuscripts")
                    .select("status")
                    .eq("id", manuscript_id)
                    .single()
                    .execute()
                ).data or {}
                current_raw = str(ms_row.get("status") or "").strip().lower()
                # 兼容：历史环境可能仍存在 pending_decision 文本状态。
                if current_raw in {"under_review", "resubmitted", "pending_decision"}:
                    supabase_admin.table("manuscripts").update({"status": "decision"}).eq("id", manuscript_id).execute()
            except Exception as e:
                # 中文注释：审稿提交优先，不应因“推进 decision 失败”导致 reviewer 端 500。
                print(f"[ReviewerSubmit] advance manuscript to decision failed (ignored): {e}")

        return {"success": True, "status": "completed"}
