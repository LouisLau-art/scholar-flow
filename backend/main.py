import asyncio
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from dotenv import load_dotenv

# 在应用启动前加载环境变量
load_dotenv()

_SENTRY_ENABLED = False
try:
    from app.core.sentry_init import init_sentry

    _SENTRY_ENABLED = init_sentry()
    if _SENTRY_ENABLED:
        print("[sentry] enabled")
except Exception as e:
    # 中文注释: 零崩溃原则 — Sentry 任何异常不得阻塞启动
    print(f"[sentry] init failed (ignored): {e}")

from app.api.v1 import (
    auth,
    manuscripts,
    reviews,
    plagiarism,
    users,
    stats,
    public,
    editor,
    invoices,
    coverage,
    notifications,
    internal,
    matchmaking,
    analytics,
    doi,
    cms,
    portal,
)
from app.api.v1.endpoints import system
from app.api.v1.admin import users as admin_users
from app.api import oaipmh
from app.core.middleware import ExceptionHandlerMiddleware
from app.core.init_cms import ensure_cms_initialized
from app.lib.api_client import supabase_admin

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 中文注释: CMS 初始化应容错（未迁移时不阻塞启动）
    ensure_cms_initialized(supabase_admin)

    # 中文注释:
    # - 审稿人 AI 推荐（sentence-transformers）首次加载可能触发模型下载，导致 Editor 点击“Assign Reviewer”时卡很久。
    # - 这里提供一个“后台预热”选项：不阻塞启动，异步把模型拉到本地缓存并完成一次 encode。
    # - 开关：MATCHMAKING_WARMUP=1（默认关闭）。
    warmup = (os.environ.get("MATCHMAKING_WARMUP") or "0").strip().lower() in {"1", "true", "yes", "on"}
    if warmup:

        async def _warmup():
            try:
                from app.core.config import MatchmakingConfig
                from app.core.ml import embed_text

                cfg = MatchmakingConfig.from_env()
                await asyncio.to_thread(embed_text, "warmup", cfg.model_name)
                print(f"[matchmaking] warmup done: model={cfg.model_name}")
            except Exception as e:
                print(f"[matchmaking] warmup failed: {e}")

        asyncio.create_task(_warmup())
    yield


app = FastAPI(
    title="ScholarFlow API",
    description="Academic workflow automation backend",
    version="1.0.0",
    lifespan=lifespan,
)

if _SENTRY_ENABLED:
    try:
        from sentry_sdk.integrations.asgi import SentryAsgiMiddleware

        app.add_middleware(SentryAsgiMiddleware)
    except Exception as e:
        print(f"[sentry] middleware attach failed (ignored): {e}")

def _parse_frontend_origins() -> list[str]:
    """
    解析允许跨域的前端 Origins。

    中文注释:
    - 本地默认: http://localhost:3000
    - 生产/预发: 通过 FRONTEND_ORIGIN 或 FRONTEND_ORIGINS 注入（逗号分隔）
    """
    origins: list[str] = []

    single = (os.environ.get("FRONTEND_ORIGIN") or "").strip()
    if single:
        origins.append(single.rstrip("/"))

    many = (os.environ.get("FRONTEND_ORIGINS") or "").strip()
    if many:
        for part in many.split(","):
            o = (part or "").strip().rstrip("/")
            if o:
                origins.append(o)

    if not origins:
        origins = ["http://localhost:3000"]

    # 去重保持顺序
    deduped: list[str] = []
    seen: set[str] = set()
    for o in origins:
        if o not in seen:
            seen.add(o)
            deduped.append(o)
    return deduped

# === 中间件配置 ===
# 1. 跨域资源共享 (CORS) - 允许前端访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=_parse_frontend_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. 统一异常处理 (T011 实现)
app.add_middleware(ExceptionHandlerMiddleware)

# === 路由注册 ===
app.include_router(auth.router, prefix="/api/v1")
app.include_router(manuscripts.router, prefix="/api/v1")
app.include_router(reviews.router, prefix="/api/v1")
app.include_router(plagiarism.router, prefix="/api/v1")
app.include_router(users.router, prefix="/api/v1")
app.include_router(stats.router, prefix="/api/v1")
app.include_router(public.router, prefix="/api/v1")
app.include_router(editor.router, prefix="/api/v1")
app.include_router(invoices.router, prefix="/api/v1")
app.include_router(coverage.router, prefix="/api/v1")
app.include_router(notifications.router, prefix="/api/v1")
app.include_router(internal.router, prefix="/api/v1")
app.include_router(matchmaking.router, prefix="/api/v1")
app.include_router(analytics.router, prefix="/api/v1")
app.include_router(doi.router, prefix="/api/v1")
app.include_router(admin_users.router, prefix="/api/v1")
app.include_router(oaipmh.router)
app.include_router(cms.router, prefix="/api/v1")
app.include_router(portal.router, prefix="/api/v1")
app.include_router(system.router, prefix="/api/v1")


@app.get("/")
async def root():
    return {"message": "ScholarFlow API is running", "docs": "/docs"}
