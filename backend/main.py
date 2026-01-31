from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# 在应用启动前加载环境变量
load_dotenv()

from app.api.v1 import (
    manuscripts,
    reviews,
    plagiarism,
    users,
    stats,
    public,
    editor,
    coverage,
    notifications,
    internal,
    matchmaking,
    analytics,
    doi,
    cms,
)
from app.api import oaipmh
from app.core.middleware import ExceptionHandlerMiddleware
from app.core.init_cms import ensure_cms_initialized
from app.lib.api_client import supabase_admin
from app.core.config import CrossrefConfig, crossref_mock_mode
from app.services.crossref_client import CrossrefClient, MockCrossrefClient

app = FastAPI(
    title="ScholarFlow API",
    description="Academic workflow automation backend",
    version="1.0.0",
)

# === 中间件配置 ===
# 1. 跨域资源共享 (CORS) - 允许前端访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # 前端默认端口
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. 统一异常处理 (T011 实现)
app.add_middleware(ExceptionHandlerMiddleware)

# === 路由注册 ===
app.include_router(manuscripts.router, prefix="/api/v1")
app.include_router(reviews.router, prefix="/api/v1")
app.include_router(plagiarism.router, prefix="/api/v1")
app.include_router(users.router, prefix="/api/v1")
app.include_router(stats.router, prefix="/api/v1")
app.include_router(public.router, prefix="/api/v1")
app.include_router(editor.router, prefix="/api/v1")
app.include_router(coverage.router, prefix="/api/v1")
app.include_router(notifications.router, prefix="/api/v1")
app.include_router(internal.router, prefix="/api/v1")
app.include_router(matchmaking.router, prefix="/api/v1")
app.include_router(analytics.router, prefix="/api/v1")
app.include_router(doi.router, prefix="/api/v1")
app.include_router(oaipmh.router)
app.include_router(cms.router, prefix="/api/v1")


@app.on_event("startup")
async def _startup_init_cms() -> None:
    # 中文注释: CMS 初始化应容错（未迁移时不阻塞启动）
    ensure_cms_initialized(supabase_admin)

    # 中文注释: CrossrefClient 注入（Feature 016）。
    # - E2E/CI 可以通过 CROSSREF_MOCK_MODE=true 禁止真实外网调用。
    config = CrossrefConfig.from_env()
    if crossref_mock_mode():
        app.state.crossref_client = MockCrossrefClient(config)
    else:
        app.state.crossref_client = CrossrefClient(config)


@app.get("/")
async def root():
    return {"message": "ScholarFlow API is running", "docs": "/docs"}
