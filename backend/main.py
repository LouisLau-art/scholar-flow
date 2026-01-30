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
)
from app.api import oaipmh
from app.core.middleware import ExceptionHandlerMiddleware

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


@app.get("/")
async def root():
    return {"message": "ScholarFlow API is running", "docs": "/docs"}
