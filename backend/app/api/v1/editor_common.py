from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.core.role_matrix import can_perform_action
from app.lib.api_client import supabase_admin
from app.models.internal_task import InternalTaskPriority, InternalTaskStatus
from uuid import UUID


def require_action_or_403(*, action: str, roles: list[str] | None) -> None:
    """
    统一动作级权限拦截（角色矩阵）。

    中文注释:
    - 路由级 require_any_role 负责“是否内部角色”；
    - 这里负责“内部角色中谁能做哪个动作”。
    """
    if not can_perform_action(action=action, roles=roles):
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail=f"Insufficient permission for action: {action}")


class InternalCommentPayload(BaseModel):
    content: str
    mention_user_ids: list[str] = Field(default_factory=list)


class InternalTaskCreatePayload(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=4000)
    assignee_user_id: str
    due_at: datetime
    status: InternalTaskStatus = InternalTaskStatus.TODO
    priority: InternalTaskPriority = InternalTaskPriority.MEDIUM


class InternalTaskUpdatePayload(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=4000)
    assignee_user_id: str | None = None
    status: InternalTaskStatus | None = None
    priority: InternalTaskPriority | None = None
    due_at: datetime | None = None


class InvoiceInfoUpdatePayload(BaseModel):
    authors: str | None = None
    affiliation: str | None = None
    apc_amount: float | None = Field(default=None, ge=0)
    funding_info: str | None = None
    reason: str | None = Field(default=None, max_length=2000)
    source: str | None = Field(default=None, max_length=100)


class QuickPrecheckPayload(BaseModel):
    decision: Literal["approve", "revision"]
    comment: str | None = Field(default=None, max_length=2000)


class AssignAERequest(BaseModel):
    ae_id: UUID
    owner_id: UUID | None = None
    start_external_review: bool = False
    bind_owner_if_empty: bool = False
    idempotency_key: str | None = Field(default=None, max_length=64)


class IntakeRevisionRequest(BaseModel):
    comment: str = Field(min_length=1, max_length=2000)
    idempotency_key: str | None = Field(default=None, max_length=64)


class TechnicalCheckRequest(BaseModel):
    decision: Literal["pass", "revision", "academic"]
    comment: str | None = Field(default=None, max_length=2000)
    idempotency_key: str | None = Field(default=None, max_length=64)


class AcademicCheckRequest(BaseModel):
    decision: Literal["review", "decision_phase"]
    comment: str | None = Field(default=None, max_length=2000)
    idempotency_key: str | None = Field(default=None, max_length=64)


class ConfirmInvoicePaidPayload(BaseModel):
    manuscript_id: str
    expected_status: Literal["unpaid", "paid", "waived"] | None = None
    source: Literal["editor_pipeline", "finance_page", "unknown"] = "unknown"


def get_signed_url(bucket: str, file_path: str, *, expires_in: int = 60 * 10) -> str | None:
    """
    生成 Supabase Storage signed URL（Editor/Admin 详情页使用）。

    中文注释:
    - 详情页的 iframe / 新标签页打开通常不携带 Authorization header；
    - 因此后端统一生成短期 signed URL。
    - 若签名失败，返回 None（不阻断页面加载）。
    """
    path = (file_path or "").strip()
    if not path:
        return None
    try:
        signed = supabase_admin.storage.from_(bucket).create_signed_url(path, expires_in)
        return (signed or {}).get("signedUrl") or (signed or {}).get("signedURL")
    except Exception as e:
        print(f"[SignedURL] create_signed_url failed: bucket={bucket} path={path} err={e}")
        return None


def ensure_bucket_exists(bucket: str, *, public: bool = False) -> None:
    """
    确保存储桶存在（用于演示/首次部署自愈）。
    - 失败不阻断：后续 upload 会返回更明确的错误。
    """
    try:
        storage = supabase_admin.storage
        storage.get_bucket(bucket)
    except Exception:
        try:
            supabase_admin.storage.create_bucket(bucket, options={"public": bool(public)})
        except Exception:
            return


def is_missing_table_error(error: Any) -> bool:
    parts: list[str] = []
    try:
        s = str(error or "")
        if s:
            parts.append(s)
    except Exception:
        pass
    try:
        r = repr(error)
        if r:
            parts.append(r)
    except Exception:
        pass
    try:
        args = getattr(error, "args", None) or []
        for item in args:
            v = str(item)
            if v:
                parts.append(v)
    except Exception:
        pass

    t = " | ".join(parts).lower()
    missing_markers = (
        "does not exist",
        "schema cache",
        "could not find the table",
        "pgrst205",
    )
    if not any(marker in t for marker in missing_markers):
        return False
    return any(
        name in t
        for name in (
            "manuscript_files",
            "internal_comments",
            "internal_comment_mentions",
            "internal_tasks",
            "internal_task_activity_logs",
        )
    )


def list_auth_user_id_set() -> set[str]:
    """
    列出当前项目中真实存在于 auth.users 的用户 ID 集合。
    """
    try:
        res = supabase_admin.auth.admin.list_users()
        users = getattr(res, "users", None)
        if users is None and isinstance(res, dict):
            users = res.get("users") or res.get("data")
        if users is None and isinstance(res, list):
            users = res
        if not isinstance(users, list):
            users = []
        out: set[str] = set()
        for user in users:
            uid = None
            if isinstance(user, dict):
                uid = user.get("id")
            else:
                uid = getattr(user, "id", None)
            if uid:
                out.add(str(uid))
        return out
    except Exception as e:
        print(f"[InternalStaff] list auth users failed: {e}")
        return set()


def auth_user_exists(user_id: str) -> bool:
    uid = str(user_id or "").strip()
    if not uid:
        return False
    try:
        res = supabase_admin.auth.admin.get_user_by_id(uid)
        user = getattr(res, "user", None)
        if user is None and isinstance(res, dict):
            user = res.get("user") or res.get("data")
        if isinstance(user, dict):
            return str(user.get("id") or "") == uid
        return bool(user) and str(getattr(user, "id", "") or "") == uid
    except Exception:
        return False
