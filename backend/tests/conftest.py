import pytest
import asyncio
from httpx import AsyncClient, ASGITransport
from main import app
from typing import AsyncGenerator

# === 全局测试配置 ===
# 中文注释:
# 1. 强制启用异步循环
# 2. 封装 httpx 客户端以测试 FastAPI 路由

@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
async def client() -> AsyncGenerator:
    """
    提供一个模拟的异步测试客户端
    """
    async with AsyncClient(
        transport=ASGITransport(app=app), 
        base_url="http://testserver"
    ) as ac:
        yield ac
