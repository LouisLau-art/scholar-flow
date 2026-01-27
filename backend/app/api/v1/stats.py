from fastapi import APIRouter, Depends
from app.core.auth_utils import get_current_user
from app.lib.api_client import supabase

router = APIRouter(prefix="/stats", tags=["Dashboard Statistics"])

@router.get("/author")
async def get_author_stats(current_user: dict = Depends(get_current_user)):
    """
    作者视角统计：投稿、发表、待修改
    """
    # 模拟从数据库聚合
    return {
        "success": True,
        "data": {
            "total_submissions": 5,
            "published": 2,
            "under_review": 2,
            "revision_required": 1
        }
    }

@router.get("/editor")
async def get_editor_stats(current_user: dict = Depends(get_current_user)):
    """
    编辑视角统计：待分配、逾期
    """
    return {
        "success": True,
        "data": {
            "pending_assignment": 12,
            "active_review_cycles": 45,
            "overdue_reviews": 3
        }
    }

@router.get("/system")
async def get_public_system_stats():
    """
    系统公开大数字统计 (用于首页)
    """
    return {
        "success": True,
        "data": {
            "total_articles": 185420,
            "global_citations": "2.4M",
            "active_journals": 240
        }
    }
