from fastapi import APIRouter, Query
from app.lib.api_client import supabase_admin

router = APIRouter(prefix="/portal", tags=["Portal Public"])

@router.get("/articles/latest")
async def get_latest_articles(limit: int = Query(default=10, ge=1, le=50)):
    """
    Get latest published articles for the homepage.
    """
    response = (
        supabase_admin.table("manuscripts")
        .select("id, title, authors, abstract, published_at")
        .eq("status", "published")
        .order("published_at", descending=True)
        .limit(limit)
        .execute()
    )
    
    return response.data
