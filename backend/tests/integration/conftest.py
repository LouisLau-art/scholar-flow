import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Callable, Iterable, Optional
from uuid import uuid4

import jwt
import pytest
from supabase import Client, create_client


@dataclass(frozen=True)
class TestUser:
    """
    集成测试用的用户封装（Auth + Profile 的最小抽象）

    中文注释:
    - 这里不直接创建 Supabase Auth 用户（需要 GoTrue/admin API），只生成后端可解码的 JWT。
    - RBAC 由后端 get_current_profile 决定；如需 editor/admin，可通过 ADMIN_EMAILS 环境变量触发。
    """

    id: str
    email: str
    token: str


@pytest.fixture(scope="session")
def supabase_url() -> str:
    url = (os.environ.get("SUPABASE_URL") or "").strip()
    if not url:
        pytest.skip("SUPABASE_URL must be set for integration tests")
    return url


@pytest.fixture(scope="session")
def supabase_anon_key() -> str:
    # 中文注释: 兼容历史变量名，优先 SUPABASE_ANON_KEY，缺省回退到 SUPABASE_KEY
    key = (os.environ.get("SUPABASE_ANON_KEY") or os.environ.get("SUPABASE_KEY") or "").strip()
    if not key:
        pytest.skip("SUPABASE_ANON_KEY or SUPABASE_KEY must be set for integration tests")
    return key


@pytest.fixture(scope="session")
def supabase_service_role_key() -> str:
    return (os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or "").strip()


@pytest.fixture(scope="session")
def supabase_client(supabase_url: str, supabase_anon_key: str) -> Client:
    client = create_client(supabase_url, supabase_anon_key)
    try:
        # 中文注释：提前做一次最小连通性探测，避免测试执行期大量抛 SSL/连接异常。
        client.table("manuscripts").select("id").limit(1).execute()
    except Exception as e:
        pytest.skip(f"Supabase (anon) is not reachable in integration tests: {e}")
    return client


@pytest.fixture(scope="session")
def supabase_admin_client(
    supabase_url: str, supabase_anon_key: str, supabase_service_role_key: str
) -> Client:
    # 中文注释: 若未提供 service role，则回退 anon key（本地/测试环境通常足够）
    client = create_client(supabase_url, supabase_service_role_key or supabase_anon_key)
    try:
        # 中文注释：session 级探测，网络不可达时统一 skip 依赖真实 DB 的集成用例。
        client.table("manuscripts").select("id").limit(1).execute()
    except Exception as e:
        pytest.skip(f"Supabase (admin) is not reachable in integration tests: {e}")
    return client


@pytest.fixture(scope="session")
def jwt_secret() -> str:
    # 与后端 app.core.auth_utils 默认值保持一致，避免测试环境未设置时直接失败
    return os.environ.get("SUPABASE_JWT_SECRET", "mock-secret-replace-later")


@pytest.fixture
def make_jwt(jwt_secret: str) -> Callable[[str, str], str]:
    def _make(user_id: str, email: str) -> str:
        now = datetime.now(timezone.utc)
        payload = {
            "sub": user_id,
            "email": email,
            "aud": "authenticated",
            "exp": now + timedelta(hours=1),
            "iat": now,
            "role": "authenticated",
        }
        return jwt.encode(payload, jwt_secret, algorithm="HS256")

    return _make


@pytest.fixture
def make_test_user(make_jwt: Callable[[str, str], str]) -> Callable[[Optional[str]], TestUser]:
    def _make(email: Optional[str] = None) -> TestUser:
        user_id = str(uuid4())
        user_email = email or f"test_user_{user_id[:8]}@example.com"
        return TestUser(id=user_id, email=user_email, token=make_jwt(user_id, user_email))

    return _make


@pytest.fixture
def set_admin_emails(monkeypatch: pytest.MonkeyPatch) -> Callable[[Iterable[str]], None]:
    """
    为测试临时设置 ADMIN_EMAILS（用于触发 editor/admin 权限）
    """

    def _set(emails: Iterable[str]) -> None:
        monkeypatch.setenv("ADMIN_EMAILS", ",".join([e.strip() for e in emails if e.strip()]))

    return _set
