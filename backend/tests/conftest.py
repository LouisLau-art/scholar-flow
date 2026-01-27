import pytest
import asyncio
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from main import app
from typing import AsyncGenerator

# === 全局测试配置 ===
# 中文注释:
# 1. 显式使用 pytest_asyncio.fixture 解决 STRICT 模式下的生成器问题。
# 2. 确保 client 能够被 await 正确获取。

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