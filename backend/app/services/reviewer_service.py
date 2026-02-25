from __future__ import annotations

import secrets
import string
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from app.lib.api_client import supabase_admin
from app.schemas.review import (
    InviteAcceptPayload,
    InviteActionWindow,
    InviteAssignmentState,
    InviteDeclinePayload,
    InviteManuscriptPreview,
    InviteTimeline,
    InviteViewData,
)
from app.schemas.reviewer import ReviewerCreate, ReviewerUpdate
from app.services.reviewer_workspace_service import ReviewerWorkspaceService as _ReviewerWorkspaceService


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
        roles = [str(r).strip().lower() for r in raw.split(",") if str(r).strip()]
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
        cooldown_override_enabled = bool(self.cooldown_override_roles())
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
                # - 冷却期命中默认拦截（can_assign=False）。
                # - 仅允许高权限角色在分配接口显式 override 后放行。
                base[rid]["can_assign"] = False
                base[rid]["allow_override"] = bool(cooldown_override_enabled and not base[rid]["conflict"])
                base[rid]["cooldown_last_invited_at"] = hit_at.isoformat()
                base[rid]["cooldown_until"] = cooldown_until
                base[rid]["hits"].append(
                    {
                        "code": "cooldown",
                        "label": "Cooldown active",
                        "severity": "warning",
                        "blocking": True,
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

    def search_page(self, query: str = "", page: int = 1, page_size: int = 50) -> Dict[str, Any]:
        q = (query or "").strip()
        safe_page = max(1, int(page or 1))
        safe_page_size = max(1, min(200, int(page_size or 50)))
        offset = (safe_page - 1) * safe_page_size
        # 中文注释：多取 1 条用于推断 has_more，避免额外 count(*) 查询。
        fetch_size = safe_page_size + 1

        base = (
            supabase_admin.table("user_profiles")
            .select("id,email,full_name,title,affiliation,homepage_url,research_interests,roles,is_reviewer_active,created_at,updated_at")
            .contains("roles", ["reviewer"])
            .eq("is_reviewer_active", True)
        )

        def _slice(query_obj):
            resp = query_obj.order("updated_at", desc=True).range(offset, offset + fetch_size - 1).execute()
            return getattr(resp, "data", None) or []

        if not q:
            rows = _slice(base)
        else:
            # Prefer generated column for fast search; fallback if remote schema not updated
            try:
                rows = _slice(base.ilike("reviewer_search_text", f"%{q}%"))
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
                rows = _slice(base.or_(ors))

        has_more = len(rows) > safe_page_size
        items = rows[:safe_page_size]
        return {
            "items": items,
            "page": safe_page,
            "page_size": safe_page_size,
            "returned": len(items),
            "has_more": has_more,
        }

    def search(self, query: str = "", limit: int = 50) -> List[Dict[str, Any]]:
        # 向后兼容旧调用：保持返回 list。
        page = self.search_page(query=query, page=1, page_size=limit)
        return list(page.get("items") or [])


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


class ReviewerWorkspaceService(_ReviewerWorkspaceService):
    """
    兼容导出:
    - 保持既有导入路径 app.services.reviewer_service.ReviewerWorkspaceService 不变；
    - 运行时注入 reviewer_service 模块级 supabase_admin，确保单测 monkeypatch 行为一致。
    """

    def __init__(self) -> None:
        super().__init__(client=supabase_admin)
