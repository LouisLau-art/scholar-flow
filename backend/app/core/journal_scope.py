from __future__ import annotations

import os
from typing import Iterable

from fastapi import HTTPException

from app.core.role_matrix import ADMIN_ROLE, normalize_roles
from app.lib.api_client import supabase_admin


_ALLOWED_SCOPE_ROLES = {
    "managing_editor",
    "assistant_editor",
    "editor_in_chief",
}

_STRICT_SCOPE_ALWAYS_ROLES = {
    "managing_editor",
    "editor_in_chief",
}


def is_scope_enforcement_enabled() -> bool:
    """
    是否启用强制 journal-scope 拦截。

    中文注释:
    - 为了平滑迁移，默认关闭（0），仅在环境变量显式开启时生效；
    - 开启后会对非 admin 执行严格的跨期刊隔离检查。
    """
    raw = (os.environ.get("JOURNAL_SCOPE_ENFORCEMENT") or "0").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def _is_missing_scope_table_error(error_text: str) -> bool:
    text = (error_text or "").lower()
    return "journal_role_scopes" in text and "does not exist" in text


def get_user_scope_journal_ids(*, user_id: str, roles: Iterable[str] | None) -> set[str]:
    """
    获取用户可访问的期刊范围。

    中文注释：
    - admin 不受 journal scope 限制，返回空集合由上层走 bypass。
    - 若 scope 表尚未迁移，返回空集合并由上层按策略处理。
    """
    role_set = normalize_roles(roles)
    if ADMIN_ROLE in role_set:
        return set()

    scope_roles = sorted(role_set.intersection(_ALLOWED_SCOPE_ROLES))
    if not scope_roles:
        return set()

    try:
        resp = (
            supabase_admin.table("journal_role_scopes")
            .select("journal_id, role")
            .eq("user_id", str(user_id))
            .eq("is_active", True)
            .in_("role", scope_roles)
            .execute()
        )
    except Exception as e:
        if _is_missing_scope_table_error(str(e)):
            return set()
        raise

    rows = getattr(resp, "data", None) or []
    allowed_ids: set[str] = set()
    for row in rows:
        journal_id = str(row.get("journal_id") or "").strip()
        if journal_id:
            allowed_ids.add(journal_id)
    return allowed_ids


def get_manuscript_journal_id(manuscript_id: str) -> str | None:
    """
    返回稿件 journal_id；稿件不存在抛 404。
    """
    try:
        resp = (
            supabase_admin.table("manuscripts")
            .select("id,journal_id")
            .eq("id", str(manuscript_id))
            .single()
            .execute()
        )
    except Exception as e:
        raise HTTPException(status_code=404, detail="Manuscript not found") from e

    row = getattr(resp, "data", None) or {}
    if not row:
        raise HTTPException(status_code=404, detail="Manuscript not found")

    journal_id = str(row.get("journal_id") or "").strip()
    return journal_id or None


def ensure_manuscript_scope_access(
    *,
    manuscript_id: str,
    user_id: str,
    roles: Iterable[str] | None,
    allow_admin_bypass: bool = True,
) -> str:
    """
    校验用户是否有权限访问该稿件所属期刊。

    返回值：稿件所属 journal_id。
    """
    role_set = normalize_roles(roles)

    if allow_admin_bypass and ADMIN_ROLE in role_set:
        if is_scope_enforcement_enabled():
            journal_id = get_manuscript_journal_id(manuscript_id)
            return str(journal_id or "")
        return ""

    should_enforce = bool(role_set.intersection(_STRICT_SCOPE_ALWAYS_ROLES)) or is_scope_enforcement_enabled()
    if not should_enforce:
        return ""

    journal_id = get_manuscript_journal_id(manuscript_id)
    if not journal_id:
        raise HTTPException(status_code=403, detail="Journal scope missing for manuscript")

    allowed_journal_ids = get_user_scope_journal_ids(user_id=str(user_id), roles=role_set)
    if journal_id not in allowed_journal_ids:
        raise HTTPException(status_code=403, detail="Forbidden by journal scope")

    return journal_id


def filter_rows_by_journal_scope(
    *,
    rows: list[dict],
    user_id: str,
    roles: Iterable[str] | None,
    journal_key: str = "journal_id",
    allow_admin_bypass: bool = True,
) -> list[dict]:
    """
    对列表结果按 journal scope 做裁剪（主要用于 process 列表）。
    """
    role_set = normalize_roles(roles)
    if allow_admin_bypass and ADMIN_ROLE in role_set:
        return rows

    should_enforce = bool(role_set.intersection(_STRICT_SCOPE_ALWAYS_ROLES)) or is_scope_enforcement_enabled()
    if not should_enforce:
        return rows

    allowed_journal_ids = get_user_scope_journal_ids(user_id=str(user_id), roles=role_set)
    if not allowed_journal_ids:
        return []

    out: list[dict] = []
    for row in rows:
        journal_id = str(row.get(journal_key) or "").strip()
        if journal_id and journal_id in allowed_journal_ids:
            out.append(row)
    return out
