from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.models.decision import DecisionSubmitRequest
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


class _RevisionQueryStub:
    def __init__(self, rows: list[dict]) -> None:
        self._rows = rows

    def select(self, *_args, **_kwargs):
        return self

    def eq(self, *_args, **_kwargs):
        return self

    def order(self, *_args, **_kwargs):
        return self

    def execute(self):
        return SimpleNamespace(data=self._rows)


class _RevisionClientStub:
    def __init__(self, rows: list[dict]) -> None:
        self._rows = rows

    def table(self, _name: str):
        return _RevisionQueryStub(self._rows)


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


def test_has_submitted_author_revision_scans_all_rows_not_only_latest() -> None:
    svc = _svc()
    svc.client = _RevisionClientStub(  # type: ignore[assignment]
        rows=[
            {"id": "rev-2", "status": "pending", "submitted_at": None},
            {"id": "rev-1", "status": "submitted", "submitted_at": "2026-02-12T00:00:00+00:00"},
        ]
    )
    assert svc._has_submitted_author_revision("ms-1") is True


def test_internal_decision_access_pure_assistant_editor_skips_scope_check(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    svc = _svc()
    called = {"scope": False}

    def _scope_guard(**_kwargs):
        called["scope"] = True
        raise AssertionError("scope check should not be called for pure assistant_editor")

    monkeypatch.setattr("app.services.decision_service.ensure_manuscript_scope_access", _scope_guard)
    monkeypatch.setattr(svc, "_ensure_editor_access", lambda **_kwargs: None)

    svc._ensure_internal_decision_access(
        manuscript={"assistant_editor_id": "ae-1"},
        manuscript_id="ms-1",
        user_id="ae-1",
        roles={"assistant_editor"},
        action="decision:record_first",
    )
    assert called["scope"] is False


def test_internal_decision_access_managing_editor_still_checks_scope(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    svc = _svc()
    called = {"scope": False}

    def _scope_ok(**_kwargs):
        called["scope"] = True
        return ""

    monkeypatch.setattr("app.services.decision_service.ensure_manuscript_scope_access", _scope_ok)
    monkeypatch.setattr(svc, "_ensure_editor_access", lambda **_kwargs: None)

    svc._ensure_internal_decision_access(
        manuscript={"editor_id": "me-1"},
        manuscript_id="ms-1",
        user_id="me-1",
        roles={"managing_editor"},
        action="decision:record_first",
    )
    assert called["scope"] is True


def test_submit_decision_allows_revision_without_submitted_author_revision(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    svc = _svc()
    monkeypatch.setattr(
        svc,
        "_get_manuscript",
        lambda _id: {
            "id": _id,
            "status": "decision",
            "version": 1,
            "author_id": "author-1",
            "editor_id": "me-1",
            "assistant_editor_id": "ae-1",
        },
    )
    monkeypatch.setattr(svc, "_ensure_internal_decision_access", lambda **_kwargs: None)
    monkeypatch.setattr(svc, "_list_submitted_reports", lambda _id: [{"id": "r1", "status": "submitted"}])
    monkeypatch.setattr(svc, "_has_submitted_author_revision", lambda _id: False)
    monkeypatch.setattr(svc, "_get_latest_letter", lambda **_kwargs: None)
    monkeypatch.setattr(
        svc,
        "_save_letter",
        lambda **_kwargs: {"id": "dl-1", "status": "final", "updated_at": "2026-02-12T00:00:00+00:00"},
    )
    monkeypatch.setattr(svc, "_transition_for_final_decision", lambda **_kwargs: "major_revision")
    monkeypatch.setattr(svc, "_notify_author", lambda **_kwargs: None)

    out = svc.submit_decision(
        manuscript_id="ms-1",
        user_id="eic-1",
        profile_roles=["editor_in_chief"],
        request=DecisionSubmitRequest(
            content="Need major revision",
            decision="major_revision",
            is_final=True,
            attachment_paths=[],
            last_updated_at=None,
        ),
    )
    assert out["manuscript_status"] == "major_revision"


def test_submit_decision_blocks_accept_without_submitted_author_revision(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    svc = _svc()
    monkeypatch.setattr(
        svc,
        "_get_manuscript",
        lambda _id: {
            "id": _id,
            "status": "decision",
            "version": 1,
            "author_id": "author-1",
            "editor_id": "me-1",
            "assistant_editor_id": "ae-1",
        },
    )
    monkeypatch.setattr(svc, "_ensure_internal_decision_access", lambda **_kwargs: None)
    monkeypatch.setattr(svc, "_list_submitted_reports", lambda _id: [{"id": "r1", "status": "submitted"}])
    monkeypatch.setattr(svc, "_has_submitted_author_revision", lambda _id: False)

    with pytest.raises(HTTPException) as exc:
        svc.submit_decision(
            manuscript_id="ms-1",
            user_id="eic-1",
            profile_roles=["editor_in_chief"],
            request=DecisionSubmitRequest(
                content="Accept",
                decision="accept",
                is_final=True,
                attachment_paths=[],
                last_updated_at=None,
            ),
        )
    assert exc.value.status_code == 422
