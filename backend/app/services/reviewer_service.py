from __future__ import annotations

import secrets
import string
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from app.lib.api_client import supabase_admin
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

