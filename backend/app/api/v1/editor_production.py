from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form
from pydantic import BaseModel, ConfigDict, EmailStr, field_validator

from app.api.v1.editor_common import resolve_author_notification_target
from app.core.auth_utils import get_current_user
from app.core.email_normalization import normalize_email
from app.core.journal_scope import ensure_manuscript_scope_access
from app.core.mail import email_service
from app.core.roles import require_any_role
from app.lib.api_client import supabase_admin
from app.models.email_log import EmailStatus
from app.models.production_workspace import (
    CreateProductionCycleRequest, 
    UpdateProductionCycleEditorsRequest,
    UpdateProductionCycleAssignmentsRequest,
    TransitionProductionCycleRequest,
)
from app.services.production_service import ProductionService
from app.services.production_workspace_service import ProductionWorkspaceService

# 与 editor.py 保持一致：这些角色可进入 Editor Command Center。
EDITOR_SCOPE_COMPAT_ROLES = [
    "admin",
    "managing_editor",
    "assistant_editor",
    "production_editor",
    "editor_in_chief",
]

router = APIRouter(tags=["Editor Command Center"])


class ProofreadingEmailPayload(BaseModel):
    model_config = ConfigDict(extra="ignore")

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


def _ensure_proofreading_email_context(manuscript_id: str, cycle_id: str) -> dict[str, Any]:
    cycle_resp = (
        supabase_admin.table("production_cycles")
        .select("id, manuscript_id, status, proofreader_author_id")
        .eq("id", str(cycle_id))
        .eq("manuscript_id", str(manuscript_id))
        .single()
        .execute()
    )
    cycle = getattr(cycle_resp, "data", None) or {}
    if not cycle:
        raise HTTPException(status_code=404, detail="Production cycle not found")

    cycle_status = str(cycle.get("status") or "").strip().lower()
    if cycle_status != "awaiting_author":
        raise HTTPException(status_code=409, detail="Proofreading email can only be sent while awaiting author")

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

    journal_id = str(manuscript.get("journal_id") or "").strip()
    if journal_id:
        try:
            jr_resp = (
                supabase_admin.table("journals")
                .select("public_editorial_email")
                .eq("id", journal_id)
                .single()
                .execute()
            )
            journal = getattr(jr_resp, "data", None) or {}
            journal_public_editorial_email = normalize_email(journal.get("public_editorial_email"))
            if journal_public_editorial_email:
                manuscript["journal_public_editorial_email"] = journal_public_editorial_email
        except Exception:
            pass

    target = resolve_author_notification_target(
        manuscript=manuscript,
        manuscript_id=str(manuscript_id),
        supabase_client=supabase_admin,
    )
    if not target.get("recipient_email"):
        raise HTTPException(status_code=422, detail="No author email available for proofreading delivery")

    manuscript_title = str(manuscript.get("title") or "Manuscript").strip() or "Manuscript"
    recipient_name = str(target.get("recipient_name") or "Author").strip() or "Author"
    return {
        "cycle": cycle,
        "manuscript": manuscript,
        "target": target,
        "manuscript_title": manuscript_title,
        "recipient_name": recipient_name,
    }


def _resolve_proofreading_email_envelope(
    *,
    target: dict[str, Any],
    payload: ProofreadingEmailPayload,
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


def _build_proofreading_email_preview(
    manuscript_id: str,
    cycle_id: str,
    payload: ProofreadingEmailPayload,
) -> dict[str, Any]:
    if not payload.editor_message:
        raise HTTPException(status_code=422, detail="editor_message is required")

    context = _ensure_proofreading_email_context(manuscript_id, cycle_id)
    subject = str(payload.subject_override or "Proofreading Required").strip() or "Proofreading Required"
    default_html = email_service.render_template(
        "status_update.html",
        {
            "recipient_name": context["recipient_name"],
            "manuscript_title": context["manuscript_title"],
            "decision_label": "Proofreading Required",
            "comment": payload.editor_message,
        },
    )
    html = str(payload.html_override or default_html).strip() or default_html
    envelope = _resolve_proofreading_email_envelope(target=context["target"], payload=payload)
    return {
        "manuscript_id": str(manuscript_id),
        "cycle_id": str(cycle_id),
        "recipient_source": context["target"].get("source"),
        "resolved_recipients": envelope,
        "subject": subject,
        "html": html,
        "text": email_service.derive_plain_text_from_html(html),
        "reply_to": envelope["reply_to"],
        "attachments": [],
        "delivery_mode": "manual",
        "idempotency_key": str(payload.idempotency_key or f"proofreading-request/{cycle_id}"),
        "can_send": True,
        "context": context,
    }


def _enforce_scope_for_management_roles(*, manuscript_id: str, current_user: dict, profile: dict) -> None:
    roles = profile.get("roles") or []
    role_set = {str(role).strip().lower() for role in roles if str(role).strip()}
    if "admin" in role_set:
        return
    if role_set.intersection({"managing_editor", "editor_in_chief"}):
        ensure_manuscript_scope_access(
            manuscript_id=str(manuscript_id),
            user_id=str(current_user.get("id") or ""),
            roles=roles,
            allow_admin_bypass=True,
        )


@router.post("/manuscripts/{id}/production/advance")
async def advance_production_stage(
    id: str,
    current_user: dict = Depends(get_current_user),
    profile: dict = Depends(require_any_role(["managing_editor", "admin"])),
):
    """
    Feature 031: 录用后出版流水线 - 前进一个阶段（approved->layout->english_editing->proofreading->published）。
    """
    _enforce_scope_for_management_roles(manuscript_id=id, current_user=current_user, profile=profile)
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
    _enforce_scope_for_management_roles(manuscript_id=id, current_user=current_user, profile=profile)
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


@router.get("/manuscripts/{id}/production-workspace")
async def get_production_workspace_context(
    id: str,
    current_user: dict = Depends(get_current_user),
    profile: dict = Depends(require_any_role(EDITOR_SCOPE_COMPAT_ROLES)),
):
    """
    Feature 042: 编辑端生产工作间上下文。
    """
    _enforce_scope_for_management_roles(manuscript_id=id, current_user=current_user, profile=profile)
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
    _enforce_scope_for_management_roles(manuscript_id=id, current_user=current_user, profile=profile)
    data = ProductionWorkspaceService().create_cycle(
        manuscript_id=id,
        user_id=str(current_user.get("id") or ""),
        profile_roles=profile.get("roles") or [],
        request=payload,
    )
    return {"success": True, "data": {"cycle": data}}


@router.patch("/manuscripts/{id}/production-cycles/{cycle_id}/editors")
async def update_production_cycle_editors(
    id: str,
    cycle_id: str,
    payload: UpdateProductionCycleEditorsRequest,
    current_user: dict = Depends(get_current_user),
    profile: dict = Depends(require_any_role(["managing_editor", "editor_in_chief", "admin"])),
):
    """
    Feature 042B: 更新生产轮次的负责人/协作者列表（仅 ME/EIC/Admin）。
    """
    _enforce_scope_for_management_roles(manuscript_id=id, current_user=current_user, profile=profile)
    data = ProductionWorkspaceService().update_cycle_editors(
        manuscript_id=id,
        cycle_id=cycle_id,
        user_id=str(current_user.get("id") or ""),
        profile_roles=profile.get("roles") or [],
        request=payload,
    )
    return {"success": True, "data": {"cycle": data}}

@router.patch("/manuscripts/{id}/production-cycles/{cycle_id}/assignments")
async def update_production_cycle_assignments(
    id: str,
    cycle_id: str,
    payload: UpdateProductionCycleAssignmentsRequest,
    current_user: dict = Depends(get_current_user),
    profile: dict = Depends(require_any_role(["managing_editor", "editor_in_chief", "admin"])),
):
    _enforce_scope_for_management_roles(manuscript_id=id, current_user=current_user, profile=profile)
    data = ProductionWorkspaceService().update_assignments(
        manuscript_id=id,
        cycle_id=cycle_id,
        user_id=str(current_user.get("id") or ""),
        profile_roles=profile.get("roles") or [],
        request=payload,
    )
    return {"success": True, "data": {"cycle": data}}


@router.post("/manuscripts/{id}/production-cycles/{cycle_id}/artifacts")
async def upload_production_artifact(
    id: str,
    cycle_id: str,
    artifact_kind: str = Form(...),
    version_note: str = Form(""),
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
    profile: dict = Depends(require_any_role(EDITOR_SCOPE_COMPAT_ROLES)),
):
    _enforce_scope_for_management_roles(manuscript_id=id, current_user=current_user, profile=profile)
    raw = await file.read()
    data = ProductionWorkspaceService().upload_artifact(
        manuscript_id=id,
        cycle_id=cycle_id,
        user_id=str(current_user.get("id") or ""),
        profile_roles=profile.get("roles") or [],
        artifact_kind=artifact_kind,
        filename=file.filename or "artifact.bin",
        content=raw,
        version_note=version_note,
        content_type=file.content_type,
    )
    
    # Locate the created artifact in the returned cycle
    artifacts = data.get("artifacts") or []
    if artifacts:
        # Just grab the last one or something that matches
        artifacts.sort(key=lambda a: a.get("created_at") or "", reverse=True)
        artifact = artifacts[0]
    else:
        # Fallback
        artifact = {"artifact_kind": artifact_kind}
        
    return {"success": True, "data": {"cycle": data, "artifact": artifact}}


@router.post("/manuscripts/{id}/production-cycles/{cycle_id}/transitions")
async def transition_production_cycle(
    id: str,
    cycle_id: str,
    payload: TransitionProductionCycleRequest,
    current_user: dict = Depends(get_current_user),
    profile: dict = Depends(require_any_role(EDITOR_SCOPE_COMPAT_ROLES)),
):
    _enforce_scope_for_management_roles(manuscript_id=id, current_user=current_user, profile=profile)
    data = ProductionWorkspaceService().transition_stage(
        manuscript_id=id,
        cycle_id=cycle_id,
        user_id=str(current_user.get("id") or ""),
        profile_roles=profile.get("roles") or [],
        target_stage=payload.target_stage,
        comment=payload.comment,
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
    profile: dict = Depends(require_any_role(["managing_editor", "production_editor", "editor_in_chief", "admin"])),
):
    """
    Feature 042: 上传生产轮次清样并进入 awaiting_author。
    """
    _enforce_scope_for_management_roles(manuscript_id=id, current_user=current_user, profile=profile)
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
    profile: dict = Depends(require_any_role(["managing_editor", "production_editor", "editor_in_chief", "admin"])),
):
    """
    Feature 042: 编辑端获取清样 signed URL。
    """
    _enforce_scope_for_management_roles(manuscript_id=id, current_user=current_user, profile=profile)
    signed_url = ProductionWorkspaceService().get_galley_signed_url(
        manuscript_id=id,
        cycle_id=cycle_id,
        user_id=str(current_user.get("id") or ""),
        profile_roles=profile.get("roles") or [],
    )
    return {"success": True, "data": {"signed_url": signed_url}}


@router.post("/manuscripts/{id}/production-cycles/{cycle_id}/proofreading-email/preview")
async def preview_proofreading_email(
    id: str,
    cycle_id: str,
    payload: ProofreadingEmailPayload,
    current_user: dict = Depends(get_current_user),
    profile: dict = Depends(require_any_role(["managing_editor", "production_editor", "editor_in_chief", "admin"])),
):
    _enforce_scope_for_management_roles(manuscript_id=id, current_user=current_user, profile=profile)
    preview = _build_proofreading_email_preview(id, cycle_id, payload)
    return {"success": True, "data": {k: v for k, v in preview.items() if k != "context"}}


@router.post("/manuscripts/{id}/production-cycles/{cycle_id}/proofreading-email/send")
async def send_proofreading_email(
    id: str,
    cycle_id: str,
    payload: ProofreadingEmailPayload,
    current_user: dict = Depends(get_current_user),
    profile: dict = Depends(require_any_role(["managing_editor", "production_editor", "editor_in_chief", "admin"])),
):
    _enforce_scope_for_management_roles(manuscript_id=id, current_user=current_user, profile=profile)
    preview = _build_proofreading_email_preview(id, cycle_id, payload)
    result = email_service.send_rendered_email(
        to_emails=preview["resolved_recipients"]["to"],
        cc_emails=preview["resolved_recipients"]["cc"],
        bcc_emails=preview["resolved_recipients"]["bcc"],
        reply_to_emails=preview["resolved_recipients"]["reply_to"],
        template_key="proofreading_request",
        subject=preview["subject"],
        html_body=preview["html"],
        text_body=preview["text"],
        idempotency_key=preview["idempotency_key"],
        audit_context={
            "manuscript_id": str(id),
            "actor_user_id": str(current_user.get("id") or "").strip() or None,
            "scene": "proofreading",
            "event_type": "proofreading_request_email",
            "delivery_mode": "manual",
            "communication_status": "system_sent",
            "idempotency_key": preview["idempotency_key"],
        },
    )
    return {
        "success": True,
        "data": {
            "manuscript_id": str(id),
            "cycle_id": str(cycle_id),
            "recipient": preview["resolved_recipients"]["to"][0] if preview["resolved_recipients"]["to"] else None,
            "delivery_status": str(result.get("status") or EmailStatus.FAILED.value),
            "delivery_error": result.get("error_message"),
            "provider_id": result.get("provider_id"),
        },
    }


@router.post("/manuscripts/{id}/production-cycles/{cycle_id}/proofreading-email/mark-external-sent")
async def mark_proofreading_email_external_sent(
    id: str,
    cycle_id: str,
    payload: ProofreadingEmailPayload,
    current_user: dict = Depends(get_current_user),
    profile: dict = Depends(require_any_role(["managing_editor", "production_editor", "editor_in_chief", "admin"])),
):
    _enforce_scope_for_management_roles(manuscript_id=id, current_user=current_user, profile=profile)
    preview = _build_proofreading_email_preview(id, cycle_id, payload)
    channel = str(payload.channel or "other").strip() or "other"
    email_service.log_attempt(
        recipient=preview["resolved_recipients"]["to"][0],
        subject=preview["subject"],
        template_name="proofreading_request",
        status=EmailStatus.SENT,
        provider=channel,
        to_recipients=preview["resolved_recipients"]["to"],
        cc_recipients=preview["resolved_recipients"]["cc"],
        bcc_recipients=preview["resolved_recipients"]["bcc"],
        reply_to_recipients=preview["resolved_recipients"]["reply_to"],
        audit_context={
            "manuscript_id": str(id),
            "actor_user_id": str(current_user.get("id") or "").strip() or None,
            "scene": "proofreading",
            "event_type": "proofreading_request_email",
            "delivery_mode": "manual",
            "communication_status": "external_sent",
            "idempotency_key": preview["idempotency_key"],
        },
    )
    return {
        "success": True,
        "data": {
            "manuscript_id": str(id),
            "cycle_id": str(cycle_id),
            "recipient": preview["resolved_recipients"]["to"][0],
            "communication_status": "external_sent",
            "provider": channel,
        },
    }


@router.post("/manuscripts/{id}/production-cycles/{cycle_id}/approve")
async def approve_production_cycle(
    id: str,
    cycle_id: str,
    current_user: dict = Depends(get_current_user),
    profile: dict = Depends(require_any_role(["managing_editor", "production_editor", "editor_in_chief", "admin"])),
):
    """
    Feature 042: 编辑确认发布前核准（approved_for_publish）。
    """
    _enforce_scope_for_management_roles(manuscript_id=id, current_user=current_user, profile=profile)
    data = ProductionWorkspaceService().approve_cycle(
        manuscript_id=id,
        cycle_id=cycle_id,
        user_id=str(current_user.get("id") or ""),
        profile_roles=profile.get("roles") or [],
    )
    return {"success": True, "data": data}


@router.get("/production/queue")
async def list_production_queue(
    limit: int = Query(50, ge=1, le=200),
    current_user: dict = Depends(get_current_user),
    profile: dict = Depends(require_any_role(["production_editor", "admin"])),
):
    """
    Production Editor Queue:
    - 返回当前 production_editor 被分配（layout_editor_id）的活跃 production cycles。
    """
    data = ProductionWorkspaceService().list_my_queue(
        user_id=str(current_user.get("id") or ""),
        profile_roles=profile.get("roles") or [],
        limit=limit,
    )
    return {"success": True, "data": data}
