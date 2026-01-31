"""
用户管理相关数据模型
Feature: 017-super-admin-management
Created: 2026-01-31
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, EmailStr, field_validator
from pydantic.types import UUIDv1


# ============================================================================
# 审计日志模型
# ============================================================================

class RoleChangeLog(BaseModel):
    """角色变更记录模型"""
    id: UUIDv1
    user_id: UUIDv1
    operator_id: UUIDv1
    old_role: str = Field(..., pattern=r'^(author|editor|reviewer|admin)$')
    new_role: str = Field(..., pattern=r'^(author|editor|reviewer|admin)$')
    reason: str = Field(..., min_length=10, max_length=500)
    ip_address: Optional[str] = Field(None, max_length=45)
    user_agent: Optional[str] = None
    created_at: datetime

    @field_validator('old_role', 'new_role')
    @classmethod
    def validate_roles(cls, v: str) -> str:
        """验证角色值"""
        valid_roles = {'author', 'editor', 'reviewer', 'admin'}
        if v not in valid_roles:
            raise ValueError(f'Invalid role: {v}. Must be one of {valid_roles}')
        return v


class AccountCreationLog(BaseModel):
    """账号创建记录模型"""
    id: UUIDv1
    user_id: UUIDv1
    creator_id: UUIDv1
    creation_type: str = Field(..., pattern=r'^(internal_editor|temporary_reviewer)$')
    invitation_status: str = Field(
        default='pending',
        pattern=r'^(pending|sent|delivered|opened|failed)$'
    )
    invitation_sent_at: Optional[datetime] = None
    invitation_opened_at: Optional[datetime] = None
    created_at: datetime

    @field_validator('creation_type')
    @classmethod
    def validate_creation_type(cls, v: str) -> str:
        """验证创建类型"""
        valid_types = {'internal_editor', 'temporary_reviewer'}
        if v not in valid_types:
            raise ValueError(f'Invalid creation type: {v}. Must be one of {valid_types}')
        return v


class EmailNotificationLog(BaseModel):
    """邮件通知记录模型"""
    id: UUIDv1
    recipient_email: EmailStr
    template_type: str = Field(..., pattern=r'^(editor_account_created|reviewer_invitation)$')
    user_id: Optional[UUIDv1] = None
    status: str = Field(
        default='queued',
        pattern=r'^(queued|sent|delivered|opened|failed)$'
    )
    failure_reason: Optional[str] = None
    sent_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    opened_at: Optional[datetime] = None
    created_at: datetime

    @field_validator('status', 'failure_reason')
    @classmethod
    def validate_failure_reason(cls, v: str, info) -> str:
        """验证失败原因：当状态为failed时必须提供失败原因"""
        if info.data.get('status') == 'failed' and v is None:
            raise ValueError('failure_reason is required when status is "failed"')
        return v


# ============================================================================
# API 请求/响应模型
# ============================================================================

class Pagination(BaseModel):
    """分页信息模型"""
    page: int = Field(..., ge=1)
    per_page: int = Field(..., ge=1, le=100)
    total_pages: int = Field(..., ge=0)
    total_items: int = Field(..., ge=0)
    has_next: bool
    has_prev: bool


class User(BaseModel):
    """用户信息模型"""
    id: UUIDv1
    email: EmailStr
    name: str = Field(..., min_length=1, max_length=100)
    role: str = Field(..., pattern=r'^(author|editor|reviewer|admin)$')
    created_at: datetime
    last_sign_in_at: Optional[datetime] = None


class UserResponse(BaseModel):
    """用户详情响应模型"""
    id: UUIDv1
    email: EmailStr
    name: str
    role: str
    created_at: datetime
    last_sign_in_at: Optional[datetime] = None
    role_changes: list[RoleChangeLog] = Field(default_factory=list)


class UserListResponse(BaseModel):
    """用户列表响应模型"""
    users: list[User]
    pagination: Pagination


# ============================================================================
# API 请求模型
# ============================================================================

class CreateUserRequest(BaseModel):
    """创建用户请求模型"""
    email: EmailStr
    name: str = Field(..., min_length=1, max_length=100)
    role: str = Field(default='editor', pattern=r'^editor$')


class UpdateRoleRequest(BaseModel):
    """更新角色请求模型"""
    new_role: str = Field(..., pattern=r'^(editor|reviewer)$')
    reason: str = Field(..., min_length=10, max_length=500)


class InviteReviewerRequest(BaseModel):
    """邀请审稿人请求模型"""
    email: EmailStr
    name: str = Field(..., min_length=1, max_length=100)
    manuscript_id: Optional[UUIDv1] = None


class RoleChangeResponse(BaseModel):
    """角色变更响应模型"""
    success: bool
    message: str
    role_change: Optional[RoleChangeLog] = None


class RoleChangeListResponse(BaseModel):
    """角色变更历史响应模型"""
    role_changes: list[RoleChangeLog]
    total_count: int


class InviteReviewerResponse(BaseModel):
    """邀请审稿人响应模型"""
    success: bool
    message: str
    user_id: Optional[UUIDv1] = None
    invitation_sent: bool
