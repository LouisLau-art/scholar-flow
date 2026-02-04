import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from uuid import uuid4

import jwt
from supabase import Client


@dataclass(frozen=True)
class UserIdentity:
    id: str
    email: str
    token: str


def generate_test_token(
    user_id: str,
    email: str,
    *,
    expires_in_seconds: int = 3600,
    secret: Optional[str] = None,
) -> str:
    """
    生成可被后端（HS256）验证的 Supabase JWT（用于 API 集成测试）

    中文注释:
    - 后端默认使用 SUPABASE_JWT_SECRET 做 HS256 校验；测试中允许缺省为 mock-secret-replace-later。
    - aud 必须为 authenticated，否则后端会拒绝。
    """

    jwt_secret = secret or os.environ.get("SUPABASE_JWT_SECRET", "mock-secret-replace-later")
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "email": email,
        "aud": "authenticated",
        "exp": now + timedelta(seconds=expires_in_seconds),
        "iat": now,
        "role": "authenticated",
    }
    return jwt.encode(payload, jwt_secret, algorithm="HS256")


def make_user(*, email: Optional[str] = None) -> UserIdentity:
    user_id = str(uuid4())
    user_email = email or f"test_user_{user_id[:8]}@example.com"
    return UserIdentity(id=user_id, email=user_email, token=generate_test_token(user_id, user_email))


def insert_manuscript(
    db: Client,
    *,
    manuscript_id: Optional[str] = None,
    author_id: str,
    title: str = "Test Manuscript",
    abstract: str = "Test abstract content",
    status: str = "decision",
    version: int = 1,
    file_path: str = "",
) -> dict[str, Any]:
    """
    插入一条 manuscripts 记录（用于修订循环的前置状态）
    """
    ms_id = manuscript_id or str(uuid4())
    payload: dict[str, Any] = {
        "id": ms_id,
        "title": title,
        "abstract": abstract,
        "author_id": author_id,
        "status": status,
        "version": version,
    }
    if file_path:
        payload["file_path"] = file_path

    resp = db.table("manuscripts").insert(payload).execute()
    data = getattr(resp, "data", None) or []
    return data[0] if data else payload


def safe_delete_by_id(db: Client, table: str, row_id: str) -> None:
    try:
        db.table(table).delete().eq("id", row_id).execute()
    except Exception:
        pass
