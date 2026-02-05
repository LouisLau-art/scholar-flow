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
            table.select("id, title, abstract, published_at, author_id")
            .eq("status", "published")
            .order("published_at", desc=True)
            .limit(limit)
            .execute()
        )
        data = response.data or []
    except Exception:
        # 兼容旧 schema（缺少 published_at）或旧版 postgrest/supabase 客户端参数差异。
        response = (
            table.select("id, title, abstract, created_at, author_id")
            .eq("status", "published")
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        data = response.data or []
        for row in data:
            row["published_at"] = row.get("created_at")
            row.pop("created_at", None)

    # manuscripts 表不保证存在 authors 字段（历史 schema 不一致）。
    # Portal 仅需要展示作者名：优先从 user_profiles.full_name 取，否则退回 email。
    author_ids = sorted({str(r.get("author_id")) for r in data if r.get("author_id")})
    author_name_by_id: dict[str, str] = {}
    if author_ids:
        profiles = supabase_admin.table("user_profiles")
        try:
            profiles_res = profiles.select("id, full_name, email").in_("id", author_ids).execute()
            rows = profiles_res.data or []
            author_name_by_id = {
                str(r.get("id")): (r.get("full_name") or r.get("email") or "Unknown") for r in rows
            }
        except Exception:
            profiles_res = profiles.select("id, email").in_("id", author_ids).execute()
            rows = profiles_res.data or []
            author_name_by_id = {str(r.get("id")): (r.get("email") or "Unknown") for r in rows}

    for row in data:
        author_id = str(row.get("author_id")) if row.get("author_id") else ""
        row["authors"] = [author_name_by_id.get(author_id, "Unknown")]
        row.pop("author_id", None)

    return data
