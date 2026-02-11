from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.v1.editor_common import (
    InternalCommentPayload,
    InternalTaskCreatePayload,
    InternalTaskUpdatePayload,
    is_missing_table_error as _is_missing_table_error,
)
from app.core.auth_utils import get_current_user
from app.core.roles import require_any_role
from app.lib.api_client import supabase_admin
from app.models.internal_task import InternalTaskStatus
from app.services.internal_collaboration_service import (
    InternalCollaborationSchemaMissingError,
    InternalCollaborationService,
    MentionValidationError,
)
from app.services.internal_task_service import InternalTaskSchemaMissingError, InternalTaskService

router = APIRouter(tags=["Editor Internal Collaboration"])
INTERNAL_COLLAB_ALLOWED_ROLES = ["admin", "managing_editor", "assistant_editor", "editor_in_chief"]


@router.get("/manuscripts/{id}/comments")
async def get_internal_comments(
    id: str,
    _profile: dict = Depends(require_any_role(INTERNAL_COLLAB_ALLOWED_ROLES)),
):
    """
    Feature 036: Fetch internal notebook comments (Staff only).
    """
    svc = InternalCollaborationService()
    try:
        return {"success": True, "data": svc.list_comments(id)}
    except InternalCollaborationSchemaMissingError as e:
        if e.table == "internal_comments":
            return {"success": True, "data": []}
        raise HTTPException(status_code=500, detail=f"DB not migrated: {e.table} table missing")
    except Exception as e:
        if _is_missing_table_error(e):
            return {"success": True, "data": []}
        print(f"[InternalComments] list failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch comments")


@router.post("/manuscripts/{id}/comments")
async def create_internal_comment(
    id: str,
    payload: InternalCommentPayload,
    current_user: dict = Depends(get_current_user),
    _profile: dict = Depends(require_any_role(INTERNAL_COLLAB_ALLOWED_ROLES)),
):
    """
    Feature 036: Post internal comment.
    """
    svc = InternalCollaborationService()
    try:
        comment = svc.create_comment(
            manuscript_id=id,
            author_user_id=str(current_user.get("id")),
            content=payload.content,
            mention_user_ids=payload.mention_user_ids,
        )
        return {"success": True, "data": comment}
    except MentionValidationError as e:
        raise HTTPException(
            status_code=422,
            detail={
                "message": "Invalid mention_user_ids",
                "invalid_user_ids": e.invalid_user_ids,
            },
        )
    except InternalCollaborationSchemaMissingError as e:
        raise HTTPException(status_code=500, detail=f"DB not migrated: {e.table} table missing")
    except HTTPException:
        raise
    except Exception as e:
        print(f"[InternalComments] create failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to post comment")


@router.get("/manuscripts/{id}/tasks")
async def list_internal_tasks(
    id: str,
    status: InternalTaskStatus | None = Query(None, description="任务状态筛选"),
    overdue_only: bool = Query(False, description="仅返回逾期任务"),
    current_user: dict = Depends(get_current_user),
    profile: dict = Depends(require_any_role(INTERNAL_COLLAB_ALLOWED_ROLES)),
):
    svc = InternalTaskService()
    try:
        rows = svc.list_tasks(
            manuscript_id=id,
            actor_user_id=str(current_user.get("id") or ""),
            actor_roles=profile.get("roles") or [],
            status=status,
            overdue_only=bool(overdue_only),
        )
        return {"success": True, "data": rows}
    except InternalTaskSchemaMissingError as e:
        raise HTTPException(status_code=500, detail=f"DB not migrated: {e.table} table missing")
    except HTTPException:
        raise
    except Exception as e:
        print(f"[InternalTasks] list failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch internal tasks")


@router.post("/manuscripts/{id}/tasks")
async def create_internal_task(
    id: str,
    payload: InternalTaskCreatePayload,
    current_user: dict = Depends(get_current_user),
    profile: dict = Depends(require_any_role(INTERNAL_COLLAB_ALLOWED_ROLES)),
):
    svc = InternalTaskService()
    try:
        task = svc.create_task(
            manuscript_id=id,
            actor_user_id=str(current_user.get("id") or ""),
            actor_roles=profile.get("roles") or [],
            title=payload.title,
            description=payload.description,
            assignee_user_id=payload.assignee_user_id,
            due_at=payload.due_at,
            status=payload.status,
            priority=payload.priority,
        )
        return {"success": True, "data": task}
    except InternalTaskSchemaMissingError as e:
        raise HTTPException(status_code=500, detail=f"DB not migrated: {e.table} table missing")
    except HTTPException:
        raise
    except Exception as e:
        print(f"[InternalTasks] create failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to create internal task")


@router.patch("/manuscripts/{id}/tasks/{task_id}")
async def patch_internal_task(
    id: str,
    task_id: str,
    payload: InternalTaskUpdatePayload,
    current_user: dict = Depends(get_current_user),
    profile: dict = Depends(require_any_role(INTERNAL_COLLAB_ALLOWED_ROLES)),
):
    svc = InternalTaskService()
    try:
        task = svc.update_task(
            manuscript_id=id,
            task_id=task_id,
            actor_user_id=str(current_user.get("id") or ""),
            actor_roles=profile.get("roles") or [],
            title=payload.title,
            description=payload.description,
            assignee_user_id=payload.assignee_user_id,
            status=payload.status,
            priority=payload.priority,
            due_at=payload.due_at,
        )
        return {"success": True, "data": task}
    except InternalTaskSchemaMissingError as e:
        raise HTTPException(status_code=500, detail=f"DB not migrated: {e.table} table missing")
    except HTTPException:
        raise
    except Exception as e:
        print(f"[InternalTasks] patch failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to update internal task")


@router.get("/manuscripts/{id}/tasks/{task_id}/activity")
async def get_internal_task_activity(
    id: str,
    task_id: str,
    _profile: dict = Depends(require_any_role(INTERNAL_COLLAB_ALLOWED_ROLES)),
):
    svc = InternalTaskService()
    try:
        rows = svc.list_activity(manuscript_id=id, task_id=task_id)
        return {"success": True, "data": rows}
    except InternalTaskSchemaMissingError as e:
        raise HTTPException(status_code=500, detail=f"DB not migrated: {e.table} table missing")
    except HTTPException:
        raise
    except Exception as e:
        print(f"[InternalTasks] activity failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch task activity")


@router.get("/manuscripts/{id}/audit-logs")
async def get_audit_logs(
    id: str,
    _profile: dict = Depends(require_any_role(INTERNAL_COLLAB_ALLOWED_ROLES)),
):
    """
    Feature 036: Fetch status transition logs.
    """
    try:
        resp = (
            supabase_admin.table("status_transition_logs")
            .select("*, changed_by")
            .eq("manuscript_id", id)
            .order("created_at", desc=True)
            .execute()
        )
        logs = getattr(resp, "data", None) or []

        user_ids = sorted(list(set(log["changed_by"] for log in logs if log.get("changed_by"))))
        users_map = {}
        if user_ids:
            try:
                u_resp = (
                    supabase_admin.table("user_profiles")
                    .select("id, full_name, email")
                    .in_("id", user_ids)
                    .execute()
                )
                for u in (getattr(u_resp, "data", None) or []):
                    users_map[u["id"]] = u
            except Exception:
                pass

        for log in logs:
            uid = log.get("changed_by")
            log["user"] = users_map.get(uid) or {"full_name": "System/Unknown", "email": ""}

        return {"success": True, "data": logs}
    except Exception as e:
        print(f"[AuditLogs] fetch failed: {e}")
        if "does not exist" in str(e):
            return {"success": True, "data": []}
        raise HTTPException(status_code=500, detail="Failed to fetch audit logs")
