from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

from fastapi import BackgroundTasks, HTTPException

from app.models.manuscript import ManuscriptStatus, normalize_status
from app.services.notification_service import NotificationService


async def submit_final_decision_impl(
    *,
    background_tasks: BackgroundTasks | None,
    current_user: dict[str, Any],
    profile: dict[str, Any],
    manuscript_id: str,
    decision: str,
    comment: str,
    apc_amount: float | None,
    supabase_admin_client: Any,
    extract_error_fn,
    extract_data_fn,
    is_missing_column_error_fn,
    require_action_or_403_fn,
    ensure_manuscript_scope_access_fn,
) -> dict[str, Any]:
    """提交最终决策（搬运原逻辑）。"""
    # 验证决策类型
    if decision not in ["accept", "reject"]:
        raise HTTPException(status_code=400, detail="Invalid decision type")
    if decision == "accept":
        if apc_amount is None:
            raise HTTPException(status_code=400, detail="apc_amount is required for accept")
        if apc_amount < 0:
            raise HTTPException(status_code=400, detail="apc_amount must be >= 0")

    roles = profile.get("roles") if isinstance(profile, dict) else ["admin"]
    require_action_or_403_fn(action="decision:submit_final", roles=roles or ["admin"])

    ensure_manuscript_scope_access_fn(
        manuscript_id=manuscript_id,
        user_id=str(current_user.get("id") or ""),
        roles=roles or ["admin"],
        allow_admin_bypass=True,
    )

    try:
        try:
            manuscript_row = (
                supabase_admin_client.table("manuscripts")
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
        allowed_statuses = {
            ManuscriptStatus.DECISION.value,
            ManuscriptStatus.DECISION_DONE.value,
        }
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
            # 录用：仅进入“已录用/待发布”状态；发布必须通过 Financial Gate
            update_data = {"status": "approved"}
        else:
            # 拒稿：进入 rejected 终态（修回请走 /editor/revisions）
            update_data = {"status": "rejected", "reject_comment": comment}

        # 执行更新
        try:
            response = (
                supabase_admin_client.table("manuscripts")
                .update(update_data)
                .eq("id", manuscript_id)
                .execute()
            )
        except Exception as e:
            error_text = str(e)
            print(f"Decision update error: {error_text}")
            if is_missing_column_error_fn(error_text):
                response = (
                    supabase_admin_client.table("manuscripts")
                    .update({"status": update_data["status"]})
                    .eq("id", manuscript_id)
                    .execute()
                )
            else:
                raise

        error = extract_error_fn(response)
        if error and is_missing_column_error_fn(str(error)):
            response = (
                supabase_admin_client.table("manuscripts")
                .update({"status": update_data["status"]})
                .eq("id", manuscript_id)
                .execute()
            )
        elif error:
            raise HTTPException(status_code=500, detail="Failed to submit decision")

        data = extract_data_fn(response) or []
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
                inv_upsert = supabase_admin_client.table("invoices").upsert(
                    invoice_payload, on_conflict="manuscript_id"
                ).execute()
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
                            supabase_admin_client.table("invoices")
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
        try:
            supabase_admin_client.table("review_assignments").update({"status": "cancelled"}).eq(
                "manuscript_id", manuscript_id
            ).eq("status", "pending").execute()
        except Exception as e:
            print(f"[Decision] cancel pending review_assignments failed (ignored): {e}")

        # === 通知中心 (Feature 011) ===
        try:
            ms_res = (
                supabase_admin_client.table("manuscripts")
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
                    supabase_admin_client.table("user_profiles")
                    .select("email")
                    .eq("id", str(author_id))
                    .single()
                    .execute()
                )
                author_email = (getattr(author_profile, "data", None) or {}).get("email")
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
                        "recipient_name": author_email.split("@")[0].replace(".", " ").title(),
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
                            "link": invoice_link,
                        },
                    )

        # GAP-P1-05 / US3: legacy final decision 审计对齐（before/after/reason/source）
        try:
            now_log = datetime.now(timezone.utc).isoformat()
            supabase_admin_client.table("status_transition_logs").insert(
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
