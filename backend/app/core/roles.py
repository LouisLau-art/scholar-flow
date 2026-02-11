import os
from typing import Callable, Iterable, Optional, Set

from fastapi import Depends, HTTPException

from app.core.auth_utils import get_current_user
from app.lib.api_client import supabase


def _parse_admin_emails() -> Set[str]:
    raw = os.environ.get("ADMIN_EMAILS", "")
    return {e.strip().lower() for e in raw.split(",") if e.strip()}


def _is_admin_email(email: Optional[str]) -> bool:
    if not email:
        return False
    return email.strip().lower() in _parse_admin_emails()


async def get_current_profile(current_user: dict = Depends(get_current_user)) -> dict:
    """
    获取当前用户的 profile（含 roles）。

    中文注释:
    1) 由于后端当前使用 Supabase anon key，因此这里做“应用层”角色管理。
    2) 首次访问时自动创建 user_profiles 记录，默认 roles=['author']。
    3) 若 email 在 ADMIN_EMAILS 中，则自动补齐 admin/managing_editor/reviewer 权限，便于本地/演示测试。
    """
    user_id = current_user["id"]
    email = current_user.get("email")

    roles = ["author"]
    if _is_admin_email(email):
        roles = ["admin", "managing_editor", "reviewer", "author"]

    try:
        resp = supabase.table("user_profiles").select("*").eq("id", user_id).execute()
        existing = (resp.data or [None])[0]
        if existing:
            # 若配置了 ADMIN_EMAILS，确保 admin 用户拥有对应角色（便于演示）
            existing_roles = existing.get("roles") or []
            if _is_admin_email(email):
                merged = list(dict.fromkeys([*roles, *existing_roles]))
                if merged != existing_roles:
                    supabase.table("user_profiles").update({"roles": merged}).eq("id", user_id).execute()
                    existing["roles"] = merged
            return existing

        inserted = (
            supabase.table("user_profiles")
            .insert({"id": user_id, "email": email, "roles": roles})
            .execute()
        )
        return (inserted.data or [{"id": user_id, "email": email, "roles": roles}])[0]
    except Exception as e:
        print(f"Failed to fetch/create user profile: {e}")
        # 最小化降级：至少把用户身份返回给上层，避免 UI 完全不可用
        return {"id": user_id, "email": email, "roles": roles}


def require_any_role(required: Iterable[str]) -> Callable[[dict], dict]:
    required_set = {r for r in required}

    async def _dep(profile: dict = Depends(get_current_profile)) -> dict:
        roles = set(profile.get("roles") or [])
        if not roles.intersection(required_set):
            raise HTTPException(status_code=403, detail="Insufficient role")
        return profile

    return _dep
