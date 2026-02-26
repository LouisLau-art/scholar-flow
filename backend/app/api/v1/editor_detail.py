from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request

from app.api.v1 import editor_detail_handlers as detail_handlers
from app.api.v1.editor_common import get_signed_url as _get_signed_url_default
from app.core.auth_utils import get_current_user
from app.core.roles import require_any_role
from app.lib.api_client import supabase_admin as _default_supabase_admin

router = APIRouter(tags=["Editor Command Center"])
EDITOR_SCOPE_COMPAT_ROLES = detail_handlers.EDITOR_SCOPE_COMPAT_ROLES

# 兼容历史测试：允许 monkeypatch editor_detail._get_signed_url / supabase_admin。
_get_signed_url = _get_signed_url_default
supabase_admin = _default_supabase_admin


def _sync_handler_overrides() -> None:
    detail_handlers._get_signed_url = _get_signed_url
    detail_handlers.supabase_admin = supabase_admin


@router.get("/manuscripts/{id}")
async def get_editor_manuscript_detail(
    request: Request,
    id: str,
    skip_cards: bool = Query(False, description="首屏详情是否跳过统计卡片计算"),
    include_heavy: bool = Query(False, description="在 skip_cards=true 时是否补齐 files/invites/revisions 等重区块"),
    current_user: dict = Depends(get_current_user),
    profile: dict = Depends(require_any_role(EDITOR_SCOPE_COMPAT_ROLES + ["owner"])),
):
    _sync_handler_overrides()
    return await detail_handlers.get_editor_manuscript_detail_impl(
        request=request,
        id=id,
        skip_cards=skip_cards,
        include_heavy=include_heavy,
        current_user=current_user,
        profile=profile,
    )


@router.get("/manuscripts/{id}/cards-context")
async def get_editor_manuscript_cards_context(
    id: str,
    current_user: dict = Depends(get_current_user),
    profile: dict = Depends(require_any_role(EDITOR_SCOPE_COMPAT_ROLES + ["owner"])),
):
    _sync_handler_overrides()
    return await detail_handlers.get_editor_manuscript_cards_context_impl(
        id=id,
        current_user=current_user,
        profile=profile,
    )
