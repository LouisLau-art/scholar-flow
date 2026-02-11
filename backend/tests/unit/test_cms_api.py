from __future__ import annotations

from typing import Any

import pytest

from app.api.v1 import cms as cms_api
from types import SimpleNamespace

from app.core import roles as roles_module


def _set_profile_roles(monkeypatch, roles: list[str]) -> None:
    """
    说明：
    - require_any_role 在路由定义阶段已捕获 Depends(get_current_profile) 的函数引用；
      直接 monkeypatch get_current_profile 在部分场景下不会生效。
    - 因此这里通过 monkeypatch roles 模块内的 supabase 客户端，控制 get_current_profile 的返回值。
    """

    class _Query:
        def select(self, *_args: Any, **_kwargs: Any):
            return self

        def eq(self, *_args: Any, **_kwargs: Any):
            return self

        def execute(self):
            return SimpleNamespace(data=[{"id": "00000000-0000-0000-0000-000000000000", "roles": roles}])

        def insert(self, *_args: Any, **_kwargs: Any):
            return self

        def update(self, *_args: Any, **_kwargs: Any):
            return self

    class _Supabase:
        def table(self, _name: str):
            return _Query()

    monkeypatch.setattr(roles_module, "supabase", _Supabase())


class _FakeCMSService:
    def __init__(self):
        self.pages: dict[str, dict] = {}
        self.menu: dict[str, list[dict]] = {"header": [], "footer": []}

    def list_pages(self) -> list[dict]:
        return list(self.pages.values())

    def get_public_page(self, slug: str):
        page = self.pages.get(slug)
        if not page or not page.get("is_published"):
            return None
        return page

    def create_page(self, **kwargs):
        slug = kwargs["slug"]
        if slug in self.pages:
            raise RuntimeError("should be handled by router/service")
        page = {
            "id": "11111111-1111-1111-1111-111111111111",
            "slug": slug,
            "title": kwargs["title"],
            "content": kwargs.get("content"),
            "is_published": kwargs.get("is_published", False),
        }
        self.pages[slug] = page
        return page

    def update_page(self, *, slug: str, patch: dict, updated_by: str):
        if slug not in self.pages:
            return {}
        self.pages[slug].update(patch)
        return self.pages[slug]

    async def upload_image(self, _file):
        return "https://example.com/cms-assets/images/1.png"

    def get_menu(self, *, location: str):
        return self.menu[location]

    def replace_menu(self, *, location: str, items: list[dict], updated_by: str):
        self.menu[location] = items
        return items


@pytest.mark.asyncio
async def test_cms_public_page_404(client, monkeypatch):
    svc = _FakeCMSService()
    monkeypatch.setattr(cms_api, "_service", lambda: svc)

    resp = await client.get("/api/v1/cms/pages/about")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_cms_public_page_success(client, monkeypatch):
    svc = _FakeCMSService()
    svc.pages["about"] = {
        "id": "11111111-1111-1111-1111-111111111111",
        "slug": "about",
        "title": "About",
        "content": "<p>Hello</p>",
        "is_published": True,
    }
    monkeypatch.setattr(cms_api, "_service", lambda: svc)

    resp = await client.get("/api/v1/cms/pages/about")
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["data"]["slug"] == "about"


@pytest.mark.asyncio
async def test_cms_list_pages_requires_auth(client, monkeypatch):
    monkeypatch.setattr(cms_api, "_service", lambda: _FakeCMSService())
    resp = await client.get("/api/v1/cms/pages")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_cms_list_pages_requires_editor_role(client, monkeypatch, auth_token):
    _set_profile_roles(monkeypatch, ["author"])
    monkeypatch.setattr(cms_api, "_service", lambda: _FakeCMSService())

    resp = await client.get("/api/v1/cms/pages", headers={"Authorization": f"Bearer {auth_token}"})
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_cms_create_page_reserved_slug_conflict(client, monkeypatch, auth_token):
    _set_profile_roles(monkeypatch, ["managing_editor"])
    monkeypatch.setattr(cms_api, "_service", lambda: _FakeCMSService())

    resp = await client.post(
        "/api/v1/cms/pages",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={"title": "X", "slug": "admin", "content": "<p>x</p>", "is_published": False},
    )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_cms_create_and_update_page_flow(client, monkeypatch, auth_token):
    _set_profile_roles(monkeypatch, ["managing_editor"])
    svc = _FakeCMSService()
    monkeypatch.setattr(cms_api, "_service", lambda: svc)

    create_resp = await client.post(
        "/api/v1/cms/pages",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={"title": "About", "slug": "about", "content": "<p>Hello</p>", "is_published": False},
    )
    assert create_resp.status_code == 201

    patch_resp = await client.patch(
        "/api/v1/cms/pages/about",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={"is_published": True},
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["data"]["is_published"] is True


@pytest.mark.asyncio
async def test_cms_upload_requires_auth(client, monkeypatch):
    monkeypatch.setattr(cms_api, "_service", lambda: _FakeCMSService())
    resp = await client.post("/api/v1/cms/upload", files={"file": ("a.png", b"x", "image/png")})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_cms_upload_success(client, monkeypatch, auth_token):
    _set_profile_roles(monkeypatch, ["managing_editor"])
    monkeypatch.setattr(cms_api, "_service", lambda: _FakeCMSService())

    resp = await client.post(
        "/api/v1/cms/upload",
        headers={"Authorization": f"Bearer {auth_token}"},
        files={"file": ("a.png", b"123", "image/png")},
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["url"].startswith("https://")


@pytest.mark.asyncio
async def test_cms_menu_public_default_shape(client, monkeypatch):
    svc = _FakeCMSService()
    svc.menu["header"] = [{"label": "About", "url": "/journal/about"}]
    svc.menu["footer"] = [{"label": "Contact", "url": "/journal/contact"}]
    monkeypatch.setattr(cms_api, "_service", lambda: svc)

    resp = await client.get("/api/v1/cms/menu")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert "header" in data and "footer" in data


@pytest.mark.asyncio
async def test_cms_menu_update_requires_editor(client, monkeypatch, auth_token):
    _set_profile_roles(monkeypatch, ["managing_editor"])
    svc = _FakeCMSService()
    monkeypatch.setattr(cms_api, "_service", lambda: svc)

    resp = await client.put(
        "/api/v1/cms/menu",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={"location": "header", "items": [{"label": "About", "url": "/journal/about", "children": []}]},
    )
    assert resp.status_code == 200
