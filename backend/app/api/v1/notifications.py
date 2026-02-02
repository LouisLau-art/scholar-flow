from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.auth_utils import get_current_user
from app.services.notification_service import NotificationService

router = APIRouter(tags=["Notifications"])
security = HTTPBearer()


@router.get("/notifications")
async def list_notifications(
    limit: int = 20,
    _current_user: dict = Depends(get_current_user),
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    """
    获取当前用户的通知列表（RLS 生效）
    """
    service = NotificationService()
    rows = service.list_for_current_user(access_token=credentials.credentials, limit=limit)
    return {"success": True, "data": rows}


@router.patch("/notifications/{id}/read")
async def mark_notification_read(
    id: str,
    _current_user: dict = Depends(get_current_user),
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    """
    将通知标记为已读（仅允许更新自己的记录）
    """
    service = NotificationService()
    updated = service.mark_read(access_token=credentials.credentials, notification_id=id)
    if updated is None:
        # 中文注释: 可能是不存在或不属于当前用户（RLS 拦截导致 data 为空）
        raise HTTPException(status_code=404, detail="Notification not found")
    return {"success": True, "data": updated}

