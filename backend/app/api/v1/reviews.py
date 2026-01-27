from fastapi import APIRouter, HTTPException, Body
from app.models.schemas import ReviewReport
from app.core.auth_utils import verify_token_expiry
from uuid import UUID
from datetime import datetime

router = APIRouter(prefix="/reviews", tags=["Reviews"])

@router.post("/submit")
async def submit_review(
    token: str = Body(..., embed=True),
    content: str = Body(...),
    score: int = Body(..., ge=1, le=5)
):
    """
    审稿人提交评审报告
    
    中文注释:
    1. 校验 Token 有效性与过期时间。
    2. 更新 review_reports 表中的内容与状态。
    3. 遵循章程: 财务与评审状态机变更显性化。
    """
    # 模拟校验逻辑 (实际需查询数据库)
    if not token or len(token) < 32:
        raise HTTPException(status_code=401, detail="无效或已失效的访问 Token")

    # 模拟过期校验
    # if not verify_token_expiry(report.expiry_date):
    #     raise HTTPException(status_code=403, detail="审稿链接已过期 (超过 14 天)")

    return {
        "success": True,
        "message": "评审报告已成功提交",
        "timestamp": datetime.now()
    }
