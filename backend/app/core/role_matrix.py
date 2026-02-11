from __future__ import annotations

from typing import Iterable

# 中文注释：
# - 这里集中定义“角色 -> 动作”权限矩阵，避免权限逻辑散落在各路由。
# - 2026-02-11 起移除 legacy `editor` 兼容；输入角色仅接受当前标准角色集合。

ADMIN_ROLE = "admin"

ROLE_ACTIONS: dict[str, set[str]] = {
    "author": {
        "author:submit",
        "author:view_own_manuscript",
    },
    "reviewer": {
        "reviewer:view_assignment",
        "reviewer:submit_report",
    },
    "assistant_editor": {
        "process:view",
        "precheck:technical_check",
        "manuscript:view_detail",
    },
    "managing_editor": {
        "process:view",
        "manuscript:view_detail",
        "manuscript:bind_owner",
        "invoice:update_info",
        "decision:record_first",
    },
    "editor_in_chief": {
        "process:view",
        "manuscript:view_detail",
        "decision:record_first",
        "decision:submit_final",
        "invoice:override_apc",
    },
    ADMIN_ROLE: {
        "*",
    },
}


def normalize_roles(roles: Iterable[str] | None) -> set[str]:
    """
    将输入角色归一化（小写、去空）。
    """
    out: set[str] = set()
    for raw in roles or []:
        role = str(raw or "").strip().lower()
        if not role:
            continue
        out.add(role)
    return out


def can_perform_action(*, action: str, roles: Iterable[str] | None) -> bool:
    """
    判定角色集合是否可执行某动作。

    中文注释：
    - admin 拥有全局通配权限；
    - 其余角色按 ROLE_ACTIONS 显式授权。
    """
    normalized = normalize_roles(roles)
    if ADMIN_ROLE in normalized:
        return True

    for role in normalized:
        allowed = ROLE_ACTIONS.get(role) or set()
        if "*" in allowed or action in allowed:
            return True
    return False


def list_allowed_actions(roles: Iterable[str] | None) -> set[str]:
    """
    返回当前角色可执行动作集合（用于前端 capability 输出）。
    """
    normalized = normalize_roles(roles)
    if ADMIN_ROLE in normalized:
        return {"*"}

    actions: set[str] = set()
    for role in normalized:
        actions.update(ROLE_ACTIONS.get(role) or set())
    return actions
