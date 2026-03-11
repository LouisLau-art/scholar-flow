import os
import re
from datetime import datetime, timezone
from urllib.parse import quote

from fastapi import APIRouter, HTTPException, Depends, Body, UploadFile, File, Form, Response, Query
from pydantic import BaseModel, ConfigDict, EmailStr, field_validator
from app.lib.api_client import supabase, supabase_admin
from app.core.auth_utils import get_current_user
from app.core.roles import require_any_role
from app.core.role_matrix import normalize_roles
from app.core.email_normalization import normalize_email
from app.core.storage_filename import sanitize_storage_filename
from uuid import UUID
from typing import Any, Dict, Optional
from postgrest.exceptions import APIError

from fastapi import Cookie

from app.core.security import create_magic_link_jwt, decode_magic_link_jwt
from app.models.email_log import EmailStatus
from app.schemas.review import InviteAcceptPayload, InviteDeclinePayload, ReviewSubmission
from app.schemas.review import AssignmentCancelPayload
from app.schemas.token import MagicLinkPayload
from app.core.mail import email_service
from app.services.reviewer_service import ReviewPolicyService, ReviewerInviteService, ReviewerWorkspaceService
from app.api.v1.reviews_common import (
    ensure_review_attachments_bucket_exists,
    ensure_review_management_access,
    get_signed_url_for_manuscripts_bucket,
    get_signed_url_for_review_attachments_bucket,
    is_admin_email,
    is_foreign_key_user_error,
    is_missing_relation_error,
    parse_roles,
)
from app.api.v1.reviews_heavy_handlers import (
    assign_reviewer_impl,
    cancel_reviewer_impl,
    establish_reviewer_workspace_session_impl,
    get_review_by_token_impl,
    get_manuscript_assignments_impl,
    submit_review_by_token_impl,
    submit_review_impl,
    submit_review_via_magic_link_impl,
    unassign_reviewer_impl,
)
from app.api.v1.reviews_handlers_workspace_magic import (
    accept_reviewer_invitation_impl,
    decline_reviewer_invitation_impl,
    get_review_assignment_pdf_signed_via_magic_link_impl,
    get_review_assignment_via_magic_link_impl,
    get_review_attachment_signed_by_token_impl,
    get_review_attachment_signed_impl,
    get_review_attachment_signed_via_magic_link_impl,
    get_review_feedback_for_manuscript_impl,
    get_review_pdf_signed_by_token_impl,
    get_reviewer_invite_data_impl,
    get_reviewer_workspace_data_impl,
    submit_reviewer_workspace_review_impl,
    upload_reviewer_workspace_attachment_impl,
)

router = APIRouter(tags=["Reviews"])

_EMAIL_TEMPLATE_KEY_RE = re.compile(r"^[a-z0-9_]{2,64}$")
_EMAIL_TEMPLATE_SCENE_RE = re.compile(r"^[a-z0-9_]{2,64}$")
_EMAIL_TEMPLATE_TABLE = "email_templates"
_REVIEW_ASSIGNMENT_SCENE = "reviewer_assignment"
_REVIEW_TEMPLATE_KEY_ALIASES = {
    "invitation": "reviewer_invitation_standard",
    "reminder": "reviewer_reminder_polite",
}

_DEFAULT_REVIEW_ASSIGNMENT_TEMPLATES: dict[str, dict[str, Any]] = {
    "reviewer_invitation_standard": {
        "template_key": "reviewer_invitation_standard",
        "display_name": "审稿邀请信（标准）",
        "description": "默认审稿邀请模板",
        "scene": _REVIEW_ASSIGNMENT_SCENE,
        "event_type": "invitation",
        "subject_template": "Invitation to Review - {{ journal_title }}",
        "body_html_template": (
            "<p>Dear {{ reviewer_name }},</p>"
            "<p>You are invited to review <strong>{{ manuscript_title }}</strong> for <strong>{{ journal_title }}</strong>.</p>"
            "<p>Due date: {{ due_date or due_at or '-' }}</p>"
            "<p>Invitation link: <a href=\"{{ review_url }}\">{{ review_url }}</a></p>"
        ),
        "body_text_template": (
            "Dear {{ reviewer_name }}, you are invited to review "
            "\"{{ manuscript_title }}\" for {{ journal_title }}. Due {{ due_date or due_at or '-' }}. "
            "Link: {{ review_url }}"
        ),
        "is_active": True,
    },
    "reviewer_reminder_polite": {
        "template_key": "reviewer_reminder_polite",
        "display_name": "审稿催促信（礼貌）",
        "description": "默认审稿催促模板",
        "scene": _REVIEW_ASSIGNMENT_SCENE,
        "event_type": "reminder",
        "subject_template": "Friendly Reminder - {{ journal_title }}",
        "body_html_template": (
            "<p>Dear {{ reviewer_name }},</p>"
            "<p>This is a reminder for your review of <strong>{{ manuscript_title }}</strong> in <strong>{{ journal_title }}</strong>.</p>"
            "<p>Current due date: {{ due_date or due_at or '-' }}</p>"
            "<p>Continue here: <a href=\"{{ review_url }}\">{{ review_url }}</a></p>"
        ),
        "body_text_template": (
            "Reminder for {{ manuscript_title }} ({{ journal_title }}). "
            "Due {{ due_date or due_at or '-' }}. Link: {{ review_url }}"
        ),
        "is_active": True,
    },
}


class AssignmentEmailActionPayload(BaseModel):
    model_config = ConfigDict(extra="ignore")

    template_key: str | None = None
    template: str | None = None
    recipient_email: EmailStr | None = None
    idempotency_key: str | None = None

    @field_validator("recipient_email", mode="before")
    @classmethod
    def _normalize_recipient_email(cls, value: Any) -> Any:
        normalized = normalize_email(value)
        return normalized or None


def _is_missing_assignment_audit_column_error(error: Exception | str) -> bool:
    text = str(error or "").lower()
    return (
        ("pgrst204" in text or "column" in text or "does not exist" in text)
        and any(
            column in text
            for column in (
                "selected_by",
                "selected_via",
                "invited_by",
                "invited_via",
                "cancelled_at",
                "cancelled_by",
                "cancel_reason",
                "cancel_via",
            )
        )
    )


def _is_missing_review_assignment_column_error(error: Exception | str, *columns: str) -> bool:
    text = str(error or "").lower()
    return ("pgrst204" in text or "column" in text or "does not exist" in text) and any(
        str(column or "").strip().lower() in text for column in columns
    )


def _load_assignment_for_send_email(assignment_id: str) -> dict[str, Any]:
    select_variants = (
        "id, manuscript_id, reviewer_id, status, due_at, invited_at, last_reminded_at, invited_by, invited_via, round_number, selected_by, selected_via, declined_at, decline_reason, decline_note",
        "id, manuscript_id, reviewer_id, status, due_at, invited_at, last_reminded_at, round_number, declined_at, decline_reason, decline_note",
        "id, manuscript_id, reviewer_id, status, due_at, invited_at, last_reminded_at, round_number, declined_at",
        "id, manuscript_id, reviewer_id, status, due_at, invited_at, last_reminded_at, round_number",
        "id, manuscript_id, reviewer_id, status, due_at, invited_at, last_reminded_at",
    )
    last_exc: Exception | None = None
    for select_clause in select_variants:
        try:
            res = (
                supabase_admin.table("review_assignments")
                .select(select_clause)
                .eq("id", assignment_id)
                .single()
                .execute()
            )
            return getattr(res, "data", None) or {}
        except Exception as exc:
            last_exc = exc
            if not _is_missing_review_assignment_column_error(
                exc,
                "selected_by",
                "selected_via",
                "invited_by",
                "invited_via",
                "round_number",
                "declined_at",
                "decline_reason",
                "decline_note",
            ):
                raise
    if last_exc:
        raise last_exc
    return {}


def _insert_reinvite_assignment_attempt(
    *,
    assignment: dict[str, Any],
    current_user_id: str,
) -> dict[str, Any]:
    base_payload: dict[str, Any] = {
        "manuscript_id": str(assignment.get("manuscript_id") or "").strip(),
        "reviewer_id": str(assignment.get("reviewer_id") or "").strip(),
        "status": "selected",
        "due_at": assignment.get("due_at"),
        "invited_at": None,
        "last_reminded_at": None,
        "opened_at": None,
        "accepted_at": None,
        "declined_at": None,
        "decline_reason": None,
        "decline_note": None,
    }
    round_number = assignment.get("round_number")
    if round_number is not None:
        base_payload["round_number"] = round_number
    if current_user_id:
        base_payload["selected_by"] = current_user_id
    base_payload["selected_via"] = "system_reinvite"

    payload_variants: list[dict[str, Any]] = [
        dict(base_payload),
        {
            key: value
            for key, value in base_payload.items()
            if key not in {"selected_by", "selected_via"}
        },
        {
            key: value
            for key, value in base_payload.items()
            if key
            not in {
                "selected_by",
                "selected_via",
                "opened_at",
                "accepted_at",
                "declined_at",
                "decline_reason",
                "decline_note",
                "last_reminded_at",
            }
        },
    ]
    last_exc: Exception | None = None
    for payload in payload_variants:
        try:
            res = supabase_admin.table("review_assignments").insert(payload).execute()
            data = getattr(res, "data", None) or []
            if isinstance(data, list) and data:
                row = dict(data[0])
            elif isinstance(data, dict) and data:
                row = dict(data)
            else:
                row = {}
            if not str(row.get("id") or "").strip():
                raise HTTPException(status_code=500, detail="Failed to fetch reviewer re-invite assignment id")
            return row
        except Exception as exc:
            last_exc = exc
            if not _is_missing_review_assignment_column_error(
                exc,
                "selected_by",
                "selected_via",
                "invited_by",
                "invited_via",
                "opened_at",
                "accepted_at",
                "declined_at",
                "decline_reason",
                "decline_note",
                "last_reminded_at",
            ):
                raise
    if last_exc:
        raise last_exc
    raise HTTPException(status_code=500, detail="Failed to create reviewer re-invite attempt")


def _build_assignment_email_idempotency_key(
    *,
    assignment_id: str,
    template_key: str,
    event_type: str,
    now: datetime,
    assignment_status: str | None = None,
) -> str:
    """
    中文注释:
    - invitation：仅首次 `selected` 邀请使用固定 key，防止重复点击产生多封邀请。
      已进入 `invited/opened/pending` 的再次发送属于合法重发，应生成新的 key，避免
      Resend 因“同 key 但 body 已变化（如新 magic link / 新环境 URL）”返回 409。
    - reminder：按小时去重，避免短时间重复触发；跨小时可再次发送。
    - none/其他：按分钟去重，兼顾防抖与可重复发送。
    """
    event = str(event_type or "none").strip().lower()
    if event == "invitation":
        status = str(assignment_status or "").strip().lower()
        if status == "selected":
            return f"reviewer-invitation/{assignment_id}"
        return f"reviewer-invitation-resend/{assignment_id}/{now.strftime('%Y%m%d%H%M%S%f')}"
    if event == "reminder":
        return f"reviewer-reminder/{assignment_id}/{now.strftime('%Y%m%d%H')}"
    return f"reviewer-email/{assignment_id}/{template_key}/{now.strftime('%Y%m%d%H%M')}"


def _build_assignment_email_tags(
    *,
    assignment_id: str,
    manuscript_id: str,
    template_key: str,
    event_type: str,
    journal_title: str,
) -> list[dict[str, str]]:
    return [
        {"name": "scene", "value": "reviewer_assignment"},
        {"name": "event", "value": str(event_type or "none")},
        {"name": "template", "value": template_key},
        {"name": "assignment_id", "value": assignment_id},
        {"name": "manuscript_id", "value": manuscript_id},
        {"name": "journal", "value": journal_title},
    ]


def _build_assignment_email_audit_context(
    *,
    assignment_id: str,
    manuscript_id: str,
    event_type: str,
    idempotency_key: str,
    actor_user_id: str | None = None,
) -> dict[str, Any]:
    return {
        "assignment_id": assignment_id,
        "manuscript_id": manuscript_id,
        "actor_user_id": str(actor_user_id or "").strip() or None,
        "scene": _REVIEW_ASSIGNMENT_SCENE,
        "event_type": event_type,
        "idempotency_key": idempotency_key,
    }


def _build_assignment_preview_email_audit_context(
    *,
    idempotency_key: str,
) -> dict[str, Any]:
    return {
        "scene": "reviewer_assignment_preview",
        "event_type": "preview",
        "idempotency_key": idempotency_key,
    }


def _resolve_assignment_email_frontend_base_url() -> str:
    return (os.environ.get("FRONTEND_BASE_URL") or "http://localhost:3000").rstrip("/")


def _build_review_assignment_url(*, token: str | None) -> str:
    frontend_base_url = _resolve_assignment_email_frontend_base_url()
    return f"{frontend_base_url}/review/invite?token={quote(str(token))}" if token else f"{frontend_base_url}/dashboard"


def _build_assignment_email_context(
    *,
    reviewer_name: str,
    manuscript_title: str,
    manuscript_id: str,
    journal_title: str,
    due_at: str,
    review_url: str,
) -> dict[str, str]:
    return {
        "review_url": review_url,
        "reviewer_name": reviewer_name,
        "recipient_name": reviewer_name,
        "manuscript_title": manuscript_title,
        "manuscript_id": manuscript_id,
        "journal_title": journal_title,
        "due_at": due_at or "",
        "due_date": str(due_at).split("T")[0] if due_at else "",
    }


def _resolve_assignment_email_payload_template_key(payload: AssignmentEmailActionPayload) -> str:
    return str(payload.template_key or payload.template or "reviewer_invitation_standard")


def _prepare_assignment_email_resources(
    *,
    assignment_id: UUID,
    payload: AssignmentEmailActionPayload,
    current_user: dict[str, Any],
    profile: dict[str, Any],
) -> dict[str, Any]:
    template_key_raw = _resolve_assignment_email_payload_template_key(payload)
    template_row = _load_review_assignment_template(template_key_raw)
    if not template_row:
        raise HTTPException(status_code=404, detail=f"Email template not found: {template_key_raw}")

    assignment = _load_assignment_for_send_email(str(assignment_id))
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")
    if str(assignment.get("status") or "").strip().lower() == "cancelled":
        raise HTTPException(status_code=409, detail="Assignment is cancelled")

    manuscript_res = (
        supabase_admin.table("manuscripts")
        .select("id, title, journal_id, assistant_editor_id, status")
        .eq("id", str(assignment.get("manuscript_id") or ""))
        .single()
        .execute()
    )
    manuscript = getattr(manuscript_res, "data", None) or {}
    if not manuscript:
        raise HTTPException(status_code=404, detail="Manuscript not found")

    roles = set(normalize_roles(_parse_roles(profile)))
    _ensure_review_management_access(
        manuscript=manuscript,
        user_id=str(current_user.get("id") or ""),
        roles=roles,
    )

    template_key = str(template_row.get("template_key") or "").strip() or _normalize_template_key(str(template_key_raw))
    subject_template = str(template_row.get("subject_template") or "").strip()
    body_html_template = str(template_row.get("body_html_template") or "").strip()
    body_text_template = str(template_row.get("body_text_template") or "").strip() or None
    if not subject_template or not body_html_template:
        raise HTTPException(status_code=422, detail=f"Email template is invalid: {template_key}")
    event_type = str(template_row.get("event_type") or "none").strip().lower()
    if event_type not in {"none", "invitation", "reminder"}:
        raise HTTPException(
            status_code=422,
            detail="Only invitation/reminder reviewer templates can be sent from this action",
        )

    assignment_status = str(assignment.get("status") or "").strip().lower()
    assignment_is_declined = assignment_status == "declined" or bool(assignment.get("declined_at"))
    if assignment_is_declined and event_type == "reminder":
        raise HTTPException(status_code=409, detail="Cannot send reminder for declined assignment")

    reviewer_id = str(assignment.get("reviewer_id") or "").strip()
    reviewer_profile_res = (
        supabase_admin.table("user_profiles")
        .select("email, full_name")
        .eq("id", reviewer_id)
        .single()
        .execute()
    )
    reviewer_profile = getattr(reviewer_profile_res, "data", None) or {}
    reviewer_email = normalize_email(reviewer_profile.get("email"))
    reviewer_name = str(reviewer_profile.get("full_name") or "").strip() or "Reviewer"
    if not reviewer_email:
        raise HTTPException(status_code=400, detail="Reviewer email is missing")

    manuscript_id = str(manuscript.get("id") or "").strip()
    manuscript_title = str(manuscript.get("title") or "").strip() or "Manuscript"
    journal_title = _resolve_journal_title_for_assignment(manuscript)
    requested_recipient_email = normalize_email(payload.recipient_email)
    recipient_email = requested_recipient_email or reviewer_email
    recipient_overridden = bool(requested_recipient_email and requested_recipient_email != reviewer_email)

    return {
        "template_row": template_row,
        "template_key": template_key,
        "subject_template": subject_template,
        "body_html_template": body_html_template,
        "body_text_template": body_text_template,
        "event_type": event_type,
        "assignment": assignment,
        "assignment_status": assignment_status,
        "assignment_is_declined": assignment_is_declined,
        "manuscript": manuscript,
        "manuscript_id": manuscript_id,
        "manuscript_title": manuscript_title,
        "journal_title": journal_title,
        "reviewer_id": reviewer_id,
        "reviewer_email": reviewer_email,
        "reviewer_name": reviewer_name,
        "recipient_email": recipient_email,
        "recipient_overridden": recipient_overridden,
    }


def _derive_assignment_state(row: dict[str, Any]) -> str:
    """
    中文注释:
    reviewer history 需要展示业务态，而不是直接暴露底层 status。
    这里沿用 reviewer summary 的优先级：
    cancelled > declined > submitted > accepted > opened > invited > selected
    """
    status_raw = str(row.get("status") or "").strip().lower()
    if status_raw == "cancelled" or row.get("cancelled_at"):
        return "cancelled"
    if status_raw in {"declined", "decline"} or row.get("declined_at"):
        return "declined"
    if status_raw in {"completed", "submitted"} or row.get("report_submitted_at"):
        return "submitted"
    if status_raw in {"accepted", "agree", "agreed", "pending"} or row.get("accepted_at"):
        return "accepted"
    if status_raw == "opened" or row.get("opened_at"):
        return "opened"
    if status_raw == "invited" or row.get("invited_at"):
        return "invited"
    return "selected"


def _serialize_assignment_email_event(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "assignment_id": row.get("assignment_id"),
        "manuscript_id": row.get("manuscript_id"),
        "status": str(row.get("status") or "").strip().lower() or None,
        "event_type": str(row.get("event_type") or "").strip().lower() or None,
        "template_name": row.get("template_name"),
        "created_at": row.get("created_at"),
        "error_message": row.get("error_message"),
        "provider_id": row.get("provider_id"),
        "idempotency_key": row.get("idempotency_key"),
        "actor": row.get("actor"),
    }


def _load_actor_profiles(actor_ids: list[str]) -> dict[str, dict[str, Any]]:
    normalized_ids = [str(item or "").strip() for item in actor_ids if str(item or "").strip()]
    if not normalized_ids:
        return {}
    try:
        actor_res = (
            supabase_admin.table("user_profiles")
            .select("id, email, full_name")
            .in_("id", normalized_ids)
            .execute()
        )
        actor_profiles: dict[str, dict[str, Any]] = {}
        for row in (getattr(actor_res, "data", None) or []):
            actor_id = str(row.get("id") or "").strip()
            if actor_id:
                actor_profiles[actor_id] = row
        return actor_profiles
    except Exception:
        return {}


def _fetch_assignment_email_event_rows(*, assignment_ids: list[str]) -> list[dict[str, Any]]:
    normalized_ids = [str(item or "").strip() for item in assignment_ids if str(item or "").strip()]
    if not normalized_ids:
        return []
    try:
        try:
            rows = (
                supabase_admin.table("email_logs")
                .select(
                    "assignment_id, manuscript_id, actor_user_id, template_name, status, event_type, error_message, provider_id, idempotency_key, created_at"
                )
                .in_("assignment_id", normalized_ids)
                .order("created_at", desc=True)
                .execute()
            )
        except Exception as exc:
            if not _is_missing_review_assignment_column_error(exc, "actor_user_id"):
                raise
            rows = (
                supabase_admin.table("email_logs")
                .select(
                    "assignment_id, manuscript_id, template_name, status, event_type, error_message, provider_id, idempotency_key, created_at"
                )
                .in_("assignment_id", normalized_ids)
                .order("created_at", desc=True)
                .execute()
            )
        return list(getattr(rows, "data", None) or [])
    except Exception:
        return []


def _group_assignment_email_events(
    raw_rows: list[dict[str, Any]],
    *,
    actor_profiles: dict[str, dict[str, Any]] | None = None,
) -> dict[str, list[dict[str, Any]]]:
    if not raw_rows:
        return {}
    profiles_map = actor_profiles or _load_actor_profiles(
        [
            str(row.get("actor_user_id") or "").strip()
            for row in raw_rows
            if str(row.get("actor_user_id") or "").strip()
        ]
    )
    out: dict[str, list[dict[str, Any]]] = {}
    for row in raw_rows:
        assignment_id = str(row.get("assignment_id") or "").strip()
        if not assignment_id:
            continue
        actor_id = str(row.get("actor_user_id") or "").strip()
        actor_profile = profiles_map.get(actor_id) or {}
        serialized = _serialize_assignment_email_event(
            {
                **row,
                "actor": (
                    {
                        "id": actor_id or None,
                        "full_name": actor_profile.get("full_name"),
                        "email": actor_profile.get("email"),
                    }
                    if actor_id or actor_profile
                    else None
                ),
            }
        )
        out.setdefault(assignment_id, []).append(serialized)
    return out


def _load_assignment_email_events(*, assignment_ids: list[str]) -> dict[str, list[dict[str, Any]]]:
    raw_rows = _fetch_assignment_email_event_rows(assignment_ids=assignment_ids)
    return _group_assignment_email_events(raw_rows)


def _get_signed_url_for_manuscripts_bucket(file_path: str, *, expires_in: int = 60 * 10) -> str:
    return get_signed_url_for_manuscripts_bucket(
        file_path=file_path,
        supabase_client=supabase,
        supabase_admin_client=supabase_admin,
        expires_in=expires_in,
    )


def _get_signed_url_for_review_attachments_bucket(file_path: str, *, expires_in: int = 60 * 10) -> str:
    return get_signed_url_for_review_attachments_bucket(
        file_path=file_path,
        supabase_client=supabase,
        supabase_admin_client=supabase_admin,
        expires_in=expires_in,
    )


def _ensure_review_attachments_bucket_exists() -> None:
    return ensure_review_attachments_bucket_exists(supabase_admin_client=supabase_admin)

def _is_missing_relation_error(err: Exception, *, relation: str) -> bool:
    return is_missing_relation_error(err, relation=relation)


def _is_foreign_key_user_error(err: Exception, *, constraint: str) -> bool:
    return is_foreign_key_user_error(err, constraint=constraint)


def _parse_roles(profile: dict | None) -> list[str]:
    return parse_roles(profile)


def _ensure_review_management_access(
    *,
    manuscript: dict[str, Any],
    user_id: str,
    roles: set[str],
) -> None:
    return ensure_review_management_access(
        manuscript=manuscript,
        user_id=user_id,
        roles=roles,
    )


def _resolve_journal_title_for_assignment(manuscript: dict[str, Any]) -> str:
    journal_id = str(manuscript.get("journal_id") or "").strip()
    if not journal_id:
        return "ScholarFlow Journal"
    try:
        row = (
            supabase_admin.table("journals")
            .select("title")
            .eq("id", journal_id)
            .single()
            .execute()
        )
        payload = getattr(row, "data", None) or {}
        title = str(payload.get("title") or "").strip()
        return title or "ScholarFlow Journal"
    except Exception:
        return "ScholarFlow Journal"


def _normalize_template_key(raw_key: str) -> str:
    key = str(raw_key or "").strip().lower()
    key = re.sub(r"[^a-z0-9_]+", "_", key)
    key = re.sub(r"_{2,}", "_", key).strip("_")
    if not key or not _EMAIL_TEMPLATE_KEY_RE.match(key):
        raise HTTPException(status_code=422, detail="template_key must contain only lowercase letters, numbers, and underscore")
    return key


def _normalize_template_scene(raw_scene: str) -> str:
    scene = str(raw_scene or "").strip().lower()
    scene = re.sub(r"[^a-z0-9_]+", "_", scene)
    scene = re.sub(r"_{2,}", "_", scene).strip("_")
    if not scene or not _EMAIL_TEMPLATE_SCENE_RE.match(scene):
        raise HTTPException(status_code=422, detail="scene must contain only lowercase letters, numbers, and underscore")
    return scene


def _is_missing_table_error(error_text: str, table_name: str) -> bool:
    lowered = str(error_text or "").lower()
    needle = str(table_name or "").strip().lower()
    if not needle:
        return False
    return needle in lowered and ("does not exist" in lowered or "schema cache" in lowered)


def _load_review_assignment_template(template_key: str) -> dict[str, Any] | None:
    normalized = _normalize_template_key(template_key)
    alias_key = _REVIEW_TEMPLATE_KEY_ALIASES.get(normalized)
    lookup_keys = [alias_key, normalized] if alias_key else [normalized]
    lookup_keys = [key for key in lookup_keys if key]

    for key in lookup_keys:
        try:
            resp = (
                supabase_admin.table(_EMAIL_TEMPLATE_TABLE)
                .select(
                    "template_key,display_name,description,scene,event_type,subject_template,body_html_template,body_text_template,is_active"
                )
                .eq("template_key", key)
                .eq("is_active", True)
                .single()
                .execute()
            )
            row = getattr(resp, "data", None) or {}
            if not row:
                continue
            scene = str(row.get("scene") or "").strip().lower()
            if scene != _REVIEW_ASSIGNMENT_SCENE:
                raise HTTPException(status_code=422, detail=f"Template scene mismatch: expected {_REVIEW_ASSIGNMENT_SCENE}")
            return row
        except HTTPException:
            raise
        except APIError as e:
            text = str(e)
            if "PGRST116" in text or "0 rows" in text or "single json object" in text:
                continue
            if _is_missing_table_error(text, _EMAIL_TEMPLATE_TABLE):
                break
            raise HTTPException(status_code=500, detail=f"Failed to load email template: {e}") from e
        except Exception as e:
            text = str(e)
            if _is_missing_table_error(text, _EMAIL_TEMPLATE_TABLE):
                break
            raise HTTPException(status_code=500, detail=f"Failed to load email template: {e}") from e

    for key in lookup_keys:
        fallback = _DEFAULT_REVIEW_ASSIGNMENT_TEMPLATES.get(key)
        if fallback:
            return fallback
    return None


def _list_active_review_assignment_templates(scene: str) -> list[dict[str, Any]]:
    normalized_scene = _normalize_template_scene(scene)
    fallback_rows = [
        {
            "template_key": row.get("template_key"),
            "display_name": row.get("display_name"),
            "description": row.get("description"),
            "scene": row.get("scene"),
            "event_type": row.get("event_type"),
        }
        for row in _DEFAULT_REVIEW_ASSIGNMENT_TEMPLATES.values()
        if str(row.get("scene") or "") == normalized_scene
    ]
    try:
        resp = (
            supabase_admin.table(_EMAIL_TEMPLATE_TABLE)
            .select("template_key,display_name,description,scene,event_type")
            .eq("scene", normalized_scene)
            .eq("is_active", True)
            .order("display_name", desc=False)
            .execute()
        )
        rows = getattr(resp, "data", None) or []
        if rows:
            return [
                row
                for row in rows
                if str(row.get("event_type") or "").strip().lower() in {"none", "invitation", "reminder"}
            ]
        return fallback_rows
    except Exception as e:
        if _is_missing_table_error(str(e), _EMAIL_TEMPLATE_TABLE):
            return fallback_rows
        raise HTTPException(status_code=500, detail=f"Failed to list email templates: {e}") from e


def _safe_create_assignment_magic_link(
    *,
    reviewer_id: str,
    manuscript_id: str,
    assignment_id: str,
) -> str | None:
    try:
        days = int((os.environ.get("MAGIC_LINK_EXPIRES_DAYS") or "14").strip())
    except Exception:
        days = 14
    try:
        return create_magic_link_jwt(
            reviewer_id=UUID(reviewer_id),
            manuscript_id=UUID(manuscript_id),
            assignment_id=UUID(assignment_id),
            expires_in_days=days,
        )
    except RuntimeError as exc:
        if "not configured" in str(exc).lower():
            return None
        raise
    except Exception:
        return None


@router.get("/reviewer/assignments/{assignment_id}/workspace")
async def get_reviewer_workspace_data(
    assignment_id: UUID,
    sf_review_magic: str | None = Cookie(default=None, alias="sf_review_magic"),
):
    return await get_reviewer_workspace_data_impl(
        assignment_id=assignment_id,
        magic_token=sf_review_magic,
        require_magic_link_scope_fn=_require_magic_link_scope,
        reviewer_workspace_service_cls=ReviewerWorkspaceService,
    )


@router.get("/reviewer/assignments/{assignment_id}/invite")
async def get_reviewer_invite_data(
    assignment_id: UUID,
    sf_review_magic: str | None = Cookie(default=None, alias="sf_review_magic"),
):
    return await get_reviewer_invite_data_impl(
        assignment_id=assignment_id,
        magic_token=sf_review_magic,
        require_magic_link_scope_fn=_require_magic_link_scope,
        reviewer_invite_service_cls=ReviewerInviteService,
    )


@router.post("/reviewer/assignments/{assignment_id}/accept")
async def accept_reviewer_invitation(
    assignment_id: UUID,
    payload: InviteAcceptPayload,
    sf_review_magic: str | None = Cookie(default=None, alias="sf_review_magic"),
):
    return await accept_reviewer_invitation_impl(
        assignment_id=assignment_id,
        body=payload,
        magic_token=sf_review_magic,
        require_magic_link_scope_fn=_require_magic_link_scope,
        reviewer_invite_service_cls=ReviewerInviteService,
    )


@router.post("/reviewer/assignments/{assignment_id}/decline")
async def decline_reviewer_invitation(
    assignment_id: UUID,
    payload: InviteDeclinePayload,
    sf_review_magic: str | None = Cookie(default=None, alias="sf_review_magic"),
):
    return await decline_reviewer_invitation_impl(
        assignment_id=assignment_id,
        body=payload,
        magic_token=sf_review_magic,
        require_magic_link_scope_fn=_require_magic_link_scope,
        reviewer_invite_service_cls=ReviewerInviteService,
    )


@router.post("/reviewer/assignments/{assignment_id}/attachments")
async def upload_reviewer_workspace_attachment(
    assignment_id: UUID,
    file: UploadFile = File(...),
    sf_review_magic: str | None = Cookie(default=None, alias="sf_review_magic"),
):
    return await upload_reviewer_workspace_attachment_impl(
        assignment_id=assignment_id,
        file=file,
        magic_token=sf_review_magic,
        require_magic_link_scope_fn=_require_magic_link_scope,
        reviewer_workspace_service_cls=ReviewerWorkspaceService,
        get_signed_url_for_review_attachments_bucket_fn=_get_signed_url_for_review_attachments_bucket,
    )


@router.post("/reviewer/assignments/{assignment_id}/submit")
async def submit_reviewer_workspace_review(
    assignment_id: UUID,
    body: ReviewSubmission,
    sf_review_magic: str | None = Cookie(default=None, alias="sf_review_magic"),
):
    return await submit_reviewer_workspace_review_impl(
        assignment_id=assignment_id,
        body=body,
        magic_token=sf_review_magic,
        require_magic_link_scope_fn=_require_magic_link_scope,
        reviewer_workspace_service_cls=ReviewerWorkspaceService,
    )


# === 1. 分配审稿人 (Editor Task) ===
@router.post("/reviews/assign")
async def assign_reviewer(
    current_user: dict = Depends(get_current_user),
    profile: dict = Depends(require_any_role(["managing_editor", "assistant_editor", "admin"])),
    manuscript_id: UUID = Body(..., embed=True),
    reviewer_id: UUID = Body(..., embed=True),
    override_cooldown: bool = Body(False, embed=True),
    override_reason: str | None = Body(None, embed=True),
):
    """
    编辑分配审稿人

    中文注释:
    1. 仅把 reviewer 加入拟邀请名单（selected），不直接发邮件。
    2. 真正的 invitation 由 `/reviews/assignments/{id}/send-email` 触发。
    """
    return await assign_reviewer_impl(
        current_user=current_user,
        profile=profile,
        manuscript_id=manuscript_id,
        reviewer_id=reviewer_id,
        override_cooldown=override_cooldown,
        override_reason=override_reason,
        supabase_client=supabase,
        supabase_admin_client=supabase_admin,
        normalize_roles_fn=normalize_roles,
        parse_roles_fn=_parse_roles,
        review_policy_service_cls=ReviewPolicyService,
        ensure_review_management_access_fn=_ensure_review_management_access,
        is_foreign_key_user_error_fn=_is_foreign_key_user_error,
        is_missing_relation_error_fn=_is_missing_relation_error,
    )


def _get_magic_link_from_cookie(magic_token: str | None) -> str:
    if not magic_token:
        raise HTTPException(status_code=401, detail="Missing magic link session")
    return magic_token


async def _require_magic_link_scope(
    *,
    assignment_id: UUID,
    magic_token: str | None,
) -> MagicLinkPayload:
    token = _get_magic_link_from_cookie(magic_token)
    payload = decode_magic_link_jwt(token)
    if str(payload.assignment_id) != str(assignment_id):
        raise HTTPException(status_code=401, detail="Magic link scope mismatch")

    try:
        a = (
            supabase_admin.table("review_assignments")
            .select("id, status, manuscript_id, reviewer_id, due_at")
            .eq("id", str(assignment_id))
            .single()
            .execute()
        )
        assignment = getattr(a, "data", None) or {}
    except Exception:
        assignment = {}

    if not assignment:
        raise HTTPException(status_code=401, detail="Assignment not found")
    status = str(assignment.get("status") or "").lower()
    if status == "cancelled":
        raise HTTPException(status_code=401, detail="Invitation revoked")
    if str(assignment.get("manuscript_id")) != str(payload.manuscript_id):
        raise HTTPException(status_code=401, detail="Magic link scope mismatch")
    if str(assignment.get("reviewer_id")) != str(payload.reviewer_id):
        raise HTTPException(status_code=401, detail="Magic link scope mismatch")

    return payload


@router.get("/reviews/magic/assignments/{assignment_id}")
async def get_review_assignment_via_magic_link(
    assignment_id: UUID,
    sf_review_magic: str | None = Cookie(default=None, alias="sf_review_magic"),
):
    """
    Magic Link 审稿任务入口（Feature 039）

    中文注释:
    - 通过 httpOnly cookie `sf_review_magic`（JWT）鉴权。
    - 严格限制仅可访问 token 指向的 assignment。
    """

    return await get_review_assignment_via_magic_link_impl(
        assignment_id=assignment_id,
        magic_token=sf_review_magic,
        require_magic_link_scope_fn=_require_magic_link_scope,
        supabase_admin_client=supabase_admin,
    )


@router.post("/reviewer/assignments/{assignment_id}/session")
async def establish_reviewer_workspace_session(
    assignment_id: UUID,
    response: Response,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    登录态 Reviewer 会话桥接（Dashboard -> Reviewer Workspace v2）。

    中文注释:
    - 内部登录 reviewer 不走邮件链接时，也需要一个 assignment-scoped 的 `sf_review_magic` cookie。
    - 这里严格校验 assignment 属于当前用户后，签发同 scope JWT 并写入 httpOnly cookie。
    """
    return await establish_reviewer_workspace_session_impl(
        assignment_id=assignment_id,
        response=response,
        current_user=current_user,
        supabase_admin_client=supabase_admin,
        create_magic_link_jwt_fn=create_magic_link_jwt,
    )


@router.get("/reviews/magic/assignments/{assignment_id}/pdf-signed")
async def get_review_assignment_pdf_signed_via_magic_link(
    assignment_id: UUID,
    sf_review_magic: str | None = Cookie(default=None, alias="sf_review_magic"),
):
    return await get_review_assignment_pdf_signed_via_magic_link_impl(
        assignment_id=assignment_id,
        magic_token=sf_review_magic,
        require_magic_link_scope_fn=_require_magic_link_scope,
        supabase_admin_client=supabase_admin,
        get_signed_url_for_manuscripts_bucket_fn=_get_signed_url_for_manuscripts_bucket,
    )


@router.get("/reviews/magic/assignments/{assignment_id}/attachment-signed")
async def get_review_attachment_signed_via_magic_link(
    assignment_id: UUID,
    sf_review_magic: str | None = Cookie(default=None, alias="sf_review_magic"),
):
    return await get_review_attachment_signed_via_magic_link_impl(
        assignment_id=assignment_id,
        magic_token=sf_review_magic,
        require_magic_link_scope_fn=_require_magic_link_scope,
        supabase_admin_client=supabase_admin,
        get_signed_url_for_review_attachments_bucket_fn=_get_signed_url_for_review_attachments_bucket,
    )


@router.post("/reviews/magic/assignments/{assignment_id}/submit")
async def submit_review_via_magic_link(
    assignment_id: UUID,
    sf_review_magic: str | None = Cookie(default=None, alias="sf_review_magic"),
    comments_for_author: str | None = Form(None),
    content: str | None = Form(None),
    confidential_comments_to_editor: str | None = Form(None),
    attachment: UploadFile | None = File(None),
):
    payload = await _require_magic_link_scope(assignment_id=assignment_id, magic_token=sf_review_magic)
    return await submit_review_via_magic_link_impl(
        assignment_id=assignment_id,
        payload=payload,
        comments_for_author=comments_for_author,
        content=content,
        confidential_comments_to_editor=confidential_comments_to_editor,
        attachment=attachment,
        supabase_admin_client=supabase_admin,
        ensure_review_attachments_bucket_exists_fn=_ensure_review_attachments_bucket_exists,
    )


@router.delete("/reviews/assign/{assignment_id}")
async def unassign_reviewer(
    assignment_id: UUID,
    current_user: dict = Depends(get_current_user),
    profile: dict = Depends(require_any_role(["managing_editor", "assistant_editor", "admin"])),
):
    """
    撤销审稿指派
    """
    return await unassign_reviewer_impl(
        assignment_id=assignment_id,
        current_user=current_user,
        profile=profile,
        supabase_admin_client=supabase_admin,
        ensure_review_management_access_fn=_ensure_review_management_access,
        normalize_roles_fn=normalize_roles,
        parse_roles_fn=_parse_roles,
    )


@router.post("/reviews/assignments/{assignment_id}/cancel")
async def cancel_reviewer_assignment(
    assignment_id: UUID,
    body: AssignmentCancelPayload,
    current_user: dict = Depends(get_current_user),
    profile: dict = Depends(require_any_role(["managing_editor", "assistant_editor", "admin"])),
):
    """
    正式取消 reviewer assignment，保留审计与后续 history。
    """
    return await cancel_reviewer_impl(
        assignment_id=assignment_id,
        reason=body.reason,
        via=body.via,
        send_email=body.send_email,
        current_user=current_user,
        profile=profile,
        supabase_admin_client=supabase_admin,
        ensure_review_management_access_fn=_ensure_review_management_access,
        normalize_roles_fn=normalize_roles,
        parse_roles_fn=_parse_roles,
    )


@router.get("/reviews/email-templates")
async def list_review_email_templates(
    scene: str = Query(default=_REVIEW_ASSIGNMENT_SCENE),
    _current_user: dict = Depends(get_current_user),
    _profile: dict = Depends(require_any_role(["managing_editor", "assistant_editor", "admin"])),
):
    """
    编辑侧可用邮件模板列表（按 scene 过滤，默认 reviewer_assignment）。
    """
    rows = _list_active_review_assignment_templates(scene)
    return {"success": True, "data": rows}


@router.post("/reviews/assignments/{assignment_id}/preview-email")
async def preview_assignment_email(
    assignment_id: UUID,
    payload: AssignmentEmailActionPayload | None = Body(default=None),
    current_user: dict = Depends(get_current_user),
    profile: dict = Depends(require_any_role(["managing_editor", "assistant_editor", "admin"])),
):
    """
    发送前预览审稿邮件（已完成模板变量注入）。
    """
    body = payload or AssignmentEmailActionPayload()
    prepared = _prepare_assignment_email_resources(
        assignment_id=assignment_id,
        payload=body,
        current_user=current_user,
        profile=profile,
    )

    assignment = prepared["assignment"]
    due_at = str(assignment.get("due_at") or "").strip()
    token = _safe_create_assignment_magic_link(
        reviewer_id=prepared["reviewer_id"],
        manuscript_id=prepared["manuscript_id"],
        assignment_id=str(assignment.get("id") or assignment_id),
    )
    context = _build_assignment_email_context(
        reviewer_name=prepared["reviewer_name"],
        manuscript_title=prepared["manuscript_title"],
        manuscript_id=prepared["manuscript_id"],
        journal_title=prepared["journal_title"],
        due_at=due_at,
        review_url=_build_review_assignment_url(token=token),
    )
    preview = email_service.render_inline_email_preview(
        subject_template=prepared["subject_template"],
        body_html_template=prepared["body_html_template"],
        body_text_template=prepared["body_text_template"],
        context=context,
    )
    return {
        "success": True,
        "data": {
            "assignment_id": str(assignment.get("id") or assignment_id),
            "template_key": prepared["template_key"],
            "template_display_name": prepared["template_row"].get("display_name"),
            "event_type": prepared["event_type"],
            "reviewer_email": prepared["reviewer_email"],
            "reviewer_name": prepared["reviewer_name"],
            "recipient_email": prepared["recipient_email"],
            "recipient_overridden": prepared["recipient_overridden"],
            "journal_title": prepared["journal_title"],
            "review_url": context["review_url"],
            "subject": preview["subject"],
            "html": preview["html"],
            "text": preview["text"],
        },
    }


@router.post("/reviews/assignments/{assignment_id}/send-email")
async def send_assignment_email(
    assignment_id: UUID,
    payload: AssignmentEmailActionPayload | None = Body(default=None),
    current_user: dict = Depends(get_current_user),
    profile: dict = Depends(require_any_role(["managing_editor", "assistant_editor", "admin"])),
):
    """
    手动发送审稿邮件（邀请/催促）。

    中文注释:
    - 根据 template_key 从 email_templates 表读取模板；
    - 自动注入 manuscript/reviewer/journal 变量；
    - 现在同步返回真实投递结果（sent/failed），避免前端把 queued 误判成“已发成功”。
    """
    body = payload or AssignmentEmailActionPayload()
    prepared = _prepare_assignment_email_resources(
        assignment_id=assignment_id,
        payload=body,
        current_user=current_user,
        profile=profile,
    )

    template_row = prepared["template_row"]
    template_key = prepared["template_key"]
    subject_template = prepared["subject_template"]
    body_html_template = prepared["body_html_template"]
    body_text_template = prepared["body_text_template"]
    event_type = prepared["event_type"]
    assignment = prepared["assignment"]
    manuscript = prepared["manuscript"]
    manuscript_id = prepared["manuscript_id"]
    journal_title = prepared["journal_title"]
    reviewer_id = prepared["reviewer_id"]
    reviewer_email = prepared["reviewer_email"]
    reviewer_name = prepared["reviewer_name"]
    recipient_email = prepared["recipient_email"]
    recipient_overridden = prepared["recipient_overridden"]
    now_dt = datetime.now(timezone.utc)
    now_iso = now_dt.isoformat()
    current_user_id = str(current_user.get("id") or "").strip()
    assignment_status = prepared["assignment_status"]
    assignment_is_declined = prepared["assignment_is_declined"]
    effective_assignment = assignment
    if assignment_is_declined:
        if event_type == "reminder":
            raise HTTPException(status_code=409, detail="Cannot send reminder for declined assignment")
    if assignment_is_declined and event_type == "invitation" and not recipient_overridden:
        effective_assignment = _insert_reinvite_assignment_attempt(
            assignment=assignment,
            current_user_id=current_user_id,
        )
    effective_assignment_id = str(effective_assignment.get("id") or assignment_id).strip()
    if not effective_assignment_id:
        raise HTTPException(status_code=500, detail="Failed to resolve assignment id for reviewer email")
    effective_due_at = str(effective_assignment.get("due_at") or assignment.get("due_at") or "").strip()
    effective_assignment_status = str(effective_assignment.get("status") or assignment_status).strip().lower()
    send_is_preview = recipient_overridden
    if send_is_preview:
        idempotency_key = str(body.idempotency_key or "").strip() or (
            f"reviewer-email-preview/{effective_assignment_id}/{template_key}/{now_dt.strftime('%Y%m%d%H%M%S%f')}"
        )
        email_tags = [
            {"name": "scene", "value": "reviewer_assignment_preview"},
            {"name": "event", "value": "preview"},
            {"name": "template", "value": template_key},
        ]
        email_headers = {
            "X-SF-Template-Key": template_key,
            "X-SF-Event-Type": "preview",
        }
        audit_context = _build_assignment_preview_email_audit_context(idempotency_key=idempotency_key)
    else:
        idempotency_key = str(body.idempotency_key or "").strip() or _build_assignment_email_idempotency_key(
            assignment_id=effective_assignment_id,
            template_key=template_key,
            event_type=event_type,
            now=now_dt,
            assignment_status=effective_assignment_status,
        )
        email_tags = _build_assignment_email_tags(
            assignment_id=effective_assignment_id,
            manuscript_id=manuscript_id,
            template_key=template_key,
            event_type=event_type,
            journal_title=journal_title,
        )
        email_headers = {
            "X-SF-Assignment-ID": effective_assignment_id,
            "X-SF-Manuscript-ID": manuscript_id,
            "X-SF-Template-Key": template_key,
            "X-SF-Event-Type": event_type,
        }
        audit_context = _build_assignment_email_audit_context(
            assignment_id=effective_assignment_id,
            manuscript_id=manuscript_id,
            event_type=event_type,
            idempotency_key=idempotency_key,
            actor_user_id=current_user_id,
        )

    token = _safe_create_assignment_magic_link(
        reviewer_id=reviewer_id,
        manuscript_id=manuscript_id,
        assignment_id=effective_assignment_id,
    )
    context = _build_assignment_email_context(
        reviewer_name=reviewer_name,
        manuscript_title=prepared["manuscript_title"],
        manuscript_id=manuscript_id,
        journal_title=journal_title,
        due_at=effective_due_at,
        review_url=_build_review_assignment_url(token=token),
    )
    try:
        subject_preview = email_service.render_inline_template(subject_template, context).strip() or "(no subject)"
    except Exception:
        subject_preview = subject_template or "(queued)"

    delivery = email_service.send_inline_email(
        to_email=recipient_email,
        template_key=template_key,
        subject_template=subject_template,
        body_html_template=body_html_template,
        body_text_template=body_text_template,
        context=context,
        idempotency_key=idempotency_key,
        tags=email_tags,
        headers=email_headers,
        audit_context=audit_context,
    )
    delivery_status = str(delivery.get("status") or EmailStatus.FAILED.value).strip().lower()
    delivery_error = str(delivery.get("error_message") or "").strip() or None
    delivery_subject = str(delivery.get("subject") or subject_preview or "(no subject)").strip() or "(no subject)"

    try:
        patch: dict[str, Any] = {}
        if not send_is_preview and event_type == "invitation" and delivery_status == EmailStatus.SENT.value:
            if not assignment_is_declined:
                patch["invited_at"] = now_iso
                if assignment_status in {"selected", "pending", "invited", "opened"}:
                    patch["status"] = "invited"
                if current_user_id and not str(assignment.get("invited_by") or "").strip():
                    patch["invited_by"] = current_user_id
                if not str(assignment.get("invited_via") or "").strip():
                    patch["invited_via"] = "template_invitation"
            else:
                patch["invited_at"] = now_iso
                patch["status"] = "invited"
                if current_user_id:
                    patch["invited_by"] = current_user_id
                patch["invited_via"] = "template_invitation"
        elif not send_is_preview and event_type == "reminder" and delivery_status == EmailStatus.SENT.value:
            patch["last_reminded_at"] = now_iso
        if patch:
            try:
                supabase_admin.table("review_assignments").update(patch).eq("id", effective_assignment_id).execute()
            except Exception as exc:
                if not _is_missing_assignment_audit_column_error(exc):
                    raise
                fallback_patch = {key: value for key, value in patch.items() if key not in {"invited_by", "invited_via"}}
                if fallback_patch:
                    supabase_admin.table("review_assignments").update(fallback_patch).eq("id", effective_assignment_id).execute()

        manuscript_status = str(manuscript.get("status") or "").strip().lower()
        if (
            not send_is_preview
            and
            event_type == "invitation"
            and delivery_status == EmailStatus.SENT.value
            and manuscript_status in {"pre_check", "resubmitted"}
        ):
            supabase_admin.table("manuscripts").update({"status": "under_review"}).eq("id", manuscript_id).execute()
    except Exception:
        # 回填失败不影响主流程（真实发送结果已返回给前端）。
        pass

    return {
        "success": True,
        "data": {
            "assignment_id": effective_assignment_id,
            "template_key": template_key,
            "template_display_name": template_row.get("display_name"),
            "event_type": event_type,
            "recipient": recipient_email,
            "reviewer_email": reviewer_email,
            "recipient_overridden": send_is_preview,
            "preview_send": send_is_preview,
            "journal_title": journal_title,
            "idempotency_key": idempotency_key,
            "delivery_status": delivery_status,
            "delivery_error": delivery_error,
            "delivery_subject": delivery_subject,
            "processed_at": now_iso,
        },
    }


@router.get("/reviews/assignments/{manuscript_id}")
async def get_manuscript_assignments(
    manuscript_id: UUID,
    round_number: int | None = None,
    current_user: dict = Depends(get_current_user),
    profile: dict = Depends(require_any_role(["managing_editor", "assistant_editor", "admin"])),
):
    """
    获取某篇稿件的审稿指派列表
    """
    return await get_manuscript_assignments_impl(
        manuscript_id=manuscript_id,
        round_number=round_number,
        current_user=current_user,
        profile=profile,
        supabase_admin_client=supabase_admin,
        ensure_review_management_access_fn=_ensure_review_management_access,
        normalize_roles_fn=normalize_roles,
        parse_roles_fn=_parse_roles,
    )


@router.get("/reviews/reviewer-history/{reviewer_id}")
async def get_reviewer_history(
    reviewer_id: UUID,
    manuscript_id: UUID | None = Query(default=None),
    limit: int = Query(default=30, ge=1, le=200),
    current_user: dict = Depends(get_current_user),
    profile: dict = Depends(require_any_role(["managing_editor", "assistant_editor", "admin"])),
):
    """
    审稿人历史记录（编辑侧）。
    """
    roles = set(normalize_roles(_parse_roles(profile)))
    reviewer_id_str = str(reviewer_id)

    try:
        query = (
            supabase_admin.table("review_assignments")
            .select(
                "id, manuscript_id, reviewer_id, status, due_at, invited_at, opened_at, accepted_at, declined_at, decline_reason, decline_note, last_reminded_at, created_at, round_number, selected_by, selected_via, invited_by, invited_via, cancelled_at, cancelled_by, cancel_reason, cancel_via"
            )
            .eq("reviewer_id", reviewer_id_str)
            .order("created_at", desc=True)
            .limit(limit)
        )
        if manuscript_id is not None:
            query = query.eq("manuscript_id", str(manuscript_id))
        assignments_res = query.execute()
    except Exception as exc:
        if not _is_missing_assignment_audit_column_error(exc):
            raise
        query = (
            supabase_admin.table("review_assignments")
            .select(
                "id, manuscript_id, reviewer_id, status, due_at, invited_at, opened_at, accepted_at, declined_at, decline_reason, decline_note, last_reminded_at, created_at, round_number"
            )
            .eq("reviewer_id", reviewer_id_str)
            .order("created_at", desc=True)
            .limit(limit)
        )
        if manuscript_id is not None:
            query = query.eq("manuscript_id", str(manuscript_id))
        assignments_res = query.execute()
    assignment_rows = getattr(assignments_res, "data", None) or []
    if not assignment_rows:
        return {"success": True, "data": []}

    manuscript_ids = sorted(
        {str(row.get("manuscript_id") or "").strip() for row in assignment_rows if str(row.get("manuscript_id") or "").strip()}
    )
    manuscript_map: dict[str, dict[str, Any]] = {}
    if manuscript_ids:
        ms_res = (
            supabase_admin.table("manuscripts")
            .select("id, title, status, journal_id, assistant_editor_id")
            .in_("id", manuscript_ids)
            .execute()
        )
        for row in (getattr(ms_res, "data", None) or []):
            manuscript_map[str(row.get("id"))] = row

    filtered_rows: list[dict[str, Any]] = []
    for row in assignment_rows:
        mid = str(row.get("manuscript_id") or "").strip()
        manuscript = manuscript_map.get(mid)
        if not manuscript:
            continue
        try:
            _ensure_review_management_access(
                manuscript=manuscript,
                user_id=str(current_user.get("id") or ""),
                roles=roles,
            )
        except HTTPException:
            continue
        filtered_rows.append(row)

    if manuscript_id is not None and assignment_rows and not filtered_rows:
        raise HTTPException(status_code=403, detail="Forbidden")
    if not filtered_rows:
        return {"success": True, "data": []}

    assignment_ids = [str(row.get("id") or "").strip() for row in filtered_rows if str(row.get("id") or "").strip()]
    email_event_rows = _fetch_assignment_email_event_rows(assignment_ids=assignment_ids)
    actor_ids = sorted(
        {
            str(row.get("selected_by") or "").strip()
            for row in filtered_rows
            if str(row.get("selected_by") or "").strip()
        }
        | {
            str(row.get("invited_by") or "").strip()
            for row in filtered_rows
            if str(row.get("invited_by") or "").strip()
        }
        | {
            str(row.get("cancelled_by") or "").strip()
            for row in filtered_rows
            if str(row.get("cancelled_by") or "").strip()
        }
        | {
            str(row.get("actor_user_id") or "").strip()
            for row in email_event_rows
            if str(row.get("actor_user_id") or "").strip()
        }
    )
    actor_profiles = _load_actor_profiles(actor_ids)
    email_events_by_assignment = _group_assignment_email_events(
        email_event_rows,
        actor_profiles=actor_profiles,
    )

    assignment_counts_by_manuscript: dict[str, int] = {}
    for row in filtered_rows:
        mid = str(row.get("manuscript_id") or "").strip()
        if not mid:
            continue
        assignment_counts_by_manuscript[mid] = assignment_counts_by_manuscript.get(mid, 0) + 1

    report_map: dict[str, dict[str, Any]] = {}
    try:
        rr_res = (
            supabase_admin.table("review_reports")
            .select("manuscript_id, reviewer_id, status, score, created_at")
            .eq("reviewer_id", reviewer_id_str)
            .in_("manuscript_id", manuscript_ids)
            .order("created_at", desc=True)
            .execute()
        )
        for row in (getattr(rr_res, "data", None) or []):
            mid = str(row.get("manuscript_id") or "").strip()
            if mid and assignment_counts_by_manuscript.get(mid, 0) == 1 and mid not in report_map:
                report_map[mid] = row
    except Exception:
        report_map = {}

    out: list[dict[str, Any]] = []
    for row in filtered_rows:
        assignment_id_value = str(row.get("id") or "").strip()
        mid = str(row.get("manuscript_id") or "").strip()
        manuscript = manuscript_map.get(mid) or {}
        report = report_map.get(mid) or {}
        email_events = email_events_by_assignment.get(assignment_id_value, [])
        latest_email = email_events[0] if email_events else {}
        added_by_id = str(row.get("selected_by") or "").strip()
        invited_by_id = str(row.get("invited_by") or "").strip()
        cancelled_by_id = str(row.get("cancelled_by") or "").strip()
        added_by_profile = actor_profiles.get(added_by_id) or {}
        invited_by_profile = actor_profiles.get(invited_by_id) or {}
        cancelled_by_profile = actor_profiles.get(cancelled_by_id) or {}
        out.append(
            {
                "assignment_id": assignment_id_value or row.get("id"),
                "reviewer_id": reviewer_id_str,
                "manuscript_id": mid,
                "manuscript_title": manuscript.get("title"),
                "manuscript_status": manuscript.get("status"),
                "assignment_status": row.get("status"),
                "assignment_state": _derive_assignment_state(
                    {
                        **row,
                        "report_submitted_at": report.get("created_at"),
                    }
                ),
                "round_number": row.get("round_number"),
                "added_on": row.get("created_at"),
                "added_by": (
                    {
                        "id": added_by_id or None,
                        "full_name": added_by_profile.get("full_name"),
                        "email": added_by_profile.get("email"),
                    }
                    if added_by_id or added_by_profile
                    else None
                ),
                "added_via": row.get("selected_via"),
                "invited_by": (
                    {
                        "id": invited_by_id or None,
                        "full_name": invited_by_profile.get("full_name"),
                        "email": invited_by_profile.get("email"),
                    }
                    if invited_by_id or invited_by_profile
                    else None
                ),
                "invited_via": row.get("invited_via"),
                "cancelled_by": (
                    {
                        "id": cancelled_by_id or None,
                        "full_name": cancelled_by_profile.get("full_name"),
                        "email": cancelled_by_profile.get("email"),
                    }
                    if cancelled_by_id or cancelled_by_profile
                    else None
                ),
                "cancelled_at": row.get("cancelled_at"),
                "cancel_reason": row.get("cancel_reason"),
                "cancel_via": row.get("cancel_via"),
                "invited_at": row.get("invited_at"),
                "opened_at": row.get("opened_at"),
                "accepted_at": row.get("accepted_at"),
                "declined_at": row.get("declined_at"),
                "decline_reason": row.get("decline_reason"),
                "decline_note": row.get("decline_note"),
                "last_reminded_at": row.get("last_reminded_at"),
                "due_at": row.get("due_at"),
                "report_status": report.get("status"),
                "report_score": report.get("score"),
                "report_submitted_at": report.get("created_at"),
                "latest_email_status": latest_email.get("status"),
                "latest_email_at": latest_email.get("created_at"),
                "latest_email_error": latest_email.get("error_message"),
                "email_events": email_events,
            }
        )

    return {"success": True, "data": out}


# === 2. 获取我的审稿任务 (Reviewer Task) ===
@router.get("/reviews/my-tasks")
async def get_my_review_tasks(
    user_id: UUID,
    current_user: dict = Depends(get_current_user),
    _profile: dict = Depends(require_any_role(["reviewer", "admin"])),
):
    """
    审稿人获取自己名下的任务
    """
    if str(user_id) != str(current_user["id"]):
        raise HTTPException(status_code=403, detail="Cannot access other user's tasks")
    try:
        res = (
            supabase.table("review_assignments")
            .select("*, manuscripts(title, abstract, file_path)")
            .eq("reviewer_id", str(user_id))
            .eq("status", "pending")
            .execute()
        )
        return {"success": True, "data": res.data}
    except APIError as e:
        # 中文注释:
        # 1) 云端 Supabase 可能还没创建 review_assignments 表（schema cache 里会 404/PGRST205）。
        # 2) Reviewer Tab 属于“可选能力”，不要因为缺表把整个 Dashboard 打崩，降级为空列表。
        print(f"Review tasks query failed (fallback to empty): {e}")
        return {
            "success": True,
            "data": [],
            "message": "review_assignments table not found",
        }


@router.get("/reviews/my-history")
async def get_my_review_history(
    user_id: UUID,
    manuscript_id: UUID | None = Query(default=None),
    limit: int = Query(default=30, ge=1, le=200),
    current_user: dict = Depends(get_current_user),
    _profile: dict = Depends(require_any_role(["reviewer", "admin"])),
):
    """
    审稿人获取自己的历史记录（仅返回 reviewer 自己可见的数据）。
    """
    if str(user_id) != str(current_user["id"]):
        raise HTTPException(status_code=403, detail="Cannot access other user's review history")

    reviewer_id_str = str(user_id)

    try:
        query = (
            supabase_admin.table("review_assignments")
            .select(
                "id, manuscript_id, reviewer_id, status, due_at, invited_at, opened_at, accepted_at, declined_at, decline_reason, decline_note, last_reminded_at, created_at, round_number, cancelled_at, cancel_reason, cancel_via"
            )
            .eq("reviewer_id", reviewer_id_str)
            .order("created_at", desc=True)
            .limit(limit)
        )
        if manuscript_id is not None:
            query = query.eq("manuscript_id", str(manuscript_id))
        assignments_res = query.execute()
    except Exception as exc:
        if not _is_missing_assignment_audit_column_error(exc):
            raise
        query = (
            supabase_admin.table("review_assignments")
            .select(
                "id, manuscript_id, reviewer_id, status, due_at, invited_at, opened_at, accepted_at, declined_at, decline_reason, decline_note, last_reminded_at, created_at, round_number"
            )
            .eq("reviewer_id", reviewer_id_str)
            .order("created_at", desc=True)
            .limit(limit)
        )
        if manuscript_id is not None:
            query = query.eq("manuscript_id", str(manuscript_id))
        assignments_res = query.execute()

    assignment_rows = getattr(assignments_res, "data", None) or []
    if not assignment_rows:
        return {"success": True, "data": []}

    manuscript_ids = sorted(
        {
            str(row.get("manuscript_id") or "").strip()
            for row in assignment_rows
            if str(row.get("manuscript_id") or "").strip()
        }
    )
    manuscript_map: dict[str, dict[str, Any]] = {}
    if manuscript_ids:
        ms_res = (
            supabase_admin.table("manuscripts")
            .select("id, title, abstract, status")
            .in_("id", manuscript_ids)
            .execute()
        )
        for row in (getattr(ms_res, "data", None) or []):
            manuscript_map[str(row.get("id"))] = row

    assignment_counts_by_manuscript: dict[str, int] = {}
    for row in assignment_rows:
        mid = str(row.get("manuscript_id") or "").strip()
        if not mid:
            continue
        assignment_counts_by_manuscript[mid] = assignment_counts_by_manuscript.get(mid, 0) + 1

    report_map: dict[str, dict[str, Any]] = {}
    try:
        rr_res = (
            supabase_admin.table("review_reports")
            .select(
                "manuscript_id, reviewer_id, status, comments_for_author, content, confidential_comments_to_editor, attachment_path, created_at, updated_at"
            )
            .eq("reviewer_id", reviewer_id_str)
            .in_("manuscript_id", manuscript_ids)
            .order("created_at", desc=True)
            .execute()
        )
        for row in (getattr(rr_res, "data", None) or []):
            mid = str(row.get("manuscript_id") or "").strip()
            if mid and assignment_counts_by_manuscript.get(mid, 0) == 1 and mid not in report_map:
                report_map[mid] = row
    except Exception:
        report_map = {}

    assignment_ids = [
        str(row.get("id") or "").strip() for row in assignment_rows if str(row.get("id") or "").strip()
    ]
    email_events_by_assignment = _load_assignment_email_events(assignment_ids=assignment_ids)

    out: list[dict[str, Any]] = []
    for row in assignment_rows:
        assignment_id_value = str(row.get("id") or "").strip()
        manuscript_id_value = str(row.get("manuscript_id") or "").strip()
        manuscript = manuscript_map.get(manuscript_id_value) or {}
        report = report_map.get(manuscript_id_value) or {}
        report_submitted_at = report.get("updated_at") or report.get("created_at")
        assignment_state = _derive_assignment_state({**row, "report_submitted_at": report_submitted_at})
        if assignment_state not in {"submitted", "declined", "cancelled"}:
            continue
        email_events = email_events_by_assignment.get(assignment_id_value, [])
        latest_email = email_events[0] if email_events else {}
        attachment_path = str(report.get("attachment_path") or "").strip() or None
        out.append(
            {
                "assignment_id": assignment_id_value or row.get("id"),
                "reviewer_id": reviewer_id_str,
                "manuscript_id": manuscript_id_value,
                "manuscript_title": manuscript.get("title"),
                "manuscript_abstract": manuscript.get("abstract"),
                "manuscript_status": manuscript.get("status"),
                "assignment_status": row.get("status"),
                "assignment_state": assignment_state,
                "round_number": row.get("round_number"),
                "added_on": row.get("created_at"),
                "invited_at": row.get("invited_at"),
                "opened_at": row.get("opened_at"),
                "accepted_at": row.get("accepted_at"),
                "declined_at": row.get("declined_at"),
                "decline_reason": row.get("decline_reason"),
                "decline_note": row.get("decline_note"),
                "cancelled_at": row.get("cancelled_at"),
                "cancel_reason": row.get("cancel_reason"),
                "cancel_via": row.get("cancel_via"),
                "last_reminded_at": row.get("last_reminded_at"),
                "due_at": row.get("due_at"),
                "report_status": report.get("status"),
                "report_submitted_at": report_submitted_at,
                "comments_for_author": report.get("comments_for_author") or report.get("content"),
                "confidential_comments_to_editor": report.get("confidential_comments_to_editor"),
                "report_attachment_filename": attachment_path.rsplit("/", 1)[-1] if attachment_path else None,
                "latest_email_status": latest_email.get("status"),
                "latest_email_at": latest_email.get("created_at"),
                "latest_email_error": latest_email.get("error_message"),
                "email_events": email_events,
            }
        )

    return {"success": True, "data": out}


# === 3. 提交多维度评价 (Submission) ===
@router.post("/reviews/submit")
async def submit_review(
    assignment_id: UUID = Body(..., embed=True),
    scores: Dict[str, int] = Body(..., embed=True),  # {novelty: 5, rigor: 4, ...}
    # Feature 022 completion: comments_for_author 必填；兼容旧字段 comments
    comments_for_author: str | None = Body(None, embed=True),
    comments: str | None = Body(None, embed=True),
    confidential_comments_to_editor: str | None = Body(None, embed=True),
    attachment_path: str | None = Body(None, embed=True),
):
    """
    提交结构化评审意见
    """
    return await submit_review_impl(
        assignment_id=assignment_id,
        scores=scores,
        comments_for_author=comments_for_author,
        comments=comments,
        confidential_comments_to_editor=confidential_comments_to_editor,
        attachment_path=attachment_path,
        supabase_client=supabase,
        supabase_admin_client=supabase_admin,
    )


@router.post("/reviews/assignments/{assignment_id}/attachment")
async def upload_review_attachment(
    assignment_id: UUID,
    current_user: dict = Depends(get_current_user),
    profile: dict = Depends(require_any_role(["reviewer", "admin"])),
    attachment: UploadFile = File(...),
):
    """
    Reviewer 上传机密附件（Annotated PDF）

    中文注释:
    - 文件存储在 review-attachments 私有桶
    - 仅 reviewer 本人（或 admin）可上传
    - 返回 attachment_path，前端在提交 review 时写入 review_reports.attachment_path
    """
    if attachment is None:
        raise HTTPException(status_code=400, detail="attachment is required")

    safe_name = sanitize_storage_filename(attachment.filename, default_name="review_attachment")
    is_pdf = (attachment.content_type == "application/pdf") or safe_name.lower().endswith(".pdf")
    if not is_pdf:
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    try:
        assignment_res = (
            supabase_admin.table("review_assignments")
            .select("id, reviewer_id, status")
            .eq("id", str(assignment_id))
            .single()
            .execute()
        )
        assignment = getattr(assignment_res, "data", None) or {}
        if not assignment:
            raise HTTPException(status_code=404, detail="Assignment not found")
        if str(assignment.get("status") or "").strip().lower() == "cancelled":
            raise HTTPException(status_code=403, detail="Invitation revoked")

        is_admin = "admin" in (profile.get("roles") or [])
        if not is_admin and str(assignment.get("reviewer_id") or "") != str(current_user.get("id") or ""):
            raise HTTPException(status_code=403, detail="Forbidden")

        file_bytes = await attachment.read()
        path = f"review_assignments/{assignment_id}/{safe_name}"
        try:
            _ensure_review_attachments_bucket_exists()
            supabase_admin.storage.from_("review-attachments").upload(
                path,
                file_bytes,
                {"content-type": attachment.content_type or "application/pdf"},
            )
        except Exception as e:
            print(f"[Review Attachment] upload failed: {e}")
            raise HTTPException(status_code=500, detail="Failed to upload attachment")

        return {"success": True, "data": {"attachment_path": path}}
    except HTTPException:
        raise
    except Exception as e:
        print(f"Upload review attachment failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to upload attachment")


def _is_admin_email(email: Optional[str]) -> bool:
    return is_admin_email(email)


@router.get("/reviews/token/{token}")
async def get_review_by_token(token: str):
    """
    免登录审稿入口：通过 token 获取审稿任务与稿件信息

    中文注释:
    - 这是 Reviewer 无需登录的落地页能力；必须严格校验 token 有效性与过期时间。
    """
    return await get_review_by_token_impl(
        token=token,
        supabase_admin_client=supabase_admin,
    )


@router.get("/reviews/token/{token}/pdf-signed")
async def get_review_pdf_signed_by_token(token: str):
    """
    免登录审稿：返回该 token 对应稿件 PDF 的 signed URL。

    中文注释:
    - 前端 iframe 无法携带 Authorization header，因此必须由后端生成 signed URL。
    - token 本身是访问凭证，必须严格校验有效性与过期时间。
    """
    return await get_review_pdf_signed_by_token_impl(
        token=token,
        supabase_admin_client=supabase_admin,
        get_signed_url_for_manuscripts_bucket_fn=_get_signed_url_for_manuscripts_bucket,
    )


@router.post("/reviews/token/{token}/submit")
async def submit_review_by_token(
    token: str,
    # Feature 022 completion: comments_for_author 必填；兼容旧字段 content
    comments_for_author: str | None = Form(None),
    content: str | None = Form(None),
    confidential_comments_to_editor: str | None = Form(None),
    attachment: UploadFile | None = File(None),
):
    """
    免登录审稿提交：支持双通道评论 + 机密附件
    """
    return await submit_review_by_token_impl(
        token=token,
        comments_for_author=comments_for_author,
        content=content,
        confidential_comments_to_editor=confidential_comments_to_editor,
        attachment=attachment,
        supabase_admin_client=supabase_admin,
        ensure_review_attachments_bucket_exists_fn=_ensure_review_attachments_bucket_exists,
    )


@router.get("/reviews/feedback/{manuscript_id}")
async def get_review_feedback_for_manuscript(
    manuscript_id: UUID,
    current_user: dict = Depends(get_current_user),
):
    """
    获取某稿件的审稿反馈（按身份过滤机密字段）

    中文注释:
    - Author 只能看到公开字段（comments_for_author/content）
    - Editor/Admin 可以看到机密字段（confidential_comments_to_editor/attachment_path）
    """
    return await get_review_feedback_for_manuscript_impl(
        manuscript_id=manuscript_id,
        current_user=current_user,
        supabase_admin_client=supabase_admin,
        is_admin_email_fn=_is_admin_email,
    )


@router.get("/reviews/token/{token}/attachment-signed")
async def get_review_attachment_signed_by_token(token: str):
    """
    免登录审稿：返回该 token 对应 review attachment 的 signed URL（如果存在）。
    """
    return await get_review_attachment_signed_by_token_impl(
        token=token,
        supabase_admin_client=supabase_admin,
        get_signed_url_for_review_attachments_bucket_fn=_get_signed_url_for_review_attachments_bucket,
    )


@router.get("/reviews/reports/{review_report_id}/attachment-signed")
async def get_review_attachment_signed(
    review_report_id: UUID,
    current_user: dict = Depends(get_current_user),
    profile: dict = Depends(require_any_role(["reviewer", "managing_editor", "admin"])),
):
    """
    登录态：Reviewer/Editor/Admin 下载机密附件（Author 禁止）。
    """
    return await get_review_attachment_signed_impl(
        review_report_id=review_report_id,
        current_user=current_user,
        profile=profile,
        supabase_admin_client=supabase_admin,
        get_signed_url_for_review_attachments_bucket_fn=_get_signed_url_for_review_attachments_bucket,
    )
