from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

from app.models.manuscript import ManuscriptStatus


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
    return table_name.lower() in text and "does not exist" in text


def is_missing_column_error(error: Exception, column_name: str) -> bool:
    text = str(error).lower()
    return column_name.lower() in text and ("column" in text or "schema cache" in text)


def safe_filename(filename: str) -> str:
    return str(filename or "proof.pdf").replace("/", "_").replace("\\", "_")
