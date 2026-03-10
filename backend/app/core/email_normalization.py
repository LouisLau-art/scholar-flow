from __future__ import annotations


def normalize_email(email: str | None) -> str:
    return str(email or "").strip().lower()
