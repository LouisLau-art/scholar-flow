"""
认证与授权模块
功能: 提供 JWT 认证和 RBAC 角色检查

中文注释:
- get_current_user: 验证 JWT 并返回用户信息
- require_roles: 角色检查装饰器，限制特定角色访问
- 遵循章程: 认证优先，所有敏感操作必须认证
"""

import os
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from supabase import create_client

# === Auth 核心配置 ===
SUPABASE_JWT_SECRET = os.environ.get("SUPABASE_JWT_SECRET", "")
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
ALGORITHM = "HS256"

security = HTTPBearer()


def get_supabase_admin():
    """获取 Supabase 管理员客户端"""
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        return None
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """
    解码并验证 Supabase JWT Token
    返回包含用户信息和角色的字典

    中文注释:
    - 首先尝试本地 JWT 解码
    - 然后查询 user_profiles 获取角色信息
    """
    token = credentials.credentials

    try:
        # 尝试本地 JWT 解码
        if SUPABASE_JWT_SECRET:
            try:
                payload = jwt.decode(
                    token,
                    SUPABASE_JWT_SECRET,
                    algorithms=[ALGORITHM],
                    audience="authenticated",
                )
                user_id = payload.get("sub")
                email = payload.get("email")

                if not user_id:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="无效的身份载荷",
                    )

                # 查询用户角色
                roles = await _get_user_roles(user_id)

                return {
                    "id": user_id,
                    "email": email,
                    "roles": roles,
                }
            except JWTError:
                pass  # 尝试 fallback

        # Fallback: 通过 Supabase Auth API 验证
        supabase = get_supabase_admin()
        if supabase:
            try:
                response = supabase.auth.get_user(token)
                user = response.user if response else None
                if user:
                    roles = await _get_user_roles(user.id)
                    return {
                        "id": user.id,
                        "email": user.email,
                        "roles": roles,
                    }
            except Exception:
                pass

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token 验证失败或已过期",
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"认证失败: {str(e)}",
        )


async def _get_user_roles(user_id: str) -> list[str]:
    """
    从 user_profiles 表获取用户角色

    中文注释:
    - 如果未找到用户配置，返回默认角色 ['author']
    - 角色存储在 roles 数组字段中
    """
    try:
        supabase = get_supabase_admin()
        if not supabase:
            return ["author"]

        response = (
            supabase.table("user_profiles")
            .select("roles")
            .eq("id", user_id)
            .single()
            .execute()
        )

        if response.data and response.data.get("roles"):
            return response.data["roles"]

        return ["author"]
    except Exception:
        return ["author"]


def require_roles(allowed_roles: list[str]):
    """
    角色检查依赖工厂

    使用方式:
        @router.get("/endpoint")
        async def endpoint(user = Depends(require_roles(["managing_editor", "admin"]))):
            ...

    中文注释:
    - 检查用户是否具有允许的角色之一
    - 支持多角色检查
    """

    async def role_checker(
        current_user: dict = Depends(get_current_user),
    ) -> dict:
        user_roles = current_user.get("roles", [])

        # 检查是否有任一允许的角色
        has_permission = any(role in allowed_roles for role in user_roles)

        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"权限不足，需要角色: {', '.join(allowed_roles)}",
            )

        return current_user

    return role_checker


# 便捷的角色检查依赖
require_editor = require_roles(
    ["managing_editor", "editor_in_chief", "admin"]
)
require_admin = require_roles(["admin"])
