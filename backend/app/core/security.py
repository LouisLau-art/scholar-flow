from fastapi import Header, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.core.config import get_admin_api_key


async def require_admin_key(x_admin_key: str | None = Header(default=None, alias="X-Admin-Key")) -> None:
    """
    内部 Cron 接口鉴权依赖

    中文注释:
    - 该 Key 不属于用户体系（不是 JWT），仅用于内部任务触发器。
    - 若未配置 ADMIN_API_KEY，则直接拒绝，避免误开放“内部接口”。
    """

    expected = get_admin_api_key()
    if not expected:
        raise HTTPException(status_code=401, detail="Admin key not configured")
    if not x_admin_key or x_admin_key != expected:
        raise HTTPException(status_code=401, detail="Invalid admin key")


_bearer = HTTPBearer()


async def require_admin_bearer_key(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
) -> None:
    """
    内部接口 Bearer 鉴权依赖（用于 reset/seed 这类 test-only 端点）。

    中文注释:
    - 这里的 Bearer Token 是“内部密钥”，不是 Supabase 用户 JWT。
    - 目的：在“清库”之前不依赖用户体系本身（否则会有鸡生蛋问题）。
    - Token 值复用 ADMIN_API_KEY，便于统一配置与轮换。
    """

    expected = get_admin_api_key()
    if not expected:
        raise HTTPException(status_code=401, detail="Admin key not configured")
    if not credentials or credentials.credentials != expected:
        raise HTTPException(status_code=401, detail="Invalid admin key")
