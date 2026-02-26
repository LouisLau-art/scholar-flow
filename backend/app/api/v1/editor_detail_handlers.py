from __future__ import annotations

from fastapi import Request

from app.api.v1 import editor_detail_runtime as runtime
from app.api.v1.editor_common import get_signed_url as _get_signed_url_default
from app.api.v1.editor_detail_cards import get_editor_manuscript_cards_context_impl as _cards_impl
from app.api.v1.editor_detail_main import get_editor_manuscript_detail_impl as _detail_impl
from app.api.v1.editor_detail_runtime import EDITOR_SCOPE_COMPAT_ROLES
from app.lib.api_client import supabase_admin as _default_supabase_admin

# 兼容历史测试：允许 monkeypatch editor_detail_handlers._get_signed_url / supabase_admin。
_get_signed_url = _get_signed_url_default
supabase_admin = _default_supabase_admin


def _sync_runtime_overrides() -> None:
    runtime._get_signed_url = _get_signed_url
    runtime.supabase_admin = supabase_admin


async def get_editor_manuscript_detail_impl(
    request: Request,
    id: str,
    skip_cards: bool,
    include_heavy: bool,
    current_user: dict,
    profile: dict,
):
    _sync_runtime_overrides()
    return await _detail_impl(
        request=request,
        id=id,
        skip_cards=skip_cards,
        include_heavy=include_heavy,
        current_user=current_user,
        profile=profile,
    )


async def get_editor_manuscript_cards_context_impl(
    id: str,
    current_user: dict,
    profile: dict,
):
    _sync_runtime_overrides()
    return await _cards_impl(
        id=id,
        current_user=current_user,
        profile=profile,
    )
