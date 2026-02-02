from datetime import datetime
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field
from pydantic.config import ConfigDict


NotificationType = Literal["submission", "review_invite", "decision", "chase", "system"]


class Notification(BaseModel):
    """
    通知实体（用于 API 返回）

    中文注释:
    - notifications 表由 Supabase 存储；此模型用于后端显式校验输出结构。
    """

    id: UUID
    user_id: UUID
    manuscript_id: Optional[UUID] = None
    type: NotificationType
    title: str = Field(..., max_length=255)
    content: str = Field(..., max_length=2000)
    is_read: bool = False
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class NotificationCreate(BaseModel):
    """
    创建通知的输入结构（服务端内部使用）
    """

    user_id: UUID
    manuscript_id: Optional[UUID] = None
    type: NotificationType
    title: str = Field(..., max_length=255)
    content: str = Field(..., max_length=2000)

