from fastapi import APIRouter, Query
from app.lib.api_client import supabase_admin

router = APIRouter(prefix="/portal", tags=["Portal Public"])

@router.get("/articles/latest")
async def get_latest_articles(limit: int = Query(default=10, ge=1, le=50)):
    """
    Get latest published articles for the homepage.
    """
    table = supabase_admin.table("manuscripts")

    try:
        response = (
            table.select("id, title, authors, abstract, published_at")
            .eq("status", "published")
            .order("published_at", desc=True)
            .limit(limit)
            .execute()
        )
        return response.data or []
    except Exception:
        # 兼容旧 schema（缺少 published_at）或旧版 postgrest/supabase 客户端参数差异。
        response = (
            table.select("id, title, authors, abstract, created_at")
            .eq("status", "published")
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        data = response.data or []
        for row in data:
            row["published_at"] = row.get("created_at")
            row.pop("created_at", None)
        return data
