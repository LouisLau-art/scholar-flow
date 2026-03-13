from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException

from app.models.manuscript import ManuscriptStatus
from app.core.storage_filename import sanitize_storage_filename


POST_ACCEPTANCE_ALLOWED = {
    ManuscriptStatus.APPROVED.value,
    ManuscriptStatus.LAYOUT.value,
    ManuscriptStatus.ENGLISH_EDITING.value,
    ManuscriptStatus.PROOFREADING.value,
}

ACTIVE_CYCLE_STATUSES = {
    "draft",
    "awaiting_author",
    "author_corrections_submitted",
    "author_confirmed",
    "in_layout_revision",
}

AUTHOR_CONTEXT_VISIBLE_STATUSES = {
    "awaiting_author",
    "author_corrections_submitted",
    "author_confirmed",
}

PRODUCTION_SOP_SCHEMA_ERROR_PREFIX = "Production SOP schema not migrated"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def utc_now_iso() -> str:
    return utc_now().isoformat()


def to_utc_datetime(raw: Any) -> datetime | None:
    if isinstance(raw, datetime):
        if raw.tzinfo is None:
            return raw.replace(tzinfo=timezone.utc)
        return raw.astimezone(timezone.utc)
    if isinstance(raw, str) and raw.strip():
        try:
            parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                return parsed.replace(tzinfo=timezone.utc)
            return parsed.astimezone(timezone.utc)
        except Exception:
            return None
    return None


def is_truthy_env(name: str, default: str = "0") -> bool:
    return (os.getenv(name, default) or "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
        "y",
    }


def is_table_missing_error(error: Exception, table_name: str) -> bool:
    text = str(error).lower()
    tname = table_name.lower()
    return tname in text and ("does not exist" in text or "in the schema cache" in text or "pgrst205" in text)


def is_missing_column_error(error: Exception, column_name: str) -> bool:
    text = str(error).lower()
    return column_name.lower() in text and ("column" in text or "schema cache" in text)


def production_sop_schema_detail(resource: str) -> str:
    normalized = str(resource or "production schema missing or outdated").strip() or "production schema missing or outdated"
    return f"{PRODUCTION_SOP_SCHEMA_ERROR_PREFIX}: {normalized}"


def production_sop_schema_http_error(resource: str, *, status_code: int = 503) -> HTTPException:
    return HTTPException(status_code=status_code, detail=production_sop_schema_detail(resource))


def normalize_production_sop_schema_http_error(error: Exception) -> HTTPException | None:
    if isinstance(error, HTTPException):
        detail_text = str(error.detail or "").strip()
        if detail_text.startswith(PRODUCTION_SOP_SCHEMA_ERROR_PREFIX):
            if error.status_code == 503:
                return error
            return production_sop_schema_http_error(detail_text.removeprefix(f"{PRODUCTION_SOP_SCHEMA_ERROR_PREFIX}:").strip())
        text = detail_text.lower()
    else:
        text = str(error).lower()

    schema_keywords = ("schema cache", "pgrst205", "pgrst204", "does not exist", "could not find", "db not migrated")
    if not any(keyword in text for keyword in schema_keywords):
        return None

    resource_map = (
        ("status_transition_logs", "status_transition_logs table missing"),
        ("production_cycle_events", "production_cycle_events table missing"),
        ("production_cycle_artifacts", "production_cycle_artifacts table missing"),
        ("production_proofreading_responses", "production_proofreading_responses table missing"),
        ("production_correction_items", "production_correction_items table missing"),
        ("production_cycles", "production_cycles table missing"),
        ("invoices", "invoices table missing"),
        ("collaborator_editor_ids", "production_cycles collaborator_editor_ids column missing"),
        ("current_assignee_id", "production_cycles current_assignee_id column missing"),
        ("coordinator_ae_id", "production_cycles assignment columns missing"),
        ("typesetter_id", "production_cycles assignment columns missing"),
        ("language_editor_id", "production_cycles assignment columns missing"),
        ("pdf_editor_id", "production_cycles assignment columns missing"),
        ("final_pdf_path", "manuscripts final_pdf_path column missing"),
        ("approved_at", "production_cycles publish gate columns missing"),
        ("galley_path", "production_cycles publish gate columns missing"),
        ("stage", "production_cycles stage column missing"),
        ("attachment_bucket", "production_proofreading_responses attachment columns missing"),
    )
    for token, resource in resource_map:
        if token in text:
            return production_sop_schema_http_error(resource)

    return production_sop_schema_http_error("production schema missing or outdated")


def safe_filename(filename: str) -> str:
    return sanitize_storage_filename(filename, default_name="proof")
