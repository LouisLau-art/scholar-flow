from datetime import datetime
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field, ConfigDict, model_validator

# --- Enums & Shared Types ---
# (User roles are typically strings in Supabase: "author", "reviewer", "managing_editor", "admin")
ALLOWED_USER_ROLES = {
    "author",
    "reviewer",
    "managing_editor",
    "assistant_editor",
    "editor_in_chief",
    "admin",
}

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
    role: str = Field(..., pattern="^(reviewer|managing_editor|assistant_editor|editor_in_chief|admin)$")

class UpdateRoleRequest(BaseModel):
    """
    T012: 修改用户角色请求
    """
    new_role: Optional[str] = Field(default=None)
    new_roles: Optional[List[str]] = Field(default=None)
    scope_journal_ids: Optional[List[UUID]] = Field(
        default=None,
        description="当角色包含 managing_editor/editor_in_chief 时可一次性提交绑定期刊列表",
    )
    reason: str = Field(..., min_length=10, description="Reason for role change is mandatory for audit trail")

    @model_validator(mode="after")
    def validate_role_payload(self):
        raw_roles = self.new_roles or ([self.new_role] if self.new_role else [])
        roles = [str(r).strip().lower() for r in raw_roles if str(r).strip()]
        if not roles:
            raise ValueError("At least one role is required")
        invalid = [r for r in roles if r not in ALLOWED_USER_ROLES]
        if invalid:
            raise ValueError(f"Invalid roles: {', '.join(sorted(set(invalid)))}")
        return self

    def resolved_roles(self) -> List[str]:
        raw_roles = self.new_roles or ([self.new_role] if self.new_role else [])
        dedup: List[str] = []
        seen: set[str] = set()
        for role in raw_roles:
            normalized = str(role).strip().lower()
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            dedup.append(normalized)
        return dedup

class InviteReviewerRequest(BaseModel):
    """
    T012: 邀请临时审稿人请求
    """
    email: EmailStr
    full_name: str = Field(..., min_length=1, max_length=100)
    manuscript_id: Optional[UUID] = None  # Context for the invitation


class ResetPasswordRequest(BaseModel):
    """
    Admin 重置密码请求。
    默认值遵循产品约定：12345678
    """

    temporary_password: str = Field(default="12345678", min_length=8, max_length=128)


class ResetPasswordResponse(BaseModel):
    """
    Admin 重置密码响应。
    """

    id: UUID
    email: Optional[EmailStr] = None
    temporary_password: str
    must_change_password: bool = True
