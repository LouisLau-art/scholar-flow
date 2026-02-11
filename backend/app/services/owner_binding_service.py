from __future__ import annotations

from typing import Optional
from uuid import UUID

from app.lib.api_client import supabase_admin


INTERNAL_ROLES = {"admin", "managing_editor"}


def get_profile_for_owner(owner_id: UUID) -> Optional[dict]:
    """
    获取 owner 的 profile（用于展示姓名/邮箱）.

    中文注释:
    - 这里使用 service_role client（supabase_admin）读取，避免云端 RLS 或权限造成 managing_editor 侧空数据。
    - 若 user_profiles 不存在或该用户未建 profile，则返回 None（由上层决定是否报错）。
    """
    try:
        resp = (
            supabase_admin.table("user_profiles")
            .select("id, email, full_name, roles")
            .eq("id", str(owner_id))
            .maybe_single()
            .execute()
        )
        return getattr(resp, "data", None)
    except Exception as e:
        print(f"[OwnerBinding] 读取 user_profiles 失败: {e}")
        return None


def is_internal_staff_profile(profile: Optional[dict]) -> bool:
    if not profile:
        return False
    roles = set(profile.get("roles") or [])
    return bool(roles.intersection(INTERNAL_ROLES))


def validate_internal_owner_id(owner_id: UUID) -> dict:
    """
    显性逻辑：owner_id 必须属于内部员工（managing_editor/admin）。
    """
    profile = get_profile_for_owner(owner_id)
    if not profile:
        raise ValueError("owner_id profile not found")
    if not is_internal_staff_profile(profile):
        raise ValueError("owner_id must be managing_editor/admin")
    return profile
