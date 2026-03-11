from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.core.email_normalization import normalize_email
from app.core.role_matrix import can_perform_action
from app.lib.api_client import supabase_admin
from app.models.internal_task import InternalTaskPriority, InternalTaskStatus
from uuid import UUID




def _titleize_email_local_part(email: str | None) -> str:
    local = str(email or '').split('@', 1)[0].replace('.', ' ').replace('_', ' ').strip()
    return local.title() if local else 'Author'


def _normalize_author_contact(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    name = str(raw.get('name') or '').strip()
    email = normalize_email(raw.get('email'))
    affiliation = str(raw.get('affiliation') or '').strip()
    city = str(raw.get('city') or '').strip()
    country_or_region = str(raw.get('country_or_region') or '').strip()
    return {
        'name': name,
        'email': email,
        'affiliation': affiliation,
        'city': city,
        'country_or_region': country_or_region,
        'is_corresponding': bool(raw.get('is_corresponding')),
    }


def resolve_author_notification_target(
    *,
    manuscript: dict[str, Any] | None,
    manuscript_id: str | None = None,
    supabase_client: Any | None = None,
    author_profile: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    统一解析作者侧邮件接收目标。

    优先级：
    1. manuscripts.submission_email
    2. author_contacts 中的通讯作者邮箱
    3. user_profiles.email（作者账号邮箱）
    """
    manuscript_data = dict(manuscript or {})
    author_id = str(manuscript_data.get('author_id') or '').strip()

    need_fetch = bool(supabase_client and manuscript_id and (
        not manuscript_data.get('submission_email') or not isinstance(manuscript_data.get('author_contacts'), list)
    ))
    if need_fetch:
        try:
            fetched = (
                supabase_client.table('manuscripts')
                .select('author_id, submission_email, author_contacts')
                .eq('id', str(manuscript_id))
                .single()
                .execute()
            )
            fetched_data = getattr(fetched, 'data', None) or {}
            if isinstance(fetched_data, dict):
                for key in ('author_id', 'submission_email', 'author_contacts'):
                    if manuscript_data.get(key) in (None, '', []):
                        manuscript_data[key] = fetched_data.get(key)
                author_id = str(manuscript_data.get('author_id') or '').strip()
        except Exception:
            pass

    contacts: list[dict[str, Any]] = []
    raw_contacts = manuscript_data.get('author_contacts')
    if isinstance(raw_contacts, list):
        for item in raw_contacts:
            normalized = _normalize_author_contact(item)
            if normalized is not None:
                contacts.append(normalized)

    corresponding = next((item for item in contacts if item.get('is_corresponding')), None)
    first_contact = contacts[0] if contacts else None

    profile_data = dict(author_profile or {})
    need_profile = bool(supabase_client and author_id and not profile_data and (not corresponding or not corresponding.get('name')) )
    if need_profile or (supabase_client and author_id and not normalize_email(profile_data.get('email'))):
        try:
            prof = (
                supabase_client.table('user_profiles')
                .select('email, full_name')
                .eq('id', author_id)
                .single()
                .execute()
            )
            pdata = getattr(prof, 'data', None) or {}
            if isinstance(pdata, dict):
                profile_data.update({k: v for k, v in pdata.items() if v not in (None, '')})
        except Exception:
            pass

    submission_email = normalize_email(manuscript_data.get('submission_email'))
    corresponding_email = normalize_email((corresponding or {}).get('email'))
    profile_email = normalize_email(profile_data.get('email'))

    recipient_email = ''
    source = 'none'
    if submission_email:
        recipient_email = submission_email
        source = 'submission_email'
    elif corresponding_email:
        recipient_email = corresponding_email
        source = 'corresponding_author_email'
    elif profile_email:
        recipient_email = profile_email
        source = 'author_profile_email'

    recipient_name = (
        str((corresponding or {}).get('name') or '').strip()
        or str((first_contact or {}).get('name') or '').strip()
        or str(profile_data.get('full_name') or '').strip()
        or _titleize_email_local_part(recipient_email)
    )

    return {
        'recipient_email': recipient_email or None,
        'recipient_name': recipient_name or 'Author',
        'corresponding_author': corresponding,
        'source': source,
        'author_profile': profile_data or None,
    }


def extract_supabase_data(response: Any) -> Any:
    """
    兼容 supabase-py / postgrest 在不同版本下的 execute() 返回值形态。
    - 新版: response.data
    - 旧/自定义 mock: (error, data)
    """
    if response is None:
        return None
    data = getattr(response, "data", None)
    if data is not None:
        return data
    if isinstance(response, tuple) and len(response) == 2:
        return response[1]
    return None


def extract_supabase_error(response: Any) -> Any:
    """
    兼容不同版本的 supabase-py 错误字段。
    """
    if response is None:
        return None
    error = getattr(response, "error", None)
    if error:
        return error
    if isinstance(response, tuple) and len(response) == 2:
        return response[0]
    return None


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
    academic_editor_id: UUID | None = None
    idempotency_key: str | None = Field(default=None, max_length=64)


class RevertTechnicalCheckRequest(BaseModel):
    reason: str = Field(min_length=10, max_length=2000)
    source: str | None = Field(default=None, max_length=100)
    idempotency_key: str | None = Field(default=None, max_length=64)


class AcademicCheckRequest(BaseModel):
    decision: Literal["review", "decision_phase"]
    comment: str | None = Field(default=None, max_length=2000)
    idempotency_key: str | None = Field(default=None, max_length=64)


class BindAcademicEditorRequest(BaseModel):
    academic_editor_id: UUID
    reason: str | None = Field(default=None, max_length=2000)
    source: str | None = Field(default=None, max_length=100)


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
