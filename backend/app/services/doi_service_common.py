from __future__ import annotations

import logging
from datetime import datetime, timezone

logger = logging.getLogger("scholarflow.doi")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def truncate(value: str, max_len: int = 2000) -> str:
    text = str(value or "").strip()
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."


def looks_like_single_no_rows(error_text: str) -> bool:
    lowered = (error_text or "").lower()
    return (
        "pgrst116" in lowered
        or "cannot coerce the result to a single json object" in lowered
        or "0 rows" in lowered
    )


def looks_like_missing_schema(error_text: str) -> bool:
    lowered = (error_text or "").lower()
    return (
        "pgrst205" in lowered
        or "schema cache" in lowered
        or "does not exist" in lowered
        or "relation" in lowered
        or "undefinedtable" in lowered
    )
