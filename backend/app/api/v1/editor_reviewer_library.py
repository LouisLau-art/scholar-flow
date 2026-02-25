from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query

from app.core.role_matrix import normalize_roles
from app.core.roles import require_any_role
from app.lib.api_client import supabase_admin
from app.schemas.reviewer import ReviewerCreate, ReviewerUpdate
from app.services.matchmaking_service import MatchmakingService
from app.services.reviewer_service import ReviewPolicyService, ReviewerService
from app.api.v1.editor_heavy_handlers import search_reviewer_library_impl


router = APIRouter(tags=["Editor Command Center"])


def _compat_symbol(name: str, default: object) -> object:
    """
    兼容旧测试/monkeypatch 入口：
    - 历史测试会 patch `app.api.v1.editor.<symbol>`。
    - 拆分后这里优先回读 editor 模块中的同名符号，保持测试与运行时行为稳定。
    """
    try:
        from app.api.v1 import editor as editor_module

        return getattr(editor_module, name, default)
    except Exception:
        return default


@router.post("/reviewer-library", status_code=201)
async def add_reviewer_to_library(
    payload: ReviewerCreate,
    _profile: dict = Depends(require_any_role(["managing_editor", "admin"])),
    background_tasks: BackgroundTasks = None,
):
    """
    User Story 1:
    - 将潜在审稿人加入“审稿人库”
    - 立即创建/关联 auth.users + public.user_profiles
    - **不发送邮件**
    """
    try:
        reviewer_service_cls = _compat_symbol("ReviewerService", ReviewerService)
        data = reviewer_service_cls().add_to_library(payload)
        # 中文注释:
        # - Reviewer Library 新增/激活后，异步触发 embedding 索引，降低 AI 推荐数据不足概率。
        # - 索引失败不阻断主流程（fail-open）。
        try:
            reviewer_id = str(data.get("id") or "").strip()
            roles = [str(r).strip().lower() for r in (data.get("roles") or [])]
            is_active = bool(data.get("is_reviewer_active", True))
            if reviewer_id and "reviewer" in roles and is_active and background_tasks is not None:
                matchmaking_service_cls = _compat_symbol("MatchmakingService", MatchmakingService)
                background_tasks.add_task(matchmaking_service_cls().index_reviewer, reviewer_id)
        except Exception as e:
            print(f"[ReviewerLibrary] enqueue index failed (ignored): {e}")
        return {"success": True, "data": data}
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        print(f"[ReviewerLibrary] add failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to add reviewer")


@router.get("/reviewer-library")
async def search_reviewer_library(
    query: str = Query("", description="按姓名/邮箱/单位/研究方向模糊检索（可选）"),
    page: int = Query(1, ge=1, description="分页页码（从 1 开始）"),
    page_size: int | None = Query(None, ge=1, le=200, description="每页条数（推荐使用 page_size）"),
    limit: int = Query(50, ge=1, le=200),
    manuscript_id: str | None = Query(None, description="可选：基于稿件上下文返回邀请策略命中信息"),
    profile: dict = Depends(require_any_role(["managing_editor", "assistant_editor", "admin"])),
):
    """
    User Story 2:
    - 从审稿人库搜索审稿人（仅返回 active reviewer）
    """
    reviewer_service_cls = _compat_symbol("ReviewerService", ReviewerService)
    review_policy_service_cls = _compat_symbol("ReviewPolicyService", ReviewPolicyService)
    db_client = _compat_symbol("supabase_admin", supabase_admin)
    normalize_roles_fn = _compat_symbol("normalize_roles", normalize_roles)
    search_impl = _compat_symbol("search_reviewer_library_impl", search_reviewer_library_impl)

    effective_page_size = int(page_size or limit)

    return await search_impl(
        query=query,
        page=page,
        page_size=effective_page_size,
        manuscript_id=manuscript_id,
        profile=profile,
        supabase_admin_client=db_client,
        reviewer_service_cls=reviewer_service_cls,
        review_policy_service_cls=review_policy_service_cls,
        normalize_roles_fn=normalize_roles_fn,
    )


@router.get("/reviewer-library/{id}")
async def get_reviewer_library_item(
    id: str,
    _profile: dict = Depends(require_any_role(["managing_editor", "admin"])),
):
    """
    User Story 3:
    - 获取审稿人库条目的完整信息
    """
    try:
        reviewer_service_cls = _compat_symbol("ReviewerService", ReviewerService)
        data = reviewer_service_cls().get_reviewer(UUID(id))
        return {"success": True, "data": data}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        print(f"[ReviewerLibrary] get failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to load reviewer")


@router.put("/reviewer-library/{id}")
async def update_reviewer_library_item(
    id: str,
    payload: ReviewerUpdate,
    _profile: dict = Depends(require_any_role(["managing_editor", "admin"])),
    background_tasks: BackgroundTasks = None,
):
    """
    User Story 3:
    - 更新审稿人库条目的元数据（title/homepage/interests 等）
    """
    try:
        reviewer_service_cls = _compat_symbol("ReviewerService", ReviewerService)
        data = reviewer_service_cls().update_reviewer(UUID(id), payload)
        # 中文注释:
        # - reviewer 元数据更新（尤其 research_interests）后，异步重建 embedding。
        try:
            reviewer_id = str(data.get("id") or id).strip()
            roles = [str(r).strip().lower() for r in (data.get("roles") or [])]
            is_active = bool(data.get("is_reviewer_active", True))
            if reviewer_id and "reviewer" in roles and is_active and background_tasks is not None:
                matchmaking_service_cls = _compat_symbol("MatchmakingService", MatchmakingService)
                background_tasks.add_task(matchmaking_service_cls().index_reviewer, reviewer_id)
        except Exception as e:
            print(f"[ReviewerLibrary] enqueue reindex failed (ignored): {e}")
        return {"success": True, "data": data}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        print(f"[ReviewerLibrary] update failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to update reviewer")


@router.delete("/reviewer-library/{id}")
async def deactivate_reviewer_library_item(
    id: str,
    _profile: dict = Depends(require_any_role(["managing_editor", "admin"])),
):
    """
    User Story 1:
    - 从审稿人库移除（软删除：is_reviewer_active=false）
    """
    try:
        reviewer_service_cls = _compat_symbol("ReviewerService", ReviewerService)
        data = reviewer_service_cls().deactivate(UUID(id))
        return {"success": True, "data": data}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        print(f"[ReviewerLibrary] deactivate failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to remove reviewer")
