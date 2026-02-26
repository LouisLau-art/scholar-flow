from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import BackgroundTasks, HTTPException

from app.services.notification_service import NotificationService


async def publish_manuscript_dev_impl(
    *,
    background_tasks: BackgroundTasks | None,
    current_user: dict[str, Any],
    manuscript_id: str,
    supabase_admin_client: Any,
    publish_manuscript_fn,
) -> dict[str, Any]:
    """发布稿件（搬运原逻辑）。"""
    try:
        # Feature 024：保留“直接发布”入口（MVP 提速），发布本身仍强制 Payment/Production Gate。
        # Feature 031 的线性阶段推进（layout/english_editing/proofreading）通过 /production/advance 完成。
        try:
            before = (
                supabase_admin_client.table("manuscripts")
                .select("status")
                .eq("id", manuscript_id)
                .single()
                .execute()
            )
            from_status = str((getattr(before, "data", None) or {}).get("status") or "")
        except Exception:
            from_status = ""
        published = publish_manuscript_fn(manuscript_id=manuscript_id)

        # Feature 031：尽力写入审计日志（不阻断主流程）
        try:
            now = datetime.now(timezone.utc).isoformat()
            supabase_admin_client.table("status_transition_logs").insert(
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
                supabase_admin_client.table("manuscripts")
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
                            supabase_admin_client.table("user_profiles")
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
