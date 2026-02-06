from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from uuid import UUID

import jwt
from fastapi import Header, HTTPException

from app.schemas.token import MagicLinkPayload

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


def _get_magic_link_secret() -> str:
    """
    Magic Link JWT 签名密钥。

    中文注释:
    - 严禁复用 `SUPABASE_SERVICE_ROLE_KEY`（它是最高权限密钥，绝不能参与 token 签名）。
    - 生产/UAT 必须显式配置 `MAGIC_LINK_JWT_SECRET`；本地可使用 `SECRET_KEY` 兜底。
    """

    secret = (os.environ.get("MAGIC_LINK_JWT_SECRET") or "").strip()
    if secret:
        return secret
    secret = (os.environ.get("SECRET_KEY") or "").strip()
    if secret:
        return secret
    raise RuntimeError("MAGIC_LINK_JWT_SECRET/SECRET_KEY not configured")


def create_magic_link_jwt(
    *,
    reviewer_id: UUID,
    manuscript_id: UUID,
    assignment_id: UUID,
    expires_in_days: int = 14,
) -> str:
    secret = _get_magic_link_secret()
    now = datetime.now(timezone.utc)
    exp = int((now + timedelta(days=expires_in_days)).timestamp())
    payload = {
        "type": "magic_link",
        "reviewer_id": str(reviewer_id),
        "manuscript_id": str(manuscript_id),
        "assignment_id": str(assignment_id),
        "exp": exp,
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def decode_magic_link_jwt(token: str) -> MagicLinkPayload:
    """
    解码并校验 Magic Link JWT。

    抛出:
    - HTTPException(401): token 无效/过期
    - HTTPException(500): 服务端密钥未配置
    """

    try:
        secret = _get_magic_link_secret()
    except Exception:
        raise HTTPException(status_code=500, detail="Magic Link secret not configured")

    try:
        raw = jwt.decode(token, secret, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Magic link expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid magic link")

    try:
        return MagicLinkPayload(
            type=str(raw.get("type") or "magic_link"),
            reviewer_id=UUID(str(raw.get("reviewer_id"))),
            manuscript_id=UUID(str(raw.get("manuscript_id"))),
            assignment_id=UUID(str(raw.get("assignment_id"))),
            exp=int(raw.get("exp")),
        )
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid magic link payload")
