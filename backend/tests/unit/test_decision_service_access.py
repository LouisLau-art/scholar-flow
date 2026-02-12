from __future__ import annotations

from types import SimpleNamespace

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


class _QueryStub:
    def __init__(self, outcomes: list[object]) -> None:
        self._outcomes = outcomes
        self.select_calls: list[str] = []

    def select(self, fields: str):
        self.select_calls.append(fields)
        return self

    def eq(self, *_args, **_kwargs):
        return self

    def single(self):
        return self

    def execute(self):
        current = self._outcomes.pop(0)
        if isinstance(current, Exception):
            raise current
        return SimpleNamespace(data=current)


class _ClientStub:
    def __init__(self, outcomes: list[object]) -> None:
        self.query = _QueryStub(outcomes)

    def table(self, _name: str):
        return self.query


def test_get_manuscript_falls_back_when_assistant_editor_column_missing() -> None:
    svc = _svc()
    client = _ClientStub(
        outcomes=[
            Exception("column manuscripts.assistant_editor_id does not exist"),
            {
                "id": "ms-1",
                "title": "Demo",
                "status": "decision",
                "author_id": "author-1",
                "editor_id": "editor-1",
                "updated_at": "2026-02-12T00:00:00+00:00",
            },
        ]
    )
    svc.client = client  # type: ignore[assignment]

    row = svc._get_manuscript("ms-1")

    assert row["id"] == "ms-1"
    assert row["version"] == 1
    assert row["assistant_editor_id"] is None
    assert len(client.query.select_calls) == 2


def test_get_decision_context_returns_role_based_permission_flags(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    svc = _svc()

    monkeypatch.setattr(
        svc,
        "_get_manuscript",
        lambda _id: {
            "id": _id,
            "title": "Demo",
            "abstract": "A",
            "status": "under_review",
            "file_path": "manuscripts/demo.pdf",
            "version": 2,
            "author_id": "author-1",
            "editor_id": "editor-1",
            "assistant_editor_id": "ae-1",
            "updated_at": "2026-02-12T00:00:00+00:00",
        },
    )
    monkeypatch.setattr(svc, "_ensure_internal_decision_access", lambda **_kwargs: None)
    monkeypatch.setattr(svc, "_list_submitted_reports", lambda _id: [{"id": "r1"}])
    monkeypatch.setattr(svc, "_get_latest_letter", lambda **_kwargs: None)
    monkeypatch.setattr(svc, "_build_template", lambda _reports: "template")
    monkeypatch.setattr(svc, "_signed_url", lambda _bucket, _path: "https://signed/url")

    context = svc.get_decision_context(
        manuscript_id="ms-1",
        user_id="ae-1",
        profile_roles=["assistant_editor"],
    )

    permissions = context.get("permissions") or {}
    assert permissions.get("can_record_first") is True
    assert permissions.get("can_submit_final") is False
    assert permissions.get("can_submit") is True
