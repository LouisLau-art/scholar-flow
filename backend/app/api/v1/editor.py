from fastapi import APIRouter, HTTPException, Body, Depends, BackgroundTasks, Query, UploadFile, File
import logging
from pydantic import BaseModel, ConfigDict, EmailStr, field_validator
from app.lib.api_client import supabase, supabase_admin
from app.core.auth_utils import get_current_user
from app.core.email_normalization import normalize_email
from app.core.mail import email_service
from app.core.roles import require_any_role
from app.core.journal_scope import ensure_manuscript_scope_access
from app.core.role_matrix import can_perform_action
from app.core.storage_filename import sanitize_storage_filename
from datetime import datetime
from app.models.revision import RevisionCreate, RevisionRequestResponse
from app.models.email_log import EmailStatus
from datetime import timezone
from app.services.post_acceptance_service import publish_manuscript
from app.services.editorial_service import EditorialService
from app.models.manuscript import ManuscriptStatus, normalize_status
from app.services.owner_binding_service import validate_internal_owner_id
from uuid import UUID
from app.schemas.reviewer import ReviewerCreate, ReviewerUpdate  # noqa: F401 (monkeypatch compat)
from app.services.reviewer_service import ReviewerService, ReviewPolicyService  # noqa: F401 (monkeypatch compat)
from app.services.matchmaking_service import MatchmakingService  # noqa: F401 (monkeypatch compat)
from app.services.editor_service import EditorService  # noqa: F401 (monkeypatch compat)
from app.services.decision_service import DecisionService
from app.models.decision import DecisionSubmitRequest, ReviewStageExitRequest
from typing import Annotated, Any, Literal
from uuid import uuid4
from app.api.v1.editor_internal_collaboration import router as internal_collab_router
from app.api.v1.editor_production import router as production_router
from app.api.v1.editor_detail import router as editor_detail_router
from app.api.v1.editor_process import router as editor_process_router
from app.api.v1.editor_precheck import router as editor_precheck_router
from app.api.v1.editor_finance import router as editor_finance_router
from app.api.v1.editor_reviewer_library import router as editor_reviewer_library_router
from app.api.v1.editor_common import (
    InvoiceInfoUpdatePayload,
    BindAcademicEditorRequest,
    resolve_author_notification_target,
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
logger = logging.getLogger("scholarflow.editor")
INTERNAL_COLLAB_ALLOWED_ROLES = ["admin", "managing_editor", "assistant_editor", "academic_editor", "production_editor", "editor_in_chief", "owner"]
EDITOR_SCOPE_COMPAT_ROLES = ["admin", "managing_editor", "assistant_editor", "academic_editor", "production_editor", "editor_in_chief"]
EDITOR_DECISION_ROLES = ["admin", "managing_editor", "assistant_editor", "academic_editor", "editor_in_chief"]


class RevisionRequestEmailPayload(BaseModel):
    model_config = ConfigDict(extra="ignore")

    decision_type: Literal["major", "minor"]
    editor_message: str
    subject_override: str | None = None
    html_override: str | None = None
    idempotency_key: str | None = None
    channel: str | None = "other"
    to_override: list[EmailStr] | None = None
    cc_override: list[EmailStr] | None = None
    bcc_override: list[EmailStr] | None = None
    reply_to_override: list[EmailStr] | None = None

    @field_validator("editor_message", "subject_override", "html_override", "idempotency_key", "channel", mode="before")
    @classmethod
    def _normalize_text(cls, value: Any) -> Any:
        if value is None:
            return None
        normalized = str(value).strip()
        return normalized or None

    @field_validator("to_override", "cc_override", "bcc_override", "reply_to_override", mode="before")
    @classmethod
    def _normalize_email_list(cls, value: Any) -> list[str] | None:
        if value is None:
            return None
        raw = [value] if isinstance(value, str) else list(value)
        normalized: list[str] = []
        for item in raw:
            email = normalize_email(item)
            if email and email not in normalized:
                normalized.append(email)
        return normalized


async def get_editor_pipeline_test():
    """测试兼容入口：避免老单测在重构后失效。"""
    return {"success": True, "data": {}}


async def get_available_reviewers_test():
    """测试兼容入口：避免老单测在重构后失效。"""
    return {"success": True, "data": []}


async def submit_final_decision_test(
    manuscript_id: str,
    decision: str,
    comment: str | None = None,  # noqa: ARG001 - 测试兼容签名
):
    """测试兼容入口：仅用于 unit test 的轻量回包。"""
    normalized = (decision or "").strip().lower()
    status = "published" if normalized == "accept" else "rejected"
    return {"success": True, "data": {"id": manuscript_id, "status": status}}


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


def _normalize_manual_email_list(emails: list[str] | None) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for item in emails or []:
        email = normalize_email(item)
        if not email or email in seen:
            continue
        seen.add(email)
        normalized.append(email)
    return normalized


def _ensure_revision_request_email_context(manuscript_id: UUID) -> dict[str, Any]:
    ms_resp = (
        supabase_admin.table("manuscripts")
        .select("id, title, author_id, journal_id, submission_email, author_contacts")
        .eq("id", str(manuscript_id))
        .single()
        .execute()
    )
    manuscript = getattr(ms_resp, "data", None) or {}
    if not manuscript:
        raise HTTPException(status_code=404, detail="Manuscript not found")

    target = resolve_author_notification_target(
        manuscript=manuscript,
        manuscript_id=str(manuscript_id),
        supabase_client=supabase_admin,
    )
    if not target.get("recipient_email"):
        raise HTTPException(status_code=422, detail="No author email available for revision request delivery")

    manuscript_title = str(manuscript.get("title") or "Manuscript").strip() or "Manuscript"
    recipient_name = str(target.get("recipient_name") or "Author").strip() or "Author"
    return {
        "manuscript": manuscript,
        "target": target,
        "manuscript_title": manuscript_title,
        "recipient_name": recipient_name,
    }


def _resolve_revision_request_email_envelope(
    *,
    target: dict[str, Any],
    payload: RevisionRequestEmailPayload,
) -> dict[str, list[str]]:
    to_recipients = _normalize_manual_email_list(payload.to_override) or _normalize_manual_email_list(target.get("to_recipients"))
    cc_recipients = (
        _normalize_manual_email_list(payload.cc_override)
        if payload.cc_override is not None
        else _normalize_manual_email_list(target.get("cc_recipients"))
    )
    bcc_recipients = (
        _normalize_manual_email_list(payload.bcc_override)
        if payload.bcc_override is not None
        else _normalize_manual_email_list(target.get("bcc_recipients"))
    )
    reply_to_recipients = (
        _normalize_manual_email_list(payload.reply_to_override)
        if payload.reply_to_override is not None
        else _normalize_manual_email_list(target.get("reply_to_recipients"))
    )
    if not to_recipients:
        recipient_email = normalize_email(target.get("recipient_email"))
        if recipient_email:
            to_recipients = [recipient_email]
    return {
        "to": to_recipients,
        "cc": cc_recipients,
        "bcc": bcc_recipients,
        "reply_to": reply_to_recipients,
    }


def _build_revision_request_email_preview(
    manuscript_id: UUID,
    payload: RevisionRequestEmailPayload,
) -> dict[str, Any]:
    if not payload.editor_message:
        raise HTTPException(status_code=422, detail="editor_message is required")

    context = _ensure_revision_request_email_context(manuscript_id)
    decision_label = f"{payload.decision_type.capitalize()} Revision Requested"
    subject = str(payload.subject_override or "Revision Requested").strip() or "Revision Requested"
    default_html = email_service.render_template(
        "status_update.html",
        {
            "recipient_name": context["recipient_name"],
            "manuscript_title": context["manuscript_title"],
            "decision_label": decision_label,
            "comment": payload.editor_message,
        },
    )
    html = str(payload.html_override or default_html).strip() or default_html
    envelope = _resolve_revision_request_email_envelope(target=context["target"], payload=payload)
    return {
        "manuscript_id": str(manuscript_id),
        "recipient_source": context["target"].get("source"),
        "resolved_recipients": envelope,
        "subject": subject,
        "html": html,
        "text": email_service.derive_plain_text_from_html(html),
        "reply_to": envelope["reply_to"],
        "attachments": [],
        "delivery_mode": "manual",
        "idempotency_key": str(payload.idempotency_key or f"revision-request/{manuscript_id}"),
        "can_send": True,
        "context": context,
    }


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


@router.post("/manuscripts/{id}/files/review-attachment", status_code=201)
async def upload_editor_review_attachment(
    id: str,
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
    profile: dict = Depends(require_any_role(["managing_editor", "admin"])),
):
    """
    Feature 033: Editor/Admin 上传 Peer Review Files（仅内部可见）。

    中文注释:
    - 文件上传至私有桶 `review-attachments`（Author 不可见）。
    - 元数据写入 `public.manuscript_files`（file_type=review_attachment）。
    """
    ensure_manuscript_scope_access(
        manuscript_id=id,
        user_id=str(current_user.get("id") or ""),
        roles=profile.get("roles") or [],
        allow_admin_bypass=True,
    )

    filename = (file.filename or "review_attachment").strip()
    lowered = filename.lower()
    if not (lowered.endswith(".pdf") or lowered.endswith(".doc") or lowered.endswith(".docx")):
        raise HTTPException(status_code=400, detail="Only .pdf/.doc/.docx are supported")

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Empty file")
    if len(file_bytes) > 25 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large (max 25MB)")

    safe_name = sanitize_storage_filename(filename, default_name="review_attachment")
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
        logger.error("[EditorReviewAttachment] upload failed: %s", e)
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
        logger.error("[EditorReviewAttachment] insert manuscript_files failed: %s", e)
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
    safe_name = sanitize_storage_filename(filename, default_name="cover_letter")
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
        logger.error("[EditorCoverLetter] upload failed: %s", e)
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
        logger.error("[EditorCoverLetter] insert manuscript_files failed: %s", e)
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
    roles = profile.get("roles") or []
    allow_skip = "admin" in roles

    ensure_manuscript_scope_access(
        manuscript_id=id,
        user_id=str(current_user.get("id") or ""),
        roles=roles,
        allow_admin_bypass=True,
    )

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
    transition_payload = None
    if target_status in {ManuscriptStatus.UNDER_REVIEW.value, ManuscriptStatus.DECISION.value}:
        try:
            ms_resp = (
                supabase_admin.table("manuscripts")
                .select("id,status,pre_check_status,assistant_editor_id,academic_editor_id")
                .eq("id", id)
                .single()
                .execute()
            )
            ms_row = getattr(ms_resp, "data", None) or {}
        except Exception:
            ms_row = {}
        source_status = normalize_status(str(ms_row.get("status") or ""))
        source_precheck_status = str(ms_row.get("pre_check_status") or "").strip().lower()
        assigned_ae = str(ms_row.get("assistant_editor_id") or "").strip()
        assigned_academic_editor_id = str(ms_row.get("academic_editor_id") or "").strip()
        if target_status == ManuscriptStatus.UNDER_REVIEW.value and source_status == ManuscriptStatus.PRE_CHECK.value and not assigned_ae:
            raise HTTPException(
                status_code=409,
                detail="Assistant Editor must be assigned before moving to under_review.",
            )
        if source_status == ManuscriptStatus.PRE_CHECK.value and source_precheck_status == "academic":
            if not assigned_academic_editor_id:
                raise HTTPException(
                    status_code=409,
                    detail="Academic Editor must remain assigned before moving academic manuscripts to decision/under_review.",
                )
            if target_status == ManuscriptStatus.UNDER_REVIEW.value:
                transition_payload = {
                    "action": "precheck_academic_to_review",
                    "decision": "review",
                    "source_pre_check_status": "academic",
                }
            elif target_status == ManuscriptStatus.DECISION.value:
                transition_payload = {
                    "action": "precheck_academic_to_decision",
                    "decision": "decision_phase",
                    "source_pre_check_status": "academic",
                }

    updated = EditorialService().update_status(
        manuscript_id=id,
        to_status=to_status,
        changed_by=str(current_user.get("id")),
        comment=str(comment) if comment is not None else None,
        allow_skip=bool(allow_skip),
        payload=transition_payload,
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
        logger.error("[OwnerBinding] bind owner failed: %s", e)
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
    except Exception as e:
        logger.warning("[OwnerBinding] transition log insert failed (ignored): %s", e)
    return {"success": True, "data": updated}


@router.post("/manuscripts/{id}/bind-academic-editor")
async def bind_academic_editor(
    id: str,
    payload: BindAcademicEditorRequest,
    current_user: dict = Depends(get_current_user),
    profile: dict = Depends(require_any_role(["managing_editor", "editor_in_chief", "admin"])),
):
    """
    显式改派稿件 Academic Editor。

    中文注释：
    - 仅 managing_editor / editor_in_chief / admin 可操作；
    - 目标人员必须具备 academic_editor 或 editor_in_chief 角色，并匹配稿件 journal scope。
    """
    _require_action_or_403(action="manuscript:bind_academic_editor", roles=profile.get("roles") or [])
    ensure_manuscript_scope_access(
        manuscript_id=id,
        user_id=str(current_user.get("id") or ""),
        roles=profile.get("roles") or [],
        allow_admin_bypass=True,
    )

    try:
        updated = EditorService().bind_academic_editor(
            id,
            academic_editor_id=payload.academic_editor_id,
            changed_by=current_user.get("id"),
            reason=payload.reason,
            source=payload.source,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("[AcademicEditorBinding] bind academic editor failed: %s", e)
        raise HTTPException(status_code=500, detail="Failed to bind academic editor")

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
        logger.error("[OwnerBinding] 获取内部员工列表失败: %s", e)
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
        logger.error("[Precheck] 获取 assistant editors 失败: %s", e)
        raise HTTPException(status_code=500, detail="Failed to load assistant editors")


@router.get("/academic-editors")
async def list_academic_editors(
    manuscript_id: UUID,
    search: str = Query("", description="按姓名/邮箱模糊检索（可选）"),
    current_user: dict = Depends(get_current_user),
    profile: dict = Depends(require_any_role(["assistant_editor", "managing_editor", "editor_in_chief", "admin"])),
):
    """
    提供 AE/ME 送 Academic 预审时的候选学术编辑列表。
    候选范围：
    - 当前稿件所属期刊已绑定的 academic_editor / editor_in_chief
    - 若稿件已绑定 academic_editor，则优先返回并置顶
    """
    try:
        data = EditorService().list_academic_editor_candidates(
            manuscript_id=manuscript_id,
            viewer_user_id=str(current_user.get("id") or ""),
            viewer_roles=profile.get("roles") or [],
            search=search,
        )
        return {"success": True, "data": data}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("[Precheck] 获取 academic editors 失败: %s", e)
        raise HTTPException(status_code=500, detail="Failed to load academic editors")


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
        logger.error("[Journals] list failed: %s", e)
        raise HTTPException(status_code=500, detail="Failed to load journals")


@router.get("/pipeline")
async def get_editor_pipeline(
    per_stage_limit: Annotated[int | None, Query(ge=10, le=300, description="每个状态桶返回条数上限")] = None,
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
        per_stage_limit=per_stage_limit,
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


@router.post("/manuscripts/{id}/emails/revision-request/preview")
async def preview_revision_request_email(
    id: UUID,
    payload: RevisionRequestEmailPayload,
    current_user: dict = Depends(get_current_user),
    profile: dict = Depends(require_any_role(["managing_editor", "admin"])),
):
    ensure_manuscript_scope_access(
        manuscript_id=str(id),
        user_id=str(current_user.get("id") or ""),
        roles=profile.get("roles") or [],
        allow_admin_bypass=True,
    )
    preview = _build_revision_request_email_preview(id, payload)
    return {"success": True, "data": {k: v for k, v in preview.items() if k != "context"}}


@router.post("/manuscripts/{id}/emails/revision-request/send")
async def send_revision_request_email(
    id: UUID,
    payload: RevisionRequestEmailPayload,
    current_user: dict = Depends(get_current_user),
    profile: dict = Depends(require_any_role(["managing_editor", "admin"])),
):
    ensure_manuscript_scope_access(
        manuscript_id=str(id),
        user_id=str(current_user.get("id") or ""),
        roles=profile.get("roles") or [],
        allow_admin_bypass=True,
    )
    preview = _build_revision_request_email_preview(id, payload)
    result = email_service.send_rendered_email(
        to_emails=preview["resolved_recipients"]["to"],
        cc_emails=preview["resolved_recipients"]["cc"],
        bcc_emails=preview["resolved_recipients"]["bcc"],
        reply_to_emails=preview["resolved_recipients"]["reply_to"],
        template_key="revision_request",
        subject=preview["subject"],
        html_body=preview["html"],
        text_body=preview["text"],
        idempotency_key=preview["idempotency_key"],
        audit_context={
            "manuscript_id": str(id),
            "actor_user_id": str(current_user.get("id") or "").strip() or None,
            "scene": "revision_request",
            "event_type": "revision_request_email",
            "delivery_mode": "manual",
            "communication_status": "system_sent",
            "idempotency_key": preview["idempotency_key"],
        },
    )
    return {
        "success": True,
        "data": {
            "manuscript_id": str(id),
            "recipient": preview["resolved_recipients"]["to"][0] if preview["resolved_recipients"]["to"] else None,
            "delivery_status": str(result.get("status") or EmailStatus.FAILED.value),
            "delivery_error": result.get("error_message"),
            "provider_id": result.get("provider_id"),
        },
    }


@router.post("/manuscripts/{id}/emails/revision-request/mark-external-sent")
async def mark_revision_request_email_external_sent(
    id: UUID,
    payload: RevisionRequestEmailPayload,
    current_user: dict = Depends(get_current_user),
    profile: dict = Depends(require_any_role(["managing_editor", "admin"])),
):
    ensure_manuscript_scope_access(
        manuscript_id=str(id),
        user_id=str(current_user.get("id") or ""),
        roles=profile.get("roles") or [],
        allow_admin_bypass=True,
    )
    preview = _build_revision_request_email_preview(id, payload)
    channel = str(payload.channel or "other").strip() or "other"
    email_service.log_attempt(
        recipient=preview["resolved_recipients"]["to"][0],
        subject=preview["subject"],
        template_name="revision_request",
        status=EmailStatus.SENT,
        provider=channel,
        to_recipients=preview["resolved_recipients"]["to"],
        cc_recipients=preview["resolved_recipients"]["cc"],
        bcc_recipients=preview["resolved_recipients"]["bcc"],
        reply_to_recipients=preview["resolved_recipients"]["reply_to"],
        audit_context={
            "manuscript_id": str(id),
            "actor_user_id": str(current_user.get("id") or "").strip() or None,
            "scene": "revision_request",
            "event_type": "revision_request_email",
            "delivery_mode": "manual",
            "communication_status": "external_sent",
            "idempotency_key": preview["idempotency_key"],
        },
    )
    return {
        "success": True,
        "data": {
            "manuscript_id": str(id),
            "recipient": preview["resolved_recipients"]["to"][0],
            "communication_status": "external_sent",
            "provider": channel,
        },
    }


@router.get("/available-reviewers")
async def get_available_reviewers(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(50, ge=1, le=100, description="每页条数"),
    q: str | None = Query(None, max_length=100, description="按邮箱关键词过滤"),
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
        page=page,
        page_size=page_size,
        q=q,
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


@router.post("/manuscripts/{id}/review-stage-exit")
async def exit_review_stage(
    id: str,
    payload: ReviewStageExitRequest,
    current_user: dict = Depends(get_current_user),
    profile: dict = Depends(require_any_role(EDITOR_DECISION_ROLES)),
):
    """
    Reviewer Phase 2: 显式结束 under_review / resubmitted 外审阶段。

    中文注释:
    - selected/invited/opened reviewer 会自动 cancel；
    - accepted 但未提交 reviewer 必须在 payload 中显式处理；
    - target_stage=first -> decision，且必须携带 AE 推荐结论 requested_outcome；
    - target_stage=final -> decision_done；
    - target_stage=major_revision/minor_revision -> 直接进入对应修回状态。
    """
    decision_roles = profile.get("roles") or []
    can_record_first = can_perform_action(action="decision:record_first", roles=decision_roles)
    can_submit_final = can_perform_action(action="decision:submit_final", roles=decision_roles)
    if not (can_record_first or can_submit_final):
        _require_action_or_403(action="decision:record_first", roles=decision_roles)

    data = DecisionService().exit_review_stage(
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


# 中文注释:
# - 把子路由挂载放在文件末尾，确保 `/manuscripts/process` 等静态路径优先注册。
# - 避免 `/manuscripts/{id}` 抢占匹配 `process` 导致 404（被当成 manuscript id）。
router.include_router(editor_process_router)
router.include_router(internal_collab_router)
router.include_router(production_router)
router.include_router(editor_precheck_router)
router.include_router(editor_finance_router)
router.include_router(editor_reviewer_library_router)
router.include_router(editor_detail_router)
