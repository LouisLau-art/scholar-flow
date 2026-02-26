from __future__ import annotations

from datetime import datetime, timezone
from time import perf_counter, time
from typing import Any

from fastapi import HTTPException, Request

from app.api.v1.editor_common import (
    get_signed_url as _get_signed_url,
    is_missing_table_error as _is_missing_table_error,
    require_action_or_403 as _require_action_or_403,
)
from app.core.journal_scope import ensure_manuscript_scope_access
from app.core.role_matrix import normalize_roles
from app.core.short_ttl_cache import ShortTTLCache
from app.lib.api_client import supabase_admin
from app.models.manuscript import normalize_status

# 与 editor.py 保持一致：这些角色可进入 Editor Command Center。
EDITOR_SCOPE_COMPAT_ROLES = [
    "admin",
    "managing_editor",
    "assistant_editor",
    "production_editor",
    "editor_in_chief",
]

_AUTH_PROFILE_FALLBACK_TTL_SEC = 60 * 5
_auth_profile_fallback_cache: dict[str, tuple[float, dict[str, Any] | None]] = {}
_DETAIL_HEAVY_BLOCK_CACHE_TTL_SEC = 12.0
_detail_heavy_block_cache = ShortTTLCache[dict[str, Any]](max_entries=1024)
_REVISION_QUERY_VARIANTS: list[tuple[str, str]] = [
    ("updated_at", "id,response_letter,submitted_at,updated_at,round"),
    ("created_at", "id,response_letter,submitted_at,created_at,round"),
    ("created_at", "id,response_letter,created_at"),
]
_REVISION_VARIANT_CACHE_TTL_SEC = 60 * 10
_revision_variant_cache: tuple[float, int] | None = None


def _get_cached_auth_profile(uid: str) -> tuple[bool, dict[str, Any] | None]:
    now = time()
    cached = _auth_profile_fallback_cache.get(uid)
    if not cached:
        return False, None
    expires_at, value = cached
    if expires_at <= now:
        _auth_profile_fallback_cache.pop(uid, None)
        return False, None
    return True, value


def _set_cached_auth_profile(uid: str, profile: dict[str, Any] | None) -> None:
    _auth_profile_fallback_cache[uid] = (time() + _AUTH_PROFILE_FALLBACK_TTL_SEC, profile)


def _is_force_refresh_request(request: Request) -> bool:
    token = str(request.headers.get("x-sf-force-refresh") or "").strip().lower()
    return token in {"1", "true", "yes", "on"}


def _editor_detail_data_source_marker() -> str:
    # 避免测试 monkeypatch supabase_admin 时命中旧缓存。
    return f"db_client={id(supabase_admin)}"


def _is_schema_compat_error(error: Exception) -> bool:
    lowered = str(error).lower()
    return "schema cache" in lowered or "column" in lowered or "pgrst" in lowered


def _get_cached_revision_variant_index() -> int:
    cached = _revision_variant_cache
    if not cached:
        return 0
    expires_at, idx = cached
    if expires_at <= time():
        return 0
    if idx < 0 or idx >= len(_REVISION_QUERY_VARIANTS):
        return 0
    return int(idx)


def _set_cached_revision_variant_index(idx: int) -> None:
    global _revision_variant_cache
    safe_idx = int(idx)
    if safe_idx < 0 or safe_idx >= len(_REVISION_QUERY_VARIANTS):
        safe_idx = 0
    _revision_variant_cache = (time() + _REVISION_VARIANT_CACHE_TTL_SEC, safe_idx)


def _load_revision_response_snapshot(manuscript_id: str) -> dict[str, Any]:
    snapshot: dict[str, Any] = {
        "latest_author_response_letter": None,
        "latest_author_response_submitted_at": None,
        "latest_author_response_round": None,
        "author_response_history": [],
    }
    preferred_idx = _get_cached_revision_variant_index()
    variant_indices = [preferred_idx] + [i for i in range(len(_REVISION_QUERY_VARIANTS)) if i != preferred_idx]

    for idx in variant_indices:
        order_key, select_clause = _REVISION_QUERY_VARIANTS[idx]
        try:
            revision_resp = (
                supabase_admin.table("revisions")
                .select(select_clause)
                .eq("manuscript_id", manuscript_id)
                .order(order_key, desc=True)
                .limit(30)
                .execute()
            )
            revision_rows = getattr(revision_resp, "data", None) or []
            for row in revision_rows:
                response_letter = str(row.get("response_letter") or "").strip()
                if not response_letter:
                    continue
                submitted_at = row.get("submitted_at") or row.get("updated_at") or row.get("created_at")
                round_value = row.get("round")
                try:
                    round_value = int(round_value) if round_value is not None else None
                except Exception:
                    round_value = None

                snapshot["author_response_history"].append(
                    {
                        "id": row.get("id"),
                        "response_letter": response_letter,
                        "submitted_at": submitted_at,
                        "round": round_value,
                    }
                )
                if snapshot["latest_author_response_letter"] is None:
                    snapshot["latest_author_response_letter"] = response_letter
                    snapshot["latest_author_response_submitted_at"] = submitted_at
                    snapshot["latest_author_response_round"] = round_value
            _set_cached_revision_variant_index(idx)
            break
        except Exception as e:
            if _is_schema_compat_error(e):
                continue
            print(f"[Revisions] load latest response letter failed (ignored): {e}")
            break

    return snapshot


def _load_manuscript_or_404(manuscript_id: str) -> dict[str, Any]:
    try:
        resp = (
            supabase_admin.table("manuscripts")
            .select("*, journals(title,slug)")
            .eq("id", manuscript_id)
            .single()
            .execute()
        )
        ms = getattr(resp, "data", None) or None
    except Exception as e:
        raise HTTPException(status_code=404, detail="Manuscript not found") from e
    if not ms:
        raise HTTPException(status_code=404, detail="Manuscript not found")

    normalized_status = normalize_status(str(ms.get("status") or ""))
    if normalized_status:
        ms["status"] = normalized_status
    return ms


def _authorize_manuscript_detail_access(
    *,
    manuscript_id: str,
    manuscript: dict[str, Any],
    current_user: dict[str, Any],
    profile: dict[str, Any],
) -> None:
    # RBAC / Journal Scope:
    # - admin: always allow
    # - assistant_editor: allow if assigned to this manuscript (even if user also has managing_editor role but missing scope)
    # - managing_editor/editor_in_chief: enforce journal_role_scopes
    # - production_editor: allow if assigned to any production cycle (including historical rounds)
    viewer_user_id = str(current_user.get("id") or "").strip()
    viewer_roles = sorted(normalize_roles(profile.get("roles") or []))
    viewer_role_set = set(viewer_roles)

    if "admin" in viewer_role_set:
        return

    assigned_owner_id = str(manuscript.get("owner_id") or "").strip()
    if assigned_owner_id and assigned_owner_id == viewer_user_id and "owner" in viewer_role_set:
        return

    assigned_ae_id = str(manuscript.get("assistant_editor_id") or "").strip()
    if assigned_ae_id and assigned_ae_id == viewer_user_id:
        return

    allowed = False
    if viewer_role_set.intersection({"managing_editor", "editor_in_chief"}):
        ensure_manuscript_scope_access(
            manuscript_id=manuscript_id,
            user_id=viewer_user_id,
            roles=viewer_roles,
            allow_admin_bypass=True,
        )
        allowed = True

    if (not allowed) and ("production_editor" in viewer_role_set):
        try:
            pc = (
                supabase_admin.table("production_cycles")
                .select("id")
                .eq("manuscript_id", manuscript_id)
                .eq("layout_editor_id", viewer_user_id)
                .limit(1)
                .execute()
            )
            if getattr(pc, "data", None):
                allowed = True
            else:
                # Feature 042B: 协作者（collaborator_editor_ids）同样可访问详情页。
                try:
                    pc2 = (
                        supabase_admin.table("production_cycles")
                        .select("id")
                        .eq("manuscript_id", manuscript_id)
                        .contains("collaborator_editor_ids", [viewer_user_id])
                        .limit(1)
                        .execute()
                    )
                    if getattr(pc2, "data", None):
                        allowed = True
                except Exception:
                    # 兼容旧环境未迁移 collaborator_editor_ids：忽略即可
                    pass
        except Exception:
            allowed = False

    if not allowed:
        raise HTTPException(status_code=403, detail="Forbidden")
