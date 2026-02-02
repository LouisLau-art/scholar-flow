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

