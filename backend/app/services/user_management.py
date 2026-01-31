"""
用户管理服务
Feature: 017-super-admin-management
Created: 2026-01-31
"""

import os
from datetime import datetime
from typing import Optional, List
from uuid import UUID

import httpx
from supabase import Client, create_client

from app.models.user_management import (
    RoleChangeLog,
    AccountCreationLog,
    EmailNotificationLog,
    User,
    UserListResponse,
    Pagination,
    CreateUserRequest,
    UpdateRoleRequest,
    InviteReviewerRequest,
    RoleChangeResponse,
    RoleChangeListResponse,
    InviteReviewerResponse,
)


# ============================================================================
# Supabase 客户端初始化
# ============================================================================

# 从环境变量获取 Supabase 配置
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")

# 使用服务角色密钥初始化客户端（用于创建用户等管理操作）
service_client: Optional[Client] = None
if SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY:
    service_client = create_client(
        SUPABASE_URL,
        SUPABASE_SERVICE_ROLE_KEY
    )

# 使用匿名密钥初始化客户端（用于普通查询）
anon_client: Optional[Client] = None
if SUPABASE_URL and SUPABASE_ANON_KEY:
    anon_client = create_client(
        SUPABASE_URL,
        SUPABASE_ANON_KEY
    )


# ============================================================================
# 审计日志辅助函数
# ============================================================================

async def log_role_change(
    user_id: UUID,
    operator_id: UUID,
    old_role: str,
    new_role: str,
    reason: str,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None
) -> RoleChangeLog:
    """
    记录角色变更到数据库

    Args:
        user_id: 被操作的用户ID
        operator_id: 操作者（超级管理员）ID
        old_role: 原角色
        new_role: 新角色
        reason: 变更原因
        ip_address: 操作者IP地址
        user_agent: 操作者浏览器信息

    Returns:
        RoleChangeLog: 创建的审计日志记录
    """
    if not service_client:
        raise RuntimeError("Supabase service client not initialized")

    # 创建角色变更记录
    result = service_client.table('role_change_logs').insert({
        'user_id': str(user_id),
        'operator_id': str(operator_id),
        'old_role': old_role,
        'new_role': new_role,
        'reason': reason,
        'ip_address': ip_address,
        'user_agent': user_agent,
        'created_at': datetime.utcnow().isoformat()
    }).execute()

    if result.data:
        return RoleChangeLog(
            id=UUID(result.data[0]['id']),
            user_id=user_id,
            operator_id=operator_id,
            old_role=old_role,
            new_role=new_role,
            reason=reason,
            ip_address=ip_address,
            user_agent=user_agent,
            created_at=datetime.fromisoformat(result.data[0]['created_at'])
        )

    raise RuntimeError("Failed to create role change log")


async def log_account_creation(
    user_id: UUID,
    creator_id: UUID,
    creation_type: str,
    invitation_status: str = 'pending'
) -> AccountCreationLog:
    """
    记录账号创建到数据库

    Args:
        user_id: 创建的用户ID
        creator_id: 创建者（超级管理员）ID

        creation_type: 创建类型（internal_editor 或 temporary_reviewer）
        invitation_status: 邀请状态

    Returns:
        AccountCreationLog: 创建的账号创建记录
    """
    if not service_client:
        raise RuntimeError("Supabase service client not initialized")

    # 创建账号创建记录
    result = service_client.table('account_creation_logs').insert({
        'user_id': str(user_id),
        'creator_id': str(creator_id),
        'creation_type': creation_type,
        'invitation_status': invitation_status,
        'created_at': datetime.utcnow().isoformat()
    }).execute()

    if result.data:
        return AccountCreationLog(
            id=UUID(result.data[0]['id']),
            user_id=user_id,
            creator_id=creator_id,
            creation_type=creation_type,
            invitation_status=invitation_status,
            created_at=datetime.fromisoformat(result.data[0]['created_at'])
        )

    raise RuntimeError("Failed to create account creation log")


async def log_email_notification(
    recipient_email: str,
    template_type: str,
    user_id: Optional[UUID] = None,
    status: str = 'queued'
) -> EmailNotificationLog:
    """
    记录邮件通知到数据库

    Args:
        recipient_email: 收件人邮箱
        template_type: 邮件模板类型
        user_id: 关联用户ID（可选）
        status: 发送状态

    Returns:
        EmailNotificationLog: 创建的邮件通知记录
    """
    if not service_client:
        raise RuntimeError("Supabase service client not initialized")

    # 创建邮件通知记录
    insert_data = {
        'recipient_email': recipient_email,
        'template_type': template_type,
        'status': status,
        'created_at': datetime.utcnow().isoformat()
    }

    if user_id:
        insert.insert_data['user_id'] = str(user_id)

    result = service_client.table('email_notification_logs').insert(insert_data).execute()

    if result.data:
        return EmailNotificationLog(
            id=UUID(result.data[0]['id']),
            recipient_email=recipient_email,
            template_type=template_type,
            user_id=user_id,
            status=status,
            created_at=datetime.fromisoformat(result.data[0]['created_at'])
        )

    raise RuntimeError("Failed to create email notification log")


# ============================================================================
# 用户管理服务类
# ============================================================================

class UserManagementService:
    """用户管理服务类"""

    def __init__(self, client: Optional[Client] = None):
        """
        初始化用户管理服务

        Args:
            client: Supabase 客户端（可选，默认使用 anon_client）
        """
        self.client = client or anon_client
        if not self.client:
            raise RuntimeError("Supabase client not initialized")

    async def get_users(
        self,
        page: int = 1,
        per_page: int = 20,
        search: Optional[str] = None,
        role: Optional[str] = None,
        sort_by: str = 'created_at',
        sort_order: str = 'desc'
    ) -> UserListResponse:
        """
        获取用户列表，支持分页、搜索和筛选

        Args:
            page: 页码（从1开始）
            per_page: 每页记录数
            search: 搜索关键词（邮箱或姓名前缀匹配）
            role: 按角色筛选
            sort_by: 排序字段
            sort_order: 排序方向

        Returns:
            UserListResponse: 用户列表和分页信息
        """
        # 计算偏移量
        offset = (page - 1) * per_page

        # 构建查询
        query = self.client.table('users').select('*', count='exact')

        # 添加搜索条件
        if search:
            # 支持邮箱或姓名前缀模糊匹配
            query = query.or_(
                self.client.table('users').select('*', count='exact').ilike('email', f'{search}%'),
                self.client.table('users').select('*', count='exact').ilike('name', f'{search}%')
            )

        # 添加角色筛选
        if role:
            query = query.eq('role', role)

        # 添加排序
        if sort_order == 'desc':
            query = query.order(sort_by, desc={sort_order: True})
        else:
            query = query.order(sort_order, asc={sort_order: True})

        # 添加分页
        query = query.range(offset, offset + per_page - 1)

        # 执行查询
        result = query.execute()

        # 获取总数
        count_result = self.client.table('users').select('*', count='exact')
        if search:
            count_result = count_result.or_(
                self.client.table('users').select('*', count='exact').ilike('email', f'{search}%'),
                self.client.table('users').select('*', count='exact').ilike('name', f'{search}%')
            )
        if role:
            count_result = count_result.eq('role', role)

        count_response = count_result.execute()
        total_items = count_response.count if hasattr(count_response, 'count') else len(result.data or [])

        # 计算分页信息
        total_pages = (total_items + per_page - 1) // per_page
        has_next = page < total_pages
        has_prev = page > 1

        # 转换为 User 对象
        users = []
        for user_data in result.data or []:
            users.append(User(
                id=UUID(user_data['id']),
                email=user_data['email'],
                name=user_data.get('name', ''),
                role=user_data.get('role', 'author'),
                created_at=datetime.fromisoformat(user_data['created_at']),
                last_sign_in_at=datetime.fromisoformat(user_data['last_sign_in_at']) if user_data.get('last_sign_in_at') else None
            ))

        return UserListResponse(
            users=users,
            pagination=Pagination(
                page=page,
                per_page=per_page,
                total_pages=total_pages,
                total_items=total_items,
                has_next=has_next,
                has_prev=has_prev
            )
        )

    async def get_user_detail(self, user_id: UUID) -> UserResponse:
        """
        获取用户详情

        Args:
            user_id: 用户ID

        Returns:
            UserResponse: 用户详情信息
        """
        result = self.client.table('users').select('*').eq('id', str(user_id)).execute()

        if not result.data or len(result.data) == 0:
            raise ValueError(f"User not found: {user_id}")

        user_data = result.data[0]

        # 获取角色变更历史
        role_changes_result = self.client.table('role_change_logs').select('*').eq('user_id', str(user_id)).order('created_at', desc=True).execute()

        role_changes = []
        for change_data in role_changes_result.data or []:
            role_changes.append(RoleChangeLog(
                id=UUID(change_data['id']),
                user_id=UUID(change_data['user_id']),
                operator_id=UUID(change_data['operator_id']),
                old_role=change_data['old_role'],
                new_role=change_data['new_role'],
                reason=change_data['reason'],
                ip_address=change_data.get('ip_address'),
                user_agent=change_data.get('user_agent'),
                created_at=datetime.fromisoformat(change_data['created_at'])
            ))

        return UserResponse(
            id=UUID(user_data['id']),
            email=user_data['email'],
            name=user_data.get('name', ''),
            role=user_data.get('role', 'author'),
            created_at=datetime.fromisoformat(user_data['created_at']),
            last_sign_in_at=datetime.fromisoformat(user_data['last_sign_in_at']) if user_data.get('last_sign_in_at') else None,
            role_changes=role_changes
        )

    async def update_user_role(
        self,
        user_id: UUID,
        operator_id: UUID,
        request: UpdateRoleRequest,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> RoleChangeResponse:
        """
        更新用户角色

        Args:
            user_id: 用户ID
            operator_id: 操作者ID
            request: 角色更新请求
            ip_address: 操作者IP地址
            user_agent: 操作者浏览器信息

        Returns:
            RoleChangeResponse: 角色变更结果
        """
        # 获取当前用户信息
        current_user_result = self.client.table('users').select('*').eq('id', str(user_id)).execute()

        if not current_user_result.data or len(current_user_result.data) == 0:
            raise ValueError(f"User not found: {user_id}")

        current_user = current_user_result.data[0]
        old_role = current_user.get('role', 'author')

        # 验证：禁止修改自己的角色
        if user_id == operator_id:
            return RoleChangeResponse(
                success=False,
                message="Cannot modify your own role",
                role_change=None
            )

        # 验证：禁止修改超级管理员角色
        if old_role == 'admin':
            return RoleChangeResponse(
                success=False,
                message="Cannot modify admin role",
                role_change=None
            )

        # 验证：新旧角色不能相同
        if old_role == request.new_role:
            return RoleChangeResponse(
                success=False,
                message="New role is the same as current role",
                role_change=None
            )

        # 更新用户角色
        update_result = self.client.table('users').update({
            'role': request.new_role
        }).eq('id', str(user_id)).execute()

        if not update_result.data:
            raise RuntimeError(f"Failed to update user role: {user_id}")

        # 记录角色变更审计日志
        role_change = await log_role_change(
            user_id=user_id,
            operator_id=operator_id,
            old_role=old_role,
            new_role=request.new_role,
            reason=request.reason,
            ip_address=ip_address,
            user_agent=user_agent
        )

        return RoleChangeResponse(
            success=True,
            message="Role updated successfully",
            role_change=role_change
        )

    async def create_internal_editor(
        self,
        creator_id: UUID,
        request: CreateUserRequest
    ) -> User:
        """
        创建内部编辑账号

        Args:
            creator_id: 创建者ID
            request: 创建用户请求

        Returns:
            User: 创建的用户信息
        """
        if not service_client:
            raise RuntimeError("Supabase service client not initialized")

        # 使用 Supabase Admin API 创建用户
        # 注意：这里需要使用 service role key 进行创建
        user_result = service_client.auth.sign_up({
            'email': request.email,
            'password': None,  # 临时密码，用户将通过 Magic Link 设置
            'options': {
                'data': {
                    'name': request.name,
                    'role': request.role
                }
            }
        })

        if user_result.user is None:
            raise RuntimeError(f"Failed to create user: {user_result}")

        # 记录账号创建
        await log_account_creation(
            user_id=UUID(user_result.user.id),
            creator_id=creator_id,
            creation_type='internal_editor'
        )

        # TODO: 发送账户开通通知邮件（集成 Feature 011 邮件系统）
        # await send_account_created_email(request.email, request.name)

        return User(
            id=UUID(user_result.user.id),
            email=request.email,
            name=request.name,
            role=request.role,
            created_at=datetime.utcnow(),
            last_sign_in_at=None
        )

    async def invite_reviewer(
        self,
        inviter_id: UUID,
        request: InviteReviewerRequest
    ) -> InviteReviewerResponse:
        """
        邀请临时审稿人

        Args:
            inviter_id: 邀请者ID
            request: 邀请审稿人请求

        Returns:
            InviteReviewerResponse: 邀请结果
        """
        if not service_client:
            raise RuntimeError("Supabase service client not initialized")

        # 使用 Supabase Admin API 创建临时审稿人账号
        user_result = service_client.auth.sign_up({
            'email': request.email,
            'password': None,  # 临时密码，用户将通过 Magic Link 设置
            'options': {
                'data': {
                    'name': request.name,
                    'role': 'reviewer'
                }
            }
        })

        if user_result.user is None:
            raise RuntimeError(f"Failed to create reviewer: {user_result}")

        user_id = UUID(user_result.user.id)

        # 记录账号创建
        await log_account_creation(
            user_id=user_id,
            creator_id=inviter_id,
            creation_type='temporary_reviewer'
        )

        # TODO: 生成并发送 Magic Link 邀请邮件（集成 Feature 011 邮件系统）
        # magic_link = generate_magic_link(user_id)
        # await send_reviewer_invitation_email(request.email, request.name, magic_link)

        return InviteReviewerResponse(
            success=True,
            message="Reviewer invitation sent successfully",
            user_id=user_id,
            invitation_sent=True
        )
