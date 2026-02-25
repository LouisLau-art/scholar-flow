from fastapi import APIRouter, HTTPException, Body, Depends, BackgroundTasks, Query, UploadFile, File, Form, Request
from fastapi.responses import StreamingResponse
from app.lib.api_client import supabase, supabase_admin
from app.core.auth_utils import get_current_user
from app.core.roles import require_any_role
from app.core.journal_scope import (
    ensure_manuscript_scope_access,
    get_user_scope_journal_ids,
    is_scope_enforcement_enabled,
)
import app.core.journal_scope as journal_scope_module
from app.core.role_matrix import can_perform_action, list_allowed_actions, normalize_roles
from app.core.short_ttl_cache import ShortTTLCache
from datetime import datetime
from app.services.notification_service import NotificationService
from app.models.revision import RevisionCreate, RevisionRequestResponse
from app.services.revision_service import RevisionService
from datetime import timezone
from app.services.post_acceptance_service import publish_manuscript
from app.services.production_service import ProductionService
import os
from app.services.editorial_service import EditorialService
from app.models.manuscript import ManuscriptStatus, normalize_status
from app.services.owner_binding_service import validate_internal_owner_id
from uuid import UUID
from app.schemas.reviewer import ReviewerCreate, ReviewerUpdate  # noqa: F401 (monkeypatch compat)
from app.services.reviewer_service import ReviewerService, ReviewPolicyService  # noqa: F401 (monkeypatch compat)
from app.services.matchmaking_service import MatchmakingService  # noqa: F401 (monkeypatch compat)
from app.services.editor_service import EditorService, ProcessListFilters, FinanceListFilters
import app.services.editor_service as editor_service_module
from app.services.decision_service import DecisionService
from app.models.decision import DecisionSubmitRequest
from app.models.production_workspace import CreateProductionCycleRequest, UpdateProductionCycleEditorsRequest
from app.services.production_workspace_service import ProductionWorkspaceService
from typing import Any, Literal
from io import BytesIO
from uuid import uuid4
from time import perf_counter
from app.models.internal_task import InternalTaskStatus
from app.api.v1.editor_internal_collaboration import router as internal_collab_router
from app.api.v1.editor_production import router as production_router
from app.api.v1.editor_detail import router as editor_detail_router
from app.api.v1.editor_precheck import router as editor_precheck_router
from app.api.v1.editor_finance import router as editor_finance_router
from app.api.v1.editor_reviewer_library import router as editor_reviewer_library_router
from app.api.v1.editor_common import (
    AcademicCheckRequest,
    AssignAERequest,
    ConfirmInvoicePaidPayload,
    IntakeRevisionRequest,
    InvoiceInfoUpdatePayload,
    QuickPrecheckPayload,
    TechnicalCheckRequest,
    auth_user_exists as _auth_user_exists,
    ensure_bucket_exists as _ensure_bucket_exists,
    get_signed_url as _get_signed_url,
    is_missing_table_error as _is_missing_table_error,
    list_auth_user_id_set as _list_auth_user_id_set,
    require_action_or_403 as _require_action_or_403,
)
from app.api.v1.editor_heavy_handlers import (
    get_available_reviewers_impl,
    get_editor_pipeline_impl,
    publish_manuscript_dev_impl,
    request_revision_impl,
    search_reviewer_library_impl,  # noqa: F401 (monkeypatch compat)
    submit_final_decision_impl,
)

router = APIRouter(prefix="/editor", tags=["Editor Command Center"])
INTERNAL_COLLAB_ALLOWED_ROLES = ["admin", "managing_editor", "assistant_editor", "production_editor", "editor_in_chief", "owner"]
EDITOR_SCOPE_COMPAT_ROLES = ["admin", "managing_editor", "assistant_editor", "production_editor", "editor_in_chief"]
EDITOR_DECISION_ROLES = ["admin", "managing_editor", "assistant_editor", "editor_in_chief"]
_RBAC_CONTEXT_CACHE_TTL_SEC = 30.0
_PROCESS_ROWS_CACHE_TTL_SEC = 8.0
_rbac_context_cache = ShortTTLCache[dict[str, Any]](max_entries=1024)
_process_rows_cache = ShortTTLCache[dict[str, Any]](max_entries=1024)


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


def _extract_supabase_data(response):
    """兼容不同 Supabase SDK execute() 返回值形态。"""
    if response is None:
        return None
    data = getattr(response, "data", None)
    if data is not None:
        return data
    if isinstance(response, tuple) and len(response) == 2:
        return response[1]
    return None
def _extract_supabase_error(response):
    """兼容不同版本的 Supabase 错误字段。"""
    if response is None:
        return None
    error = getattr(response, "error", None)
    if error:
        return error
    if isinstance(response, tuple) and len(response) == 2:
        return response[0]
    return None


def _is_missing_column_error(error_text: str) -> bool:
    if not error_text:
        return False
    lowered = error_text.lower()
    return (
        "column" in lowered
        or "published_at" in lowered
        or "final_pdf_path" in lowered
        or "reject_comment" in lowered
        or "doi" in lowered
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


@router.post("/manuscripts/{id}/files/review-attachment", status_code=201)
async def upload_editor_review_attachment(
    id: str,
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
    _profile: dict = Depends(require_any_role(["managing_editor", "admin"])),
):
    """
    Feature 033: Editor/Admin 上传 Peer Review Files（仅内部可见）。

    中文注释:
    - 文件上传至私有桶 `review-attachments`（Author 不可见）。
    - 元数据写入 `public.manuscript_files`（file_type=review_attachment）。
    """
    filename = (file.filename or "review_attachment").strip()
    lowered = filename.lower()
    if not (lowered.endswith(".pdf") or lowered.endswith(".doc") or lowered.endswith(".docx")):
        raise HTTPException(status_code=400, detail="Only .pdf/.doc/.docx are supported")

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Empty file")
    if len(file_bytes) > 25 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large (max 25MB)")

    safe_name = filename.replace("/", "_")
    object_path = f"editor_review_files/{id}/{uuid4()}_{safe_name}"
    try:
        _ensure_bucket_exists("review-attachments", public=False)
        supabase_admin.storage.from_("review-attachments").upload(
            object_path,
            file_bytes,
            {"content-type": file.content_type or "application/octet-stream"},
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"[EditorReviewAttachment] upload failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to upload review attachment")

    try:
        ins = (
            supabase_admin.table("manuscript_files")
            .insert(
                {
                    "manuscript_id": id,
                    "file_type": "review_attachment",
                    "bucket": "review-attachments",
                    "path": object_path,
                    "original_filename": filename,
                    "content_type": file.content_type,
                    "uploaded_by": str(current_user.get("id") or ""),
                }
            )
            .execute()
        )
        row = (getattr(ins, "data", None) or [None])[0] or None
    except Exception as e:
        # 云端未迁移时给出明确提示，便于 Dashboard SQL Editor 快速执行 migration
        if _is_missing_table_error(str(e)):
            raise HTTPException(status_code=500, detail="DB not migrated: manuscript_files table missing")
        print(f"[EditorReviewAttachment] insert manuscript_files failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to persist file metadata")

    return {
        "success": True,
        "data": {
            "id": (row or {}).get("id"),
            "file_type": "review_attachment",
            "bucket": "review-attachments",
            "path": object_path,
            "signed_url": _get_signed_url("review-attachments", object_path),
        },
    }


@router.post("/manuscripts/{id}/files/cover-letter", status_code=201)
async def upload_editor_cover_letter(
    id: str,
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
    profile: dict = Depends(require_any_role(["managing_editor", "admin"])),
):
    """
    补传/更新 Cover Letter（内部编辑入口）。

    中文注释:
    - Cover Letter 在 MVP 仍然是可选项；
    - 当作者初始未上传时，ME/Admin 可在稿件详情页补传。
    """
    roles = profile.get("roles") or []
    ensure_manuscript_scope_access(
        manuscript_id=id,
        user_id=str(current_user.get("id") or ""),
        roles=roles,
        allow_admin_bypass=True,
    )

    filename = (file.filename or "cover_letter").strip()
    lowered = filename.lower()
    if not (lowered.endswith(".pdf") or lowered.endswith(".doc") or lowered.endswith(".docx")):
        raise HTTPException(status_code=400, detail="Only .pdf/.doc/.docx are supported")

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Empty file")
    if len(file_bytes) > 25 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large (max 25MB)")

    uploader_id = str(current_user.get("id") or "").strip() or "editor"
    safe_name = filename.replace("/", "_")
    object_path = f"{uploader_id}/cover-letters/{id}/{uuid4()}_{safe_name}"
    try:
        _ensure_bucket_exists("manuscripts", public=False)
        supabase_admin.storage.from_("manuscripts").upload(
            object_path,
            file_bytes,
            {"content-type": file.content_type or "application/octet-stream"},
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"[EditorCoverLetter] upload failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to upload cover letter")

    try:
        ins = (
            supabase_admin.table("manuscript_files")
            .insert(
                {
                    "manuscript_id": id,
                    "file_type": "cover_letter",
                    "bucket": "manuscripts",
                    "path": object_path,
                    "original_filename": filename,
                    "content_type": file.content_type,
                    "uploaded_by": uploader_id,
                }
            )
            .execute()
        )
        row = (getattr(ins, "data", None) or [None])[0] or None
    except Exception as e:
        if _is_missing_table_error(str(e)):
            raise HTTPException(status_code=500, detail="DB not migrated: manuscript_files table missing")
        print(f"[EditorCoverLetter] insert manuscript_files failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to persist cover letter metadata")

    return {
        "success": True,
        "data": {
            "id": (row or {}).get("id"),
            "file_type": "cover_letter",
            "bucket": "manuscripts",
            "path": object_path,
            "signed_url": _get_signed_url("manuscripts", object_path),
        },
    }


@router.patch("/manuscripts/{id}/status")
async def patch_manuscript_status(
    id: str,
    payload: dict = Body(...),
    current_user: dict = Depends(get_current_user),
    profile: dict = Depends(require_any_role(["managing_editor", "admin"])),
):
    """
    Feature 028 / US2: 更新稿件生命周期状态，并写入 transition log。
    """
    to_status = str(payload.get("status") or "")
    comment = payload.get("comment")
    allow_skip = "admin" in (profile.get("roles") or [])

    # Feature 031：Published 必须走显式门禁（Payment/Production Gate）。
    # 中文注释：避免通过通用 patch 接口“绕过门禁”直接把稿件置为 published。
    if (to_status or "").strip().lower() == "published" and not allow_skip:
        raise HTTPException(
            status_code=400,
            detail="Publishing requires gates. Use /api/v1/editor/manuscripts/{id}/production/advance or /api/v1/editor/publish.",
        )

    # 中文注释：
    # - ME 在详情页可手动把 pre_check 推进到 under_review；
    # - 但未分配 AE 会导致稿件离开 Intake 后无人跟进，属于危险流转。
    # - 这里做服务端硬门禁，避免任何前端入口绕过检查。
    target_status = (to_status or "").strip().lower()
    if target_status == "under_review":
        try:
            ms_resp = (
                supabase_admin.table("manuscripts")
                .select("id,status,assistant_editor_id")
                .eq("id", id)
                .single()
                .execute()
            )
            ms_row = getattr(ms_resp, "data", None) or {}
        except Exception:
            ms_row = {}
        source_status = normalize_status(str(ms_row.get("status") or ""))
        assigned_ae = str(ms_row.get("assistant_editor_id") or "").strip()
        if source_status == ManuscriptStatus.PRE_CHECK.value and not assigned_ae:
            raise HTTPException(
                status_code=409,
                detail="Assistant Editor must be assigned before moving to under_review.",
            )

    updated = EditorialService().update_status(
        manuscript_id=id,
        to_status=to_status,
        changed_by=str(current_user.get("id")),
        comment=str(comment) if comment is not None else None,
        allow_skip=bool(allow_skip),
    )
    return {"success": True, "data": updated}


@router.put("/manuscripts/{id}/invoice-info")
async def put_manuscript_invoice_info(
    id: str,
    payload: InvoiceInfoUpdatePayload,
    current_user: dict = Depends(get_current_user),
    profile: dict = Depends(require_any_role(EDITOR_SCOPE_COMPAT_ROLES)),
):
    """
    Feature 028 / US2: 更新 manuscripts.invoice_metadata。
    """
    roles = profile.get("roles") or []
    if not (
        can_perform_action(action="invoice:update_info", roles=roles)
        or can_perform_action(action="invoice:override_apc", roles=roles)
    ):
        raise HTTPException(status_code=403, detail="Insufficient permission for action: invoice:update_info")

    ensure_manuscript_scope_access(
        manuscript_id=id,
        user_id=str(current_user.get("id") or ""),
        roles=roles,
        allow_admin_bypass=True,
    )

    updated = EditorialService().update_invoice_info(
        manuscript_id=id,
        authors=payload.authors,
        affiliation=payload.affiliation,
        apc_amount=payload.apc_amount,
        funding_info=payload.funding_info,
        changed_by=str(current_user.get("id")),
        reason=payload.reason,
        source=payload.source or "editor_manuscript_detail",
    )
    return {"success": True, "data": updated}


@router.post("/manuscripts/{id}/bind-owner")
async def bind_internal_owner(
    id: str,
    owner_id: str = Body(..., embed=True),
    current_user: dict = Depends(get_current_user),
    profile: dict = Depends(require_any_role(EDITOR_SCOPE_COMPAT_ROLES)),
):
    """
    Feature 028 / US3: 绑定 Internal Owner（仅 managing_editor/admin 可操作）。

    显性逻辑：owner_id 必须属于内部员工（managing_editor/admin）。
    """
    _require_action_or_403(action="manuscript:bind_owner", roles=profile.get("roles") or [])
    ensure_manuscript_scope_access(
        manuscript_id=id,
        user_id=str(current_user.get("id") or ""),
        roles=profile.get("roles") or [],
        allow_admin_bypass=True,
    )

    try:
        validate_internal_owner_id(UUID(owner_id))
    except Exception:
        raise HTTPException(status_code=422, detail="owner_id must be managing_editor/admin")

    before_owner_id: str | None = None
    before_status: str | None = None
    try:
        before_resp = (
            supabase_admin.table("manuscripts")
            .select("id,owner_id,status")
            .eq("id", id)
            .single()
            .execute()
        )
        before_row = getattr(before_resp, "data", None) or {}
        before_owner_id = str(before_row.get("owner_id") or "").strip() or None
        before_status = str(before_row.get("status") or "").strip() or None
    except Exception:
        before_owner_id = None
        before_status = None

    now = datetime.now(timezone.utc).isoformat()
    try:
        resp = (
            supabase_admin.table("manuscripts")
            .update({"owner_id": owner_id, "updated_at": now})
            .eq("id", id)
            .execute()
        )
        rows = getattr(resp, "data", None) or []
        if not rows:
            raise HTTPException(status_code=404, detail="Manuscript not found")
        updated = rows[0]
    except HTTPException:
        raise
    except Exception as e:
        print(f"[OwnerBinding] bind owner failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to bind owner")

    # 写入 transition log（若云端未跑迁移则忽略）
    try:
        supabase_admin.table("status_transition_logs").insert(
            {
                "manuscript_id": str(id),
                "from_status": str(before_status or updated.get("status") or ""),
                "to_status": str(updated.get("status") or before_status or ""),
                "comment": f"owner bound: {owner_id}",
                "changed_by": str(current_user.get("id")),
                "created_at": now,
                "payload": {
                    "action": "bind_owner",
                    "source": "editor_manuscript_detail",
                    "reason": "manual_owner_binding",
                    "before": {"owner_id": before_owner_id},
                    "after": {"owner_id": str(owner_id)},
                },
            }
        ).execute()
    except Exception:
        pass
    return {"success": True, "data": updated}


@router.get("/internal-staff")
async def list_internal_staff(
    search: str = Query("", description="按姓名/邮箱模糊检索（可选）"),
    exclude_current_user: bool = Query(False, description="是否排除当前用户（用于 mention 候选）"),
    current_user: dict = Depends(get_current_user),
    _profile: dict = Depends(require_any_role(INTERNAL_COLLAB_ALLOWED_ROLES)),
):
    """
    Feature 023: 提供 Internal Owner 下拉框的数据源（仅 managing_editor/admin）。
    """
    try:
        query = (
            supabase_admin.table("user_profiles")
            .select("id, email, full_name, roles")
            .or_(
                "roles.cs.{admin},roles.cs.{assistant_editor},roles.cs.{production_editor},roles.cs.{managing_editor},roles.cs.{editor_in_chief},roles.cs.{owner}"
            )
        )
        resp = query.execute()
        data = getattr(resp, "data", None) or []
        # 只保留真实存在于 auth.users 的账号，避免后续写入外键表时报 23503。
        auth_user_ids = _list_auth_user_id_set()
        if auth_user_ids:
            data = [row for row in data if str(row.get("id") or "") in auth_user_ids]
        else:
            # SDK 返回异常时兜底逐个校验，避免把 mock profile 放进候选。
            verified: list[dict[str, Any]] = []
            for row in data:
                uid = str(row.get("id") or "")
                if uid and _auth_user_exists(uid):
                    verified.append(row)
            data = verified

        if exclude_current_user:
            my_id = str(current_user.get("id") or "")
            if my_id:
                data = [row for row in data if str(row.get("id") or "") != my_id]

        if search.strip():
            s = search.strip().lower()
            data = [
                row
                for row in data
                if s in (row.get("email") or "").lower() or s in (row.get("full_name") or "").lower()
            ]
        # 中文注释: 置顶有 full_name 的记录，便于下拉框展示
        data.sort(key=lambda x: (0 if (x.get("full_name") or "").strip() else 1, (x.get("full_name") or x.get("email") or "")))
        return {"success": True, "data": data}
    except Exception as e:
        print(f"[OwnerBinding] 获取内部员工列表失败: {e}")
        raise HTTPException(status_code=500, detail="Failed to load internal staff")


@router.get("/assistant-editors")
async def list_assistant_editors(
    search: str = Query("", description="按姓名/邮箱模糊检索（可选）"),
    _profile: dict = Depends(require_any_role(["managing_editor", "admin"])),
):
    """
    044: 提供 ME 分派 AE 的候选列表（assistant_editor + admin）。
    """
    try:
        query = (
            supabase_admin.table("user_profiles")
            .select("id, email, full_name, roles")
            .or_("roles.cs.{assistant_editor},roles.cs.{admin}")
        )
        resp = query.execute()
        data = getattr(resp, "data", None) or []
        if search.strip():
            s = search.strip().lower()
            data = [
                row
                for row in data
                if s in (row.get("email") or "").lower() or s in (row.get("full_name") or "").lower()
            ]
        data.sort(key=lambda x: (0 if (x.get("full_name") or "").strip() else 1, (x.get("full_name") or x.get("email") or "")))
        return {"success": True, "data": data}
    except Exception as e:
        print(f"[Precheck] 获取 assistant editors 失败: {e}")
        raise HTTPException(status_code=500, detail="Failed to load assistant editors")


@router.get("/journals")
async def list_journals(
    _profile: dict = Depends(require_any_role(["managing_editor", "admin"])),
):
    """
    Feature 028: ProcessFilterBar 数据源（期刊下拉框）。
    """
    try:
        try:
            resp = (
                supabase_admin.table("journals")
                .select("id,title,slug,is_active")
                .eq("is_active", True)
                .order("title", desc=False)
                .execute()
            )
            rows = getattr(resp, "data", None) or []
        except Exception as e:
            lowered = str(e).lower()
            if "is_active" in lowered and "does not exist" in lowered:
                fallback = (
                    supabase_admin.table("journals")
                    .select("id,title,slug")
                    .order("title", desc=False)
                    .execute()
                )
                rows = getattr(fallback, "data", None) or []
            else:
                raise
        return {"success": True, "data": rows}
    except Exception as e:
        print(f"[Journals] list failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to load journals")


@router.get("/pipeline")
async def get_editor_pipeline(
    current_user: dict = Depends(get_current_user),
    _profile: dict = Depends(require_any_role(["managing_editor", "admin"])),
):
    """
    获取全站稿件流转状态看板数据
    分栏：待质检、评审中、待录用、已发布
    """
    return await get_editor_pipeline_impl(
        supabase_admin_client=supabase_admin,
        extract_data_fn=_extract_supabase_data,
    )


@router.post("/revisions", response_model=RevisionRequestResponse)
async def request_revision(
    request: RevisionCreate,
    current_user: dict = Depends(get_current_user),
    profile: dict = Depends(require_any_role(["managing_editor", "admin"])),
    background_tasks: BackgroundTasks = None,
):
    """
    Editor 请求修订 (Request Revision)

    中文注释:
    1. 只能由 Editor 或 Admin 发起。
    2. 调用 RevisionService 处理核心逻辑（创建快照、更新状态）。
    3. 触发通知给作者。
    """
    result = await request_revision_impl(
        request=request,
        profile=profile,
        background_tasks=background_tasks,
        supabase_admin_client=supabase_admin,
    )
    return RevisionRequestResponse(data=result["data"]["revision"])


@router.get("/available-reviewers")
async def get_available_reviewers(
    current_user: dict = Depends(get_current_user),
    _profile: dict = Depends(require_any_role(["managing_editor", "admin"])),
):
    """
    获取可用的审稿人专家池
    """
    return await get_available_reviewers_impl(
        current_user=current_user,
        supabase_client=supabase,
        extract_data_fn=_extract_supabase_data,
    )


@router.get("/manuscripts/{id}/decision-context")
async def get_decision_workspace_context(
    id: str,
    current_user: dict = Depends(get_current_user),
    profile: dict = Depends(require_any_role(EDITOR_DECISION_ROLES)),
):
    """
    Feature 041: 获取决策工作台聚合上下文。
    """
    decision_roles = profile.get("roles") or []
    can_record_first = can_perform_action(action="decision:record_first", roles=decision_roles)
    can_submit_final = can_perform_action(action="decision:submit_final", roles=decision_roles)
    if not (can_record_first or can_submit_final):
        _require_action_or_403(action="decision:record_first", roles=decision_roles)

    data = DecisionService().get_decision_context(
        manuscript_id=id,
        user_id=str(current_user.get("id") or ""),
        profile_roles=decision_roles,
    )
    return {"success": True, "data": data}


@router.post("/manuscripts/{id}/submit-decision")
async def submit_decision_workspace(
    id: str,
    payload: DecisionSubmitRequest,
    current_user: dict = Depends(get_current_user),
    profile: dict = Depends(require_any_role(EDITOR_DECISION_ROLES)),
):
    """
    Feature 041: 保存草稿或提交最终决策。
    """
    decision_roles = profile.get("roles") or []
    if payload.is_final:
        _require_action_or_403(action="decision:submit_final", roles=decision_roles)
    else:
        can_record_first = can_perform_action(action="decision:record_first", roles=decision_roles)
        can_submit_final = can_perform_action(action="decision:submit_final", roles=decision_roles)
        if not (can_record_first or can_submit_final):
            _require_action_or_403(action="decision:record_first", roles=decision_roles)

    data = DecisionService().submit_decision(
        manuscript_id=id,
        user_id=str(current_user.get("id") or ""),
        profile_roles=decision_roles,
        request=payload,
    )
    return {"success": True, "data": data}


@router.post("/manuscripts/{id}/decision-attachments")
async def upload_decision_attachment(
    id: str,
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
    profile: dict = Depends(require_any_role(EDITOR_DECISION_ROLES)),
):
    """
    Feature 041: 决策信附件上传（编辑态）。
    """
    _require_action_or_403(action="decision:record_first", roles=profile.get("roles") or [])

    raw = await file.read()
    data = DecisionService().upload_attachment(
        manuscript_id=id,
        user_id=str(current_user.get("id") or ""),
        profile_roles=profile.get("roles") or [],
        filename=file.filename or "decision-attachment",
        content=raw,
        content_type=file.content_type,
    )
    return {"success": True, "data": data}


@router.get("/manuscripts/{id}/decision-attachments/{attachment_id}/signed-url")
async def get_decision_attachment_signed_url_editor(
    id: str,
    attachment_id: str,
    current_user: dict = Depends(get_current_user),
    profile: dict = Depends(require_any_role(EDITOR_DECISION_ROLES)),
):
    """
    Feature 041: 编辑端获取决策附件 signed URL。
    """
    _require_action_or_403(action="decision:record_first", roles=profile.get("roles") or [])

    signed_url = DecisionService().get_attachment_signed_url_for_editor(
        manuscript_id=id,
        attachment_id=attachment_id,
        user_id=str(current_user.get("id") or ""),
        profile_roles=profile.get("roles") or [],
    )
    return {"success": True, "data": {"signed_url": signed_url}}


@router.post("/decision")
async def submit_final_decision(
    background_tasks: BackgroundTasks = None,
    current_user: dict = Depends(get_current_user),
    profile: dict = Depends(require_any_role(EDITOR_DECISION_ROLES)),
    manuscript_id: str = Body(..., embed=True),
    decision: str = Body(..., embed=True),
    comment: str = Body("", embed=True),
    apc_amount: float | None = Body(None, embed=True),
):
    """
    提交最终录用或退回决策
    decision: "accept" | "reject"
    """
    return await submit_final_decision_impl(
        background_tasks=background_tasks,
        current_user=current_user,
        profile=profile,
        manuscript_id=manuscript_id,
        decision=decision,
        comment=comment,
        apc_amount=apc_amount,
        supabase_admin_client=supabase_admin,
        extract_error_fn=_extract_supabase_error,
        extract_data_fn=_extract_supabase_data,
        is_missing_column_error_fn=_is_missing_column_error,
        require_action_or_403_fn=_require_action_or_403,
        ensure_manuscript_scope_access_fn=ensure_manuscript_scope_access,
    )


@router.post("/publish")
async def publish_manuscript_dev(
    current_user: dict = Depends(get_current_user),
    _profile: dict = Depends(require_any_role(["managing_editor", "admin"])),
    manuscript_id: str = Body(..., embed=True),
    background_tasks: BackgroundTasks = None,
):
    """
    Feature 024: 发布（Post-Acceptance Pipeline）

    中文注释:
    - 仍然需要 managing_editor/admin 角色，避免普通作者误操作。
    - 门禁显性化：Payment Gate + Production Gate（final_pdf_path）。
    """
    return await publish_manuscript_dev_impl(
        background_tasks=background_tasks,
        current_user=current_user,
        manuscript_id=manuscript_id,
        supabase_admin_client=supabase_admin,
        publish_manuscript_fn=publish_manuscript,
    )


# 测试端点 - 不需要身份验证
@router.get("/test/pipeline")
async def get_editor_pipeline_test():
    """
    测试端点：获取全站稿件流转状态看板数据（无需身份验证）
    """
    try:
        # Mock数据用于测试
        return {
            "success": True,
            "data": {
                "pending_quality": [
                    {"id": "1", "title": "Test Manuscript 1", "status": "pre_check"}
                ],
                "under_review": [
                    {"id": "2", "title": "Test Manuscript 2", "status": "under_review"}
                ],
                "pending_decision": [
                    {
                        "id": "3",
                        "title": "Test Manuscript 3",
                        "status": "decision",
                    }
                ],
                "published": [
                    {"id": "4", "title": "Test Manuscript 4", "status": "published"}
                ],
            },
        }

    except Exception as e:
        print(f"Pipeline query failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch pipeline data")


@router.get("/test/available-reviewers")
async def get_available_reviewers_test():
    """
    测试端点：获取可用的审稿人专家池（无需身份验证）
    """
    try:
        # Mock数据用于测试
        return {
            "success": True,
            "data": [
                {
                    "id": "1",
                    "name": "Dr. Jane Smith",
                    "email": "jane.smith@example.com",
                    "affiliation": "MIT",
                    "expertise": ["AI", "Machine Learning"],
                    "review_count": 15,
                },
                {
                    "id": "2",
                    "name": "Prof. John Doe",
                    "email": "john.doe@example.com",
                    "affiliation": "Stanford University",
                    "expertise": ["Computer Science", "Data Science"],
                    "review_count": 20,
                },
            ],
        }

    except Exception as e:
        print(f"Reviewers query failed: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to fetch available reviewers"
        )


@router.post("/test/decision")
async def submit_final_decision_test(
    manuscript_id: str = Body(..., embed=True),
    decision: str = Body(..., embed=True),
    comment: str = Body("", embed=True),
):
    """
    测试端点：提交最终录用或退回决策（无需身份验证）
    decision: "accept" | "reject"
    """
    # 验证决策类型
    if decision not in ["accept", "reject"]:
        raise HTTPException(status_code=400, detail="Invalid decision type")

    # Mock响应
    if decision == "accept":
        status = "published"
    else:
        status = "rejected"

    return {
        "success": True,
        "message": "Decision submitted successfully",
        "data": {
            "manuscript_id": manuscript_id,
            "decision": decision,
            "status": status,
        },
    }


# 中文注释:
# - 把子路由挂载放在文件末尾，确保 `/manuscripts/process` 等静态路径优先注册。
# - 避免 `/manuscripts/{id}` 抢占匹配 `process` 导致 404（被当成 manuscript id）。
router.include_router(internal_collab_router)
router.include_router(production_router)
router.include_router(editor_precheck_router)
router.include_router(editor_finance_router)
router.include_router(editor_reviewer_library_router)
router.include_router(editor_detail_router)
