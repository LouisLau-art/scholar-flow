from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from app.core.mail import EmailService
from app.lib.api_client import supabase_admin


class ChaseScheduler:
    """
    自动催办调度器（P3: Automated Chasing）

    中文注释:
    1) 触发方式：通过内部接口 /api/v1/internal/cron/chase-reviews 手动/定时触发。
    2) 幂等性：仅处理 last_reminded_at 为空且 due_at <= now + 24h 的 pending 任务。
    3) 失败处理：SMTP 失败只记录日志，不抛异常；last_reminded_at 仅在发送成功后写入。
    """

    def __init__(self, email_service: Optional[EmailService] = None):
        self._email = email_service or EmailService()

    def run(self) -> Dict[str, int]:
        now = datetime.now(timezone.utc)
        threshold = now + timedelta(hours=24)

        processed_count = 0
        emails_sent = 0

        try:
            # 中文注释:
            # - 依赖 review_assignments.due_at 与 last_reminded_at 字段。
            # - select manuscripts(title) 让邮件内容更专业（可读性更强）。
            res = (
                supabase_admin.table("review_assignments")
                .select("id, reviewer_id, manuscript_id, due_at, last_reminded_at, manuscripts(title)")
                .eq("status", "pending")
                .is_("last_reminded_at", "null")
                .lte("due_at", threshold.isoformat())
                .execute()
            )
            assignments = getattr(res, "data", None) or []
        except Exception as e:
            print(f"[ChaseScheduler] 查询失败（可能缺表/缺列）: {e}")
            return {"processed_count": 0, "emails_sent": 0}

        for row in assignments:
            processed_count += 1
            assignment_id = row.get("id")
            reviewer_id = row.get("reviewer_id")
            manuscript_id = row.get("manuscript_id")
            due_at = row.get("due_at")
            manuscript = row.get("manuscripts") or {}
            manuscript_title = manuscript.get("title") or "Manuscript"

            reviewer_email = self._get_reviewer_email(reviewer_id)
            if not reviewer_email:
                print(f"[ChaseScheduler] 缺少 reviewer email，跳过: reviewer_id={reviewer_id}")
                continue

            ok = self._email.send_template_email(
                to_email=reviewer_email,
                subject="Friendly Reminder: Review Deadline Approaching",
                template_name="review_reminder.html",
                context={
                    "subject": "Friendly Reminder: Review Deadline Approaching",
                    "recipient_name": reviewer_email.split("@")[0].replace(".", " ").title(),
                    "manuscript_title": manuscript_title,
                    "manuscript_id": manuscript_id,
                    "due_at": due_at,
                    "review_url": None,
                },
            )
            if not ok:
                continue

            emails_sent += 1
            try:
                supabase_admin.table("review_assignments").update(
                    {"last_reminded_at": now.isoformat()}
                ).eq("id", assignment_id).execute()
            except Exception as e:
                # 中文注释: 仅影响幂等标记，不影响本次 Cron 调用结果
                print(f"[ChaseScheduler] 写入 last_reminded_at 失败: {e}")

        return {"processed_count": processed_count, "emails_sent": emails_sent}

    def _get_reviewer_email(self, reviewer_id: Any) -> Optional[str]:
        if not reviewer_id:
            return None
        try:
            res = (
                supabase_admin.table("user_profiles")
                .select("email")
                .eq("id", str(reviewer_id))
                .single()
                .execute()
            )
            profile = getattr(res, "data", None) or {}
            email = (profile.get("email") or "").strip()
            return email or None
        except Exception:
            return None

