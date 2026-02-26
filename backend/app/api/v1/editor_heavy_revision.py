from __future__ import annotations

from typing import Any

from fastapi import BackgroundTasks, HTTPException

from app.services.notification_service import NotificationService
from app.services.revision_service import RevisionService


async def request_revision_impl(
    *,
    request,
    profile: dict[str, Any],
    background_tasks: BackgroundTasks | None,
    supabase_admin_client: Any,
) -> Any:
    """Editor 请求修订（搬运原逻辑）。"""
    # MVP 业务规则:
    # - 上一轮如果是“小修”，Editor 不允许升级成“大修”；如确需升级，必须由 Admin 执行。
    try:
        roles = set((profile or {}).get("roles") or [])
        if request.decision_type == "major" and "admin" not in roles:
            latest = (
                supabase_admin_client.table("revisions")
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
                    prof = supabase_admin_client.table("user_profiles").select("email, full_name").eq("id", str(author_id)).single().execute()
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

    return result
