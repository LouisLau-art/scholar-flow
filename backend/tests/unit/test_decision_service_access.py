from __future__ import annotations

import pytest
from fastapi import HTTPException

from app.services.decision_service import DecisionService


def _svc() -> DecisionService:
    return DecisionService()


def test_ensure_editor_access_allows_assigned_editor() -> None:
    svc = _svc()
    svc._ensure_editor_access(
        manuscript={"editor_id": "editor-1"},
        user_id="editor-1",
        roles={"managing_editor"},
    )


def test_ensure_editor_access_allows_assigned_assistant_editor() -> None:
    svc = _svc()
    svc._ensure_editor_access(
        manuscript={"assistant_editor_id": "ae-1"},
        user_id="ae-1",
        roles={"assistant_editor"},
    )


def test_ensure_editor_access_rejects_unassigned_user() -> None:
    svc = _svc()
    with pytest.raises(HTTPException) as exc:
        svc._ensure_editor_access(
            manuscript={"editor_id": "editor-1", "assistant_editor_id": "ae-1"},
            user_id="other",
            roles={"assistant_editor"},
        )
    assert exc.value.status_code == 403
