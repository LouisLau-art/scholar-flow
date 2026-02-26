from fastapi import APIRouter, Depends, HTTPException, Query, Request

from app.api.v1.editor_common import require_action_or_403 as _require_action_or_403
from app.core.auth_utils import get_current_user
from app.core.journal_scope import get_user_scope_journal_ids, is_scope_enforcement_enabled
import app.core.journal_scope as journal_scope_module
from app.core.role_matrix import list_allowed_actions, normalize_roles
from app.core.roles import require_any_role
from app.core.short_ttl_cache import ShortTTLCache
from app.services.editor_service import EditorService, ProcessListFilters
import app.services.editor_service as editor_service_module

EDITOR_SCOPE_COMPAT_ROLES = [
    "admin",
    "managing_editor",
    "assistant_editor",
    "production_editor",
    "editor_in_chief",
]
_RBAC_CONTEXT_CACHE_TTL_SEC = 30.0
_PROCESS_ROWS_CACHE_TTL_SEC = 8.0
_rbac_context_cache = ShortTTLCache[dict[str, object]](max_entries=1024)
_process_rows_cache = ShortTTLCache[dict[str, object]](max_entries=1024)

router = APIRouter(tags=["Editor Command Center"])


def _is_force_refresh_request(request: Request) -> bool:
    token = str(request.headers.get("x-sf-force-refresh") or "").strip().lower()
    return token in {"1", "true", "yes", "on"}


def _build_scope_cache_context(
    *,
    user_id: str,
    raw_roles: list[str] | tuple[str, ...] | set[str] | None,
) -> tuple[list[str], bool, bool, list[str], str]:
    """
    计算 cache key 需要的 scope 上下文。

    中文注释:
    - 强约束角色（ME/EIC）即使灰度开关关闭也要纳入 scope；
    - key 纳入 allowed_journal_ids，避免 scope 变更后命中旧缓存。
    """
    normalized_roles = sorted(normalize_roles(raw_roles or []))
    role_set = set(normalized_roles)
    is_admin = "admin" in role_set
    has_strict_scope_role = bool({"managing_editor", "editor_in_chief"} & role_set)
    enforcement_enabled = bool(is_scope_enforcement_enabled() or has_strict_scope_role)

    allowed_journal_ids: list[str] = []
    if enforcement_enabled and not is_admin:
        allowed_journal_ids = sorted(
            get_user_scope_journal_ids(
                user_id=str(user_id or ""),
                roles=list(raw_roles or normalized_roles),
            )
        )

    scope_key = (
        f"scope_enf={1 if enforcement_enabled else 0}|is_admin={1 if is_admin else 0}"
        f"|allowed={','.join(allowed_journal_ids)}"
    )
    return normalized_roles, is_admin, enforcement_enabled, allowed_journal_ids, scope_key


def _data_source_cache_marker() -> str:
    """
    标记当前数据源对象身份，避免测试/热替换阶段缓存串读。
    """
    return (
        f"scope_client={id(getattr(journal_scope_module, 'supabase_admin', None))}"
        f"|process_client={id(getattr(editor_service_module, 'supabase_admin', None))}"
    )


@router.get("/rbac/context")
async def get_editor_rbac_context(
    request: Request,
    current_user: dict = Depends(get_current_user),
    profile: dict = Depends(require_any_role(EDITOR_SCOPE_COMPAT_ROLES)),
):
    """
    GAP-P1-05: 返回当前用户的 RBAC 能力与 journal-scope 上下文（前端显隐使用）。
    """
    user_id = str(current_user.get("id") or "")
    raw_roles = profile.get("roles") or []
    normalized_roles, is_admin, enforcement_enabled, allowed_journal_ids, scope_key = _build_scope_cache_context(
        user_id=user_id,
        raw_roles=raw_roles,
    )

    cache_key = (
        f"uid={user_id}|roles={','.join(normalized_roles)}|{scope_key}|{_data_source_cache_marker()}"
    )
    if not _is_force_refresh_request(request):
        cached = _rbac_context_cache.get(cache_key)
        if cached is not None:
            return cached

    actions = sorted(list_allowed_actions(raw_roles))

    response = {
        "success": True,
        "data": {
            "user_id": user_id,
            "roles": raw_roles,
            "normalized_roles": normalized_roles,
            "allowed_actions": actions,
            "journal_scope": {
                "enforcement_enabled": enforcement_enabled,
                "allowed_journal_ids": allowed_journal_ids,
                "is_admin": is_admin,
            },
        },
    }
    _rbac_context_cache.set(cache_key, response, ttl_sec=_RBAC_CONTEXT_CACHE_TTL_SEC)
    return response


@router.get("/manuscripts/process")
async def get_manuscripts_process(
    request: Request,
    q: str | None = Query(None, description="搜索（Title / UUID 精确匹配，可选）"),
    journal_id: str | None = Query(None, description="期刊筛选（可选）"),
    status: list[str] | None = Query(None, description="状态筛选（可选，多选）"),
    owner_id: str | None = Query(None, description="Internal Owner（可选）"),
    editor_id: str | None = Query(None, description="Assign Editor（可选）"),
    manuscript_id: str | None = Query(None, description="Manuscript ID 精确匹配（可选）"),
    overdue_only: bool = Query(False, description="仅看逾期稿件"),
    current_user: dict = Depends(get_current_user),
    profile: dict = Depends(require_any_role(EDITOR_SCOPE_COMPAT_ROLES)),
):
    """
    Feature 028 / US1: Manuscripts Process 表格数据源。

    返回字段（前端可按需使用）：
    - id, created_at, updated_at, status, owner_id, editor_id, journal_id, journals(title,slug)
    - owner/editor 的 profile（full_name/email）
    """
    try:
        viewer_user_id = str(current_user.get("id") or "")
        viewer_roles = profile.get("roles") or []
        normalized_roles, _is_admin, _enforcement_enabled, _allowed_journal_ids, scope_key = _build_scope_cache_context(
            user_id=viewer_user_id,
            raw_roles=viewer_roles,
        )
        status_key = ",".join(
            sorted(
                {
                    str(item or "").strip().lower()
                    for item in (status or [])
                    if str(item or "").strip()
                }
            )
        )
        cache_key = (
            f"uid={viewer_user_id}|roles={','.join(normalized_roles)}|q={str(q or '').strip().lower()}"
            f"|journal={str(journal_id or '').strip()}|status={status_key}|owner={str(owner_id or '').strip()}"
            f"|editor={str(editor_id or '').strip()}|mid={str(manuscript_id or '').strip()}|overdue={1 if overdue_only else 0}"
            f"|{scope_key}|{_data_source_cache_marker()}"
        )
        if not _is_force_refresh_request(request):
            cached = _process_rows_cache.get(cache_key)
            if cached is not None:
                return cached

        _require_action_or_403(action="process:view", roles=profile.get("roles") or [])
        rows = EditorService().list_manuscripts_process(
            filters=ProcessListFilters(
                q=q,
                statuses=status,
                journal_id=journal_id,
                editor_id=editor_id,
                owner_id=owner_id,
                manuscript_id=manuscript_id,
                overdue_only=bool(overdue_only),
            ),
            viewer_user_id=viewer_user_id,
            viewer_roles=viewer_roles,
            scoped_journal_ids=set(_allowed_journal_ids),
            scope_enforcement_enabled=bool(_enforcement_enabled),
        )
        response = {"success": True, "data": rows}
        _process_rows_cache.set(cache_key, response, ttl_sec=_PROCESS_ROWS_CACHE_TTL_SEC)
        return response
    except HTTPException:
        raise
    except Exception as e:
        print(f"[Process] query failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch manuscripts process")
