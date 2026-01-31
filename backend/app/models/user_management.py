from datetime import datetime
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field, ConfigDict

# --- Enums & Shared Types ---
# (User roles are typically strings in Supabase: "author", "editor", "reviewer", "admin")

# --- Log Models (T008, T009, T010) ---

class RoleChangeLog(BaseModel):
    """
    User role modification audit log.
    T008: 记录用户角色变更历史
    """
    id: UUID
    user_id: UUID
    changed_by: UUID
    old_role: str
    new_role: str
    reason: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class AccountCreationLog(BaseModel):
    """
    Internal account creation audit log.
    T009: 记录内部账号创建操作
    """
    id: UUID
    created_user_id: UUID
    created_by: UUID
    initial_role: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class EmailNotificationLog(BaseModel):
    """
    Email notification log.
    T010: 记录关键邮件通知发送状态
    """
    id: UUID
    recipient_email: EmailStr
    notification_type: str  # e.g., "account_created", "reviewer_invite"
    status: str             # "sent", "failed"
    error_message: Optional[str] = None
    sent_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Response Models (T011) ---

class UserResponse(BaseModel):
    """
    Standard user profile response.
    T011: 用户详情响应
    """
    id: UUID
    email: EmailStr
    full_name: Optional[str] = None
    roles: List[str] = []
    created_at: datetime
    is_verified: bool = False  # Derived from email_confirmed_at

    model_config = ConfigDict(from_attributes=True)

class Pagination(BaseModel):
    """
    T011: 通用分页元数据
    """
    total: int
    page: int
    per_page: int
    total_pages: int

class UserListResponse(BaseModel):
    """
    T011: 用户列表响应
    """
    data: List[UserResponse]
    pagination: Pagination


# --- Request Models (T012) ---

class CreateUserRequest(BaseModel):
    """
    T012: 创建内部账号请求
    """
    email: EmailStr
    full_name: str = Field(..., min_length=1, max_length=100)
    role: str = Field(..., pattern="^(editor|reviewer|admin)$")  # 限制只能创建非 Author 角色

class UpdateRoleRequest(BaseModel):
    """
    T012: 修改用户角色请求
    """
    new_role: str = Field(..., pattern="^(author|editor|reviewer|admin)$")
    reason: str = Field(..., min_length=10, description="Reason for role change is mandatory for audit trail")

class InviteReviewerRequest(BaseModel):
    """
    T012: 邀请临时审稿人请求
    """
    email: EmailStr
    full_name: str = Field(..., min_length=1, max_length=100)
    manuscript_id: Optional[UUID] = None  # Context for the invitation