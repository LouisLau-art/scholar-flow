from fastapi import APIRouter, Depends

from app.core.scheduler import ChaseScheduler
from app.core.security import require_admin_key

router = APIRouter(prefix="/internal", tags=["Internal"])


@router.post("/cron/chase-reviews")
async def chase_reviews(_admin: None = Depends(require_admin_key)):
    """
    触发自动催办逻辑（内部接口）
    """
    scheduler = ChaseScheduler()
    result = scheduler.run()
    return {"success": True, **result}


@router.get("/sentry/test-error")
async def sentry_test_error(_admin: None = Depends(require_admin_key)):
    """
    Sentry 联调用的“已知错误”端点（Feature 027）。

    中文注释:
    - 仅内部接口（需 ADMIN_API_KEY），避免公网被滥用。
    - 目的：验证 Sentry 能捕获后端异常 + 堆栈。
    """
    raise RuntimeError("Sentry test error (backend)")
