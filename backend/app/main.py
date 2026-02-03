"""
兼容入口：部分测试/工具会使用 `app.main:app` 作为 ASGI 入口。

项目真实 FastAPI 实例定义在 repo 根的 `backend/main.py`（模块名为 `main`）中。
这里仅做转发，避免重复创建应用对象导致中间件/路由不一致。
"""

from main import app

__all__ = ["app"]

