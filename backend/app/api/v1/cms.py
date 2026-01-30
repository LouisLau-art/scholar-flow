from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.core.auth_utils import get_current_user
from app.core.roles import require_any_role
from app.models.cms import CMSMenuUpdateRequest, CMSPageCreate, CMSPageUpdate
from app.lib.api_client import supabase, supabase_admin
from app.services.cms_service import CMSService, validate_slug_or_400


router = APIRouter(prefix="/cms", tags=["CMS"])


def _service() -> CMSService:
    return CMSService(supabase=supabase, supabase_admin=supabase_admin)


@router.get("/pages")
async def list_pages(
    _current_user: dict = Depends(get_current_user),
    _profile: dict = Depends(require_any_role(["editor", "admin"])),
):
    """
    列出所有 CMS 页面（编辑/管理员）。
    """
    pages = _service().list_pages()
    return {"success": True, "data": pages}


@router.post("/pages", status_code=201)
async def create_page(
    payload: CMSPageCreate,
    current_user: dict = Depends(get_current_user),
    _profile: dict = Depends(require_any_role(["editor", "admin"])),
):
    """
    创建 CMS 页面（编辑/管理员）。
    """
    slug = validate_slug_or_400(payload.slug)
    created = _service().create_page(
        title=payload.title,
        slug=slug,
        content=payload.content,
        is_published=payload.is_published,
        updated_by=current_user["id"],
    )
    print(f"[CMS] create_page slug={slug} by={current_user.get('id')}")
    return {"success": True, "data": created}


@router.patch("/pages/{slug}")
async def update_page(
    slug: str,
    payload: CMSPageUpdate,
    current_user: dict = Depends(get_current_user),
    _profile: dict = Depends(require_any_role(["editor", "admin"])),
):
    """
    更新 CMS 页面（编辑/管理员）。

    中文注释:
    - 不支持 slug 变更（避免公开 URL 失效与 SEO 断链）。
    """
    patch = payload.model_dump(exclude_unset=True)
    if not patch:
        raise HTTPException(status_code=400, detail="No fields to update")

    updated = _service().update_page(slug=slug, patch=patch, updated_by=current_user["id"])
    print(f"[CMS] update_page slug={slug} by={current_user.get('id')} fields={sorted(patch.keys())}")
    return {"success": True, "data": updated}


@router.get("/pages/{slug}")
async def get_public_page(slug: str):
    """
    公开获取已发布页面（无需认证）。
    - Draft 页面一律返回 404（防止泄露）。
    """
    page = _service().get_public_page(slug)
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")
    return {"success": True, "data": page}


@router.post("/upload")
async def upload_image(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
    _profile: dict = Depends(require_any_role(["editor", "admin"])),
):
    """
    CMS 图片上传（编辑/管理员）。
    返回 public URL（用于富文本 img src）。
    """
    url = await _service().upload_image(file)
    print(f"[CMS] upload_image by={current_user.get('id')} url={url}")
    return {"success": True, "data": {"url": url}}


@router.get("/menu")
async def get_menu(location: str | None = None):
    """
    获取菜单结构（公开）。
    - 若未指定 location，则返回 header + footer。
    """
    svc = _service()
    if location:
        return {"success": True, "data": svc.get_menu(location=location)}
    return {
        "success": True,
        "data": {
            "header": svc.get_menu(location="header"),
            "footer": svc.get_menu(location="footer"),
        },
    }


@router.put("/menu")
async def update_menu(
    payload: CMSMenuUpdateRequest,
    current_user: dict = Depends(get_current_user),
    _profile: dict = Depends(require_any_role(["editor", "admin"])),
):
    """
    更新菜单结构（编辑/管理员）。

    中文注释:
    - MVP：按 location 全量替换，避免复杂的局部更新/拖拽冲突处理。
    """
    updated = _service().replace_menu(
        location=payload.location,
        items=[i.model_dump() for i in payload.items],
        updated_by=current_user["id"],
    )
    print(f"[CMS] update_menu location={payload.location} by={current_user.get('id')}")
    return {"success": True, "data": updated}

