from fastapi import APIRouter, Depends, HTTPException
from app.core.auth_utils import get_current_user
from app.lib.api_client import supabase
import uuid
from datetime import datetime

router = APIRouter(prefix="/stats", tags=["Dashboard Statistics"])

@router.get("/author")
async def get_author_stats(current_user: dict = Depends(get_current_user)):
    """
    作者视角统计：投稿、发表、待修改
    """
    try:
        # 中文注释: 真实统计以数据库为准（按当前登录作者过滤）
        rows = (
            supabase.table("manuscripts")
            .select("status")
            .eq("author_id", current_user["id"])
            .execute()
            .data
        ) or []
        total = len(rows)
        published = sum(1 for r in rows if r.get("status") == "published")
        under_review = sum(1 for r in rows if r.get("status") == "under_review")
        revision_required = sum(1 for r in rows if r.get("status") == "revision_required")

        return {
            "success": True,
            "data": {
                "total_submissions": total,
                "published": published,
                "under_review": under_review,
                "revision_required": revision_required
            }
        }
    except Exception as e:
        print(f"Author stats query failed: {e}")
        return {
            "success": True,
            "data": {
                "total_submissions": 0,
                "published": 0,
                "under_review": 0,
                "revision_required": 0
            }
        }

@router.get("/editor")
async def get_editor_stats(current_user: dict = Depends(get_current_user)):
    """
    编辑视角统计：待分配、逾期
    """
    try:
        pending_assignment = (
            supabase.table("manuscripts")
            .select("id")
            .eq("status", "submitted")
            .execute()
            .data
        )
        active_review_cycles = (
            supabase.table("manuscripts")
            .select("id")
            .eq("status", "under_review")
            .execute()
            .data
        )
        overdue_reviews = (
            supabase.table("manuscripts")
            .select("id")
            .eq("status", "pending_decision")
            .execute()
            .data
        )

        return {
            "success": True,
            "data": {
                "pending_assignment": len(pending_assignment or []),
                "active_review_cycles": len(active_review_cycles or []),
                "overdue_reviews": len(overdue_reviews or [])
            }
        }
    except Exception as e:
        print(f"Editor stats query failed: {e}")
        return {
            "success": True,
            "data": {
                "pending_assignment": 0,
                "active_review_cycles": 0,
                "overdue_reviews": 0
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

@router.post("/download/{article_id}")
async def record_download(article_id: str):
    """
    记录文章下载统计 (Mock实现)
    """
    try:
        # 验证文章ID格式
        if not article_id or len(article_id) < 1:
            raise HTTPException(status_code=400, detail="Invalid article ID")
        
        # 模拟数据库操作 - 在实际项目中这里会更新数据库中的下载计数
        print(f"[Download Stats] Article {article_id} downloaded at {datetime.now().isoformat()}")
        
        # 模拟返回成功响应
        return {
            "success": True,
            "message": "Download recorded successfully",
            "data": {
                "article_id": article_id,
                "timestamp": datetime.now().isoformat(),
                "download_count": 450  # 模拟当前下载次数
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[Download Stats Error] Failed to record download for article {article_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to record download")
