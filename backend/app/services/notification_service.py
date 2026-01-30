from __future__ import annotations

from typing import Any, Dict, List, Optional
from uuid import UUID

from app.lib.api_client import create_user_supabase_client, supabase_admin


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
        type: str,
        title: str,
        content: str,
    ) -> Optional[Dict[str, Any]]:
        try:
            payload = {
                "user_id": user_id,
                "manuscript_id": manuscript_id,
                "type": type,
                "title": title,
                "content": content,
                "is_read": False,
            }
            res = supabase_admin.table("notifications").insert(payload).execute()
            rows = getattr(res, "data", None) or []
            return rows[0] if rows else None
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

