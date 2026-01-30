from __future__ import annotations

from typing import Any

from app.services.cms_service import sanitize_html


_DEFAULT_PAGES: list[dict[str, str]] = [
    {
        "slug": "about",
        "title": "About",
        "content": "<p>Welcome to ScholarFlow. This is a placeholder About page.</p>",
    },
    {
        "slug": "board",
        "title": "Editorial Board",
        "content": "<p>Editorial Board placeholder. Update this content in Editor → Website.</p>",
    },
    {
        "slug": "guidelines",
        "title": "Author Guidelines",
        "content": "<p>Submission guidelines placeholder. Please edit and publish the final version.</p>",
    },
    {
        "slug": "contact",
        "title": "Contact",
        "content": "<p>Contact information placeholder.</p>",
    },
    {
        "slug": "ethics",
        "title": "Ethics",
        "content": "<p>Publication ethics placeholder.</p>",
    },
]


def ensure_cms_initialized(supabase_admin: Any) -> None:
    """
    确保标准 CMS 页面存在（缺失则补齐）。

    中文注释:
    - 该逻辑必须对“迁移未执行”的场景容错：不应阻止应用启动。
    - 初始化页面默认设置为已发布，满足「部署后即可访问」的要求。
    """

    try:
        slugs = [p["slug"] for p in _DEFAULT_PAGES]
        existing_resp = (
            supabase_admin.table("cms_pages").select("slug").in_("slug", slugs).execute()
        )
        existing = getattr(existing_resp, "data", None)
        if existing is None and isinstance(existing_resp, tuple) and len(existing_resp) == 2:
            existing = existing_resp[1]
        existing_slugs = {row.get("slug") for row in (existing or [])}

        missing = [p for p in _DEFAULT_PAGES if p["slug"] not in existing_slugs]
        if not missing:
            return

        payloads = []
        for page in missing:
            payloads.append(
                {
                    "slug": page["slug"],
                    "title": page["title"],
                    "content": sanitize_html(page["content"]),
                    "is_published": True,
                    "updated_by": None,
                }
            )

        supabase_admin.table("cms_pages").insert(payloads).execute()
        print(f"[CMS] initialized default pages: {[p['slug'] for p in missing]}")
    except Exception as e:
        print(f"[CMS] init skipped (db not ready?): {e}")

