from __future__ import annotations

import re
from typing import Any

from postgrest.exceptions import APIError

from app.core.mail import email_service
from app.lib.api_client import supabase_admin
from app.models.email_log import EmailStatus

_EMAIL_TEMPLATE_KEY_RE = re.compile(r"^[a-z0-9_]{2,64}$")
_EMAIL_TEMPLATE_TABLE = "email_templates"
_REVIEW_ASSIGNMENT_SCENE = "reviewer_assignment"
_CANCELLATION_EVENT_TYPE = "cancellation"
_CANCELLATION_TEMPLATE_KEY = "reviewer_cancellation_standard"

_DEFAULT_REVIEWER_CANCELLATION_TEMPLATE: dict[str, Any] = {
    "template_key": _CANCELLATION_TEMPLATE_KEY,
    "display_name": "审稿取消通知（标准）",
    "description": "当编辑部结束本轮外审或取消 reviewer assignment 时发送。",
    "scene": _REVIEW_ASSIGNMENT_SCENE,
    "event_type": _CANCELLATION_EVENT_TYPE,
    "subject_template": "Review Assignment Cancelled - {{ journal_title }}",
    "body_html_template": (
        "<p>Dear {{ reviewer_name }},</p>"
        "<p>Your review assignment for <strong>{{ manuscript_title }}</strong> in "
        "<strong>{{ journal_title }}</strong> has been cancelled.</p>"
        "<p>Manuscript ID: {{ manuscript_id }}</p>"
        "<p>Reason: {{ cancel_reason or 'Editorial workflow updated.' }}</p>"
        "<p>No further action is required. If you have already started reviewing, please disregard the earlier invitation link.</p>"
        "<p>Thank you for your time and support.</p>"
    ),
    "body_text_template": (
        "Dear {{ reviewer_name }}, your review assignment for \"{{ manuscript_title }}\" "
        "in {{ journal_title }} has been cancelled. Manuscript ID: {{ manuscript_id }}. "
        "Reason: {{ cancel_reason or 'Editorial workflow updated.' }}. No further action is required."
    ),
    "is_active": True,
}


def should_send_reviewer_assignment_cancellation_email(assignment: dict[str, Any]) -> bool:
    status_raw = str(assignment.get("status") or "").strip().lower()
    if status_raw in {"invited", "opened", "accepted", "agree", "agreed", "pending", "completed", "submitted"}:
        return True
    return any(
        assignment.get(field)
        for field in ("invited_at", "opened_at", "accepted_at", "submitted_at")
    )


def _normalize_template_key(raw_key: str) -> str:
    key = str(raw_key or "").strip().lower()
    key = re.sub(r"[^a-z0-9_]+", "_", key)
    key = re.sub(r"_{2,}", "_", key).strip("_")
    if not key or not _EMAIL_TEMPLATE_KEY_RE.match(key):
        raise ValueError("template_key must contain only lowercase letters, numbers, and underscore")
    return key


def _is_missing_table_error(error_text: str, table_name: str) -> bool:
    lowered = str(error_text or "").lower()
    needle = str(table_name or "").strip().lower()
    if not needle:
        return False
    return needle in lowered and ("does not exist" in lowered or "schema cache" in lowered)


def _load_cancellation_template() -> dict[str, Any]:
    try:
        resp = (
            supabase_admin.table(_EMAIL_TEMPLATE_TABLE)
            .select(
                "template_key,display_name,description,scene,event_type,subject_template,body_html_template,body_text_template,is_active"
            )
            .eq("template_key", _CANCELLATION_TEMPLATE_KEY)
            .eq("is_active", True)
            .single()
            .execute()
        )
        row = getattr(resp, "data", None) or {}
        if row:
            scene = str(row.get("scene") or "").strip().lower()
            if scene == _REVIEW_ASSIGNMENT_SCENE:
                return row
    except APIError as exc:
        text = str(exc)
        if "PGRST116" not in text and "0 rows" not in text and "single json object" not in text:
            if not _is_missing_table_error(text, _EMAIL_TEMPLATE_TABLE):
                raise
    except Exception as exc:
        if not _is_missing_table_error(str(exc), _EMAIL_TEMPLATE_TABLE):
            raise
    return dict(_DEFAULT_REVIEWER_CANCELLATION_TEMPLATE)


def _resolve_journal_title(manuscript: dict[str, Any]) -> str:
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


def send_reviewer_assignment_cancellation_email(
    *,
    assignment: dict[str, Any],
    manuscript: dict[str, Any],
    cancel_reason: str,
) -> dict[str, Any]:
    reviewer_id = str(assignment.get("reviewer_id") or "").strip()
    if not reviewer_id:
        return {
            "status": "skipped",
            "template_key": _CANCELLATION_TEMPLATE_KEY,
            "error_message": "Reviewer id is missing",
        }

    try:
        reviewer_profile_res = (
            supabase_admin.table("user_profiles")
            .select("email, full_name")
            .eq("id", reviewer_id)
            .single()
            .execute()
        )
        reviewer_profile = getattr(reviewer_profile_res, "data", None) or {}
    except Exception:
        reviewer_profile = {}

    reviewer_email = str(reviewer_profile.get("email") or "").strip()
    reviewer_name = str(reviewer_profile.get("full_name") or "").strip() or "Reviewer"
    if not reviewer_email:
        return {
            "status": "skipped",
            "template_key": _CANCELLATION_TEMPLATE_KEY,
            "error_message": "Reviewer email is missing",
        }

    template_row = _load_cancellation_template()
    template_key = _normalize_template_key(str(template_row.get("template_key") or _CANCELLATION_TEMPLATE_KEY))
    journal_title = _resolve_journal_title(manuscript)
    manuscript_id = str(manuscript.get("id") or assignment.get("manuscript_id") or "").strip()
    manuscript_title = str(manuscript.get("title") or "").strip() or "Manuscript"
    assignment_id = str(assignment.get("id") or "").strip()
    due_at = str(assignment.get("due_at") or "").strip()
    idempotency_key = f"reviewer-cancellation/{assignment_id}" if assignment_id else None
    audit_context = {
        "assignment_id": assignment_id or None,
        "manuscript_id": manuscript_id or None,
        "scene": _REVIEW_ASSIGNMENT_SCENE,
        "event_type": _CANCELLATION_EVENT_TYPE,
        "idempotency_key": idempotency_key,
    }
    headers = {
        "X-SF-Assignment-ID": assignment_id,
        "X-SF-Manuscript-ID": manuscript_id,
        "X-SF-Template-Key": template_key,
        "X-SF-Event-Type": _CANCELLATION_EVENT_TYPE,
    }
    tags = [
        {"name": "scene", "value": _REVIEW_ASSIGNMENT_SCENE},
        {"name": "event", "value": _CANCELLATION_EVENT_TYPE},
        {"name": "assignment_id", "value": assignment_id},
        {"name": "manuscript_id", "value": manuscript_id},
        {"name": "journal", "value": journal_title},
    ]
    context = {
        "reviewer_name": reviewer_name,
        "recipient_name": reviewer_name,
        "manuscript_title": manuscript_title,
        "manuscript_id": manuscript_id,
        "journal_title": journal_title,
        "due_at": due_at,
        "due_date": str(due_at).split("T")[0] if due_at else "",
        "cancel_reason": str(cancel_reason or "").strip(),
    }
    delivery = email_service.send_inline_email(
        to_email=reviewer_email,
        template_key=template_key,
        subject_template=str(template_row.get("subject_template") or "").strip() or _DEFAULT_REVIEWER_CANCELLATION_TEMPLATE["subject_template"],
        body_html_template=str(template_row.get("body_html_template") or "").strip() or _DEFAULT_REVIEWER_CANCELLATION_TEMPLATE["body_html_template"],
        body_text_template=str(template_row.get("body_text_template") or "").strip() or _DEFAULT_REVIEWER_CANCELLATION_TEMPLATE["body_text_template"],
        context=context,
        idempotency_key=idempotency_key,
        tags=tags,
        headers=headers,
        audit_context=audit_context,
    )
    return {
        "status": str(delivery.get("status") or EmailStatus.FAILED.value).strip().lower() or EmailStatus.FAILED.value,
        "template_key": template_key,
        "subject": str(delivery.get("subject") or "").strip() or None,
        "provider_id": delivery.get("provider_id"),
        "error_message": str(delivery.get("error_message") or "").strip() or None,
        "recipient": reviewer_email,
    }
