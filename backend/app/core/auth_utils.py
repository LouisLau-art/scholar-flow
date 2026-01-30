import os
from typing import Optional
from fastapi import Request, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from app.lib.api_client import supabase

# === Auth 核心配置 ===
# 中文注释:
# 1. 密钥来源于 Supabase Project Settings 中的 JWT Secret。
# 2. 我们使用 HTTPBearer 作为验证头。
SUPABASE_JWT_SECRET = os.environ.get("SUPABASE_JWT_SECRET", "mock-secret-replace-later")
ALGORITHM = "HS256"

security = HTTPBearer()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """
    解码并验证 Supabase JWT Token
    返回解析后的 User Payload
    """
    token = credentials.credentials
    try:
        # 中文注释:
        # 1. Supabase 新版可能使用 JWT Signing Keys（非 HS256），需要走 Auth API 获取用户。
        # 2. 若仍为 HS256，则用本地密钥校验以减少外部请求。
        header = jwt.get_unverified_header(token)
        if header.get("alg") == ALGORITHM and SUPABASE_JWT_SECRET:
            payload = jwt.decode(token, SUPABASE_JWT_SECRET, algorithms=[ALGORITHM], audience="authenticated")
            user_id = payload.get("sub")
            if user_id is None:
                raise HTTPException(status_code=401, detail="无效的身份载荷")
            return {"id": user_id, "email": payload.get("email")}

        # fallback: 通过 Supabase Auth API 校验并获取用户信息
        try:
            response = supabase.auth.get_user(token)
            user = response.user if response else None
        except Exception as e:
            # 中文注释: 若 Supabase 配置缺失/网络异常，不应返回 500 泄露内部错误，统一视为鉴权失败
            print(f"JWT fallback 校验失败: {e}")
            raise HTTPException(status_code=401, detail="Token 验证失败或已过期")

        if not user:
            raise HTTPException(status_code=401, detail="无效的身份载荷")
        return {"id": user.id, "email": user.email}
    except JWTError as e:
        print(f"JWT 验证失败: {str(e)}")
        raise HTTPException(status_code=401, detail="Token 验证失败或已过期")

def optional_user(request: Request) -> Optional[dict]:
    """
    可选的 Auth 注入（用于公开/私有混合页面）
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return None
    # 简化版实现，正式环境需同上校验
    return {"id": "guest"}
