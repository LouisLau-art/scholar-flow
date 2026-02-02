from __future__ import annotations

import mimetypes
import re
import uuid
from dataclasses import dataclass
from typing import Any, Optional

import bleach
from fastapi import HTTPException, UploadFile


_SLUG_RE = re.compile(r"^[a-z0-9-]+$")

# 中文注释:
# - 防止创建会误导用户/冲突的 slug（即使本功能在 /journal/[slug] 下，仍按规范做拦截）
# - 可根据业务需要继续扩展
_RESERVED_SLUGS = {
    "api",
    "admin",
    "login",
    "signup",
    "submit",
    "dashboard",
    "journals",
    "journal",
    "articles",
    "topics",
    "review",
    "search",
}


def _extract_supabase_data(response: Any) -> Any:
    if response is None:
        return None
    data = getattr(response, "data", None)
    if data is not None:
        return data
    if isinstance(response, tuple) and len(response) == 2:
        return response[1]
    return None


def _extract_supabase_error(response: Any) -> Optional[str]:
    if response is None:
        return None
    error = getattr(response, "error", None)
    if error:
        return str(error)
    if isinstance(response, tuple) and len(response) == 2 and response[0]:
        return str(response[0])
    return None


def _is_unique_violation(error_text: Optional[str]) -> bool:
    if not error_text:
        return False
    lowered = error_text.lower()
    return "duplicate key" in lowered or "unique constraint" in lowered or "already exists" in lowered


def validate_slug_or_400(slug: str) -> str:
    normalized = (slug or "").strip().lower()
    if not normalized:
        raise HTTPException(status_code=400, detail="Invalid slug")
    if normalized in _RESERVED_SLUGS:
        raise HTTPException(status_code=409, detail="Slug is reserved")
    if not _SLUG_RE.match(normalized):
        raise HTTPException(status_code=400, detail="Slug must match ^[a-z0-9-]+$")
    return normalized


def sanitize_html(html: Optional[str]) -> Optional[str]:
    if html is None:
        return None
    raw = html.strip()
    if raw == "":
        return ""

    # 中文注释:
    # - 白名单策略：仅允许常见富文本标签与必要属性
    # - 禁止 style/on* 事件等高风险属性，避免 XSS
    allowed_tags = [
        "p",
        "br",
        "strong",
        "em",
        "u",
        "s",
        "blockquote",
        "ul",
        "ol",
        "li",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "hr",
        "pre",
        "code",
        "a",
        "img",
        "span",
        "div",
    ]
    allowed_attrs = {
        "a": ["href", "title", "target", "rel"],
        "img": ["src", "alt", "title", "width", "height"],
        "div": ["class"],
        "span": ["class"],
        "*": [],
    }
    allowed_protocols = ["http", "https", "mailto"]

    cleaned = bleach.clean(
        raw,
        tags=allowed_tags,
        attributes=allowed_attrs,
        protocols=allowed_protocols,
        strip=True,
    )
    return cleaned


@dataclass
class CMSService:
    supabase: Any
    supabase_admin: Any

    def list_pages(self) -> list[dict]:
        resp = (
            self.supabase_admin.table("cms_pages")
            .select("id,slug,title,content,is_published,updated_at,created_at,updated_by")
            .order("updated_at", desc=True)
            .execute()
        )
        data = _extract_supabase_data(resp) or []
        return list(data)

    def get_public_page(self, slug: str) -> Optional[dict]:
        normalized = (slug or "").strip().lower()
        if not normalized:
            return None
        resp = (
            self.supabase.table("cms_pages")
            .select("id,slug,title,content,is_published,updated_at,created_at")
            .eq("slug", normalized)
            .eq("is_published", True)
            .limit(1)
            .execute()
        )
        data = _extract_supabase_data(resp) or []
        return data[0] if data else None

    def create_page(self, *, title: str, slug: str, content: Optional[str], is_published: bool, updated_by: str) -> dict:
        normalized_slug = validate_slug_or_400(slug)
        payload = {
            "title": title.strip(),
            "slug": normalized_slug,
            "content": sanitize_html(content),
            "is_published": bool(is_published),
            "updated_by": updated_by,
        }
        resp = self.supabase_admin.table("cms_pages").insert(payload).execute()
        err = _extract_supabase_error(resp)
        if _is_unique_violation(err):
            raise HTTPException(status_code=409, detail="Slug already exists")
        if err:
            raise HTTPException(status_code=500, detail="Failed to create page")
        data = _extract_supabase_data(resp) or []
        if not data:
            raise HTTPException(status_code=500, detail="Failed to create page")
        return data[0]

    def update_page(self, *, slug: str, patch: dict, updated_by: str) -> dict:
        normalized_slug = (slug or "").strip().lower()
        if not normalized_slug:
            raise HTTPException(status_code=400, detail="Invalid slug")

        update_payload: dict[str, Any] = {"updated_by": updated_by}
        if "title" in patch and patch["title"] is not None:
            update_payload["title"] = str(patch["title"]).strip()
        if "content" in patch and patch["content"] is not None:
            update_payload["content"] = sanitize_html(patch["content"])
        if "is_published" in patch and patch["is_published"] is not None:
            update_payload["is_published"] = bool(patch["is_published"])

        resp = (
            self.supabase_admin.table("cms_pages")
            .update(update_payload)
            .eq("slug", normalized_slug)
            .execute()
        )
        err = _extract_supabase_error(resp)
        if err:
            raise HTTPException(status_code=500, detail="Failed to update page")
        data = _extract_supabase_data(resp) or []
        if not data:
            raise HTTPException(status_code=404, detail="Page not found")
        return data[0]

    def replace_menu(self, *, location: str, items: list[dict], updated_by: str) -> list[dict]:
        if location not in {"header", "footer"}:
            raise HTTPException(status_code=400, detail="Invalid menu location")

        # 先清空 location 下的旧菜单（MVP）
        self.supabase_admin.table("cms_menu_items").delete().eq("location", location).execute()

        def resolve_page_id(page_slug: Optional[str]) -> Optional[str]:
            if not page_slug:
                return None
            resp = (
                self.supabase_admin.table("cms_pages")
                .select("id")
                .eq("slug", page_slug.strip().lower())
                .limit(1)
                .execute()
            )
            data = _extract_supabase_data(resp) or []
            if not data:
                raise HTTPException(status_code=400, detail=f"Unknown page slug: {page_slug}")
            return data[0]["id"]

        def insert_tree(nodes: list[dict], parent_id: Optional[str]) -> None:
            for index, node in enumerate(nodes):
                label = (node.get("label") or "").strip()
                if not label:
                    raise HTTPException(status_code=400, detail="Menu label is required")

                page_slug = node.get("page_slug")
                url = node.get("url")
                if page_slug and url:
                    raise HTTPException(status_code=400, detail="Menu item cannot set both url and page_slug")

                payload: dict[str, Any] = {
                    "parent_id": parent_id,
                    "label": label,
                    "url": url,
                    "page_id": resolve_page_id(page_slug),
                    "order_index": index,
                    "location": location,
                    "updated_by": updated_by,
                }

                resp = self.supabase_admin.table("cms_menu_items").insert(payload).execute()
                err = _extract_supabase_error(resp)
                if err:
                    raise HTTPException(status_code=500, detail="Failed to update menu")
                inserted = _extract_supabase_data(resp) or []
                if not inserted:
                    raise HTTPException(status_code=500, detail="Failed to update menu")

                children = node.get("children") or []
                if children:
                    insert_tree(children, inserted[0]["id"])

        insert_tree(items, None)
        return self.get_menu(location=location)

    def get_menu(self, *, location: str) -> list[dict]:
        if location not in {"header", "footer"}:
            raise HTTPException(status_code=400, detail="Invalid menu location")

        resp = (
            self.supabase.table("cms_menu_items")
            .select("id,parent_id,label,url,page_id,order_index,location")
            .eq("location", location)
            .order("order_index", desc=False)
            .execute()
        )
        rows = _extract_supabase_data(resp) or []
        if not rows:
            return []

        page_ids = [r.get("page_id") for r in rows if r.get("page_id")]
        page_slug_by_id: dict[str, str] = {}
        if page_ids:
            pages_resp = (
                self.supabase.table("cms_pages")
                .select("id,slug")
                .in_("id", page_ids)
                .execute()
            )
            pages = _extract_supabase_data(pages_resp) or []
            page_slug_by_id = {p["id"]: p["slug"] for p in pages if p.get("id") and p.get("slug")}

        nodes: dict[str, dict] = {}
        for row in rows:
            rid = row["id"]
            nodes[rid] = {
                "id": rid,
                "parent_id": row.get("parent_id"),
                "label": row.get("label"),
                "url": row.get("url"),
                "page_slug": page_slug_by_id.get(row.get("page_id")) if row.get("page_id") else None,
                "order_index": row.get("order_index", 0),
                "location": row.get("location", location),
                "children": [],
            }

        roots: list[dict] = []
        for node in nodes.values():
            parent_id = node.get("parent_id")
            if parent_id and parent_id in nodes:
                nodes[parent_id]["children"].append(node)
            else:
                roots.append(node)

        def sort_tree(items: list[dict]) -> None:
            items.sort(key=lambda x: int(x.get("order_index", 0)))
            for item in items:
                sort_tree(item.get("children", []))

        sort_tree(roots)
        return roots

    async def upload_image(self, file: UploadFile) -> str:
        if not file:
            raise HTTPException(status_code=400, detail="Missing file")

        content_type = (file.content_type or "").lower()
        # 部分浏览器可能不给 content_type，做一次后备推断
        if not content_type and file.filename:
            guessed, _ = mimetypes.guess_type(file.filename)
            content_type = (guessed or "").lower()

        if content_type not in {"image/png", "image/jpeg", "image/gif", "image/webp"}:
            raise HTTPException(status_code=400, detail="Unsupported file type")

        data = await file.read()
        if len(data) == 0:
            raise HTTPException(status_code=400, detail="Empty file")
        if len(data) > 5 * 1024 * 1024:
            raise HTTPException(status_code=413, detail="File too large")

        ext = "png"
        if content_type == "image/jpeg":
            ext = "jpg"
        elif content_type == "image/gif":
            ext = "gif"
        elif content_type == "image/webp":
            ext = "webp"

        object_name = f"images/{uuid.uuid4().hex}.{ext}"
        try:
            self.supabase_admin.storage.from_("cms-assets").upload(
                object_name,
                data,
                file_options={"content-type": content_type},
            )
        except Exception as e:
            print(f"CMS upload failed: {e}")
            raise HTTPException(status_code=500, detail="Failed to upload image")

        try:
            public_url = self.supabase_admin.storage.from_("cms-assets").get_public_url(object_name)
        except Exception as e:
            print(f"CMS get_public_url failed: {e}")
            raise HTTPException(status_code=500, detail="Failed to get public URL")

        return public_url
