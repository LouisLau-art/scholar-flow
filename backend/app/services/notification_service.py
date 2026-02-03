from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.lib.api_client import create_user_supabase_client, supabase_admin
from postgrest.exceptions import APIError


class NotificationService:
    """
    通知服务：封装 notifications 表的读写

    中文注释:
    1) 写入使用 supabase_admin（service_role），避免 RLS 导致写入失败。
    2) 用户读取/更新使用“用户态 client”（注入 JWT），确保 RLS 生效，防止越权。
    """

    def create_notification(
        self,
        *,
        user_id: str,
        manuscript_id: Optional[str],
        action_url: Optional[str] = None,
        type: str,
        title: str,
        content: str,
    ) -> Optional[Dict[str, Any]]:
        try:
            # Feature 011 UX: 通知点击跳转（action_url）
            if not action_url:
                if type == "review_invite":
                    action_url = "/dashboard?tab=reviewer"
                elif type == "chase":
                    action_url = "/dashboard?tab=reviewer"
                elif type == "system":
                    action_url = "/dashboard?tab=editor"
                elif manuscript_id:
                    action_url = f"/dashboard/author/manuscripts/{manuscript_id}"
                else:
                    action_url = "/dashboard/notifications"

            payload = {
                "user_id": user_id,
                "manuscript_id": manuscript_id,
                "action_url": action_url,
                "type": type,
                "title": title,
                "content": content,
                "is_read": False,
            }
            res = supabase_admin.table("notifications").insert(payload).execute()
            rows = getattr(res, "data", None) or []
            return rows[0] if rows else None
        except APIError as e:
            # 中文注释:
            # - 云端环境里可能存在“仅用于展示的 mock user_profiles”（不对应 auth.users）。
            # - notifications.user_id 有外键指向 auth.users(id)，因此对这类用户写通知会触发 23503。
            # - 该情况对主流程无影响，且会造成日志刷屏；这里静默忽略并返回 None。
            # supabase/postgrest 的 APIError 在不同版本里字段不完全一致，这里尽量从字符串中兜底解析。
            text = str(e).lower()
            code = str(getattr(e, "code", "") or "").lower()
            if "23503" in code or "23503" in text:
                if "notifications_user_id_fkey" in text or "foreign key" in text:
                    return None
            print(f"[Notifications] 创建失败: {e}")
            return None
        except Exception as e:
            print(f"[Notifications] 创建失败: {e}")
            return None

    def list_for_current_user(self, *, access_token: str, limit: int = 20) -> List[Dict[str, Any]]:
        client = create_user_supabase_client(access_token)
        res = (
            client.table("notifications")
            .select("*")
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return getattr(res, "data", None) or []

    def mark_read(self, *, access_token: str, notification_id: str) -> Optional[Dict[str, Any]]:
        client = create_user_supabase_client(access_token)
        res = (
            client.table("notifications")
            .update({"is_read": True})
            .eq("id", notification_id)
            .execute()
        )
        rows = getattr(res, "data", None) or []
        return rows[0] if rows else None
