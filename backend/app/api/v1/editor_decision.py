from __future__ import annotations

import os
from datetime import datetime, timezone

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Body,
    Depends,
    File,
    HTTPException,
    UploadFile,
)

from app.api.v1.editor_common import (
    extract_supabase_data,
    extract_supabase_error,
    require_action_or_403,
)
from app.core.auth_utils import get_current_user
from app.core.journal_scope import ensure_manuscript_scope_access
from app.core.role_matrix import can_perform_action
from app.core.roles import require_any_role
from app.lib.api_client import supabase_admin
from app.models.manuscript import ManuscriptStatus, normalize_status
from app.models.decision import DecisionSubmitRequest
from app.models.revision import RevisionCreate, RevisionRequestResponse
from app.services.decision_service import DecisionService
from app.services.notification_service import NotificationService
from app.services.revision_service import RevisionService


# 与 editor.py 保持一致：这些角色可进入 Decision Workspace 相关端点。
EDITOR_DECISION_ROLES = ["admin", "managing_editor", "assistant_editor", "editor_in_chief"]

router = APIRouter(tags=["Editor Command Center"])


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
        require_action_or_403(action="decision:record_first", roles=decision_roles)

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
        require_action_or_403(action="decision:submit_final", roles=decision_roles)
    else:
        can_record_first = can_perform_action(action="decision:record_first", roles=decision_roles)
        can_submit_final = can_perform_action(action="decision:submit_final", roles=decision_roles)
        if not (can_record_first or can_submit_final):
            require_action_or_403(action="decision:record_first", roles=decision_roles)

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
    require_action_or_403(action="decision:record_first", roles=profile.get("roles") or [])

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
    require_action_or_403(action="decision:record_first", roles=profile.get("roles") or [])

    signed_url = DecisionService().get_attachment_signed_url_for_editor(
        manuscript_id=id,
        attachment_id=attachment_id,
        user_id=str(current_user.get("id") or ""),
        profile_roles=profile.get("roles") or [],
    )
    return {"success": True, "data": {"signed_url": signed_url}}


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
    1. 只能由 ME 或 Admin 发起。
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
                    prof = (
                        supabase_admin.table("user_profiles")
                        .select("email, full_name")
                        .eq("id", str(author_id))
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
                            subject="Revision Requested",
                            template_name="status_update.html",
                            context={
                                "recipient_name": recipient_name,
                                "manuscript_title": title,
                                "decision_label": f"{request.decision_type.capitalize()} Revision Requested",
                                "comment": request.comment or "Please check the portal for details.",
                            },
                        )
                except Exception as e:
                    print(f"[Email] Failed to send revision email: {e}")

    except Exception as e:
        print(f"[Notifications] Failed to send revision notification: {e}")

    return RevisionRequestResponse(data=result["data"]["revision"])


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
    提交最终录用或退回决策（legacy endpoint）
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
    require_action_or_403(action="decision:submit_final", roles=roles or ["admin"])

    ensure_manuscript_scope_access(
        manuscript_id=manuscript_id,
        user_id=str(current_user.get("id") or ""),
        roles=roles or ["admin"],
        allow_admin_bypass=True,
    )

    try:
        try:
            manuscript_row = (
                supabase_admin.table("manuscripts").select("status").eq("id", manuscript_id).single().execute()
            )
        except Exception as e:
            raise HTTPException(status_code=404, detail="Manuscript not found") from e

        manuscript = getattr(manuscript_row, "data", None) or {}
        current_status = normalize_status(str(manuscript.get("status") or ""))
        if not current_status:
            raise HTTPException(status_code=404, detail="Manuscript not found")

        allowed_statuses = {ManuscriptStatus.DECISION.value, ManuscriptStatus.DECISION_DONE.value}
        # 中文注释:
        # - Accept 后（approved）仍允许再次“accept”以便调整 APC / 触发 invoice upsert（幂等）。
        # - Reject 不允许在 approved 后执行，避免破坏已进入 Production 的稿件。
        if decision == "accept":
            allowed_statuses.add("approved")
        if current_status not in allowed_statuses:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Decision is only allowed in {ManuscriptStatus.DECISION.value}/"
                    f"{ManuscriptStatus.DECISION_DONE.value}. Current: {current_status}"
                ),
            )

        # 更新稿件状态
        if decision == "accept":
            update_data = {"status": "approved"}
        else:
            update_data = {"status": "rejected", "reject_comment": comment}

        # 执行更新（兼容历史列缺失）
        try:
            response = supabase_admin.table("manuscripts").update(update_data).eq("id", manuscript_id).execute()
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

        error = extract_supabase_error(response)
        if error and _is_missing_column_error(str(error)):
            response = (
                supabase_admin.table("manuscripts").update({"status": update_data["status"]}).eq("id", manuscript_id).execute()
            )
        elif error:
            raise HTTPException(status_code=500, detail="Failed to submit decision")

        data = extract_supabase_data(response) or []
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
                inv_upsert = supabase_admin.table("invoices").upsert(invoice_payload, on_conflict="manuscript_id").execute()
                inv_rows = getattr(inv_upsert, "data", None) or []
                if inv_rows:
                    invoice_id = (inv_rows[0] or {}).get("id")
            except Exception as e:
                print(f"[Financial] Failed to upsert invoice: {e}")
                raise HTTPException(status_code=500, detail="Failed to create invoice")

            # === Feature 026: 自动生成并持久化 Invoice PDF（后台任务） ===
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

                        from app.services.invoice_pdf_service import generate_and_store_invoice_pdf_safe

                        background_tasks.add_task(
                            generate_and_store_invoice_pdf_safe,
                            invoice_id=UUID(str(invoice_id)),
                        )
                except Exception as e:
                    print(f"[InvoicePDF] enqueue failed (ignored): {e}")

        # === MVP: 决策后取消未完成的审稿任务（避免 Reviewer 继续看到该稿件）===
        try:
            (
                supabase_admin.table("review_assignments")
                .update({"status": "cancelled"})
                .eq("manuscript_id", manuscript_id)
                .eq("status", "pending")
                .execute()
            )
        except Exception as e:
            print(f"[Decision] cancel pending review_assignments failed (ignored): {e}")

        # === 通知中心 (Feature 011) ===
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
            decision_title = "Editorial Decision" if decision == "accept" else "Editorial Decision: Rejected"

            NotificationService().create_notification(
                user_id=str(author_id),
                manuscript_id=manuscript_id,
                type="decision",
                title=decision_title,
                content=f"Decision for '{manuscript_title}': {decision_label}.",
            )

            try:
                author_profile = (
                    supabase_admin.table("user_profiles").select("email").eq("id", str(author_id)).single().execute()
                )
                author_email = (getattr(author_profile, "data", None) or {}).get("email")
            except Exception:
                author_email = None

            if author_email and background_tasks is not None:
                from app.core.mail import email_service

                background_tasks.add_task(
                    email_service.send_email_background,
                    to_email=author_email,
                    subject=decision_title,
                    template_name="status_update.html",
                    context={
                        "recipient_name": author_email.split("@")[0].replace(".", " ").title(),
                        "manuscript_title": manuscript_title,
                        "decision_label": decision_label,
                        "comment": comment or "",
                    },
                )

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
                            "link": invoice_link,
                        },
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
                        "before": {"status": current_status, "apc_amount": None},
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
            "data": {"manuscript_id": manuscript_id, "decision": decision, "status": update_data["status"]},
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"Decision submission failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to submit decision")

