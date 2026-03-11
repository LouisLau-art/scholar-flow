from __future__ import annotations

import re
from typing import Any

from postgrest.exceptions import APIError

from app.core.mail import email_service
from app.lib.api_client import supabase_admin
from app.models.email_log import EmailStatus

_EMAIL_TEMPLATE_KEY_RE = re.compile(r"^[a-z0-9_]{2,64}$")
_EMAIL_TEMPLATE_TABLE = "email_templates"
_DECISION_SCENE = "decision_workflow"
_FIRST_DECISION_EVENT_TYPE = "first_decision_request"
_FIRST_DECISION_TEMPLATE_KEY = "first_decision_request_standard"
_OUTCOME_LABELS = {
    "major_revision": "Major Revision",
    "minor_revision": "Minor Revision",
    "reject": "Reject",
    "add_reviewer": "Add Reviewer",
}

_DEFAULT_FIRST_DECISION_TEMPLATE: dict[str, Any] = {
    "template_key": _FIRST_DECISION_TEMPLATE_KEY,
    "display_name": "初审决定交办通知（标准）",
    "description": "AE 将稿件送入 First Decision 时，通知学术编辑/主编处理。",
    "scene": _DECISION_SCENE,
    "event_type": _FIRST_DECISION_EVENT_TYPE,
    "subject_template": "[{{ journal_title }}] First Decision Request - {{ manuscript_title }}",
    "body_html_template": (
        "<p>Dear {{ recipient_name }},</p>"
        "<p>The manuscript <strong>{{ manuscript_title }}</strong> has been routed to "
        "<strong>First Decision</strong>.</p>"
        "<p>Journal: <strong>{{ journal_title }}</strong><br/>"
        "Manuscript ID: <strong>{{ manuscript_id }}</strong><br/>"
        "AE Recommendation: <strong>{{ requested_outcome_label }}</strong></p>"
        "<p>AE Note: {{ ae_note or 'No additional note provided.' }}</p>"
        "<p>Open the decision workspace here: "
        "<a href=\"{{ decision_url }}\">{{ decision_url }}</a></p>"
        "<p>Requested by: {{ requested_by_name }}</p>"
    ),
    "body_text_template": (
        "Dear {{ recipient_name }}, manuscript \"{{ manuscript_title }}\" "
        "(ID: {{ manuscript_id }}) has been routed to First Decision for {{ journal_title }}. "
        "AE recommendation: {{ requested_outcome_label }}. "
        "AE note: {{ ae_note or 'No additional note provided.' }}. "
        "Decision workspace: {{ decision_url }}. Requested by: {{ requested_by_name }}."
    ),
    "is_active": True,
}


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


def _resolve_frontend_base_url() -> str:
    import os

    raw = (
        os.environ.get("FRONTEND_BASE_URL")
        or os.environ.get("FRONTEND_ORIGIN")
        or "http://localhost:3000"
    )
    return str(raw).strip().rstrip("/")


def _load_first_decision_template() -> dict[str, Any]:
    try:
        resp = (
            supabase_admin.table(_EMAIL_TEMPLATE_TABLE)
            .select(
                "template_key,display_name,description,scene,event_type,subject_template,body_html_template,body_text_template,is_active"
            )
            .eq("template_key", _FIRST_DECISION_TEMPLATE_KEY)
            .eq("is_active", True)
            .single()
            .execute()
        )
        row = getattr(resp, "data", None) or {}
        if row:
            scene = str(row.get("scene") or "").strip().lower()
            if scene == _DECISION_SCENE:
                return row
    except APIError as exc:
        text = str(exc)
        if "PGRST116" not in text and "0 rows" not in text and "single json object" not in text:
            if not _is_missing_table_error(text, _EMAIL_TEMPLATE_TABLE):
                raise
    except Exception as exc:
        if not _is_missing_table_error(str(exc), _EMAIL_TEMPLATE_TABLE):
            raise
    return dict(_DEFAULT_FIRST_DECISION_TEMPLATE)


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


def _resolve_user_name(user_id: str) -> str:
    try:
        resp = (
            supabase_admin.table("user_profiles")
            .select("full_name,email")
            .eq("id", user_id)
            .single()
            .execute()
        )
        payload = getattr(resp, "data", None) or {}
        full_name = str(payload.get("full_name") or "").strip()
        email = str(payload.get("email") or "").strip()
        return full_name or email or "Editorial Team"
    except Exception:
        return "Editorial Team"


def send_first_decision_request_email(
    *,
    manuscript: dict[str, Any],
    recipient_email: str,
    requested_outcome: str,
    requested_by: str,
    ae_note: str,
) -> dict[str, Any]:
    to_email = str(recipient_email or "").strip().lower()
    if not to_email:
        return {
            "status": "failed",
            "template_key": _FIRST_DECISION_TEMPLATE_KEY,
            "error_message": "Recipient email is missing",
            "recipient": None,
        }

    template_row = _load_first_decision_template()
    template_key = _normalize_template_key(
        str(template_row.get("template_key") or _FIRST_DECISION_TEMPLATE_KEY)
    )
    manuscript_id = str(manuscript.get("id") or "").strip()
    manuscript_title = str(manuscript.get("title") or "").strip() or "Manuscript"
    journal_title = _resolve_journal_title(manuscript)
    decision_url = f"{_resolve_frontend_base_url()}/editor/decision/{manuscript_id}"
    requested_outcome_value = str(requested_outcome or "").strip().lower()
    requested_outcome_label = _OUTCOME_LABELS.get(requested_outcome_value, requested_outcome_value or "Review")
    requested_by_name = _resolve_user_name(str(requested_by or "").strip())
    idempotency_key = f"first-decision-request/{manuscript_id}/{to_email}"
    audit_context = {
        "manuscript_id": manuscript_id or None,
        "actor_user_id": str(requested_by or "").strip() or None,
        "scene": _DECISION_SCENE,
        "event_type": _FIRST_DECISION_EVENT_TYPE,
        "idempotency_key": idempotency_key,
    }
    headers = {
        "X-SF-Manuscript-ID": manuscript_id,
        "X-SF-Template-Key": template_key,
        "X-SF-Event-Type": _FIRST_DECISION_EVENT_TYPE,
    }
    tags = [
        {"name": "scene", "value": _DECISION_SCENE},
        {"name": "event", "value": _FIRST_DECISION_EVENT_TYPE},
        {"name": "manuscript_id", "value": manuscript_id},
        {"name": "journal", "value": journal_title},
        {"name": "requested_outcome", "value": requested_outcome_value or "unknown"},
    ]
    context = {
        "recipient_name": to_email,
        "manuscript_title": manuscript_title,
        "manuscript_id": manuscript_id,
        "journal_title": journal_title,
        "requested_outcome": requested_outcome_value,
        "requested_outcome_label": requested_outcome_label,
        "ae_note": str(ae_note or "").strip(),
        "decision_url": decision_url,
        "requested_by_name": requested_by_name,
    }
    delivery = email_service.send_inline_email(
        to_email=to_email,
        template_key=template_key,
        subject_template=str(template_row.get("subject_template") or "").strip()
        or _DEFAULT_FIRST_DECISION_TEMPLATE["subject_template"],
        body_html_template=str(template_row.get("body_html_template") or "").strip()
        or _DEFAULT_FIRST_DECISION_TEMPLATE["body_html_template"],
        body_text_template=str(template_row.get("body_text_template") or "").strip()
        or _DEFAULT_FIRST_DECISION_TEMPLATE["body_text_template"],
        context=context,
        idempotency_key=idempotency_key,
        tags=tags,
        headers=headers,
        audit_context=audit_context,
    )
    return {
        "status": str(delivery.get("status") or EmailStatus.FAILED.value).strip().lower()
        or EmailStatus.FAILED.value,
        "template_key": template_key,
        "subject": str(delivery.get("subject") or "").strip() or None,
        "provider_id": delivery.get("provider_id"),
        "error_message": str(delivery.get("error_message") or "").strip() or None,
        "recipient": to_email,
    }
