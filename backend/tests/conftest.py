import pytest
import asyncio
import pytest_asyncio
import os
import jwt
from datetime import datetime, timedelta, timezone
from httpx import AsyncClient, ASGITransport
from typing import AsyncGenerator
from supabase import create_client

# Import app from the correct location
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from main import app

# === 全局测试配置 ===
# 中文注释:
# 1. 显式使用 pytest_asyncio.fixture 解决 STRICT 模式下的生成器问题。
# 2. 确保 client 能够被 await 正确获取。
# 3. JWT 令牌生成用于测试认证。

@pytest.fixture(scope="session")
def event_loop():
    try:
        loop = asyncio.get_event_loop_policy().get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
    yield loop
    loop.close()

@pytest_asyncio.fixture
async def client() -> AsyncGenerator:
    """
    提供一个模拟的异步测试客户端
    """
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver"
    ) as ac:
        yield ac

def generate_test_token(user_id: str = "00000000-0000-0000-0000-000000000000"):
    """
    生成用于测试的JWT令牌
    使用真实的Supabase JWT secret进行签名
    """
    secret = os.environ.get("SUPABASE_JWT_SECRET", "mock-secret-replace-later")
    now = datetime.now(timezone.utc)

    payload = {
        "sub": user_id,
        "email": "test@example.com",
        "aud": "authenticated",
        "exp": now + timedelta(hours=1),
        "iat": now,
        "role": "authenticated"
    }

    return jwt.encode(payload, secret, algorithm="HS256")

@pytest.fixture
def auth_token():
    """
    提供有效的认证令牌用于测试
    """
    return generate_test_token()

@pytest.fixture
def expired_token():
    """
    提供过期的认证令牌用于测试
    """
    secret = os.environ.get("SUPABASE_JWT_SECRET", "mock-secret-replace-later")
    now = datetime.now(timezone.utc)

    payload = {
        "sub": "00000000-0000-0000-0000-000000000000",
        "email": "test@example.com",
        "aud": "authenticated",
        "exp": now - timedelta(hours=1),  # 已过期
        "iat": now - timedelta(hours=2),
        "role": "authenticated"
    }

    return jwt.encode(payload, secret, algorithm="HS256")

@pytest.fixture
def invalid_token():
    """
    提供无效的认证令牌用于测试
    """
    return "invalid.jwt.token"

@pytest.fixture(scope="function")
def db_connection():
    """
    为每个测试函数创建数据库连接
    注意: Supabase Python SDK 不支持显式事务
    所以我们使用手动清理策略
    """
    url = os.environ.get("SUPABASE_URL")
    # 优先使用 service_role 以避免 RLS 影响真实数据库写入型集成测试。
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_KEY")

    if not url or not key:
        pytest.skip("SUPABASE_URL and (SUPABASE_SERVICE_ROLE_KEY or SUPABASE_KEY) must be set for integration tests")

    client = create_client(url, key)
    yield client

@pytest.fixture
def test_manuscript(db_connection):
    """
    创建测试稿件并在测试后清理
    """
    import uuid

    data = {
        "id": str(uuid.uuid4()),
        "title": "Test Manuscript",
        "abstract": "Test abstract content",
        "author_id": "00000000-0000-0000-0000-000000000000",
        "status": "pre_check"
    }

    response = db_connection.table("manuscripts").insert(data).execute()

    yield response.data[0]

    # 清理测试数据
    try:
        db_connection.table("manuscripts").delete().eq("id", data["id"]).execute()
    except:
        pass
