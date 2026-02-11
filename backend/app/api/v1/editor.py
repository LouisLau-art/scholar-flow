from fastapi import APIRouter, HTTPException, Body, Depends, BackgroundTasks, Query, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from app.lib.api_client import supabase, supabase_admin
from app.core.auth_utils import get_current_user
from app.core.roles import require_any_role
from app.core.journal_scope import (
    ensure_manuscript_scope_access,
    get_user_scope_journal_ids,
    is_scope_enforcement_enabled,
)
from app.core.role_matrix import can_perform_action, list_allowed_actions, normalize_roles
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
from app.schemas.reviewer import ReviewerCreate, ReviewerUpdate
from app.services.reviewer_service import ReviewerService, ReviewPolicyService
from app.services.editor_service import EditorService, ProcessListFilters, FinanceListFilters
from app.services.decision_service import DecisionService
from app.models.decision import DecisionSubmitRequest
from app.models.production_workspace import CreateProductionCycleRequest
from app.services.production_workspace_service import ProductionWorkspaceService
from typing import Any, Literal
from io import BytesIO
from uuid import uuid4
from time import perf_counter
from app.models.internal_task import InternalTaskPriority, InternalTaskStatus
from app.api.v1.editor_common import (
    AcademicCheckRequest,
    AssignAERequest,
    ConfirmInvoicePaidPayload,
    IntakeRevisionRequest,
    InternalCommentPayload,
    InternalTaskCreatePayload,
    InternalTaskUpdatePayload,
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
from app.services.internal_collaboration_service import (
    InternalCollaborationService,
    InternalCollaborationSchemaMissingError,
    MentionValidationError,
)
from app.services.internal_task_service import InternalTaskSchemaMissingError, InternalTaskService

router = APIRouter(prefix="/editor", tags=["Editor Command Center"])
INTERNAL_COLLAB_ALLOWED_ROLES = ["admin", "managing_editor", "assistant_editor", "editor_in_chief"]
EDITOR_SCOPE_COMPAT_ROLES = ["admin", "managing_editor", "assistant_editor", "editor_in_chief"]
EDITOR_DECISION_ROLES = ["admin", "managing_editor", "editor_in_chief"]

@router.get("/manuscripts/{id}/comments")
async def get_internal_comments(
    id: str,
    _profile: dict = Depends(require_any_role(INTERNAL_COLLAB_ALLOWED_ROLES)),
):
    """
    Feature 036: Fetch internal notebook comments (Staff only).
    """
    svc = InternalCollaborationService()
    try:
        return {"success": True, "data": svc.list_comments(id)}
    except InternalCollaborationSchemaMissingError as e:
        if e.table == "internal_comments":
            return {"success": True, "data": []}
        raise HTTPException(status_code=500, detail=f"DB not migrated: {e.table} table missing")
    except Exception as e:
        if _is_missing_table_error(e):
            return {"success": True, "data": []}
        print(f"[InternalComments] list failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch comments")


@router.post("/manuscripts/{id}/comments")
async def create_internal_comment(
    id: str,
    payload: InternalCommentPayload,
    current_user: dict = Depends(get_current_user),
    _profile: dict = Depends(require_any_role(INTERNAL_COLLAB_ALLOWED_ROLES)),
):
    """
    Feature 036: Post internal comment.
    """
    svc = InternalCollaborationService()
    try:
        comment = svc.create_comment(
            manuscript_id=id,
            author_user_id=str(current_user.get("id")),
            content=payload.content,
            mention_user_ids=payload.mention_user_ids,
        )
        return {"success": True, "data": comment}
    except MentionValidationError as e:
        raise HTTPException(
            status_code=422,
            detail={
                "message": "Invalid mention_user_ids",
                "invalid_user_ids": e.invalid_user_ids,
            },
        )
    except InternalCollaborationSchemaMissingError as e:
        raise HTTPException(status_code=500, detail=f"DB not migrated: {e.table} table missing")
    except HTTPException:
        raise
    except Exception as e:
        print(f"[InternalComments] create failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to post comment")


@router.get("/manuscripts/{id}/tasks")
async def list_internal_tasks(
    id: str,
    status: InternalTaskStatus | None = Query(None, description="任务状态筛选"),
    overdue_only: bool = Query(False, description="仅返回逾期任务"),
    current_user: dict = Depends(get_current_user),
    profile: dict = Depends(require_any_role(INTERNAL_COLLAB_ALLOWED_ROLES)),
):
    svc = InternalTaskService()
    try:
        rows = svc.list_tasks(
            manuscript_id=id,
            actor_user_id=str(current_user.get("id") or ""),
            actor_roles=profile.get("roles") or [],
            status=status,
            overdue_only=bool(overdue_only),
        )
        return {"success": True, "data": rows}
    except InternalTaskSchemaMissingError as e:
        raise HTTPException(status_code=500, detail=f"DB not migrated: {e.table} table missing")
    except HTTPException:
        raise
    except Exception as e:
        print(f"[InternalTasks] list failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch internal tasks")


@router.post("/manuscripts/{id}/tasks")
async def create_internal_task(
    id: str,
    payload: InternalTaskCreatePayload,
    current_user: dict = Depends(get_current_user),
    profile: dict = Depends(require_any_role(INTERNAL_COLLAB_ALLOWED_ROLES)),
):
    svc = InternalTaskService()
    try:
        task = svc.create_task(
            manuscript_id=id,
            actor_user_id=str(current_user.get("id") or ""),
            actor_roles=profile.get("roles") or [],
            title=payload.title,
            description=payload.description,
            assignee_user_id=payload.assignee_user_id,
            due_at=payload.due_at,
            status=payload.status,
            priority=payload.priority,
        )
        return {"success": True, "data": task}
    except InternalTaskSchemaMissingError as e:
        raise HTTPException(status_code=500, detail=f"DB not migrated: {e.table} table missing")
    except HTTPException:
        raise
    except Exception as e:
        print(f"[InternalTasks] create failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to create internal task")


@router.patch("/manuscripts/{id}/tasks/{task_id}")
async def patch_internal_task(
    id: str,
    task_id: str,
    payload: InternalTaskUpdatePayload,
    current_user: dict = Depends(get_current_user),
    profile: dict = Depends(require_any_role(INTERNAL_COLLAB_ALLOWED_ROLES)),
):
    svc = InternalTaskService()
    try:
        task = svc.update_task(
            manuscript_id=id,
            task_id=task_id,
            actor_user_id=str(current_user.get("id") or ""),
            actor_roles=profile.get("roles") or [],
            title=payload.title,
            description=payload.description,
            assignee_user_id=payload.assignee_user_id,
            status=payload.status,
            priority=payload.priority,
            due_at=payload.due_at,
        )
        return {"success": True, "data": task}
    except InternalTaskSchemaMissingError as e:
        raise HTTPException(status_code=500, detail=f"DB not migrated: {e.table} table missing")
    except HTTPException:
        raise
    except Exception as e:
        print(f"[InternalTasks] patch failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to update internal task")


@router.get("/manuscripts/{id}/tasks/{task_id}/activity")
async def get_internal_task_activity(
    id: str,
    task_id: str,
    _profile: dict = Depends(require_any_role(INTERNAL_COLLAB_ALLOWED_ROLES)),
):
    svc = InternalTaskService()
    try:
        rows = svc.list_activity(manuscript_id=id, task_id=task_id)
        return {"success": True, "data": rows}
    except InternalTaskSchemaMissingError as e:
        raise HTTPException(status_code=500, detail=f"DB not migrated: {e.table} table missing")
    except HTTPException:
        raise
    except Exception as e:
        print(f"[InternalTasks] activity failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch task activity")


@router.get("/manuscripts/{id}/audit-logs")
async def get_audit_logs(
    id: str,
    _profile: dict = Depends(require_any_role(INTERNAL_COLLAB_ALLOWED_ROLES)),
):
    """
    Feature 036: Fetch status transition logs.
    """
    try:
        resp = (
            supabase_admin.table("status_transition_logs")
            .select("*, changed_by")
            .eq("manuscript_id", id)
            .order("created_at", desc=True)
            .execute()
        )
        logs = getattr(resp, "data", None) or []
        
        # Populate user info
        user_ids = sorted(list(set(l["changed_by"] for l in logs if l.get("changed_by"))))
        users_map = {}
        if user_ids:
            try:
                u_resp = (
                    supabase_admin.table("user_profiles")
                    .select("id, full_name, email")
                    .in_("id", user_ids)
                    .execute()
                )
                for u in (getattr(u_resp, "data", None) or []):
                    users_map[u["id"]] = u
            except Exception:
                pass
                
        for l in logs:
            uid = l.get("changed_by")
            l["user"] = users_map.get(uid) or {"full_name": "System/Unknown", "email": ""}
            
        return {"success": True, "data": logs}
    except Exception as e:
        print(f"[AuditLogs] fetch failed: {e}")
        # Allow fail-open if table missing (though it should exist from Feature 028)
        if "does not exist" in str(e):
             return {"success": True, "data": []}
        raise HTTPException(status_code=500, detail="Failed to fetch audit logs")


def _extract_supabase_data(response):
    """
    兼容 supabase-py / postgrest 在不同版本下的 execute() 返回值形态。
    - 新版: response.data
    - 旧/自定义 mock: (error, data)
    """
    if response is None:
        return None
    data = getattr(response, "data", None)
    if data is not None:
        return data
    if isinstance(response, tuple) and len(response) == 2:
        return response[1]
    return None


def _extract_supabase_error(response):
    """
    兼容不同版本的 supabase-py 错误字段。
    """
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
    current_user: dict = Depends(get_current_user),
    profile: dict = Depends(require_any_role(EDITOR_SCOPE_COMPAT_ROLES)),
):
    """
    GAP-P1-05: 返回当前用户的 RBAC 能力与 journal-scope 上下文（前端显隐使用）。
    """
    raw_roles = profile.get("roles") or []
    normalized_roles = sorted(normalize_roles(raw_roles))
    actions = sorted(list_allowed_actions(raw_roles))
    is_admin = "admin" in normalized_roles
    has_strict_scope_role = bool({"managing_editor", "editor_in_chief"} & set(normalized_roles))
    enforcement_enabled = bool(is_scope_enforcement_enabled() or has_strict_scope_role)

    allowed_journal_ids: list[str] = []
    if enforcement_enabled and not is_admin:
        allowed_journal_ids = sorted(
            get_user_scope_journal_ids(
                user_id=str(current_user.get("id") or ""),
                roles=raw_roles,
            )
        )

    return {
        "success": True,
        "data": {
            "user_id": str(current_user.get("id") or ""),
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


@router.get("/manuscripts/process")
async def get_manuscripts_process(
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
            viewer_user_id=str(current_user.get("id") or ""),
            viewer_roles=profile.get("roles") or [],
        )
        return {"success": True, "data": rows}
    except HTTPException:
        raise
    except Exception as e:
        print(f"[Process] query failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch manuscripts process")


@router.get("/finance/invoices")
async def get_finance_invoices(
    status: Literal["all", "unpaid", "paid", "waived"] = Query("all", description="状态筛选"),
    q: str | None = Query(None, max_length=100, description="关键词（invoice number / manuscript title）"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_by: Literal["updated_at", "amount", "status"] = Query("updated_at"),
    sort_order: Literal["asc", "desc"] = Query("desc"),
    _profile: dict = Depends(require_any_role(["managing_editor", "admin"])),
):
    """
    Feature 046: Finance 页面真实账单列表（内部角色）。
    """
    try:
        result = EditorService().list_finance_invoices(
            filters=FinanceListFilters(
                status=status,
                q=q,
                page=page,
                page_size=page_size,
                sort_by=sort_by,
                sort_order=sort_order,
            )
        )
        return {"success": True, "data": result["rows"], "meta": result["meta"]}
    except HTTPException:
        raise
    except Exception as e:
        print(f"[Finance] list invoices failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch finance invoices")


@router.get("/finance/invoices/export")
async def export_finance_invoices_csv(
    status: Literal["all", "unpaid", "paid", "waived"] = Query("all", description="状态筛选"),
    q: str | None = Query(None, max_length=100, description="关键词（invoice number / manuscript title）"),
    sort_by: Literal["updated_at", "amount", "status"] = Query("updated_at"),
    sort_order: Literal["asc", "desc"] = Query("desc"),
    _profile: dict = Depends(require_any_role(["managing_editor", "admin"])),
):
    """
    Feature 046: 导出 Finance 当前筛选结果（CSV）。
    """
    try:
        result = EditorService().export_finance_invoices_csv(
            filters=FinanceListFilters(
                status=status,
                q=q,
                page=1,
                page_size=100,
                sort_by=sort_by,
                sort_order=sort_order,
            )
        )
        csv_text = result.get("csv_text", "")
        snapshot_at = str(result.get("snapshot_at") or datetime.now(timezone.utc).isoformat())
        empty = bool(result.get("empty"))
        filename = f"finance_invoices_{status}_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}.csv"
        headers = {
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Export-Snapshot-At": snapshot_at,
            "X-Export-Empty": "1" if empty else "0",
        }
        return StreamingResponse(
            BytesIO(csv_text.encode("utf-8")),
            media_type="text/csv",
            headers=headers,
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"[Finance] export invoices failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to export finance invoices")


# --- Feature 038: Pre-check Role Workflow Endpoints ---

@router.get("/intake")
async def get_intake_queue(
    page: int = 1,
    page_size: int = 20,
    q: str | None = Query(None, max_length=100),
    overdue_only: bool = Query(False),
    current_user: dict = Depends(get_current_user),
    profile: dict = Depends(require_any_role(["managing_editor", "admin"])),
):
    """
    List manuscripts in Managing Editor Intake Queue.
    Status: pre_check, Sub-status: intake
    """
    try:
        return EditorService().get_intake_queue(
            page,
            page_size,
            q=q,
            overdue_only=overdue_only,
            viewer_user_id=str(current_user.get("id") or ""),
            viewer_roles=profile.get("roles") or [],
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"[Intake] query failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch intake queue")


@router.post("/manuscripts/{id}/assign-ae")
async def assign_ae(
    id: UUID,
    request: AssignAERequest,
    current_user: dict = Depends(get_current_user),
    _profile: dict = Depends(require_any_role(["managing_editor", "admin"])),
):
    """
    Assign an Assistant Editor (AE) to a manuscript.
    Moves manuscript from 'intake' to 'technical'.
    """
    try:
        updated = EditorService().assign_ae(
            id,
            request.ae_id,
            current_user["id"],
            idempotency_key=request.idempotency_key,
        )
        return {"message": "AE assigned successfully", "data": updated}
    except HTTPException:
        raise
    except Exception as e:
        print(f"[AssignAE] failed: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/manuscripts/{id}/intake-return")
async def submit_intake_revision(
    id: UUID,
    request: IntakeRevisionRequest,
    current_user: dict = Depends(get_current_user),
    _profile: dict = Depends(require_any_role(["managing_editor", "admin"])),
    background_tasks: BackgroundTasks = None,
):
    """
    ME Intake technical screening:
    return manuscript to author for revision with mandatory comment.
    """
    try:
        updated = EditorService().request_intake_revision(
            manuscript_id=id,
            current_user_id=current_user["id"],
            comment=request.comment,
            idempotency_key=request.idempotency_key,
        )

        # 中文注释:
        # ME 技术退回属于作者必须感知的关键事件，需同时写站内通知 + 邮件（邮件失败不阻断主流程）。
        try:
            author_id = str(updated.get("author_id") or "").strip()
            manuscript_title = str(updated.get("title") or "Manuscript").strip() or "Manuscript"
            comment_clean = str(request.comment or "").strip()
            if author_id:
                NotificationService().create_notification(
                    user_id=author_id,
                    manuscript_id=str(id),
                    action_url=f"/submit-revision/{id}",
                    type="decision",
                    title="Technical Revision Requested",
                    content=f"Managing Editor requested technical revision for '{manuscript_title}'. Feedback: {comment_clean}",
                )

                if background_tasks:
                    try:
                        prof = (
                            supabase_admin.table("user_profiles")
                            .select("email, full_name")
                            .eq("id", author_id)
                            .single()
                            .execute()
                        )
                        pdata = getattr(prof, "data", None) or {}
                        author_email = pdata.get("email")
                        recipient_name = pdata.get("full_name") or "Author"
                        if author_email:
                            from app.core.mail import email_service

                            background_tasks.add_task(
                                email_service.send_email_background,
                                to_email=author_email,
                                subject="Technical Revision Requested",
                                template_name="status_update.html",
                                context={
                                    "recipient_name": recipient_name,
                                    "manuscript_title": manuscript_title,
                                    "decision_label": "Technical Revision Requested",
                                    "comment": comment_clean or "Please check the portal for details.",
                                },
                            )
                    except Exception as e:
                        print(f"[Email] Failed to send intake-revision email: {e}")
        except Exception as e:
            print(f"[Notifications] Failed to send intake-revision notification: {e}")

        return {"message": "Intake revision submitted", "data": updated}
    except HTTPException:
        raise
    except Exception as e:
        print(f"[IntakeRevision] failed: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/workspace")
async def get_ae_workspace(
    page: int = 1,
    page_size: int = 20,
    current_user: dict = Depends(get_current_user),
    _profile: dict = Depends(require_any_role(["assistant_editor", "admin"])),
):
    """
    List manuscripts in Assistant Editor Workspace (owned by current AE).

    Includes AE work-in-progress states:
    - pre_check(technical)
    - under_review
    - major_revision / minor_revision / resubmitted
    - decision
    """
    try:
        return EditorService().get_ae_workspace(current_user["id"], page, page_size)
    except HTTPException:
        raise
    except Exception as e:
        print(f"[AEWorkspace] query failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch AE workspace")


@router.post("/manuscripts/{id}/submit-check")
async def submit_technical_check(
    id: UUID,
    request: TechnicalCheckRequest,
    current_user: dict = Depends(get_current_user),
    _profile: dict = Depends(require_any_role(["assistant_editor", "admin"])),
):
    """
    Submit technical check.
    - pass: 直接进入 under_review（跳过 Academic Pre-check）
    - academic: 进入 Academic Queue（可选）
    - revision: 技术退回作者
    """
    try:
        updated = EditorService().submit_technical_check(
            id,
            current_user["id"],
            decision=request.decision,
            comment=request.comment,
            idempotency_key=request.idempotency_key,
        )
        return {"message": "Technical check submitted", "data": updated}
    except HTTPException:
        raise
    except Exception as e:
        print(f"[SubmitCheck] failed: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/academic")
async def get_academic_queue(
    page: int = 1,
    page_size: int = 20,
    current_user: dict = Depends(get_current_user),
    profile: dict = Depends(require_any_role(["editor_in_chief", "admin"])),
):
    """
    List manuscripts in Academic Check Queue (EIC).
    Status: pre_check, Sub-status: academic
    """
    try:
        return EditorService().get_academic_queue(
            viewer_user_id=str(current_user.get("id") or ""),
            viewer_roles=profile.get("roles") or [],
            page=page,
            page_size=page_size,
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"[AcademicQueue] query failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch academic queue")


@router.post("/manuscripts/{id}/academic-check")
async def submit_academic_check(
    id: UUID,
    request: AcademicCheckRequest,
    current_user: dict = Depends(get_current_user),
    profile: dict = Depends(require_any_role(["editor_in_chief", "admin"])),
):
    """
    Submit academic check. Routes to Review or Decision Phase.
    """
    try:
        ensure_manuscript_scope_access(
            manuscript_id=str(id),
            user_id=str(current_user.get("id") or ""),
            roles=profile.get("roles") or [],
        )
        updated = EditorService().submit_academic_check(
            id,
            request.decision,
            request.comment,
            changed_by=current_user.get("id"),
            idempotency_key=request.idempotency_key,
        )
        return {"message": "Academic check submitted", "data": updated}
    except HTTPException:
        raise
    except Exception as e:
        print(f"[AcademicCheck] failed: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/manuscripts/{id}/quick-precheck")
async def quick_precheck(
    id: str,
    payload: QuickPrecheckPayload,
    current_user: dict = Depends(get_current_user),
    _profile: dict = Depends(require_any_role(["managing_editor", "admin"])),
):
    """
    032 / US2: 高频“Pre-check”快操作（无需进入详情页）。

    decision 映射：
    - approve  -> under_review
    - revision -> minor_revision
    """
    decision = payload.decision
    comment = (payload.comment or "").strip() or None

    if decision == "revision" and not comment:
        raise HTTPException(status_code=422, detail="comment is required for revision")

    svc = EditorialService()
    ms = svc.get_manuscript(id)
    current_status = normalize_status(str(ms.get("status") or "")) or ""
    if current_status != "pre_check":
        raise HTTPException(status_code=400, detail=f"Quick pre-check only allowed for pre_check. Current: {current_status}")

    to_status = "under_review" if decision == "approve" else "minor_revision"
    updated = svc.update_status(
        manuscript_id=id,
        to_status=to_status,
        changed_by=str(current_user.get("id")),
        comment=comment,
        allow_skip=False,
    )
    return {"success": True, "data": updated}


@router.get("/manuscripts/{id}")
async def get_editor_manuscript_detail(
    id: str,
    current_user: dict = Depends(get_current_user),
    profile: dict = Depends(require_any_role(EDITOR_SCOPE_COMPAT_ROLES)),
):
    """
    Feature 028 / US2: Editor 专用稿件详情（包含 invoice_metadata、owner/editor profile、journal 信息）。
    """
    _require_action_or_403(action="manuscript:view_detail", roles=profile.get("roles") or [])
    ensure_manuscript_scope_access(
        manuscript_id=id,
        user_id=str(current_user.get("id") or ""),
        roles=profile.get("roles") or [],
        allow_admin_bypass=True,
    )

    try:
        resp = (
            supabase_admin.table("manuscripts")
            .select("*, journals(title,slug)")
            .eq("id", id)
            .single()
            .execute()
        )
        ms = getattr(resp, "data", None) or None
    except Exception as e:
        raise HTTPException(status_code=404, detail="Manuscript not found") from e
    if not ms:
        raise HTTPException(status_code=404, detail="Manuscript not found")

    t_total_start = perf_counter()
    timings: dict[str, float] = {}

    def _mark(name: str, t_start: float) -> None:
        timings[name] = round((perf_counter() - t_start) * 1000, 1)

    # 票据/支付状态（容错：没有 invoice 也不应 500）
    invoice = None
    t0 = perf_counter()
    try:
        inv_resp = (
            supabase_admin.table("invoices")
            .select("id,manuscript_id,amount,status,confirmed_at,invoice_number,pdf_path,pdf_generated_at,pdf_error")
            .eq("manuscript_id", id)
            .single()
            .execute()
        )
        invoice = getattr(inv_resp, "data", None) or None
    except Exception:
        invoice = None
    _mark("invoice", t0)
    ms["invoice"] = invoice

    # Feature 033: 内部文件（cover letter / editor peer review attachments）
    mf_rows: list[dict[str, Any]] = []
    t0 = perf_counter()
    try:
        mf = (
            supabase_admin.table("manuscript_files")
            .select("id,file_type,bucket,path,original_filename,content_type,created_at,uploaded_by")
            .eq("manuscript_id", id)
            .order("created_at", desc=True)
            .execute()
        )
        mf_rows = getattr(mf, "data", None) or []
    except Exception as e:
        # 中文注释: 云端未应用 migration 时不应导致详情页 500
        if not _is_missing_table_error(str(e)):
            print(f"[ManuscriptFiles] load manuscript_files failed (ignored): {e}")
    _mark("manuscript_files", t0)

    # 审稿报告（用于附件 + submitted_at 聚合），尽量复用同一查询结果，避免重复打 DB。
    rr_rows: list[dict[str, Any]] = []
    t0 = perf_counter()
    try:
        rr = (
            supabase_admin.table("review_reports")
            .select("id,reviewer_id,attachment_path,created_at,status")
            .eq("manuscript_id", id)
            .order("created_at", desc=True)
            .execute()
        )
        rr_rows = getattr(rr, "data", None) or []
    except Exception as e:
        print(f"[ReviewReports] load failed (ignored): {e}")
    _mark("review_reports", t0)

    # 作者最近一次修回说明（Response Letter），用于 editor 详情页快速查看。
    ms["latest_author_response_letter"] = None
    ms["latest_author_response_submitted_at"] = None
    ms["latest_author_response_round"] = None
    ms["author_response_history"] = []
    # 中文注释:
    # - 云端历史 schema 可能无 revisions.updated_at，仅有 created_at；
    # - 这里按“排序列 + select”双重降级，确保 response_letter 可回显。
    t0 = perf_counter()
    revision_query_variants = [
        ("updated_at", "id,response_letter,submitted_at,updated_at,round"),
        ("created_at", "id,response_letter,submitted_at,created_at,round"),
        ("created_at", "id,response_letter,created_at"),
    ]
    for order_key, select_clause in revision_query_variants:
        try:
            revision_resp = (
                supabase_admin.table("revisions")
                .select(select_clause)
                .eq("manuscript_id", id)
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

                ms["author_response_history"].append(
                    {
                        "id": row.get("id"),
                        "response_letter": response_letter,
                        "submitted_at": submitted_at,
                        "round": round_value,
                    }
                )

                if ms["latest_author_response_letter"] is None:
                    ms["latest_author_response_letter"] = response_letter
                    ms["latest_author_response_submitted_at"] = submitted_at
                    ms["latest_author_response_round"] = round_value
            break
        except Exception as e:
            lowered = str(e).lower()
            if "schema cache" in lowered or "column" in lowered or "pgrst" in lowered:
                continue
            print(f"[Revisions] load latest response letter failed (ignored): {e}")
            break
    _mark("revisions", t0)

    # 预审时间线
    tl_rows: list[dict[str, Any]] = []
    t0 = perf_counter()
    try:
        tl_resp = (
            supabase_admin.table("status_transition_logs")
            .select("id, manuscript_id, from_status, to_status, comment, changed_by, created_at, payload")
            .eq("manuscript_id", id)
            .order("created_at", desc=False)
            .execute()
        )
        tl_rows = getattr(tl_resp, "data", None) or []
    except Exception as e:
        print(f"[PrecheckTimeline] load failed (ignored): {e}")
    _mark("status_logs", t0)

    # Reviewer 邀请时间线
    ra_rows: list[dict[str, Any]] = []
    t0 = perf_counter()
    try:
        ra_resp = (
            supabase_admin.table("review_assignments")
            .select(
                "id,reviewer_id,status,due_at,invited_at,opened_at,accepted_at,declined_at,decline_reason,decline_note,created_at"
            )
            .eq("manuscript_id", id)
            .order("created_at", desc=True)
            .execute()
        )
        ra_rows = getattr(ra_resp, "data", None) or []
    except Exception as e:
        print(f"[ReviewerInvites] load failed (ignored): {e}")
    _mark("review_assignments", t0)

    # Feature 045: 稿件级任务逾期摘要（详情页右侧摘要使用）
    ms["task_summary"] = {
        "open_tasks_count": 0,
        "overdue_tasks_count": 0,
        "is_overdue": False,
        "nearest_due_at": None,
    }
    t0 = perf_counter()
    try:
        t_resp = (
            supabase_admin.table("internal_tasks")
            .select("id,status,due_at")
            .eq("manuscript_id", id)
            .execute()
        )
        t_rows = getattr(t_resp, "data", None) or []
        open_rows = [r for r in t_rows if str(r.get("status") or "").lower() != InternalTaskStatus.DONE.value]
        overdue_count = 0
        nearest_due: str | None = None
        now = datetime.now(timezone.utc)
        for row in open_rows:
            due_raw = str(row.get("due_at") or "")
            if not due_raw:
                continue
            try:
                due_at = datetime.fromisoformat(due_raw.replace("Z", "+00:00")).astimezone(timezone.utc)
            except Exception:
                continue
            if due_at < now:
                overdue_count += 1
            if not nearest_due:
                nearest_due = due_at.isoformat()
            else:
                try:
                    prev = datetime.fromisoformat(nearest_due.replace("Z", "+00:00")).astimezone(timezone.utc)
                    if due_at < prev:
                        nearest_due = due_at.isoformat()
                except Exception:
                    nearest_due = due_at.isoformat()

        ms["task_summary"] = {
            "open_tasks_count": len(open_rows),
            "overdue_tasks_count": overdue_count,
            "is_overdue": overdue_count > 0,
            "nearest_due_at": nearest_due,
        }
    except Exception as e:
        if not _is_missing_table_error(str(e)):
            print(f"[InternalTasks] task summary failed (ignored): {e}")
    _mark("task_summary", t0)

    # 合并构建 profile id，减少 user_profiles 的重复查询。
    profile_ids: set[str] = set()
    if ms.get("author_id"):
        profile_ids.add(str(ms["author_id"]))
    if ms.get("owner_id"):
        profile_ids.add(str(ms["owner_id"]))
    if ms.get("editor_id"):
        profile_ids.add(str(ms["editor_id"]))
    if ms.get("assistant_editor_id"):
        profile_ids.add(str(ms["assistant_editor_id"]))
    for row in rr_rows:
        rid = str(row.get("reviewer_id") or "").strip()
        if rid:
            profile_ids.add(rid)
    for row in ra_rows:
        rid = str(row.get("reviewer_id") or "").strip()
        if rid:
            profile_ids.add(rid)

    profiles_map: dict[str, dict] = {}
    t0 = perf_counter()
    if profile_ids:
        try:
            p = (
                supabase_admin.table("user_profiles")
                .select("id,email,full_name,roles,affiliation")
                .in_("id", sorted(profile_ids))
                .execute()
            )
            for row in (getattr(p, "data", None) or []):
                pid = str(row.get("id") or "")
                if pid:
                    profiles_map[pid] = row
        except Exception as e:
            print(f"[Profiles] load failed (ignored): {e}")
    _mark("profiles", t0)

    aid = str(ms.get("author_id") or "")
    oid = str(ms.get("owner_id") or "")
    eid = str(ms.get("editor_id") or "")
    ms["author"] = (
        {
            "id": aid,
            "full_name": (profiles_map.get(aid) or {}).get("full_name"),
            "email": (profiles_map.get(aid) or {}).get("email"),
            "affiliation": (profiles_map.get(aid) or {}).get("affiliation"),
        }
        if aid
        else None
    )
    ms["owner"] = (
        {"id": oid, "full_name": (profiles_map.get(oid) or {}).get("full_name"), "email": (profiles_map.get(oid) or {}).get("email")}
        if oid
        else None
    )
    ms["editor"] = (
        {"id": eid, "full_name": (profiles_map.get(eid) or {}).get("full_name"), "email": (profiles_map.get(eid) or {}).get("email")}
        if eid
        else None
    )

    # 作者元信息兜底：若 invoice_metadata 未填写，详情页仍可回显作者姓名与机构。
    meta = ms.get("invoice_metadata")
    if not isinstance(meta, dict):
        meta = {}
        ms["invoice_metadata"] = meta
    if not str(meta.get("authors") or "").strip():
        meta["authors"] = str((ms.get("author") or {}).get("full_name") or "").strip() or None
    if not str(meta.get("affiliation") or "").strip():
        meta["affiliation"] = str((ms.get("author") or {}).get("affiliation") or "").strip() or None

    # 文件签名（原稿 PDF + 审稿附件）
    file_path = str(ms.get("file_path") or "").strip()
    original_signed_url = _get_signed_url("manuscripts", file_path) if file_path else None
    ms["files"] = []
    ms["signed_files"] = {
        "original_manuscript": {
            "bucket": "manuscripts",
            "path": file_path or None,
            "signed_url": original_signed_url,
        },
        "peer_review_reports": [],
    }
    if file_path:
        ms["files"].append(
            {
                "id": "original_manuscript",
                "file_type": "manuscript",
                "bucket": "manuscripts",
                "path": file_path,
                "label": "Current Manuscript PDF",
                "signed_url": original_signed_url,
                "created_at": ms.get("updated_at") or ms.get("created_at"),
            }
        )

    # 内部文件（cover letter / editor peer review attachments）
    for row in mf_rows:
        bucket = str(row.get("bucket") or "").strip()
        path = str(row.get("path") or "").strip()
        if not bucket or not path:
            continue
        ms["files"].append(
            {
                "id": row.get("id"),
                "file_type": row.get("file_type"),
                "bucket": bucket,
                "path": path,
                "label": row.get("original_filename") or path,
                "signed_url": _get_signed_url(bucket, path),
                "created_at": row.get("created_at"),
                "uploaded_by": row.get("uploaded_by"),
            }
        )

    # 从同一份 review_reports 行中同时构建:
    # - reviewer report 附件列表
    # - reviewer 提交时间 submitted_map（用于 Reviewer Invite Timeline）
    submitted_map: dict[str, str] = {}
    for row in rr_rows:
        rid = str(row.get("reviewer_id") or "").strip()
        status_raw = str(row.get("status") or "").lower()
        created_at = str(row.get("created_at") or "")
        if rid and status_raw == "completed" and rid not in submitted_map and created_at:
            submitted_map[rid] = created_at

    for row in rr_rows:
        path = str(row.get("attachment_path") or "").strip()
        if not path:
            continue
        rid = str(row.get("reviewer_id") or "").strip()
        prof = profiles_map.get(rid) or {}
        signed_url = _get_signed_url("review-attachments", path)
        ms["signed_files"]["peer_review_reports"].append(
            {
                "review_report_id": row.get("id"),
                "reviewer_id": row.get("reviewer_id"),
                "reviewer_name": prof.get("full_name"),
                "reviewer_email": prof.get("email"),
                "status": row.get("status"),
                "created_at": row.get("created_at"),
                "bucket": "review-attachments",
                "path": path,
                "signed_url": signed_url,
            }
        )
        ms["files"].append(
            {
                "id": row.get("id"),
                "file_type": "review_attachment",
                "bucket": "review-attachments",
                "path": path,
                "label": f"{prof.get('full_name') or prof.get('email') or rid or 'Reviewer'} — Annotated PDF",
                "signed_url": signed_url,
                "created_at": row.get("created_at"),
                "uploaded_by": row.get("reviewer_id"),
            }
        )

    # 044: 预审队列可视化（详情页）
    role_map = {
        "intake": "managing_editor",
        "technical": "assistant_editor",
        "academic": "editor_in_chief",
    }
    pre_stage = str(ms.get("pre_check_status") or "intake").strip().lower() or "intake"
    current_role = role_map.get(pre_stage, "managing_editor")
    current_assignee = None
    if pre_stage == "technical" and ms.get("assistant_editor_id"):
        aid = str(ms.get("assistant_editor_id"))
        aprof = profiles_map.get(aid) or {}
        current_assignee = {"id": aid, "full_name": aprof.get("full_name"), "email": aprof.get("email")}

    ms["precheck_timeline"] = []
    assigned_at = None
    technical_completed_at = None
    academic_completed_at = None
    for row in tl_rows:
        payload = row.get("payload") if isinstance(row.get("payload"), dict) else {}
        action = str(payload.get("action") or "")
        if action.startswith("precheck_"):
            ms["precheck_timeline"].append(row)
            created_at = str(row.get("created_at") or "")
            if action in {"precheck_assign_ae", "precheck_reassign_ae"}:
                assigned_at = created_at or assigned_at
            if action in {"precheck_technical_pass", "precheck_technical_revision", "precheck_technical_to_under_review"}:
                technical_completed_at = created_at or technical_completed_at
            if action in {"precheck_academic_to_review", "precheck_academic_to_decision"}:
                academic_completed_at = created_at or academic_completed_at

    ms["role_queue"] = {
        "current_role": current_role,
        "current_assignee": current_assignee,
        "assigned_at": assigned_at,
        "technical_completed_at": technical_completed_at,
        "academic_completed_at": academic_completed_at,
    }

    # Feature 037: Reviewer invite timeline（Editor 可见）
    ms["reviewer_invites"] = []
    for row in ra_rows:
        rid = str(row.get("reviewer_id") or "").strip()
        prof = profiles_map.get(rid) or {}
        status_raw = str(row.get("status") or "").lower()
        if status_raw == "completed":
            invite_state = "submitted"
        elif status_raw == "declined" or row.get("declined_at"):
            invite_state = "declined"
        elif row.get("accepted_at"):
            invite_state = "accepted"
        else:
            invite_state = "invited"

        ms["reviewer_invites"].append(
            {
                "id": row.get("id"),
                "reviewer_id": row.get("reviewer_id"),
                "reviewer_name": prof.get("full_name"),
                "reviewer_email": prof.get("email"),
                "status": invite_state,
                "due_at": row.get("due_at"),
                "invited_at": row.get("invited_at") or row.get("created_at"),
                "opened_at": row.get("opened_at"),
                "accepted_at": row.get("accepted_at"),
                "declined_at": row.get("declined_at"),
                "submitted_at": submitted_map.get(rid),
                "decline_reason": row.get("decline_reason"),
                "decline_note": row.get("decline_note"),
            }
        )

    total_ms = round((perf_counter() - t_total_start) * 1000, 1)
    timing_text = " ".join([f"{k}={v}ms" for k, v in timings.items()])
    print(f"[EditorDetail:{id}] total={total_ms}ms {timing_text}")

    return {"success": True, "data": ms}


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


@router.post("/manuscripts/{id}/production/advance")
async def advance_production_stage(
    id: str,
    current_user: dict = Depends(get_current_user),
    profile: dict = Depends(require_any_role(["managing_editor", "admin"])),
):
    """
    Feature 031: 录用后出版流水线 - 前进一个阶段（approved->layout->english_editing->proofreading->published）。
    """
    allow_skip = "admin" in (profile.get("roles") or [])
    res = ProductionService().advance(
        manuscript_id=id,
        changed_by=str(current_user.get("id")),
        allow_skip=bool(allow_skip),
    )
    return {
        "success": True,
        "data": {
            "previous_status": res.previous_status,
            "new_status": res.new_status,
            "manuscript": res.manuscript,
        },
    }


@router.post("/manuscripts/{id}/production/revert")
async def revert_production_stage(
    id: str,
    current_user: dict = Depends(get_current_user),
    profile: dict = Depends(require_any_role(["managing_editor", "admin"])),
):
    """
    Feature 031: 录用后出版流水线 - 回退一个阶段（proofreading->english_editing->layout->approved）。
    """
    allow_skip = "admin" in (profile.get("roles") or [])
    res = ProductionService().revert(
        manuscript_id=id,
        changed_by=str(current_user.get("id")),
        allow_skip=bool(allow_skip),
    )
    return {
        "success": True,
        "data": {
            "previous_status": res.previous_status,
            "new_status": res.new_status,
            "manuscript": res.manuscript,
        },
    }


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
                "roles.cs.{admin},roles.cs.{assistant_editor},roles.cs.{managing_editor},roles.cs.{editor_in_chief}"
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


# ----------------------------
# Feature 030: Reviewer Library
# ----------------------------


@router.post("/reviewer-library", status_code=201)
async def add_reviewer_to_library(
    payload: ReviewerCreate,
    _profile: dict = Depends(require_any_role(["managing_editor", "admin"])),
):
    """
    User Story 1:
    - 将潜在审稿人加入“审稿人库”
    - 立即创建/关联 auth.users + public.user_profiles
    - **不发送邮件**
    """
    try:
        data = ReviewerService().add_to_library(payload)
        return {"success": True, "data": data}
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        print(f"[ReviewerLibrary] add failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to add reviewer")


@router.get("/reviewer-library")
async def search_reviewer_library(
    query: str = Query("", description="按姓名/邮箱/单位/研究方向模糊检索（可选）"),
    limit: int = Query(50, ge=1, le=200),
    manuscript_id: str | None = Query(None, description="可选：基于稿件上下文返回邀请策略命中信息"),
    _profile: dict = Depends(require_any_role(["managing_editor", "admin"])),
):
    """
    User Story 2:
    - 从审稿人库搜索审稿人（仅返回 active reviewer）
    """
    try:
        rows = ReviewerService().search(query=query, limit=limit)
        meta: dict[str, Any] = {}
        if manuscript_id:
            ms_resp = (
                supabase_admin.table("manuscripts")
                .select("id,author_id,journal_id,status")
                .eq("id", manuscript_id)
                .single()
                .execute()
            )
            manuscript = getattr(ms_resp, "data", None) or {}
            if not manuscript:
                raise HTTPException(status_code=404, detail="Manuscript not found")

            policy_service = ReviewPolicyService()
            reviewer_ids = [str(r.get("id") or "").strip() for r in rows if str(r.get("id") or "").strip()]
            policy_map = policy_service.evaluate_candidates(manuscript=manuscript, reviewer_ids=reviewer_ids)
            for row in rows:
                rid = str(row.get("id") or "").strip()
                row["invite_policy"] = policy_map.get(rid) or {
                    "can_assign": True,
                    "allow_override": False,
                    "cooldown_active": False,
                    "conflict": False,
                    "overdue_risk": False,
                    "overdue_open_count": 0,
                    "hits": [],
                }
            meta = {
                "cooldown_days": policy_service.cooldown_days(),
                "override_roles": policy_service.cooldown_override_roles(),
            }
        return {"success": True, "data": rows, "policy": meta}
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ReviewerLibrary] search failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to search reviewer library")


@router.get("/reviewer-library/{id}")
async def get_reviewer_library_item(
    id: str,
    _profile: dict = Depends(require_any_role(["managing_editor", "admin"])),
):
    """
    User Story 3:
    - 获取审稿人库条目的完整信息
    """
    try:
        data = ReviewerService().get_reviewer(UUID(id))
        return {"success": True, "data": data}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        print(f"[ReviewerLibrary] get failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to load reviewer")


@router.put("/reviewer-library/{id}")
async def update_reviewer_library_item(
    id: str,
    payload: ReviewerUpdate,
    _profile: dict = Depends(require_any_role(["managing_editor", "admin"])),
):
    """
    User Story 3:
    - 更新审稿人库条目的元数据（title/homepage/interests 等）
    """
    try:
        data = ReviewerService().update_reviewer(UUID(id), payload)
        return {"success": True, "data": data}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        print(f"[ReviewerLibrary] update failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to update reviewer")


@router.delete("/reviewer-library/{id}")
async def deactivate_reviewer_library_item(
    id: str,
    _profile: dict = Depends(require_any_role(["managing_editor", "admin"])),
):
    """
    User Story 1:
    - 从审稿人库移除（软删除：is_reviewer_active=false）
    """
    try:
        data = ReviewerService().deactivate(UUID(id))
        return {"success": True, "data": data}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        print(f"[ReviewerLibrary] deactivate failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to remove reviewer")


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
    try:
        # 中文注释: 这里使用 service_role 读取，避免启用 RLS 的云端环境导致 editor 看板空数据。
        db = supabase_admin

        # Pre-check（旧：submitted/pending_quality）
        pending_quality_resp = (
            db.table("manuscripts")
            .select("*")
            .eq("status", "pre_check")
            .order("created_at", desc=True)
            .execute()
        )
        pending_quality = _extract_supabase_data(pending_quality_resp) or []

        # 评审中 (under_review)
        under_review_resp = (
            db.table("manuscripts")
            .select("*, review_assignments(count)")
            .eq("status", "under_review")
            .order("created_at", desc=True)
            .execute()
        )
        under_review_data = _extract_supabase_data(under_review_resp) or []
        # 中文注释: review_assignments(count) 会按“行数”计数，若历史/并发导致重复指派，会把同一 reviewer 计为 2。
        # 这里改为统计 distinct reviewer_id，保证 UI 中 review_count 与“人数”一致。
        under_review_ids = [str(m.get("id")) for m in under_review_data if m.get("id")]
        reviewers_by_ms: dict[str, set[str]] = {}
        if under_review_ids and hasattr(db.table("review_assignments"), "in_"):
            try:
                ras = (
                    db.table("review_assignments")
                    .select("manuscript_id, reviewer_id")
                    .in_("manuscript_id", under_review_ids)
                    .execute()
                )
                for row in (getattr(ras, "data", None) or []):
                    mid = str(row.get("manuscript_id") or "")
                    rid = str(row.get("reviewer_id") or "")
                    if not mid or not rid:
                        continue
                    reviewers_by_ms.setdefault(mid, set()).add(rid)
            except Exception as e:
                print(f"Pipeline reviewer count fallback to row count: {e}")
        under_review = []
        for item in under_review_data:
            mid = str(item.get("id") or "")
            distinct_count = len(reviewers_by_ms.get(mid, set())) if reviewers_by_ms else 0
            if distinct_count == 0 and "review_assignments" in item:
                # 兜底：若 distinct 查询失败，仍用后端原始 count
                ra = item["review_assignments"]
                if isinstance(ra, list) and ra and isinstance(ra[0], dict) and "count" in ra[0]:
                    distinct_count = ra[0].get("count", 0)
                elif isinstance(ra, list):
                    distinct_count = len(ra)

            item["review_count"] = distinct_count
            if "review_assignments" in item:
                del item["review_assignments"]
            under_review.append(item)

        # 待决策（decision，旧：pending_decision）
        pending_decision_resp = (
            db.table("manuscripts")
            .select("*, review_assignments(count)")
            .eq("status", "decision")
            .order("created_at", desc=True)
            .execute()
        )
        pending_decision_data = _extract_supabase_data(pending_decision_resp) or []
        pending_ids = [str(m.get("id")) for m in pending_decision_data if m.get("id")]
        reviewers_by_ms_pending: dict[str, set[str]] = {}
        if pending_ids and hasattr(db.table("review_assignments"), "in_"):
            try:
                ras = (
                    db.table("review_assignments")
                    .select("manuscript_id, reviewer_id")
                    .in_("manuscript_id", pending_ids)
                    .execute()
                )
                for row in (getattr(ras, "data", None) or []):
                    mid = str(row.get("manuscript_id") or "")
                    rid = str(row.get("reviewer_id") or "")
                    if not mid or not rid:
                        continue
                    reviewers_by_ms_pending.setdefault(mid, set()).add(rid)
            except Exception as e:
                print(f"Pipeline reviewer count fallback to row count (pending_decision): {e}")
        pending_decision = []
        for item in pending_decision_data:
            mid = str(item.get("id") or "")
            distinct_count = len(reviewers_by_ms_pending.get(mid, set())) if reviewers_by_ms_pending else 0
            if distinct_count == 0 and "review_assignments" in item:
                ra = item["review_assignments"]
                if isinstance(ra, list) and ra and isinstance(ra[0], dict) and "count" in ra[0]:
                    distinct_count = ra[0].get("count", 0)
                elif isinstance(ra, list):
                    distinct_count = len(ra)

            item["review_count"] = distinct_count
            if "review_assignments" in item:
                del item["review_assignments"]
            pending_decision.append(item)

        # Post-acceptance（approved/layout/english_editing/proofreading）- 需要显示发文前的财务状态
        approved_query = (
            db.table("manuscripts")
            .select("*, invoices(id,amount,status)")
            .order("updated_at", desc=True)
        )
        if hasattr(approved_query, "in_"):
            approved_query = approved_query.in_("status", ["approved", "layout", "english_editing", "proofreading"])
        else:
            # 单元测试 stub client 可能不实现 in_；此时仅返回 approved，避免抛错阻断看板。
            approved_query = approved_query.eq("status", "approved")
        approved_resp = approved_query.execute()
        approved_data = _extract_supabase_data(approved_resp) or []
        approved = []
        for item in approved_data:
            invoices = item.get("invoices")
            # PostgREST 1:1 关联可能返回 dict（而不是 list）
            if isinstance(invoices, dict):
                inv = invoices
            elif isinstance(invoices, list):
                inv = invoices[0] if invoices else {}
            else:
                inv = {}
            item["invoice_amount"] = inv.get("amount")
            item["invoice_status"] = inv.get("status")
            item["invoice_id"] = inv.get("id")
            if "invoices" in item:
                del item["invoices"]
            approved.append(item)

        # 已发布 (published)
        published_resp = (
            db.table("manuscripts")
            .select("*")
            .eq("status", "published")
            .order("created_at", desc=True)
            .execute()
        )
        published = _extract_supabase_data(published_resp) or []

        # 待处理修订稿 (resubmitted) - 类似待质检，需 Editor 处理
        resubmitted_resp = (
            db.table("manuscripts")
            .select("*")
            .eq("status", "resubmitted")
            .order("updated_at", desc=True)
            .execute()
        )
        resubmitted = _extract_supabase_data(resubmitted_resp) or []

        # 等待作者修订（major/minor revision，旧：revision_requested）- 监控用
        revision_requested = []
        try:
            rr_query = (
                db.table("manuscripts")
                .select("*")
                .order("updated_at", desc=True)
            )
            if hasattr(rr_query, "in_"):
                rr_query = rr_query.in_("status", ["major_revision", "minor_revision"])
                revision_requested = _extract_supabase_data(rr_query.execute()) or []
            else:
                # fallback: 两次 eq 合并（不阻断）
                maj = _extract_supabase_data(
                    db.table("manuscripts").select("*").eq("status", "major_revision").order("updated_at", desc=True).execute()
                ) or []
                minor = _extract_supabase_data(
                    db.table("manuscripts").select("*").eq("status", "minor_revision").order("updated_at", desc=True).execute()
                ) or []
                revision_requested = (maj or []) + (minor or [])
        except Exception as e:
            print(f"Pipeline revision_requested fallback empty: {e}")

        # 已拒稿 (rejected) - 终态归档
        rejected_resp = (
            db.table("manuscripts")
            .select("*")
            .eq("status", "rejected")
            .order("updated_at", desc=True)
            .execute()
        )
        rejected = _extract_supabase_data(rejected_resp) or []

        return {
            "success": True,
            "data": {
                "pending_quality": pending_quality,
                "resubmitted": resubmitted,  # New
                "under_review": under_review,
                "revision_requested": revision_requested,  # New
                "pending_decision": pending_decision,
                "approved": approved,
                "published": published,
                "rejected": rejected,
            },
        }

    except Exception as e:
        print(f"Pipeline query failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch pipeline data")


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
    # MVP 业务规则:
    # - 上一轮如果是“小修”，Editor 不允许升级成“大修”；如确需升级，必须由 Admin 执行。
    try:
        roles = set((profile or {}).get("roles") or [])
        if request.decision_type == "major" and "admin" not in roles:
            latest = (
                supabase_admin.table("revisions")
                .select("decision_type, round_number")
                .eq("manuscript_id", str(request.manuscript_id))
                .order("round_number", desc=True)
                .limit(1)
                .execute()
            )
            latest_rows = getattr(latest, "data", None) or []
            if latest_rows:
                last_type = str(latest_rows[0].get("decision_type") or "").strip().lower()
                if last_type == "minor":
                    raise HTTPException(
                        status_code=403,
                        detail="该稿件上一轮为小修，编辑无权升级为大修；如确需大修请用 Admin 账号操作。",
                    )
    except HTTPException:
        raise
    except Exception as e:
        print(f"[Revision] major-after-minor guard failed (ignored): {e}")

    service = RevisionService()
    result = service.create_revision_request(
        manuscript_id=str(request.manuscript_id),
        decision_type=request.decision_type,
        editor_comment=request.comment,
    )

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])

    # === 通知中心 (Feature 011 / T024) ===
    try:
        manuscript = service.get_manuscript(str(request.manuscript_id))
        if manuscript:
            author_id = manuscript.get("author_id")
            title = manuscript.get("title", "Manuscript")

            notification_service = NotificationService()
            notification_service.create_notification(
                user_id=str(author_id),
                manuscript_id=str(request.manuscript_id),
                type="decision",
                title="Revision Requested",
                content=f"Editor has requested a {request.decision_type} revision for '{title}'.",
            )

            # Feature 025: Send Email
            if background_tasks:
                try:
                    prof = supabase_admin.table("user_profiles").select("email, full_name").eq("id", str(author_id)).single().execute()
                    pdata = getattr(prof, "data", None) or {}
                    author_email = pdata.get("email")
                    recipient_name = pdata.get("full_name") or "Author"
                    
                    if author_email:
                        from app.core.mail import email_service
                        background_tasks.add_task(
                            email_service.send_email_background,
                            to_email=author_email,
                            subject="Revision Requested",
                            template_name="status_update.html",
                            context={
                                "recipient_name": recipient_name,
                                "manuscript_title": title,
                                "decision_label": f"{request.decision_type.capitalize()} Revision Requested",
                                "comment": request.comment or "Please check the portal for details.",
                            }
                        )
                except Exception as e:
                    print(f"[Email] Failed to send revision email: {e}")

    except Exception as e:
        print(f"[Notifications] Failed to send revision notification: {e}")

    return RevisionRequestResponse(data=result["data"]["revision"])


@router.get("/available-reviewers")
async def get_available_reviewers(
    current_user: dict = Depends(get_current_user),
    _profile: dict = Depends(require_any_role(["managing_editor", "admin"])),
):
    """
    获取可用的审稿人专家池
    """
    try:
        user_id = current_user.get("id")
        email = current_user.get("email")
        self_candidate = None
        if user_id and email:
            name_part = email.split("@")[0].replace(".", " ").title()
            self_candidate = {
                "id": str(user_id),
                "name": f"{name_part} (You)",
                "email": email,
                "affiliation": "Your Account",
                "expertise": ["AI", "Systems"],
                "review_count": 0,
            }

        reviewers_resp = (
            supabase.table("user_profiles")
            .select("id, email, roles")
            .contains("roles", ["reviewer"])
            .execute()
        )
        reviewers = _extract_supabase_data(reviewers_resp) or []

        formatted_reviewers = []
        for reviewer in reviewers:
            email = reviewer.get("email") or "reviewer@example.com"
            name_part = email.split("@")[0].replace(".", " ").title()
            formatted_reviewers.append(
                {
                    "id": reviewer["id"],
                    "name": name_part or "Reviewer",
                    "email": email,
                    "affiliation": "Independent Researcher",
                    "expertise": ["AI", "Systems"],
                    "review_count": 0,
                }
            )

        if formatted_reviewers:
            if self_candidate and not any(
                r["id"] == self_candidate["id"] for r in formatted_reviewers
            ):
                formatted_reviewers.insert(0, self_candidate)
            return {"success": True, "data": formatted_reviewers}

        # fallback: demo reviewers for empty dataset
        if self_candidate:
            return {
                "success": True,
                "data": [
                    self_candidate,
                    {
                        "id": "88888888-8888-8888-8888-888888888888",
                        "name": "Dr. Demo Reviewer",
                        "email": "reviewer1@example.com",
                        "affiliation": "Demo Lab",
                        "expertise": ["AI", "NLP"],
                        "review_count": 12,
                    },
                    {
                        "id": "77777777-7777-7777-7777-777777777777",
                        "name": "Prof. Sample Expert",
                        "email": "reviewer2@example.com",
                        "affiliation": "Sample University",
                        "expertise": ["Machine Learning", "Computer Vision"],
                        "review_count": 8,
                    },
                    {
                        "id": "66666666-6666-6666-6666-666666666666",
                        "name": "Dr. Placeholder",
                        "email": "reviewer3@example.com",
                        "affiliation": "Research Institute",
                        "expertise": ["Security", "Blockchain"],
                        "review_count": 5,
                    },
                ],
            }
        return {
            "success": True,
            "data": [
                {
                    "id": "88888888-8888-8888-8888-888888888888",
                    "name": "Dr. Demo Reviewer",
                    "email": "reviewer1@example.com",
                    "affiliation": "Demo Lab",
                    "expertise": ["AI", "NLP"],
                    "review_count": 12,
                },
                {
                    "id": "77777777-7777-7777-7777-777777777777",
                    "name": "Prof. Sample Expert",
                    "email": "reviewer2@example.com",
                    "affiliation": "Sample University",
                    "expertise": ["Machine Learning", "Computer Vision"],
                    "review_count": 8,
                },
                {
                    "id": "66666666-6666-6666-6666-666666666666",
                    "name": "Dr. Placeholder",
                    "email": "reviewer3@example.com",
                    "affiliation": "Research Institute",
                    "expertise": ["Security", "Blockchain"],
                    "review_count": 5,
                },
            ],
        }

    except Exception as e:
        print(f"Reviewers query failed: {e}")
        if self_candidate:
            return {"success": True, "data": [self_candidate]}
        return {"success": True, "data": []}


@router.get("/manuscripts/{id}/decision-context")
async def get_decision_workspace_context(
    id: str,
    current_user: dict = Depends(get_current_user),
    profile: dict = Depends(require_any_role(EDITOR_DECISION_ROLES)),
):
    """
    Feature 041: 获取决策工作台聚合上下文。
    """
    _require_action_or_403(action="decision:record_first", roles=profile.get("roles") or [])
    ensure_manuscript_scope_access(
        manuscript_id=id,
        user_id=str(current_user.get("id") or ""),
        roles=profile.get("roles") or [],
        allow_admin_bypass=True,
    )

    data = DecisionService().get_decision_context(
        manuscript_id=id,
        user_id=str(current_user.get("id") or ""),
        profile_roles=profile.get("roles") or [],
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
    _require_action_or_403(
        action="decision:submit_final" if payload.is_final else "decision:record_first",
        roles=profile.get("roles") or [],
    )
    ensure_manuscript_scope_access(
        manuscript_id=id,
        user_id=str(current_user.get("id") or ""),
        roles=profile.get("roles") or [],
        allow_admin_bypass=True,
    )

    data = DecisionService().submit_decision(
        manuscript_id=id,
        user_id=str(current_user.get("id") or ""),
        profile_roles=profile.get("roles") or [],
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
    ensure_manuscript_scope_access(
        manuscript_id=id,
        user_id=str(current_user.get("id") or ""),
        roles=profile.get("roles") or [],
        allow_admin_bypass=True,
    )

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
    ensure_manuscript_scope_access(
        manuscript_id=id,
        user_id=str(current_user.get("id") or ""),
        roles=profile.get("roles") or [],
        allow_admin_bypass=True,
    )

    signed_url = DecisionService().get_attachment_signed_url_for_editor(
        manuscript_id=id,
        attachment_id=attachment_id,
        user_id=str(current_user.get("id") or ""),
        profile_roles=profile.get("roles") or [],
    )
    return {"success": True, "data": {"signed_url": signed_url}}


@router.get("/manuscripts/{id}/production-workspace")
async def get_production_workspace_context(
    id: str,
    current_user: dict = Depends(get_current_user),
    profile: dict = Depends(require_any_role(["managing_editor", "editor_in_chief", "admin"])),
):
    """
    Feature 042: 编辑端生产工作间上下文。
    """
    data = ProductionWorkspaceService().get_workspace_context(
        manuscript_id=id,
        user_id=str(current_user.get("id") or ""),
        profile_roles=profile.get("roles") or [],
    )
    return {"success": True, "data": data}


@router.post("/manuscripts/{id}/production-cycles", status_code=201)
async def create_production_cycle(
    id: str,
    payload: CreateProductionCycleRequest,
    current_user: dict = Depends(get_current_user),
    profile: dict = Depends(require_any_role(["managing_editor", "editor_in_chief", "admin"])),
):
    """
    Feature 042: 创建生产轮次。
    """
    data = ProductionWorkspaceService().create_cycle(
        manuscript_id=id,
        user_id=str(current_user.get("id") or ""),
        profile_roles=profile.get("roles") or [],
        request=payload,
    )
    return {"success": True, "data": {"cycle": data}}


@router.post("/manuscripts/{id}/production-cycles/{cycle_id}/galley")
async def upload_production_galley(
    id: str,
    cycle_id: str,
    file: UploadFile = File(...),
    version_note: str = Form(...),
    proof_due_at: str | None = Form(default=None),
    current_user: dict = Depends(get_current_user),
    profile: dict = Depends(require_any_role(["managing_editor", "editor_in_chief", "admin"])),
):
    """
    Feature 042: 上传生产轮次清样并进入 awaiting_author。
    """
    due_dt: datetime | None = None
    if proof_due_at:
        try:
            due_dt = datetime.fromisoformat(str(proof_due_at).replace("Z", "+00:00"))
        except Exception as e:
            raise HTTPException(status_code=422, detail=f"Invalid proof_due_at: {proof_due_at}") from e

    raw = await file.read()
    data = ProductionWorkspaceService().upload_galley(
        manuscript_id=id,
        cycle_id=cycle_id,
        user_id=str(current_user.get("id") or ""),
        profile_roles=profile.get("roles") or [],
        filename=file.filename or "proof.pdf",
        content=raw,
        version_note=version_note,
        proof_due_at=due_dt,
        content_type=file.content_type,
    )
    return {"success": True, "data": {"cycle": data}}


@router.get("/manuscripts/{id}/production-cycles/{cycle_id}/galley-signed")
async def get_production_galley_signed_url_editor(
    id: str,
    cycle_id: str,
    current_user: dict = Depends(get_current_user),
    profile: dict = Depends(require_any_role(["managing_editor", "editor_in_chief", "admin"])),
):
    """
    Feature 042: 编辑端获取清样 signed URL。
    """
    signed_url = ProductionWorkspaceService().get_galley_signed_url(
        manuscript_id=id,
        cycle_id=cycle_id,
        user_id=str(current_user.get("id") or ""),
        profile_roles=profile.get("roles") or [],
    )
    return {"success": True, "data": {"signed_url": signed_url}}


@router.post("/manuscripts/{id}/production-cycles/{cycle_id}/approve")
async def approve_production_cycle(
    id: str,
    cycle_id: str,
    current_user: dict = Depends(get_current_user),
    profile: dict = Depends(require_any_role(["managing_editor", "editor_in_chief", "admin"])),
):
    """
    Feature 042: 编辑确认发布前核准（approved_for_publish）。
    """
    data = ProductionWorkspaceService().approve_cycle(
        manuscript_id=id,
        cycle_id=cycle_id,
        user_id=str(current_user.get("id") or ""),
        profile_roles=profile.get("roles") or [],
    )
    return {"success": True, "data": data}


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
    # 验证决策类型
    if decision not in ["accept", "reject"]:
        raise HTTPException(status_code=400, detail="Invalid decision type")
    if decision == "accept":
        if apc_amount is None:
            raise HTTPException(status_code=400, detail="apc_amount is required for accept")
        if apc_amount < 0:
            raise HTTPException(status_code=400, detail="apc_amount must be >= 0")

    roles = profile.get("roles") if isinstance(profile, dict) else ["admin"]
    _require_action_or_403(action="decision:submit_final", roles=roles or ["admin"])

    ensure_manuscript_scope_access(
        manuscript_id=manuscript_id,
        user_id=str(current_user.get("id") or ""),
        roles=roles or ["admin"],
        allow_admin_bypass=True,
    )

    try:
        try:
            manuscript_row = (
                supabase_admin.table("manuscripts")
                .select("status")
                .eq("id", manuscript_id)
                .single()
                .execute()
            )
        except Exception as e:
            raise HTTPException(status_code=404, detail="Manuscript not found") from e
        manuscript = getattr(manuscript_row, "data", None) or {}
        current_status = normalize_status(str(manuscript.get("status") or ""))
        if not current_status:
            raise HTTPException(status_code=404, detail="Manuscript not found")
        if current_status not in {ManuscriptStatus.DECISION.value, ManuscriptStatus.DECISION_DONE.value}:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Decision is only allowed in {ManuscriptStatus.DECISION.value}/"
                    f"{ManuscriptStatus.DECISION_DONE.value}. Current: {current_status}"
                ),
            )

        # 更新稿件状态
        if decision == "accept":
            # 录用：仅进入“已录用/待发布”状态；发布必须通过 Financial Gate
            update_data = {"status": "approved"}
        else:
            # 拒稿：进入 rejected 终态（修回请走 /editor/revisions）
            update_data = {"status": "rejected", "reject_comment": comment}

        # 执行更新
        try:
            response = (
                supabase_admin.table("manuscripts")
                .update(update_data)
                .eq("id", manuscript_id)
                .execute()
            )
        except Exception as e:
            error_text = str(e)
            print(f"Decision update error: {error_text}")
            if _is_missing_column_error(error_text):
                response = (
                    supabase_admin.table("manuscripts")
                    .update({"status": update_data["status"]})
                    .eq("id", manuscript_id)
                    .execute()
                )
            else:
                raise

        error = _extract_supabase_error(response)
        if error and _is_missing_column_error(str(error)):
            response = (
                supabase_admin.table("manuscripts")
                .update({"status": update_data["status"]})
                .eq("id", manuscript_id)
                .execute()
            )
        elif error:
            raise HTTPException(status_code=500, detail="Failed to submit decision")

        data = _extract_supabase_data(response) or []
        if len(data) == 0:
            raise HTTPException(status_code=404, detail="Manuscript not found")

        # === Feature 022: APC 确认（录用时创建/更新 Invoice） ===
        if decision == "accept":
            invoice_status = "paid" if apc_amount == 0 else "unpaid"
            invoice_payload = {
                "manuscript_id": manuscript_id,
                "amount": apc_amount,
                "status": invoice_status,
                "confirmed_at": datetime.now().isoformat() if invoice_status == "paid" else None,
            }
            invoice_id: str | None = None
            try:
                inv_upsert = supabase_admin.table("invoices").upsert(
                    invoice_payload, on_conflict="manuscript_id"
                ).execute()
                inv_rows = getattr(inv_upsert, "data", None) or []
                if inv_rows:
                    invoice_id = (inv_rows[0] or {}).get("id")
            except Exception as e:
                print(f"[Financial] Failed to upsert invoice: {e}")
                raise HTTPException(status_code=500, detail="Failed to create invoice")

            # === Feature 026: 自动生成并持久化 Invoice PDF（后台任务） ===
            # 中文注释:
            # - 不阻塞 editor 决策接口，避免 WeasyPrint 生成耗时影响 UX。
            # - 再次录用/重复点击应保持幂等（invoice_id 不变；PDF 覆盖同一路径）。
            if background_tasks is not None:
                try:
                    if not invoice_id:
                        inv_q = (
                            supabase_admin.table("invoices")
                            .select("id")
                            .eq("manuscript_id", manuscript_id)
                            .limit(1)
                            .execute()
                        )
                        inv_q_rows = getattr(inv_q, "data", None) or []
                        invoice_id = (inv_q_rows[0] or {}).get("id") if inv_q_rows else None

                    if invoice_id:
                        from uuid import UUID

                        from app.services.invoice_pdf_service import (
                            generate_and_store_invoice_pdf_safe,
                        )

                        background_tasks.add_task(
                            generate_and_store_invoice_pdf_safe,
                            invoice_id=UUID(str(invoice_id)),
                        )
                except Exception as e:
                    print(f"[InvoicePDF] enqueue failed (ignored): {e}")

        # === MVP: 决策后取消未完成的审稿任务（避免 Reviewer 继续看到该稿件）===
        # 中文注释:
        # - MVP 允许 Editor 在 under_review 阶段直接做 accept/reject（不强制等到 pending_decision）。
        # - 若存在未提交的 reviewer，应该将其 assignment 标记为 cancelled，避免 Reviewer 端继续显示任务。
        try:
            supabase_admin.table("review_assignments").update({"status": "cancelled"}).eq(
                "manuscript_id", manuscript_id
            ).eq("status", "pending").execute()
        except Exception as e:
            print(f"[Decision] cancel pending review_assignments failed (ignored): {e}")

        # === 通知中心 (Feature 011) ===
        # 中文注释:
        # 1) 稿件决策变更属于核心状态变化：作者必须同时收到站内信 + 邮件（异步）。
        try:
            ms_res = (
                supabase_admin.table("manuscripts")
                .select("author_id, title")
                .eq("id", manuscript_id)
                .single()
                .execute()
            )
            ms = getattr(ms_res, "data", None) or {}
            author_id = ms.get("author_id")
            manuscript_title = ms.get("title") or "Manuscript"
        except Exception:
            author_id = None
            manuscript_title = "Manuscript"

        if author_id:
            decision_label = "Accepted" if decision == "accept" else "Rejected"
            decision_title = (
                "Editorial Decision"
                if decision == "accept"
                else "Editorial Decision: Rejected"
            )

            NotificationService().create_notification(
                user_id=str(author_id),
                manuscript_id=manuscript_id,
                type="decision",
                title=decision_title,
                content=f"Decision for '{manuscript_title}': {decision_label}.",
            )

            try:
                author_profile = (
                    supabase_admin.table("user_profiles")
                    .select("email")
                    .eq("id", str(author_id))
                    .single()
                    .execute()
                )
                author_email = (getattr(author_profile, "data", None) or {}).get(
                    "email"
                )
            except Exception:
                author_email = None

            if author_email and background_tasks is not None:
                from app.core.mail import email_service
                # 1. Decision Email
                background_tasks.add_task(
                    email_service.send_email_background,
                    to_email=author_email,
                    subject=decision_title,
                    template_name="status_update.html",
                    context={
                        "recipient_name": author_email.split("@")[0]
                        .replace(".", " ")
                        .title(),
                        "manuscript_title": manuscript_title,
                        "decision_label": decision_label,
                        "comment": comment or "",
                    },
                )

                # 2. Invoice Email (Feature 025)
                if decision == "accept" and apc_amount and apc_amount > 0:
                    frontend_base_url = os.environ.get("FRONTEND_BASE_URL", "http://localhost:3000").rstrip("/")
                    invoice_link = f"{frontend_base_url}/dashboard"
                    
                    background_tasks.add_task(
                        email_service.send_email_background,
                        to_email=author_email,
                        subject="Invoice Generated",
                        template_name="invoice.html",
                        context={
                            "recipient_name": author_email.split("@")[0].replace(".", " ").title(),
                            "manuscript_title": manuscript_title,
                            "amount": f"{apc_amount:,.2f}",
                            "link": invoice_link
                        }
                    )

        # GAP-P1-05 / US3: legacy final decision 审计对齐（before/after/reason/source）
        try:
            now_log = datetime.now(timezone.utc).isoformat()
            supabase_admin.table("status_transition_logs").insert(
                {
                    "manuscript_id": manuscript_id,
                    "from_status": current_status,
                    "to_status": str(update_data.get("status") or current_status),
                    "comment": f"legacy final decision: {decision}",
                    "changed_by": str(current_user.get("id") or ""),
                    "created_at": now_log,
                    "payload": {
                        "action": "final_decision_legacy",
                        "decision_stage": "final",
                        "source": "legacy_editor_decision_endpoint",
                        "reason": "editor_submit_final_decision",
                        "decision": decision,
                        "before": {
                            "status": current_status,
                            "apc_amount": None,
                        },
                        "after": {
                            "status": str(update_data.get("status") or current_status),
                            "apc_amount": apc_amount if decision == "accept" else None,
                        },
                    },
                }
            ).execute()
        except Exception:
            pass

        return {
            "success": True,
            "message": "Decision submitted successfully",
            "data": {
                "manuscript_id": manuscript_id,
                "decision": decision,
                "status": update_data["status"],
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"Decision submission failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to submit decision")


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
    try:
        # Feature 024：保留“直接发布”入口（MVP 提速），发布本身仍强制 Payment/Production Gate。
        # Feature 031 的线性阶段推进（layout/english_editing/proofreading）通过 /production/advance 完成。
        try:
            before = (
                supabase_admin.table("manuscripts")
                .select("status")
                .eq("id", manuscript_id)
                .single()
                .execute()
            )
            from_status = str((getattr(before, "data", None) or {}).get("status") or "")
        except Exception:
            from_status = ""
        published = publish_manuscript(manuscript_id=manuscript_id)

        # Feature 031：尽力写入审计日志（不阻断主流程）
        try:
            now = datetime.now(timezone.utc).isoformat()
            supabase_admin.table("status_transition_logs").insert(
                {
                    "manuscript_id": manuscript_id,
                    "from_status": from_status,
                    "to_status": "published",
                    "comment": "publish",
                    "changed_by": str(current_user.get("id")),
                    "created_at": now,
                }
            ).execute()
        except Exception:
            pass

        # Feature 024: 发布通知（站内信 + 邮件，失败不影响主流程）
        try:
            ms_res = (
                supabase_admin.table("manuscripts")
                .select("author_id, title")
                .eq("id", manuscript_id)
                .single()
                .execute()
            )
            ms = getattr(ms_res, "data", None) or {}
            author_id = ms.get("author_id")
            title = ms.get("title") or "Manuscript"

            if author_id:
                NotificationService().create_notification(
                    user_id=str(author_id),
                    manuscript_id=manuscript_id,
                    type="system",
                    title="Article Published",
                    content=f"Your article '{title}' has been published.",
                    action_url=f"/articles/{manuscript_id}",
                )

                if background_tasks is not None:
                    try:
                        prof = (
                            supabase_admin.table("user_profiles")
                            .select("email, full_name")
                            .eq("id", str(author_id))
                            .single()
                            .execute()
                        )
                        pdata = getattr(prof, "data", None) or {}
                        author_email = pdata.get("email")
                        author_name = pdata.get("full_name") or (author_email.split("@")[0] if author_email else "Author")
                    except Exception:
                        author_email = None
                        author_name = "Author"

                    if author_email:
                        from app.core.mail import email_service
                        background_tasks.add_task(
                            email_service.send_email_background,
                            to_email=author_email,
                            subject="Your article has been published",
                            template_name="published.html",
                            context={
                                "recipient_name": author_name,
                                "manuscript_title": title,
                                "doi": published.get("doi"),
                            },
                        )
        except Exception as e:
            print(f"[Publish] notify author failed (ignored): {e}")

        return {"success": True, "data": published}
    except HTTPException:
        raise
    except Exception as e:
        print(f"Publish failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to publish manuscript")


@router.post("/invoices/confirm")
async def confirm_invoice_paid(
    current_user: dict = Depends(get_current_user),
    profile: dict = Depends(require_any_role(EDITOR_SCOPE_COMPAT_ROLES)),
    payload: ConfirmInvoicePaidPayload = Body(...),
):
    """
    MVP：财务确认到账（把 invoices.status 置为 paid）。

    中文注释:
    - 支付渠道/自动对账后续再做；MVP 先提供一个“人工确认到账”入口。
    - Publish 时会做 Payment Gate 检查：amount>0 且 status!=paid -> 禁止发布。
    """
    _require_action_or_403(action="invoice:override_apc", roles=profile.get("roles") or [])
    try:
        manuscript_id = str(payload.manuscript_id or "").strip()
        if not manuscript_id:
            raise HTTPException(status_code=422, detail="manuscript_id is required")

        ensure_manuscript_scope_access(
            manuscript_id=manuscript_id,
            user_id=str(current_user.get("id") or ""),
            roles=profile.get("roles") or [],
            allow_admin_bypass=True,
        )

        expected_status = str(payload.expected_status or "").strip().lower() or None
        source = str(payload.source or "unknown").strip().lower() or "unknown"

        inv_resp = (
            supabase_admin.table("invoices")
            .select("id, amount, status, confirmed_at")
            .eq("manuscript_id", manuscript_id)
            .limit(1)
            .execute()
        )
        inv_rows = getattr(inv_resp, "data", None) or []
        if not inv_rows:
            raise HTTPException(status_code=404, detail="Invoice not found")
        inv = inv_rows[0]

        previous_status = str(inv.get("status") or "").strip().lower() or "unpaid"
        if expected_status and previous_status != expected_status:
            raise HTTPException(status_code=409, detail="Invoice status changed by another operation")

        if previous_status == "paid":
            confirmed_at = str(inv.get("confirmed_at") or datetime.now(timezone.utc).isoformat())
            return {
                "success": True,
                "data": {
                    "invoice_id": inv["id"],
                    "manuscript_id": manuscript_id,
                    "previous_status": previous_status,
                    "current_status": "paid",
                    "confirmed_at": confirmed_at,
                    "already_paid": True,
                    "conflict": False,
                    "source": source,
                },
            }

        confirmed_at = datetime.now(timezone.utc).isoformat()
        update_query = supabase_admin.table("invoices").update(
            {"status": "paid", "confirmed_at": confirmed_at}
        ).eq("id", inv["id"])
        if expected_status:
            update_query = update_query.eq("status", expected_status)
        upd_resp = update_query.execute()
        upd_rows = getattr(upd_resp, "data", None) or []
        if expected_status and not upd_rows:
            raise HTTPException(status_code=409, detail="Invoice status changed by another operation")

        EditorService()._safe_insert_transition_log(
            manuscript_id=manuscript_id,
            from_status=f"invoice:{previous_status}",
            to_status="invoice:paid",
            changed_by=str(current_user.get("id") or ""),
            comment="finance invoice confirmed paid",
            payload={
                "action": "finance_invoice_confirm_paid",
                "invoice_id": str(inv.get("id") or ""),
                "before_status": previous_status,
                "after_status": "paid",
                "source": source,
            },
            created_at=confirmed_at,
        )

        return {
            "success": True,
            "data": {
                "invoice_id": inv["id"],
                "manuscript_id": manuscript_id,
                "previous_status": previous_status,
                "current_status": "paid",
                "confirmed_at": confirmed_at,
                "already_paid": False,
                "conflict": False,
                "source": source,
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"[Financial] confirm invoice failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to confirm invoice")


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
