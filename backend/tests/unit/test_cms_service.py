from __future__ import annotations

import pytest
from fastapi import HTTPException

from types import SimpleNamespace
from unittest.mock import MagicMock

from app.core.init_cms import ensure_cms_initialized
from app.services import cms_service as cms_service_module
from app.services.cms_service import CMSService, sanitize_html, validate_slug_or_400


def test_validate_slug_rejects_reserved():
    with pytest.raises(HTTPException) as exc:
        validate_slug_or_400("admin")
    assert exc.value.status_code == 409


def test_validate_slug_rejects_bad_format():
    with pytest.raises(HTTPException) as exc:
        validate_slug_or_400("Bad Slug!")
    assert exc.value.status_code == 400


def test_sanitize_html_strips_script():
    raw = "<p>Hello</p><script>alert(1)</script><img src=\"https://x.com/a.png\" onerror=\"alert(1)\" />"
    cleaned = sanitize_html(raw) or ""
    assert "<script" not in cleaned
    assert "onerror" not in cleaned
    assert "<p>" in cleaned


def test_list_pages_and_get_public_page():
    admin_query = MagicMock()
    admin_query.select.return_value = admin_query
    admin_query.order.return_value = admin_query
    admin_query.execute.return_value = SimpleNamespace(data=[{"slug": "about"}])

    public_query = MagicMock()
    public_query.select.return_value = public_query
    public_query.eq.return_value = public_query
    public_query.limit.return_value = public_query
    public_query.execute.return_value = SimpleNamespace(data=[{"slug": "about", "is_published": True}])

    supabase_admin = MagicMock()
    supabase_admin.table.side_effect = lambda name: admin_query if name == "cms_pages" else MagicMock()

    supabase = MagicMock()
    supabase.table.side_effect = lambda name: public_query if name == "cms_pages" else MagicMock()

    svc = CMSService(supabase=supabase, supabase_admin=supabase_admin)
    assert svc.list_pages()[0]["slug"] == "about"
    assert svc.get_public_page("about")["slug"] == "about"


def test_create_page_duplicate_slug_409():
    insert_query = MagicMock()
    insert_query.insert.return_value = insert_query
    insert_query.execute.return_value = SimpleNamespace(data=None, error="duplicate key value violates unique constraint")

    supabase_admin = MagicMock()
    supabase_admin.table.return_value = insert_query

    svc = CMSService(supabase=MagicMock(), supabase_admin=supabase_admin)
    with pytest.raises(HTTPException) as exc:
        svc.create_page(title="t", slug="about", content="<p>x</p>", is_published=False, updated_by="u")
    assert exc.value.status_code == 409


def test_update_page_not_found_404():
    update_query = MagicMock()
    update_query.update.return_value = update_query
    update_query.eq.return_value = update_query
    update_query.execute.return_value = SimpleNamespace(data=[])

    supabase_admin = MagicMock()
    supabase_admin.table.return_value = update_query

    svc = CMSService(supabase=MagicMock(), supabase_admin=supabase_admin)
    with pytest.raises(HTTPException) as exc:
        svc.update_page(slug="missing", patch={"title": "x"}, updated_by="u")
    assert exc.value.status_code == 404


def test_get_menu_builds_tree_and_resolves_page_slug():
    menu_rows = [
        {"id": "p1", "parent_id": None, "label": "About", "url": None, "page_id": "pg1", "order_index": 1, "location": "header"},
        {"id": "p0", "parent_id": None, "label": "Home", "url": "/", "page_id": None, "order_index": 0, "location": "header"},
        {"id": "c1", "parent_id": "p1", "label": "Ethics", "url": None, "page_id": "pg2", "order_index": 0, "location": "header"},
    ]
    pages_rows = [{"id": "pg1", "slug": "about"}, {"id": "pg2", "slug": "ethics"}]

    menu_query = MagicMock()
    menu_query.select.return_value = menu_query
    menu_query.eq.return_value = menu_query
    menu_query.order.return_value = menu_query
    menu_query.execute.return_value = SimpleNamespace(data=menu_rows)

    pages_query = MagicMock()
    pages_query.select.return_value = pages_query
    pages_query.in_.return_value = pages_query
    pages_query.execute.return_value = SimpleNamespace(data=pages_rows)

    supabase = MagicMock()
    supabase.table.side_effect = lambda name: menu_query if name == "cms_menu_items" else pages_query

    svc = CMSService(supabase=supabase, supabase_admin=MagicMock())
    tree = svc.get_menu(location="header")
    assert tree[0]["label"] == "Home"
    assert tree[1]["label"] == "About"
    assert tree[1]["page_slug"] == "about"
    assert tree[1]["children"][0]["page_slug"] == "ethics"


@pytest.mark.asyncio
async def test_upload_image_validates_and_returns_public_url():
    class _File:
        filename = "a.png"
        content_type = "image/png"

        async def read(self):
            return b"1234"

    bucket = MagicMock()
    bucket.get_public_url.return_value = "https://example.com/cms-assets/images/1.png"
    storage = MagicMock()
    storage.from_.return_value = bucket

    supabase_admin = MagicMock()
    supabase_admin.storage = storage

    svc = CMSService(supabase=MagicMock(), supabase_admin=supabase_admin)
    url = await svc.upload_image(_File())
    assert url.startswith("https://")


def test_init_cms_inserts_missing_pages(monkeypatch):
    query = MagicMock()
    query.select.return_value = query
    query.in_.return_value = query
    query.execute.return_value = SimpleNamespace(data=[{"slug": "about"}])
    query.insert.return_value = query

    supabase_admin = MagicMock()
    supabase_admin.table.return_value = query

    ensure_cms_initialized(supabase_admin)
    assert query.insert.called is True


def test_extract_helpers_support_tuple_shape():
    assert cms_service_module._extract_supabase_data((None, [{"id": 1}])) == [{"id": 1}]
    assert cms_service_module._extract_supabase_error(("boom", [])) == "boom"


def test_get_menu_invalid_location_400():
    svc = CMSService(supabase=MagicMock(), supabase_admin=MagicMock())
    with pytest.raises(HTTPException) as exc:
        svc.get_menu(location="side")
    assert exc.value.status_code == 400


def test_get_menu_empty_rows_returns_empty_list():
    menu_query = MagicMock()
    menu_query.select.return_value = menu_query
    menu_query.eq.return_value = menu_query
    menu_query.order.return_value = menu_query
    menu_query.execute.return_value = SimpleNamespace(data=[])

    supabase = MagicMock()
    supabase.table.return_value = menu_query

    svc = CMSService(supabase=supabase, supabase_admin=MagicMock())
    assert svc.get_menu(location="header") == []


def test_replace_menu_invalid_location_400():
    svc = CMSService(supabase=MagicMock(), supabase_admin=MagicMock())
    with pytest.raises(HTTPException) as exc:
        svc.replace_menu(location="side", items=[], updated_by="u")
    assert exc.value.status_code == 400


def test_replace_menu_unknown_page_slug_400():
    class _PagesQuery:
        def select(self, *_args, **_kwargs):
            return self

        def eq(self, *_args, **_kwargs):
            return self

        def limit(self, *_args, **_kwargs):
            return self

        def execute(self):
            return SimpleNamespace(data=[])

    class _MenuQuery:
        def delete(self):
            return self

        def eq(self, *_args, **_kwargs):
            return self

        def execute(self):
            return SimpleNamespace(data=[])

        def insert(self, *_args, **_kwargs):
            return self

    class _Admin:
        def table(self, name: str):
            if name == "cms_pages":
                return _PagesQuery()
            return _MenuQuery()

    svc = CMSService(supabase=MagicMock(), supabase_admin=_Admin())
    svc.get_menu = lambda *, location: []  # type: ignore[method-assign]

    with pytest.raises(HTTPException) as exc:
        svc.replace_menu(
            location="header",
            items=[{"label": "About", "page_slug": "missing"}],
            updated_by="u",
        )
    assert exc.value.status_code == 400


def test_replace_menu_rejects_both_url_and_page_slug():
    menu_query = MagicMock()
    menu_query.delete.return_value = menu_query
    menu_query.eq.return_value = menu_query
    menu_query.execute.return_value = SimpleNamespace(data=[])

    supabase_admin = MagicMock()
    supabase_admin.table.return_value = menu_query

    svc = CMSService(supabase=MagicMock(), supabase_admin=supabase_admin)
    svc.get_menu = lambda *, location: []  # type: ignore[method-assign]

    with pytest.raises(HTTPException) as exc:
        svc.replace_menu(
            location="header",
            items=[{"label": "X", "url": "https://a.com", "page_slug": "about"}],
            updated_by="u",
        )
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_upload_image_rejects_unsupported_type():
    class _File:
        filename = "a.txt"
        content_type = "text/plain"

        async def read(self):
            return b"1"

    svc = CMSService(supabase=MagicMock(), supabase_admin=MagicMock())
    with pytest.raises(HTTPException) as exc:
        await svc.upload_image(_File())
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_upload_image_guesses_content_type_and_rejects_empty_file():
    class _File:
        filename = "a.png"
        content_type = ""

        async def read(self):
            return b""

    svc = CMSService(supabase=MagicMock(), supabase_admin=MagicMock())
    with pytest.raises(HTTPException) as exc:
        await svc.upload_image(_File())
    assert exc.value.status_code == 400
