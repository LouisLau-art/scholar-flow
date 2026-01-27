import os
from typing import Optional
from fastapi import Request, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError

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
        payload = jwt.decode(token, SUPABASE_JWT_SECRET, algorithms=[ALGORITHM], audience="authenticated")
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="无效的身份载荷")
        return {"id": user_id, "email": payload.get("email")}
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