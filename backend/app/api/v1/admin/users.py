from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import List, Optional
from uuid import UUID

from app.core.auth_utils import get_current_user
from app.core.roles import require_any_role
from app.services.user_management import UserManagementService
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