from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import Any, List, Optional, Literal
from uuid import UUID
from datetime import datetime, timezone
import re
from pydantic import BaseModel, Field, field_validator

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
    RoleChangeLog,
    ResetPasswordRequest,
    ResetPasswordResponse,
)

# T016: Create admin users API router
router = APIRouter(tags=["Admin User Management"])

# T036: Implement admin role verification
admin_only = require_any_role(["admin"])
editor_or_admin = require_any_role(["admin", "managing_editor"])

def get_user_management_service():
    return UserManagementService()


class JournalScopeUpsertRequest(BaseModel):
    user_id: UUID
    journal_id: UUID
    role: Literal["managing_editor", "editor_in_chief"]
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


class JournalCreateRequest(BaseModel):
    title: str = Field(..., min_length=2, max_length=200)
    slug: str = Field(..., min_length=2, max_length=120)
    description: Optional[str] = Field(default=None, max_length=5000)
    issn: Optional[str] = Field(default=None, max_length=32)
    impact_factor: Optional[float] = Field(default=None, ge=0.0)
    cover_url: Optional[str] = Field(default=None, max_length=2000)
    is_active: bool = True

    @field_validator("title")
    @classmethod
    def _normalize_title(cls, value: str) -> str:
        return str(value or "").strip()

    @field_validator("slug")
    @classmethod
    def _normalize_slug(cls, value: str) -> str:
        return _normalize_journal_slug(value)


class JournalUpdateRequest(BaseModel):
    title: Optional[str] = Field(default=None, min_length=2, max_length=200)
    slug: Optional[str] = Field(default=None, min_length=2, max_length=120)
    description: Optional[str] = Field(default=None, max_length=5000)
    issn: Optional[str] = Field(default=None, max_length=32)
    impact_factor: Optional[float] = Field(default=None, ge=0.0)
    cover_url: Optional[str] = Field(default=None, max_length=2000)
    is_active: Optional[bool] = None

    @field_validator("title")
    @classmethod
    def _normalize_title(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        return str(value).strip() or None

    @field_validator("slug")
    @classmethod
    def _normalize_slug(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        return _normalize_journal_slug(value)

    @field_validator("description", "issn", "cover_url")
    @classmethod
    def _normalize_optional_text(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        trimmed = str(value).strip()
        return trimmed or None


class JournalResponse(BaseModel):
    id: UUID
    title: str
    slug: str
    description: Optional[str] = None
    issn: Optional[str] = None
    impact_factor: Optional[float] = None
    cover_url: Optional[str] = None
    is_active: bool = True
    created_at: datetime
    updated_at: Optional[datetime] = None


_JOURNAL_SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_SCOPE_REQUIRED_ROLES = {"managing_editor", "editor_in_chief"}
_SCOPE_TABLE = "journal_role_scopes"


def _normalize_journal_slug(raw_slug: str) -> str:
    slug = str(raw_slug or "").strip().lower()
    slug = re.sub(r"[^a-z0-9-]+", "-", slug)
    slug = re.sub(r"-{2,}", "-", slug).strip("-")
    if not slug or not _JOURNAL_SLUG_RE.match(slug):
        raise ValueError("slug must contain only lowercase letters, numbers, and hyphen")
    return slug


def _is_missing_column_error(error_text: str, column_name: str) -> bool:
    lowered = str(error_text or "").lower()
    col = str(column_name or "").strip().lower()
    if not col:
        return False
    return col in lowered and "does not exist" in lowered


def _is_duplicate_error(error_text: str) -> bool:
    lowered = str(error_text or "").lower()
    return "duplicate" in lowered or "unique constraint" in lowered


def _is_missing_table_error(error_text: str, table_name: str) -> bool:
    lowered = str(error_text or "").lower()
    needle = str(table_name or "").strip().lower()
    if not needle:
        return False
    return needle in lowered and ("does not exist" in lowered or "schema cache" in lowered)


def _normalize_uuid_strings(raw_values: Optional[List[UUID]]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for raw in raw_values or []:
        value = str(raw).strip()
        if not value or value in seen:
            continue
        seen.add(value)
        out.append(value)
    return out


def _list_active_user_scopes_by_roles(*, user_id: str, roles: list[str]) -> list[dict[str, Any]]:
    if not roles:
        return []
    try:
        resp = (
            supabase_admin.table(_SCOPE_TABLE)
            .select("id,user_id,journal_id,role,is_active")
            .eq("user_id", str(user_id))
            .eq("is_active", True)
            .in_("role", roles)
            .execute()
        )
    except Exception as e:
        if _is_missing_table_error(str(e), _SCOPE_TABLE):
            raise HTTPException(status_code=500, detail=f"DB not migrated: {_SCOPE_TABLE} table missing") from e
        raise
    return getattr(resp, "data", None) or []


def _ensure_journals_exist(*, journal_ids: list[str]) -> None:
    if not journal_ids:
        return
    try:
        resp = supabase_admin.table("journals").select("id").in_("id", journal_ids).execute()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to validate journals: {e}") from e
    rows = getattr(resp, "data", None) or []
    existing = {str(row.get("id") or "").strip() for row in rows if str(row.get("id") or "").strip()}
    missing = [jid for jid in journal_ids if jid not in existing]
    if missing:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid journal ids: {', '.join(missing)}",
        )


def _sync_required_role_scopes(
    *,
    user_id: str,
    role: str,
    journal_ids: list[str],
    actor_id: str,
) -> None:
    now_iso = datetime.now(timezone.utc).isoformat()
    payload = [
        {
            "user_id": str(user_id),
            "journal_id": journal_id,
            "role": role,
            "is_active": True,
            "created_by": actor_id,
            "updated_at": now_iso,
        }
        for journal_id in journal_ids
    ]

    if payload:
        try:
            (
                supabase_admin.table(_SCOPE_TABLE)
                .upsert(payload, on_conflict="user_id,journal_id,role")
                .execute()
            )
        except Exception as e:
            if _is_missing_table_error(str(e), _SCOPE_TABLE):
                raise HTTPException(status_code=500, detail=f"DB not migrated: {_SCOPE_TABLE} table missing") from e
            raise HTTPException(status_code=500, detail=f"Failed to upsert journal scopes: {e}") from e

    try:
        existing = (
            supabase_admin.table(_SCOPE_TABLE)
            .select("id,journal_id")
            .eq("user_id", str(user_id))
            .eq("role", role)
            .eq("is_active", True)
            .execute()
        )
    except Exception as e:
        if _is_missing_table_error(str(e), _SCOPE_TABLE):
            raise HTTPException(status_code=500, detail=f"DB not migrated: {_SCOPE_TABLE} table missing") from e
        raise HTTPException(status_code=500, detail=f"Failed to list journal scopes: {e}") from e

    target = set(journal_ids)
    existing_rows = getattr(existing, "data", None) or []
    for row in existing_rows:
        row_id = str(row.get("id") or "").strip()
        row_journal_id = str(row.get("journal_id") or "").strip()
        if not row_id or not row_journal_id or row_journal_id in target:
            continue
        try:
            (
                supabase_admin.table(_SCOPE_TABLE)
                .update({"is_active": False, "updated_at": now_iso})
                .eq("id", row_id)
                .execute()
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to deactivate journal scope: {e}") from e


def _deactivate_required_role_scopes(*, user_id: str, roles: list[str]) -> None:
    if not roles:
        return
    now_iso = datetime.now(timezone.utc).isoformat()
    for role in roles:
        try:
            (
                supabase_admin.table(_SCOPE_TABLE)
                .update({"is_active": False, "updated_at": now_iso})
                .eq("user_id", str(user_id))
                .eq("role", role)
                .eq("is_active", True)
                .execute()
            )
        except Exception as e:
            if _is_missing_table_error(str(e), _SCOPE_TABLE):
                raise HTTPException(status_code=500, detail=f"DB not migrated: {_SCOPE_TABLE} table missing") from e
            raise HTTPException(status_code=500, detail=f"Failed to deactivate journal scopes: {e}") from e


def _fallback_journal_rows(rows: list[dict[str, Any]], *, include_inactive: bool) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for row in rows:
        copied = dict(row)
        copied.setdefault("is_active", True)
        copied.setdefault("updated_at", copied.get("created_at"))
        normalized.append(copied)

    if include_inactive:
        return normalized
    return [row for row in normalized if bool(row.get("is_active", True))]


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
        requested_roles = set(request.resolved_roles())
        required_scope_roles = sorted(requested_roles.intersection(_SCOPE_REQUIRED_ROLES))
        requested_journal_ids = _normalize_uuid_strings(request.scope_journal_ids)

        if required_scope_roles:
            if requested_journal_ids:
                _ensure_journals_exist(journal_ids=requested_journal_ids)
            else:
                existing_scopes = _list_active_user_scopes_by_roles(
                    user_id=str(user_id),
                    roles=required_scope_roles,
                )
                scoped_roles = {
                    str(row.get("role") or "").strip()
                    for row in existing_scopes
                    if str(row.get("journal_id") or "").strip()
                }
                missing_roles = [role for role in required_scope_roles if role not in scoped_roles]
                if missing_roles:
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail=(
                            "managing_editor/editor_in_chief requires journal binding. "
                            "Provide scope_journal_ids or pre-bind scopes via /api/v1/admin/journal-scopes."
                        ),
                    )

        # T059: We pass current_user['id'] as changed_by
        result = service.update_user_role(
            target_user_id=user_id,
            new_role=request.new_role,
            new_roles=request.resolved_roles(),
            reason=request.reason,
            changed_by=UUID(current_user["id"])
        )

        if required_scope_roles:
            if requested_journal_ids:
                for role in required_scope_roles:
                    _sync_required_role_scopes(
                        user_id=str(user_id),
                        role=role,
                        journal_ids=requested_journal_ids,
                        actor_id=str(current_user.get("id") or ""),
                    )
        else:
            _deactivate_required_role_scopes(user_id=str(user_id), roles=sorted(_SCOPE_REQUIRED_ROLES))

        return result
    except HTTPException:
        raise
    except ValueError as e:
        # Handle known business logic errors
        msg = str(e)
        if (
            "Cannot modify" in msg
            or "Cannot remove your own admin role" in msg
            or "You can only add roles to yourself" in msg
        ):
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


@router.post("/admin/users/{user_id}/reset-password", response_model=ResetPasswordResponse)
async def reset_user_password(
    user_id: UUID,
    request: ResetPasswordRequest,
    _admin: dict = Depends(admin_only),
    service: UserManagementService = Depends(get_user_management_service),
    current_user: dict = Depends(get_current_user),
):
    """
    Admin 将指定用户密码重置为临时密码（默认由后端生成强随机密码）。
    """
    try:
        return service.reset_user_password(
            target_user_id=user_id,
            changed_by=UUID(current_user["id"]),
            temporary_password=request.temporary_password,
        )
    except ValueError as e:
        msg = str(e)
        if "User not found" in msg:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=msg)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/admin/journals", response_model=List[JournalResponse])
async def list_admin_journals(
    include_inactive: bool = Query(False),
    _admin: dict = Depends(admin_only),
):
    """
    Journal Management: 获取期刊列表（admin only）。
    """
    try:
        query = (
            supabase_admin.table("journals")
            .select("id,title,slug,description,issn,impact_factor,cover_url,is_active,created_at,updated_at")
        )
        if not include_inactive:
            query = query.eq("is_active", True)
        resp = query.order("title", desc=False).execute()
        rows = getattr(resp, "data", None) or []
        return rows
    except Exception as e:
        if _is_missing_column_error(str(e), "is_active") or _is_missing_column_error(str(e), "updated_at"):
            fallback = (
                supabase_admin.table("journals")
                .select("id,title,slug,description,issn,impact_factor,cover_url,created_at")
                .order("title", desc=False)
                .execute()
            )
            fallback_rows = getattr(fallback, "data", None) or []
            return _fallback_journal_rows(fallback_rows, include_inactive=include_inactive)

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post("/admin/journals", response_model=JournalResponse, status_code=status.HTTP_201_CREATED)
async def create_admin_journal(
    request: JournalCreateRequest,
    _admin: dict = Depends(admin_only),
):
    """
    Journal Management: 创建期刊（admin only）。
    """
    now_iso = datetime.now(timezone.utc).isoformat()
    payload: dict[str, Any] = {
        "title": request.title,
        "slug": request.slug,
        "description": request.description,
        "issn": request.issn,
        "impact_factor": request.impact_factor,
        "cover_url": request.cover_url,
        "is_active": bool(request.is_active),
        "created_at": now_iso,
        "updated_at": now_iso,
    }

    try:
        resp = supabase_admin.table("journals").insert(payload).execute()
        rows = getattr(resp, "data", None) or []
        if not rows:
            raise HTTPException(status_code=500, detail="Failed to create journal")
        return rows[0]
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        text = str(e)
        if _is_missing_column_error(text, "is_active") or _is_missing_column_error(text, "updated_at"):
            fallback_payload = dict(payload)
            fallback_payload.pop("is_active", None)
            fallback_payload.pop("updated_at", None)
            fallback_resp = supabase_admin.table("journals").insert(fallback_payload).execute()
            fallback_rows = getattr(fallback_resp, "data", None) or []
            if not fallback_rows:
                raise HTTPException(status_code=500, detail="Failed to create journal")
            row = dict(fallback_rows[0])
            row.setdefault("is_active", True)
            row.setdefault("updated_at", row.get("created_at"))
            return row
        if _is_duplicate_error(text):
            raise HTTPException(status_code=409, detail="Journal slug already exists")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=text,
        )


@router.put("/admin/journals/{journal_id}", response_model=JournalResponse)
async def update_admin_journal(
    journal_id: UUID,
    request: JournalUpdateRequest,
    _admin: dict = Depends(admin_only),
):
    """
    Journal Management: 更新期刊（admin only）。
    """
    patch: dict[str, Any] = {}
    if request.title is not None:
        patch["title"] = request.title
    if request.slug is not None:
        patch["slug"] = request.slug
    if request.description is not None:
        patch["description"] = request.description
    if request.issn is not None:
        patch["issn"] = request.issn
    if request.impact_factor is not None:
        patch["impact_factor"] = request.impact_factor
    if request.cover_url is not None:
        patch["cover_url"] = request.cover_url
    if request.is_active is not None:
        patch["is_active"] = bool(request.is_active)

    if not patch:
        raise HTTPException(status_code=422, detail="No fields to update")

    patch["updated_at"] = datetime.now(timezone.utc).isoformat()

    try:
        resp = (
            supabase_admin.table("journals")
            .update(patch)
            .eq("id", str(journal_id))
            .execute()
        )
        rows = getattr(resp, "data", None) or []
        if not rows:
            raise HTTPException(status_code=404, detail="Journal not found")
        return rows[0]
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        text = str(e)
        if _is_missing_column_error(text, "is_active") or _is_missing_column_error(text, "updated_at"):
            fallback_patch = dict(patch)
            fallback_patch.pop("updated_at", None)
            if "is_active" in fallback_patch:
                raise HTTPException(
                    status_code=500,
                    detail="DB not migrated: journals.is_active column missing",
                )
            fallback_resp = (
                supabase_admin.table("journals")
                .update(fallback_patch)
                .eq("id", str(journal_id))
                .execute()
            )
            fallback_rows = getattr(fallback_resp, "data", None) or []
            if not fallback_rows:
                raise HTTPException(status_code=404, detail="Journal not found")
            row = dict(fallback_rows[0])
            row.setdefault("is_active", True)
            row.setdefault("updated_at", row.get("created_at"))
            return row
        if _is_duplicate_error(text):
            raise HTTPException(status_code=409, detail="Journal slug already exists")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=text,
        )


@router.delete("/admin/journals/{journal_id}", response_model=JournalResponse)
async def deactivate_admin_journal(
    journal_id: UUID,
    _admin: dict = Depends(admin_only),
):
    """
    Journal Management: 停用期刊（软删除，admin only）。
    """
    patch = {
        "is_active": False,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    try:
        resp = (
            supabase_admin.table("journals")
            .update(patch)
            .eq("id", str(journal_id))
            .execute()
        )
        rows = getattr(resp, "data", None) or []
        if not rows:
            raise HTTPException(status_code=404, detail="Journal not found")
        return rows[0]
    except HTTPException:
        raise
    except Exception as e:
        text = str(e)
        if _is_missing_column_error(text, "is_active"):
            raise HTTPException(
                status_code=500,
                detail="DB not migrated: journals.is_active column missing",
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=text,
        )
