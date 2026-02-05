from functools import lru_cache

from fastapi import APIRouter, Query
from app.lib.api_client import supabase_admin

router = APIRouter(prefix="/portal", tags=["Portal Public"])


def _mask_email(email: str) -> str:
    email = (email or "").strip()
    if not email or "@" not in email:
        return ""
    local, domain = email.split("@", 1)
    local = local.strip()
    domain = domain.strip()
    if not local:
        return f"*@{domain}" if domain else "*"
    if len(local) == 1:
        return f"{local}*@{domain}" if domain else f"{local}*"
    return f"{local[0]}***@{domain}" if domain else f"{local[0]}***"


@lru_cache(maxsize=2048)
def _fallback_author_label_from_auth(uid: str) -> str:
    """
    Portal 公开接口兜底：当 user_profiles 缺失时，尽量避免返回 'Unknown'，
    但也不能泄露明文邮箱。这里用 Supabase Admin API 取 email 并做脱敏。
    """
    try:
        res = supabase_admin.auth.admin.get_user_by_id(str(uid))
        email = getattr(getattr(res, "user", None), "email", None)
        masked = _mask_email(email or "")
        return masked or "Author"
    except Exception:
        return "Author"


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
        label = author_name_by_id.get(author_id)
        if not label or label == "Unknown":
            label = _fallback_author_label_from_auth(author_id) if author_id else "Author"
        row["authors"] = [label]
        row.pop("author_id", None)

    return data
