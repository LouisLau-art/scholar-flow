"""
用户管理 API 端点
Feature: 017-super-admin-management
Created: 2026-01-31
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.models.user_management import (
    User,
    UserResponse,
    UserListResponse,
    CreateUserRequest,
    UpdateRoleRequest,
    InviteReviewerRequest,
    RoleChangeResponse,
    RoleChangeListResponse,
    InviteReviewerResponse,
)
from app.services.user_management import UserManagementService
from app.core.auth import get_current_user, verify_admin_role


# ============================================================================
# API Router 初始化
# ============================================================================

router = APIRouter(prefix="/api/v1/admin/users", tags=["AdminUsers"])

# 初始化服务
user_service = UserManagementService()


# ============================================================================
# 依赖项
# ============================================================================

async def get_admin_user(
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())
) -> dict:
    """
    获取当前超级管理员用户

    Args:
        credentials: HTTP Bearer 认证凭据

    Returns:
        dict: 当前用户信息

    Raises:
        HTTPException: 401 未授权或 403 权限不足
    """
    user = await get_current_user(credentials)
    await verify_admin_role(user)
    return user


# ============================================================================
# API 端点
# ============================================================================

@router.get("/", response_model=UserListResponse)
async def get_users(
    page: int = 1,
    per_page: int = 20,
    search: Optional[str] = None,
    role: Optional[str] = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
    admin_user: dict = Depends(get_admin_user)
) -> UserListResponse:
    """
    获取用户列表

    Args:
        page: 页码（从1开始）
        per_page: 每页记录数（1-100）
        search: 搜索关键词（邮箱或姓名前缀匹配）
        role: 按角色筛选
        sort_by: 排序字段（created_at, name, email）
        sort_order: 排序方向（asc, desc）
        admin_user: 当前超级管理员用户

    Returns:
        UserListResponse: 用户列表和分页信息
    """
    # 验证分页参数
    if page < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Page must be >= 1"
        )

    if per_page < 1 or per_page > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Per page must be between 1 and 100"
        )

    # 验证排序参数
    valid_sort_fields = {"created_at", "name", "email"}
    if sort_by not in valid_sort_fields:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid sort_by field. Must be one of {valid_sort_fields}"
        )

    if sort_order not in {"asc", "desc"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Sort order must be 'asc' or 'desc'"
        )

    # 验证角色参数
    valid_roles = {"author", "editor", "reviewer", "admin"}
    if role and role not in valid_roles:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role. Must be one of {valid_roles}"
        )

    # 获取用户列表
    return await user_service.get_users(
        page=page,
        per_page=per_page,
        search=search,
        role=role,
        sort_by=sort_by,
        sort_order=sort_order
    )


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    request: CreateUserRequest,
    admin_user: dict = Depends(get_admin_user)
) -> UserResponse:
    """
    创建内部编辑账号

    Args:
        request: 创建用户请求
        admin_user: 当前超级管理员用户

    Returns:
        UserResponse: 创建的用户信息

    Raises:
        HTTPException: 400 参数无效，409 韮箱已存在
    """
    # 使用当前管理员ID作为创建者
    creator_id = UUID(admin_user["id"])

    return await user_service.create_internal_editor(
        creator_id=creator_id,
        request=request
    )


@router.get("/{user_id}", response_model=UserResponse)
async def get_user_detail(
    user_id: UUID,
    admin_user: dict = Depends(get_admin_user)
) -> UserResponse:
    """
    获取用户详情

    Args:
        user_id: 用户ID
        admin_user: 当前超级管理员用户

    Returns:
        UserResponse: 用户详情信息

    Raises:
        HTTPException: 404 用户不存在
    """
    return await user_service.get_user_detail(user_id)


@router.put("/{user_id}/role", response_model=RoleChangeResponse)
async def update_user_role(
    user_id: UUID,
    request: UpdateRoleRequest,
    admin_user: dict = Depends(get_admin_user)
) -> RoleChangeResponse:
    """
    修改用户角色

    Args:
        user_id: 用户ID
        request: 角色更新请求
        admin_user: 当前超级管理员用户

    Returns:
        RoleChangeResponse: 角色变更结果

    Raises:
        HTTPException: 400 参数无效，403 权限不足，404 用户不存在
    """
    # 使用当前管理员ID作为操作者
    operator_id = UUID(admin_user["id"])

    return await user_service.update_user_role(
        user_id=user_id,
        operator_id=operator_id,
        request=request
    )


@router.get("/{user_id}/role-changes", response_model=RoleChangeListResponse)
async def get_role_changes(
    user_id: UUID,
    limit: int = 10,
    admin_user: dict = Depends(get_admin_user)
) -> RoleChangeListResponse:
    """
    获取用户角色变更历史

    Args:
        user_id: 用户ID
        limit: 返回记录数限制（1-100）
        admin_user: 当前超级管理员用户

    Returns:
        RoleChangeListResponse: 角色变更历史

    Raises:
        HTTPException: 400 参数无效，404 用户不存在
    """
    # 验证限制参数
    if limit < 1 or limit > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Limit must be between 1 and 100"
        )

    # 获取用户详情（包含角色变更历史）
    user_detail = await user_service.get_user_detail(user_id)

    return RoleChangeListResponse(
        role_changes=user_detail.role_changes[:limit],
        total_count=len(user_detail.role_changes)
    )


@router.post("/invite-reviewer", response_model=InviteReviewerResponse, status_code=status.HTTP_201_CREATED)
async def invite_reviewer(
    request: InviteReviewerRequest,
    admin_user: dict = Depends(get_admin_user)
) -> InviteReviewerResponse:
    """
    邀请临时审稿人

    Args:
        request: 邀请审稿人请求
        admin_user: 当前用户（编辑或超级管理员）

    Returns:
        InviteReviewerResponse: 邀请结果

    Raises:
        HTTPException: 400 参数无效，403 权限不足，409 邮箱已存在
    """
    # 使用当前用户ID作为邀请者
    inviter_id = UUID(admin_user["id"])

    return await user_service.invite_reviewer(
        inviter_id=inviter_id,
        request=request
    )
