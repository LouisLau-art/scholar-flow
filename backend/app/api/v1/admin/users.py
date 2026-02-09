from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import Any, List, Optional, Literal
from uuid import UUID
from datetime import datetime, timezone
from pydantic import BaseModel, Field

from app.core.auth_utils import get_current_user
from app.core.roles import require_any_role
from app.services.user_management import UserManagementService
from app.lib.api_client import supabase_admin
from app.models.user_management import (
    UserListResponse, 
    UserResponse, 
    CreateUserRequest, 
    UpdateRoleRequest, 
    InviteReviewerRequest,
    RoleChangeLog
)

# T016: Create admin users API router
router = APIRouter(tags=["Admin User Management"])

# T036: Implement admin role verification
admin_only = require_any_role(["admin"])
editor_or_admin = require_any_role(["admin", "editor"])

def get_user_management_service():
    return UserManagementService()


class JournalScopeUpsertRequest(BaseModel):
    user_id: UUID
    journal_id: UUID
    role: Literal["editor", "managing_editor", "assistant_editor", "editor_in_chief", "admin"]
    is_active: bool = True


class JournalScopeListItem(BaseModel):
    id: UUID
    user_id: UUID
    journal_id: UUID
    role: str
    is_active: bool
    created_by: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime


@router.get("/admin/users", response_model=UserListResponse)
async def get_users(
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
    search: Optional[str] = None,
    role: Optional[str] = None,
    _auth: dict = Depends(editor_or_admin),
    service: UserManagementService = Depends(get_user_management_service)
):
    """
    T032: Get list of users with pagination, search and filters.
    """
    try:
        return service.get_users(page=page, per_page=per_page, search=search, role=role)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/admin/journal-scopes", response_model=List[JournalScopeListItem])
async def list_journal_scopes(
    user_id: Optional[UUID] = Query(None),
    journal_id: Optional[UUID] = Query(None),
    is_active: Optional[bool] = Query(None),
    _admin: dict = Depends(admin_only),
):
    """
    GAP-P1-05: 查看 journal role scope 绑定（admin only）。
    """
    try:
        query = supabase_admin.table("journal_role_scopes").select(
            "id,user_id,journal_id,role,is_active,created_by,created_at,updated_at"
        )
        if user_id:
            query = query.eq("user_id", str(user_id))
        if journal_id:
            query = query.eq("journal_id", str(journal_id))
        if is_active is not None:
            query = query.eq("is_active", bool(is_active))

        resp = query.order("created_at", desc=True).execute()
        rows = getattr(resp, "data", None) or []
        return rows
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post("/admin/journal-scopes", response_model=JournalScopeListItem, status_code=status.HTTP_201_CREATED)
async def upsert_journal_scope(
    request: JournalScopeUpsertRequest,
    current_user: dict = Depends(get_current_user),
    _admin: dict = Depends(admin_only),
):
    """
    GAP-P1-05: 创建/更新 journal role scope 绑定（admin only）。
    """
    payload: dict[str, Any] = {
        "user_id": str(request.user_id),
        "journal_id": str(request.journal_id),
        "role": request.role,
        "is_active": bool(request.is_active),
        "created_by": str(current_user.get("id") or ""),
    }

    try:
        resp = (
            supabase_admin.table("journal_role_scopes")
            .upsert(payload, on_conflict="user_id,journal_id,role")
            .execute()
        )
        rows = getattr(resp, "data", None) or []
        if not rows:
            raise HTTPException(status_code=500, detail="Failed to upsert journal scope")
        return rows[0]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.delete("/admin/journal-scopes/{scope_id}", response_model=JournalScopeListItem)
async def deactivate_journal_scope(
    scope_id: UUID,
    _admin: dict = Depends(admin_only),
):
    """
    GAP-P1-05: 停用 journal role scope（软停用，admin only）。
    """
    try:
        resp = (
            supabase_admin.table("journal_role_scopes")
            .update(
                {
                    "is_active": False,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
            )
            .eq("id", str(scope_id))
            .execute()
        )
        rows = getattr(resp, "data", None) or []
        if not rows:
            raise HTTPException(status_code=404, detail="Journal scope not found")
        return rows[0]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )

@router.post("/admin/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    request: CreateUserRequest,
    _admin: dict = Depends(admin_only),
    service: UserManagementService = Depends(get_user_management_service),
    current_user: dict = Depends(get_current_user)
):
    """
    T082: Create internal user.
    """
    try:
        return service.create_internal_user(
            email=request.email,
            full_name=request.full_name,
            role=request.role,
            created_by=UUID(current_user["id"])
        )
    except ValueError as e:
        if "already exists" in str(e):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.put("/admin/users/{user_id}/role", response_model=UserResponse)
async def update_user_role(
    user_id: UUID,
    request: UpdateRoleRequest,
    _admin: dict = Depends(admin_only),
    service: UserManagementService = Depends(get_user_management_service),
    current_user: dict = Depends(get_current_user)
):
    """
    T056: Update user role.
    """
    try:
        # T059: We pass current_user['id'] as changed_by
        return service.update_user_role(
            target_user_id=user_id,
            new_role=request.new_role,
            new_roles=request.resolved_roles(),
            reason=request.reason,
            changed_by=UUID(current_user["id"])
        )
    except ValueError as e:
        # Handle known business logic errors
        msg = str(e)
        if "Cannot modify" in msg:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=msg)
        if "User not found" in msg:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=msg)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/admin/users/{user_id}/role-changes", response_model=List[RoleChangeLog])
async def get_role_changes(
    user_id: UUID,
    _admin: dict = Depends(admin_only),
    service: UserManagementService = Depends(get_user_management_service)
):
    """
    T061: Get role change history for a user.
    """
    try:
        return service.get_role_changes(user_id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.post("/admin/users/invite-reviewer", response_model=UserResponse)
async def invite_reviewer(
    request: InviteReviewerRequest,
    _auth: dict = Depends(editor_or_admin),
    service: UserManagementService = Depends(get_user_management_service),
    current_user: dict = Depends(get_current_user)
):
    """
    T105: Invite reviewer via Magic Link.
    """
    try:
        return service.invite_reviewer(
            email=request.email,
            full_name=request.full_name,
            invited_by=UUID(current_user["id"])
        )
    except ValueError as e:
        if "already exists" in str(e):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
