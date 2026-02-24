from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query

from app.api.v1.editor_common import (
    AcademicCheckRequest,
    AssignAERequest,
    IntakeRevisionRequest,
    QuickPrecheckPayload,
    TechnicalCheckRequest,
)
from app.core.auth_utils import get_current_user
from app.core.journal_scope import ensure_manuscript_scope_access
from app.core.roles import require_any_role
from app.lib.api_client import supabase_admin
from app.models.manuscript import normalize_status
from app.services.editor_service import EditorService
from app.services.editorial_service import EditorialService
from app.services.notification_service import NotificationService

router = APIRouter(tags=["Editor Command Center"])


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
    默认仅从 'intake' 进入 'technical'。
    可选：一键推进到 under_review（由前端显式传 start_external_review=true）。
    """
    try:
        updated = EditorService().assign_ae(
            id,
            request.ae_id,
            current_user["id"],
            owner_id=request.owner_id,
            start_external_review=bool(request.start_external_review),
            bind_owner_if_empty=bool(request.bind_owner_if_empty),
            idempotency_key=request.idempotency_key,
        )
        if request.start_external_review:
            return {"message": "AE assigned and moved to under_review", "data": updated}
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


@router.get("/managing-workspace")
async def get_managing_workspace(
    page: int = 1,
    page_size: int = 20,
    q: str | None = Query(None, max_length=100),
    current_user: dict = Depends(get_current_user),
    profile: dict = Depends(require_any_role(["managing_editor", "admin"])),
):
    """
    Managing Editor Workspace:
    - 按状态分桶返回 ME 需要跟进的非终态稿件。
    """
    try:
        return EditorService().get_managing_workspace(
            viewer_user_id=str(current_user.get("id") or ""),
            viewer_roles=profile.get("roles") or [],
            page=page,
            page_size=page_size,
            q=q,
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"[MEWorkspace] query failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch managing workspace")


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


@router.get("/final-decision")
async def get_final_decision_queue(
    page: int = 1,
    page_size: int = 20,
    current_user: dict = Depends(get_current_user),
    profile: dict = Depends(require_any_role(["editor_in_chief", "admin"])),
):
    """
    EIC Final Decision Queue:
    - 聚焦终审阶段（decision/decision_done）
    - 供 EIC 从 AE first-decision 草稿接手最终学术决策
    """
    try:
        return EditorService().get_final_decision_queue(
            viewer_user_id=str(current_user.get("id") or ""),
            viewer_roles=profile.get("roles") or [],
            page=page,
            page_size=page_size,
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"[FinalDecisionQueue] query failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch final decision queue")


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
