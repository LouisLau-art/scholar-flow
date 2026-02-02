from fastapi import APIRouter, Depends, HTTPException

from app.core.auth_utils import get_current_user
from app.services.coverage_service import get_coverage_summary

router = APIRouter()


@router.get("/coverage")
async def get_coverage(current_user: dict = Depends(get_current_user)):
    # 中文注释: 覆盖率报告只对已认证用户开放
    summary = get_coverage_summary()
    if not summary["backend"] and not summary["frontend"]:
        raise HTTPException(status_code=404, detail="覆盖率报告未生成")

    return {
        "user_id": current_user["id"],
        "coverage": summary,
    }
