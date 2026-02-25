from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form

from app.core.auth_utils import get_current_user
from app.core.journal_scope import ensure_manuscript_scope_access
from app.core.roles import require_any_role
from app.models.production_workspace import CreateProductionCycleRequest, UpdateProductionCycleEditorsRequest
from app.services.production_service import ProductionService
from app.services.production_workspace_service import ProductionWorkspaceService

# 与 editor.py 保持一致：这些角色可进入 Editor Command Center。
EDITOR_SCOPE_COMPAT_ROLES = [
    "admin",
    "managing_editor",
    "assistant_editor",
    "production_editor",
    "editor_in_chief",
]

router = APIRouter(tags=["Editor Command Center"])


def _enforce_scope_for_management_roles(*, manuscript_id: str, current_user: dict, profile: dict) -> None:
    roles = profile.get("roles") or []
    role_set = {str(role).strip().lower() for role in roles if str(role).strip()}
    if "admin" in role_set:
        return
    if role_set.intersection({"managing_editor", "editor_in_chief"}):
        ensure_manuscript_scope_access(
            manuscript_id=str(manuscript_id),
            user_id=str(current_user.get("id") or ""),
            roles=roles,
            allow_admin_bypass=True,
        )


@router.post("/manuscripts/{id}/production/advance")
async def advance_production_stage(
    id: str,
    current_user: dict = Depends(get_current_user),
    profile: dict = Depends(require_any_role(["managing_editor", "admin"])),
):
    """
    Feature 031: 录用后出版流水线 - 前进一个阶段（approved->layout->english_editing->proofreading->published）。
    """
    _enforce_scope_for_management_roles(manuscript_id=id, current_user=current_user, profile=profile)
    allow_skip = "admin" in (profile.get("roles") or [])
    res = ProductionService().advance(
        manuscript_id=id,
        changed_by=str(current_user.get("id")),
        allow_skip=bool(allow_skip),
    )
    return {
        "success": True,
        "data": {
            "previous_status": res.previous_status,
            "new_status": res.new_status,
            "manuscript": res.manuscript,
        },
    }


@router.post("/manuscripts/{id}/production/revert")
async def revert_production_stage(
    id: str,
    current_user: dict = Depends(get_current_user),
    profile: dict = Depends(require_any_role(["managing_editor", "admin"])),
):
    """
    Feature 031: 录用后出版流水线 - 回退一个阶段（proofreading->english_editing->layout->approved）。
    """
    _enforce_scope_for_management_roles(manuscript_id=id, current_user=current_user, profile=profile)
    allow_skip = "admin" in (profile.get("roles") or [])
    res = ProductionService().revert(
        manuscript_id=id,
        changed_by=str(current_user.get("id")),
        allow_skip=bool(allow_skip),
    )
    return {
        "success": True,
        "data": {
            "previous_status": res.previous_status,
            "new_status": res.new_status,
            "manuscript": res.manuscript,
        },
    }


@router.get("/manuscripts/{id}/production-workspace")
async def get_production_workspace_context(
    id: str,
    current_user: dict = Depends(get_current_user),
    profile: dict = Depends(require_any_role(EDITOR_SCOPE_COMPAT_ROLES)),
):
    """
    Feature 042: 编辑端生产工作间上下文。
    """
    _enforce_scope_for_management_roles(manuscript_id=id, current_user=current_user, profile=profile)
    data = ProductionWorkspaceService().get_workspace_context(
        manuscript_id=id,
        user_id=str(current_user.get("id") or ""),
        profile_roles=profile.get("roles") or [],
    )
    return {"success": True, "data": data}


@router.post("/manuscripts/{id}/production-cycles", status_code=201)
async def create_production_cycle(
    id: str,
    payload: CreateProductionCycleRequest,
    current_user: dict = Depends(get_current_user),
    profile: dict = Depends(require_any_role(["managing_editor", "editor_in_chief", "admin"])),
):
    """
    Feature 042: 创建生产轮次。
    """
    _enforce_scope_for_management_roles(manuscript_id=id, current_user=current_user, profile=profile)
    data = ProductionWorkspaceService().create_cycle(
        manuscript_id=id,
        user_id=str(current_user.get("id") or ""),
        profile_roles=profile.get("roles") or [],
        request=payload,
    )
    return {"success": True, "data": {"cycle": data}}


@router.patch("/manuscripts/{id}/production-cycles/{cycle_id}/editors")
async def update_production_cycle_editors(
    id: str,
    cycle_id: str,
    payload: UpdateProductionCycleEditorsRequest,
    current_user: dict = Depends(get_current_user),
    profile: dict = Depends(require_any_role(["managing_editor", "editor_in_chief", "admin"])),
):
    """
    Feature 042B: 更新生产轮次的负责人/协作者列表（仅 ME/EIC/Admin）。
    """
    _enforce_scope_for_management_roles(manuscript_id=id, current_user=current_user, profile=profile)
    data = ProductionWorkspaceService().update_cycle_editors(
        manuscript_id=id,
        cycle_id=cycle_id,
        user_id=str(current_user.get("id") or ""),
        profile_roles=profile.get("roles") or [],
        request=payload,
    )
    return {"success": True, "data": {"cycle": data}}


@router.post("/manuscripts/{id}/production-cycles/{cycle_id}/galley")
async def upload_production_galley(
    id: str,
    cycle_id: str,
    file: UploadFile = File(...),
    version_note: str = Form(...),
    proof_due_at: str | None = Form(default=None),
    current_user: dict = Depends(get_current_user),
    profile: dict = Depends(require_any_role(["managing_editor", "production_editor", "editor_in_chief", "admin"])),
):
    """
    Feature 042: 上传生产轮次清样并进入 awaiting_author。
    """
    _enforce_scope_for_management_roles(manuscript_id=id, current_user=current_user, profile=profile)
    due_dt: datetime | None = None
    if proof_due_at:
        try:
            due_dt = datetime.fromisoformat(str(proof_due_at).replace("Z", "+00:00"))
        except Exception as e:
            raise HTTPException(status_code=422, detail=f"Invalid proof_due_at: {proof_due_at}") from e

    raw = await file.read()
    data = ProductionWorkspaceService().upload_galley(
        manuscript_id=id,
        cycle_id=cycle_id,
        user_id=str(current_user.get("id") or ""),
        profile_roles=profile.get("roles") or [],
        filename=file.filename or "proof.pdf",
        content=raw,
        version_note=version_note,
        proof_due_at=due_dt,
        content_type=file.content_type,
    )
    return {"success": True, "data": {"cycle": data}}


@router.get("/manuscripts/{id}/production-cycles/{cycle_id}/galley-signed")
async def get_production_galley_signed_url_editor(
    id: str,
    cycle_id: str,
    current_user: dict = Depends(get_current_user),
    profile: dict = Depends(require_any_role(["managing_editor", "production_editor", "editor_in_chief", "admin"])),
):
    """
    Feature 042: 编辑端获取清样 signed URL。
    """
    _enforce_scope_for_management_roles(manuscript_id=id, current_user=current_user, profile=profile)
    signed_url = ProductionWorkspaceService().get_galley_signed_url(
        manuscript_id=id,
        cycle_id=cycle_id,
        user_id=str(current_user.get("id") or ""),
        profile_roles=profile.get("roles") or [],
    )
    return {"success": True, "data": {"signed_url": signed_url}}


@router.post("/manuscripts/{id}/production-cycles/{cycle_id}/approve")
async def approve_production_cycle(
    id: str,
    cycle_id: str,
    current_user: dict = Depends(get_current_user),
    profile: dict = Depends(require_any_role(["managing_editor", "production_editor", "editor_in_chief", "admin"])),
):
    """
    Feature 042: 编辑确认发布前核准（approved_for_publish）。
    """
    _enforce_scope_for_management_roles(manuscript_id=id, current_user=current_user, profile=profile)
    data = ProductionWorkspaceService().approve_cycle(
        manuscript_id=id,
        cycle_id=cycle_id,
        user_id=str(current_user.get("id") or ""),
        profile_roles=profile.get("roles") or [],
    )
    return {"success": True, "data": data}


@router.get("/production/queue")
async def list_production_queue(
    limit: int = Query(50, ge=1, le=200),
    current_user: dict = Depends(get_current_user),
    profile: dict = Depends(require_any_role(["production_editor", "admin"])),
):
    """
    Production Editor Queue:
    - 返回当前 production_editor 被分配（layout_editor_id）的活跃 production cycles。
    """
    data = ProductionWorkspaceService().list_my_queue(
        user_id=str(current_user.get("id") or ""),
        profile_roles=profile.get("roles") or [],
        limit=limit,
    )
    return {"success": True, "data": data}
