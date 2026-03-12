from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.models.decision import DecisionSubmitRequest, ReviewStageExitRequest
from app.services.decision_service import DecisionService
from app.services.decision_service_transitions import build_author_decision_email_payload


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




def test_ensure_editor_access_allows_bound_academic_editor() -> None:
    svc = _svc()
    svc._ensure_editor_access(
        manuscript={"academic_editor_id": "academic-1"},
        user_id="academic-1",
        roles={"academic_editor"},
    )


def test_ensure_editor_access_rejects_unassigned_editor_in_chief() -> None:
    svc = _svc()
    with pytest.raises(HTTPException) as exc:
        svc._ensure_editor_access(
            manuscript={"editor_id": "editor-1", "assistant_editor_id": "ae-1", "academic_editor_id": "academic-1"},
            user_id="chief-2",
            roles={"editor_in_chief"},
        )
    assert exc.value.status_code == 403


def test_ensure_editor_access_rejects_unassigned_user() -> None:
    svc = _svc()
    with pytest.raises(HTTPException) as exc:
        svc._ensure_editor_access(
            manuscript={"editor_id": "editor-1", "assistant_editor_id": "ae-1"},
            user_id="other",
            roles={"assistant_editor"},
        )
    assert exc.value.status_code == 403


def test_ensure_editor_access_rejects_unassigned_managing_editor() -> None:
    svc = _svc()
    with pytest.raises(HTTPException) as exc:
        svc._ensure_editor_access(
            manuscript={"editor_id": "editor-1", "assistant_editor_id": "ae-1"},
            user_id="me-2",
            roles={"managing_editor"},
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
            "status": "decision",
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
    monkeypatch.setattr(
        svc,
        "_get_latest_review_stage_exit_request",
        lambda _id: {
            "target_stage": "first",
            "requested_outcome": "reject_resubmit",
            "note": "AE recommends reject and resubmit",
            "recipient_emails": ["chief@example.com", "board@example.com"],
            "changed_at": "2026-03-10T00:00:00+00:00",
            "changed_by": "ae-1",
        },
    )
    monkeypatch.setattr(svc, "_get_latest_decision_recommendation", lambda _id: None)
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
    assert context.get("review_stage_exit_request", {}).get("requested_outcome") == "reject_resubmit"
    assert context.get("review_stage_exit_request", {}).get("recipient_emails") == [
        "chief@example.com",
        "board@example.com",
    ]


def test_get_decision_context_allows_academic_editor_to_submit_final(
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
            "status": "decision_done",
            "file_path": "manuscripts/demo.pdf",
            "version": 2,
            "author_id": "author-1",
            "editor_id": "editor-1",
            "assistant_editor_id": "ae-1",
            "academic_editor_id": "academic-1",
            "updated_at": "2026-02-12T00:00:00+00:00",
        },
    )
    monkeypatch.setattr(svc, "_ensure_internal_decision_access", lambda **_kwargs: None)
    monkeypatch.setattr(svc, "_list_submitted_reports", lambda _id: [])
    monkeypatch.setattr(svc, "_get_latest_letter", lambda **_kwargs: None)
    monkeypatch.setattr(svc, "_get_latest_review_stage_exit_request", lambda _id: None)
    monkeypatch.setattr(svc, "_get_latest_decision_recommendation", lambda _id: None)
    monkeypatch.setattr(svc, "_build_template", lambda _reports: "template")
    monkeypatch.setattr(svc, "_signed_url", lambda _bucket, _path: "https://signed/url")

    context = svc.get_decision_context(
        manuscript_id="ms-1",
        user_id="academic-1",
        profile_roles=["academic_editor"],
    )

    permissions = context.get("permissions") or {}
    assert permissions.get("can_record_first") is True
    assert permissions.get("can_submit_final") is True
    assert permissions.get("can_submit") is True
    assert permissions.get("submission_mode") == "recommendation"


def test_review_stage_exit_request_requires_requested_outcome_for_first_target() -> None:
    with pytest.raises(ValueError, match="requested_outcome is required"):
        ReviewStageExitRequest(
            target_stage="first",
            note="Send to academic editor",
            accepted_pending_resolutions=[],
        )


def test_review_stage_exit_request_requires_recipients_for_first_target() -> None:
    with pytest.raises(ValueError, match="recipient_emails is required"):
        ReviewStageExitRequest(
            target_stage="first",
            requested_outcome="accept_after_minor_revision",
            note="Send to academic editor",
            accepted_pending_resolutions=[],
        )


def test_review_stage_exit_request_rejects_requested_outcome_for_non_first_target() -> None:
    with pytest.raises(ValueError, match="requested_outcome is only allowed"):
        ReviewStageExitRequest(
            target_stage="major_revision",
            requested_outcome="reject_resubmit",
            note="AE direct major revision",
            accepted_pending_resolutions=[],
        )


def test_review_stage_exit_request_normalizes_first_decision_recipient_emails() -> None:
    request = ReviewStageExitRequest(
        target_stage="first",
        requested_outcome="reject_resubmit",
        recipient_emails=" Chief@example.com ; board@example.com\nchief@example.com ",
        note="Send to academic decision",
        accepted_pending_resolutions=[],
    )

    assert request.recipient_emails == ["chief@example.com", "board@example.com"]


def test_review_stage_exit_request_rejects_legacy_add_reviewer_outcome() -> None:
    with pytest.raises(ValueError):
        ReviewStageExitRequest(
            target_stage="first",
            requested_outcome="add_reviewer",
            recipient_emails=["chief@example.com"],
            note="Legacy add reviewer should no longer be accepted",
            accepted_pending_resolutions=[],
        )


def test_review_stage_exit_request_rejects_recipient_emails_for_non_first_target() -> None:
    with pytest.raises(ValueError, match="recipient_emails is only allowed"):
        ReviewStageExitRequest(
            target_stage="major_revision",
            recipient_emails=["chief@example.com"],
            note="Direct revision should not carry academic recipients",
            accepted_pending_resolutions=[],
        )


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
        user_id="me-1",
        profile_roles=["managing_editor"],
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
            user_id="me-1",
            profile_roles=["managing_editor"],
            request=DecisionSubmitRequest(
                content="Accept",
                decision="accept",
                is_final=True,
                attachment_paths=[],
                last_updated_at=None,
            ),
        )
    assert exc.value.status_code == 422


def test_submit_decision_blocks_first_decision_accept(
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

    with pytest.raises(HTTPException) as exc:
        svc.submit_decision(
            manuscript_id="ms-1",
            user_id="ae-1",
            profile_roles=["assistant_editor"],
            request=DecisionSubmitRequest(
                content="Looks good",
                decision="accept",
                is_final=False,
                attachment_paths=[],
                last_updated_at=None,
            ),
        )
    assert exc.value.status_code == 422


def test_decision_submit_request_allows_committed_first_stage_action() -> None:
    request = DecisionSubmitRequest(
        content="Need one more reviewer",
        decision="add_reviewer",
        is_final=True,
        decision_stage="first",
        attachment_paths=[],
        last_updated_at=None,
    )

    assert request.decision_stage == "first"


def test_submit_decision_first_stage_add_reviewer_returns_to_under_review_without_letter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    svc = _svc()
    deleted_letters: list[str] = []
    monkeypatch.setattr(
        svc,
        "_get_manuscript",
        lambda _id: {
            "id": _id,
            "status": "decision",
            "version": 2,
            "author_id": "author-1",
            "editor_id": "eic-1",
            "assistant_editor_id": "ae-1",
        },
    )
    monkeypatch.setattr(svc, "_ensure_internal_decision_access", lambda **_kwargs: None)
    monkeypatch.setattr(svc, "_list_submitted_reports", lambda _id: [])
    monkeypatch.setattr(
        svc,
        "_get_latest_letter",
        lambda **_kwargs: {
            "id": "draft-1",
            "status": "draft",
            "updated_at": "2026-03-10T00:00:00+00:00",
        },
    )
    monkeypatch.setattr(
        svc,
        "_save_letter",
        lambda **_kwargs: (_ for _ in ()).throw(AssertionError("add_reviewer should not persist decision letter")),
    )
    transition_calls: list[dict[str, object]] = []
    monkeypatch.setattr(
        svc,
        "_transition_for_first_decision",
        lambda **kwargs: transition_calls.append(kwargs) or "under_review",
    )
    monkeypatch.setattr(
        svc,
        "_notify_author",
        lambda **_kwargs: (_ for _ in ()).throw(AssertionError("add_reviewer should not notify author")),
    )
    monkeypatch.setattr(
        svc,
        "_delete_letter_by_id",
        lambda *, letter_id: deleted_letters.append(letter_id),
    )

    out = svc.submit_decision(
        manuscript_id="ms-1",
        user_id="me-1",
        profile_roles=["managing_editor"],
        request=DecisionSubmitRequest(
            content="",
            decision="add_reviewer",
            is_final=True,
            decision_stage="first",
            attachment_paths=[],
            last_updated_at=None,
        ),
    )

    assert out["decision_letter_id"] is None
    assert out["status"] is None
    assert out["manuscript_status"] == "under_review"
    assert len(transition_calls) == 1
    assert transition_calls[0]["decision"] == "add_reviewer"
    assert deleted_letters == ["draft-1"]


def test_submit_decision_first_stage_reuses_current_draft_instead_of_latest_final_letter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    svc = _svc()
    save_calls: list[dict[str, object]] = []
    latest_letter_calls: list[dict[str, object]] = []
    monkeypatch.setattr(
        svc,
        "_get_manuscript",
        lambda _id: {
            "id": _id,
            "status": "decision",
            "version": 2,
            "author_id": "author-1",
            "editor_id": "eic-1",
            "assistant_editor_id": "ae-1",
        },
    )
    monkeypatch.setattr(svc, "_ensure_internal_decision_access", lambda **_kwargs: None)
    monkeypatch.setattr(svc, "_list_submitted_reports", lambda _id: [{"id": "r1", "status": "submitted"}])
    monkeypatch.setattr(
        svc,
        "_get_latest_letter",
        lambda **kwargs: latest_letter_calls.append(kwargs)
        or (
            {
                "id": "draft-1",
                "status": "draft",
                "updated_at": "2026-03-10T00:00:00+00:00",
            }
            if kwargs.get("status") == "draft"
            else (_ for _ in ()).throw(AssertionError("first decision should only query draft letter"))
        ),
    )
    monkeypatch.setattr(
        svc,
        "_save_letter",
        lambda **kwargs: save_calls.append(kwargs)
        or {
            "id": "draft-1",
            "status": "final",
            "updated_at": "2026-03-10T00:05:00+00:00",
            "attachment_paths": [],
            "content": kwargs["content"],
        },
    )
    monkeypatch.setattr(svc, "_transition_for_first_decision", lambda **_kwargs: "major_revision")
    monkeypatch.setattr(svc, "_notify_author", lambda **_kwargs: None)

    out = svc.submit_decision(
        manuscript_id="ms-1",
        user_id="me-1",
        profile_roles=["managing_editor"],
        request=DecisionSubmitRequest(
            content="Need major revision",
            decision="major_revision",
            is_final=True,
            decision_stage="first",
            attachment_paths=[],
            last_updated_at=None,
        ),
    )

    assert out["decision_letter_id"] == "draft-1"
    assert len(save_calls) == 1
    assert save_calls[0]["existing"]["id"] == "draft-1"
    assert save_calls[0]["status"] == "final"
    assert latest_letter_calls[0]["manuscript_version"] == 2


def test_submit_decision_final_stage_creates_new_letter_and_discards_stale_draft(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    svc = _svc()
    save_calls: list[dict[str, object]] = []
    deleted_letters: list[str] = []
    latest_letter_calls: list[dict[str, object]] = []
    monkeypatch.setattr(
        svc,
        "_get_manuscript",
        lambda _id: {
            "id": _id,
            "status": "decision_done",
            "version": 3,
            "author_id": "author-1",
            "editor_id": "eic-1",
            "assistant_editor_id": "ae-1",
        },
    )
    monkeypatch.setattr(svc, "_ensure_internal_decision_access", lambda **_kwargs: None)
    monkeypatch.setattr(svc, "_list_submitted_reports", lambda _id: [{"id": "r1", "status": "submitted"}])
    monkeypatch.setattr(
        svc,
        "_get_latest_letter",
        lambda **kwargs: latest_letter_calls.append(kwargs)
        or (
            {
                "id": "draft-9",
                "status": "draft",
                "updated_at": "2026-03-10T00:00:00+00:00",
            }
            if kwargs.get("status") == "draft"
            else None
        ),
    )
    monkeypatch.setattr(
        svc,
        "_save_letter",
        lambda **kwargs: save_calls.append(kwargs)
        or {
            "id": "final-1",
            "status": "final",
            "updated_at": "2026-03-10T00:10:00+00:00",
            "attachment_paths": [],
            "content": kwargs["content"],
        },
    )
    monkeypatch.setattr(svc, "_transition_for_final_decision", lambda **_kwargs: "approved")
    monkeypatch.setattr(svc, "_notify_author", lambda **_kwargs: None)
    monkeypatch.setattr(
        svc,
        "_delete_letter_by_id",
        lambda *, letter_id: deleted_letters.append(letter_id),
    )

    out = svc.submit_decision(
        manuscript_id="ms-1",
        user_id="me-1",
        profile_roles=["managing_editor"],
        request=DecisionSubmitRequest(
            content="Accept",
            decision="accept",
            is_final=True,
            decision_stage="final",
            attachment_paths=[],
            last_updated_at=None,
        ),
    )

    assert out["decision_letter_id"] == "final-1"
    assert len(save_calls) == 1
    assert save_calls[0]["existing"] is None
    assert save_calls[0]["status"] == "final"
    assert deleted_letters == ["draft-9"]
    assert latest_letter_calls[0]["manuscript_version"] == 3


def test_submit_decision_blocks_add_reviewer_in_final_stage(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    svc = _svc()
    monkeypatch.setattr(
        svc,
        "_get_manuscript",
        lambda _id: {
            "id": _id,
            "status": "decision_done",
            "version": 2,
            "author_id": "author-1",
            "editor_id": "eic-1",
            "assistant_editor_id": "ae-1",
        },
    )
    monkeypatch.setattr(svc, "_ensure_internal_decision_access", lambda **_kwargs: None)
    monkeypatch.setattr(svc, "_list_submitted_reports", lambda _id: [])

    with pytest.raises(HTTPException) as exc:
        svc.submit_decision(
            manuscript_id="ms-1",
            user_id="me-1",
            profile_roles=["managing_editor"],
            request=DecisionSubmitRequest(
                content="Need more reviewers",
                decision="add_reviewer",
                is_final=True,
                decision_stage="final",
                attachment_paths=[],
                last_updated_at=None,
            ),
        )

    assert exc.value.status_code == 422
    assert "only allowed in first decision" in str(exc.value.detail).lower()


def test_get_decision_context_blocks_under_review_until_exit_review_stage(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    svc = _svc()
    monkeypatch.setattr(
        svc,
        "_get_manuscript",
        lambda _id: {
            "id": _id,
            "status": "under_review",
            "version": 1,
            "author_id": "author-1",
            "editor_id": "me-1",
            "assistant_editor_id": "ae-1",
        },
    )
    monkeypatch.setattr(svc, "_ensure_internal_decision_access", lambda **_kwargs: None)
    monkeypatch.setattr(svc, "_list_submitted_reports", lambda _id: [{"id": "r1", "status": "submitted"}])
    monkeypatch.setattr(svc, "_get_latest_letter", lambda **_kwargs: None)
    monkeypatch.setattr(svc, "_build_template", lambda _reports: "template")
    monkeypatch.setattr(svc, "_signed_url", lambda _bucket, _path: "https://signed/url")
    monkeypatch.setattr(svc, "_has_submitted_author_revision", lambda _id: False)

    with pytest.raises(HTTPException) as exc:
        svc.get_decision_context(
            manuscript_id="ms-1",
            user_id="ae-1",
            profile_roles=["assistant_editor"],
        )

    assert exc.value.status_code == 400
    assert "decision workspace unavailable" in str(exc.value.detail).lower()


def test_submit_decision_blocks_final_revision_before_decision_queue(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    svc = _svc()
    monkeypatch.setattr(
        svc,
        "_get_manuscript",
        lambda _id: {
            "id": _id,
            "status": "under_review",
            "version": 1,
            "author_id": "author-1",
            "editor_id": "me-1",
            "assistant_editor_id": "ae-1",
        },
    )
    monkeypatch.setattr(svc, "_ensure_internal_decision_access", lambda **_kwargs: None)
    monkeypatch.setattr(svc, "_list_submitted_reports", lambda _id: [{"id": "r1", "status": "submitted"}])
    monkeypatch.setattr(svc, "_get_latest_letter", lambda **_kwargs: None)
    monkeypatch.setattr(
        svc,
        "_save_letter",
        lambda **_kwargs: {"id": "dl-1", "status": "final", "updated_at": "2026-02-12T00:00:00+00:00"},
    )
    monkeypatch.setattr(svc, "_transition_for_final_decision", lambda **_kwargs: "major_revision")
    monkeypatch.setattr(svc, "_notify_author", lambda **_kwargs: None)

    with pytest.raises(HTTPException) as exc:
        svc.submit_decision(
            manuscript_id="ms-1",
            user_id="me-1",
            profile_roles=["managing_editor"],
            request=DecisionSubmitRequest(
                content="Need revision",
                decision="major_revision",
                is_final=True,
                attachment_paths=[],
                last_updated_at=None,
            ),
        )

    assert exc.value.status_code == 422
    assert "exit review stage first" in str(exc.value.detail).lower()


def test_submit_decision_allows_accept_in_decision_done_without_author_revision(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    svc = _svc()
    monkeypatch.setattr(
        svc,
        "_get_manuscript",
        lambda _id: {
            "id": _id,
            "status": "decision_done",
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
    monkeypatch.setattr(svc, "_transition_for_final_decision", lambda **_kwargs: "approved")
    monkeypatch.setattr(svc, "_notify_author", lambda **_kwargs: None)

    out = svc.submit_decision(
        manuscript_id="ms-1",
        user_id="me-1",
        profile_roles=["managing_editor"],
        request=DecisionSubmitRequest(
            content="Accept",
            decision="accept",
            is_final=True,
            attachment_paths=[],
            last_updated_at=None,
        ),
    )
    assert out["manuscript_status"] == "approved"


def test_submit_decision_maps_reject_resubmit_to_reject_workflow_bucket(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    svc = _svc()
    save_calls: list[dict[str, object]] = []
    transition_calls: list[dict[str, object]] = []
    notify_calls: list[dict[str, object]] = []
    monkeypatch.setattr(
        svc,
        "_get_manuscript",
        lambda _id: {
            "id": _id,
            "status": "decision_done",
            "version": 2,
            "author_id": "author-1",
            "editor_id": "me-1",
            "assistant_editor_id": "ae-1",
        },
    )
    monkeypatch.setattr(svc, "_ensure_internal_decision_access", lambda **_kwargs: None)
    monkeypatch.setattr(svc, "_list_submitted_reports", lambda _id: [{"id": "r1", "status": "submitted"}])
    monkeypatch.setattr(svc, "_get_latest_letter", lambda **_kwargs: None)
    monkeypatch.setattr(
        svc,
        "_save_letter",
        lambda **kwargs: save_calls.append(kwargs)
        or {
            "id": "dl-1",
            "status": "final",
            "decision": kwargs["decision"],
            "updated_at": "2026-03-12T00:00:00+00:00",
        },
    )
    monkeypatch.setattr(
        svc,
        "_transition_for_final_decision",
        lambda **kwargs: transition_calls.append(kwargs) or "rejected",
    )
    monkeypatch.setattr(
        svc,
        "_notify_author",
        lambda **kwargs: notify_calls.append(kwargs),
    )

    out = svc.submit_decision(
        manuscript_id="ms-1",
        user_id="me-1",
        profile_roles=["managing_editor"],
        request=DecisionSubmitRequest(
            content="The idea is promising, but the manuscript needs to be rewritten and resubmitted.",
            decision="reject_resubmit",
            is_final=True,
            decision_stage="final",
            attachment_paths=[],
            last_updated_at=None,
        ),
    )

    assert out["manuscript_status"] == "rejected"
    assert save_calls[0]["decision"] == "reject"
    assert transition_calls[0]["decision"] == "reject"
    assert transition_calls[0]["transition_payload"]["decision"] == "reject_resubmit"
    assert transition_calls[0]["transition_payload"]["workflow_decision"] == "reject"
    assert notify_calls[0]["decision"] == "reject_resubmit"


def test_build_author_decision_email_payload_maps_reject_resubmit_template_key() -> None:
    payload = build_author_decision_email_payload(
        decision="reject_resubmit",
        manuscript_title="Promising Manuscript",
        recipient_name="Dr. Author",
    )

    assert payload["template_key"] == "decision_reject_resubmit"
    assert payload["context"]["decision_label"] == "Reject and Encourage Resubmitting after Revision"
    assert "encourage" in str(payload["body_text_template"]).lower()


def test_notify_author_sends_email_for_reject_resubmit(monkeypatch: pytest.MonkeyPatch) -> None:
    svc = _svc()
    email_calls: list[dict[str, object]] = []
    notification_calls: list[dict[str, object]] = []

    monkeypatch.setattr(
        "app.services.decision_service_transitions.resolve_author_notification_target",
        lambda **_kwargs: {
            "recipient_email": "submission@example.org",
            "recipient_name": "Dr. Author",
        },
    )
    monkeypatch.setattr(
        "app.services.decision_service_transitions.email_service.send_inline_email",
        lambda **kwargs: email_calls.append(kwargs) or {"status": "sent", "ok": True},
    )
    monkeypatch.setattr(
        svc.notification,
        "create_notification",
        lambda **kwargs: notification_calls.append(kwargs),
    )

    svc._notify_author(
        manuscript={
            "id": "ms-1",
            "title": "Promising Manuscript",
            "author_id": "author-1",
        },
        manuscript_id="ms-1",
        decision="reject_resubmit",
    )

    assert email_calls[0]["to_email"] == "submission@example.org"
    assert email_calls[0]["template_key"] == "decision_reject_resubmit"
    assert email_calls[0]["context"]["decision_label"] == "Reject and Encourage Resubmitting after Revision"
    assert notification_calls[0]["user_id"] == "author-1"


def test_notify_author_prefers_latest_recommendation_template_when_bucket_matches(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    svc = _svc()
    email_calls: list[dict[str, object]] = []

    monkeypatch.setattr(
        "app.services.decision_service_transitions.resolve_author_notification_target",
        lambda **_kwargs: {
            "recipient_email": "submission@example.org",
            "recipient_name": "Dr. Author",
        },
    )
    monkeypatch.setattr(
        svc,
        "_get_latest_decision_recommendation",
        lambda _manuscript_id: {"decision": "reject_resubmit"},
    )
    monkeypatch.setattr(
        "app.services.decision_service_transitions.email_service.send_inline_email",
        lambda **kwargs: email_calls.append(kwargs) or {"status": "sent", "ok": True},
    )
    monkeypatch.setattr(svc.notification, "create_notification", lambda **_kwargs: None)

    svc._notify_author(
        manuscript={
            "id": "ms-1",
            "title": "Promising Manuscript",
            "author_id": "author-1",
        },
        manuscript_id="ms-1",
        decision="reject",
    )

    assert email_calls[0]["template_key"] == "decision_reject_resubmit"
    assert email_calls[0]["context"]["decision_label"] == "Reject and Encourage Resubmitting after Revision"


def test_submit_decision_first_stage_academic_recommendation_keeps_status_and_skips_transition(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    svc = _svc()
    audit_calls: list[dict[str, object]] = []
    monkeypatch.setattr(
        svc,
        "_get_manuscript",
        lambda _id: {
            "id": _id,
            "status": "decision",
            "version": 1,
            "author_id": "author-1",
            "academic_editor_id": "academic-1",
        },
    )
    monkeypatch.setattr(svc, "_ensure_internal_decision_access", lambda **_kwargs: None)
    monkeypatch.setattr(svc, "_list_submitted_reports", lambda _id: [])
    monkeypatch.setattr(
        svc,
        "_transition_for_first_decision",
        lambda **_kwargs: (_ for _ in ()).throw(AssertionError("recommendation submit should not transition")),
    )
    monkeypatch.setattr(
        svc,
        "_notify_author",
        lambda **_kwargs: (_ for _ in ()).throw(AssertionError("recommendation submit should not notify author")),
    )
    monkeypatch.setattr(
        svc,
        "_safe_insert_audit_log",
        lambda **kwargs: audit_calls.append(kwargs),
    )

    out = svc.submit_decision(
        manuscript_id="ms-1",
        user_id="academic-1",
        profile_roles=["academic_editor"],
        request=DecisionSubmitRequest(
            content="Optional recommendation note",
            decision="accept",
            is_final=True,
            decision_stage="first",
            attachment_paths=["att-1|decision/recommendation-note.docx"],
            last_updated_at=None,
        ),
    )

    assert out["decision_letter_id"] is None
    assert out["status"] is None
    assert out["manuscript_status"] == "decision"
    assert len(audit_calls) == 1
    assert audit_calls[0]["from_status"] == "decision"
    assert audit_calls[0]["to_status"] == "decision"
    payload = audit_calls[0]["payload"]
    assert isinstance(payload, dict)
    assert payload["action"] == "decision_recommendation_submitted"
    assert payload["decision"] == "accept"
    assert payload["decision_stage"] == "first"


def test_submit_decision_final_stage_academic_recommendation_audits_without_notify(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    svc = _svc()
    audit_calls: list[dict[str, object]] = []
    monkeypatch.setattr(
        svc,
        "_get_manuscript",
        lambda _id: {
            "id": _id,
            "status": "decision_done",
            "version": 2,
            "author_id": "author-1",
            "academic_editor_id": "academic-1",
        },
    )
    monkeypatch.setattr(svc, "_ensure_internal_decision_access", lambda **_kwargs: None)
    monkeypatch.setattr(svc, "_list_submitted_reports", lambda _id: [{"id": "r1", "status": "submitted"}])
    monkeypatch.setattr(
        svc,
        "_transition_for_final_decision",
        lambda **_kwargs: (_ for _ in ()).throw(AssertionError("recommendation submit should not transition")),
    )
    monkeypatch.setattr(
        svc,
        "_notify_author",
        lambda **_kwargs: (_ for _ in ()).throw(AssertionError("recommendation submit should not notify author")),
    )
    monkeypatch.setattr(
        svc,
        "_safe_insert_audit_log",
        lambda **kwargs: audit_calls.append(kwargs),
    )

    out = svc.submit_decision(
        manuscript_id="ms-1",
        user_id="academic-1",
        profile_roles=["academic_editor"],
        request=DecisionSubmitRequest(
            content="The idea is promising, but the manuscript needs to be rewritten and resubmitted.",
            decision="reject_resubmit",
            is_final=True,
            decision_stage="final",
            attachment_paths=[],
            last_updated_at=None,
        ),
    )

    assert out["manuscript_status"] == "decision_done"
    assert len(audit_calls) == 1
    payload = audit_calls[0]["payload"]
    assert isinstance(payload, dict)
    assert payload["action"] == "decision_recommendation_submitted"
    assert payload["decision"] == "reject_resubmit"
    assert payload["workflow_decision"] == "reject"
    assert payload["decision_stage"] == "final"


def test_exit_review_stage_cancels_auto_and_explicit_pending_reviewers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    svc = _svc()
    monkeypatch.setattr(
        svc,
        "_get_manuscript",
        lambda _id: {
            "id": _id,
            "status": "under_review",
            "version": 2,
            "author_id": "author-1",
            "editor_id": "me-1",
            "assistant_editor_id": "ae-1",
        },
    )
    monkeypatch.setattr(svc, "_ensure_internal_decision_access", lambda **_kwargs: None)
    monkeypatch.setattr(svc, "_list_submitted_reports", lambda _id: [{"id": "r1", "status": "submitted"}])
    monkeypatch.setattr(
        svc,
        "_list_current_round_review_assignments",
        lambda **_kwargs: [
            {"id": "sel-1", "status": "selected"},
            {"id": "inv-1", "status": "invited", "invited_at": "2026-03-09T00:00:00Z"},
            {"id": "opn-1", "status": "opened", "opened_at": "2026-03-09T01:00:00Z"},
            {"id": "acc-1", "status": "pending", "accepted_at": "2026-03-09T02:00:00Z"},
            {"id": "sub-1", "status": "completed", "submitted_at": "2026-03-09T03:00:00Z"},
        ],
    )
    cancelled: list[tuple[str, str, str]] = []

    def _cancel(**kwargs):
        cancelled.append((kwargs["assignment_id"], kwargs["reason"], kwargs["via"]))

    monkeypatch.setattr(svc, "_cancel_assignment_for_stage_exit", _cancel)
    cancellation_emails: list[tuple[str, str]] = []
    monkeypatch.setattr(
        svc,
        "_send_cancellation_email_for_stage_exit",
        lambda **kwargs: cancellation_emails.append(
            (
                str(kwargs["assignment"].get("id") or ""),
                str(kwargs["cancel_reason"] or ""),
            )
        )
        or {"status": "sent"},
    )
    monkeypatch.setattr(
        svc,
        "editorial",
        SimpleNamespace(update_status=lambda **kwargs: {"status": kwargs["to_status"]}),
    )

    out = svc.exit_review_stage(
        manuscript_id="ms-1",
        user_id="ae-1",
        profile_roles=["assistant_editor"],
        request=ReviewStageExitRequest(
            target_stage="first",
            requested_outcome="major_revision",
            recipient_emails=["chief@example.com"],
            note="Enough evidence collected",
            accepted_pending_resolutions=[
                {"assignment_id": "acc-1", "action": "cancel", "reason": "AE decided two reviews are enough"}
            ],
        ),
    )

    assert out["manuscript_status"] == "decision"
    assert out["auto_cancelled_assignment_ids"] == ["sel-1", "inv-1", "opn-1"]
    assert out["manually_cancelled_assignment_ids"] == ["acc-1"]
    assert out["remaining_pending_assignment_ids"] == []
    assert cancelled == [
        ("sel-1", "Enough evidence collected", "auto_stage_exit"),
        ("inv-1", "Enough evidence collected", "auto_stage_exit"),
        ("opn-1", "Enough evidence collected", "auto_stage_exit"),
        ("acc-1", "AE decided two reviews are enough", "post_acceptance_cleanup"),
    ]
    assert cancellation_emails == [
        ("inv-1", "Enough evidence collected"),
        ("opn-1", "Enough evidence collected"),
        ("acc-1", "AE decided two reviews are enough"),
    ]
    assert out["cancellation_email_sent_assignment_ids"] == ["inv-1", "opn-1", "acc-1"]
    assert out["cancellation_email_failed_assignment_ids"] == []


def test_exit_review_stage_allows_zero_submitted_reports(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    svc = _svc()
    monkeypatch.setattr(
        svc,
        "_get_manuscript",
        lambda _id: {
            "id": _id,
            "status": "under_review",
            "version": 2,
            "author_id": "author-1",
            "editor_id": "me-1",
            "assistant_editor_id": "ae-1",
        },
    )
    monkeypatch.setattr(svc, "_ensure_internal_decision_access", lambda **_kwargs: None)
    monkeypatch.setattr(svc, "_list_submitted_reports", lambda _id: [])
    monkeypatch.setattr(
        svc,
        "_list_current_round_review_assignments",
        lambda **_kwargs: [
            {"id": "sel-1", "status": "selected"},
            {"id": "inv-1", "status": "invited", "invited_at": "2026-03-09T00:00:00Z"},
        ],
    )
    cancelled: list[tuple[str, str, str]] = []

    def _cancel(**kwargs):
        cancelled.append((kwargs["assignment_id"], kwargs["reason"], kwargs["via"]))

    monkeypatch.setattr(svc, "_cancel_assignment_for_stage_exit", _cancel)
    monkeypatch.setattr(
        svc,
        "_send_cancellation_email_for_stage_exit",
        lambda **kwargs: {"status": "sent"},
    )
    monkeypatch.setattr(
        svc,
        "editorial",
        SimpleNamespace(update_status=lambda **kwargs: {"status": kwargs["to_status"]}),
    )

    out = svc.exit_review_stage(
        manuscript_id="ms-1",
        user_id="ae-1",
        profile_roles=["assistant_editor"],
        request=ReviewStageExitRequest(
            target_stage="first",
            requested_outcome="accept_after_minor_revision",
            recipient_emails=["chief@example.com"],
            note="Proceed without waiting for reviewer reports",
            accepted_pending_resolutions=[],
        ),
    )

    assert out["manuscript_status"] == "decision"
    assert out["auto_cancelled_assignment_ids"] == ["sel-1", "inv-1"]
    assert out["manually_cancelled_assignment_ids"] == []
    assert out["remaining_pending_assignment_ids"] == []
    assert cancelled == [
        ("sel-1", "Proceed without waiting for reviewer reports", "auto_stage_exit"),
        ("inv-1", "Proceed without waiting for reviewer reports", "auto_stage_exit"),
    ]


@pytest.mark.parametrize(
    ("target_stage", "expected_status"),
    [
        ("major_revision", "major_revision"),
        ("minor_revision", "minor_revision"),
    ],
)
def test_exit_review_stage_allows_direct_revision_targets(
    monkeypatch: pytest.MonkeyPatch,
    target_stage: str,
    expected_status: str,
) -> None:
    svc = _svc()
    monkeypatch.setattr(
        svc,
        "_get_manuscript",
        lambda _id: {
            "id": _id,
            "status": "under_review",
            "version": 2,
            "author_id": "author-1",
            "editor_id": "me-1",
            "assistant_editor_id": "ae-1",
        },
    )
    monkeypatch.setattr(svc, "_ensure_internal_decision_access", lambda **_kwargs: None)
    monkeypatch.setattr(svc, "_list_current_round_review_assignments", lambda **_kwargs: [])
    transitions: list[dict[str, object]] = []
    monkeypatch.setattr(
        svc,
        "editorial",
        SimpleNamespace(
            update_status=lambda **kwargs: transitions.append(kwargs) or {"status": kwargs["to_status"]}
        ),
    )
    monkeypatch.setattr(
        "app.services.decision_service.RevisionService",
        lambda: SimpleNamespace(
            create_revision_request=lambda **_kwargs: {
                "success": True,
                "data": {
                    "revision": {"id": "rev-1"},
                    "manuscript_status": expected_status,
                    "round_number": 3,
                },
            }
        ),
    )
    monkeypatch.setattr(svc, "_send_direct_revision_request_email", lambda **_kwargs: (None, None))
    monkeypatch.setattr(svc.notification, "create_notification", lambda **_kwargs: None)
    audit_logs: list[dict[str, object]] = []
    monkeypatch.setattr(svc, "_safe_insert_audit_log", lambda **kwargs: audit_logs.append(kwargs))

    out = svc.exit_review_stage(
        manuscript_id="ms-1",
        user_id="ae-1",
        profile_roles=["assistant_editor"],
        request=ReviewStageExitRequest(
            target_stage=target_stage,  # type: ignore[arg-type]
            note=f"AE requested {target_stage}",
            accepted_pending_resolutions=[],
        ),
    )

    assert out["manuscript_status"] == expected_status
    assert transitions == []
    assert len(audit_logs) == 1
    assert audit_logs[0]["to_status"] == expected_status


@pytest.mark.parametrize(
    ("target_stage", "decision_type", "expected_status"),
    [
        ("major_revision", "major", "major_revision"),
        ("minor_revision", "minor", "minor_revision"),
    ],
)
def test_exit_review_stage_direct_revision_uses_revision_service_and_returns_author_email_summary(
    monkeypatch: pytest.MonkeyPatch,
    target_stage: str,
    decision_type: str,
    expected_status: str,
) -> None:
    svc = _svc()
    monkeypatch.setattr(
        svc,
        "_get_manuscript",
        lambda _id: {
            "id": _id,
            "status": "under_review",
            "version": 2,
            "title": "Demo Manuscript",
            "journal_id": "journal-1",
            "author_id": "author-1",
            "editor_id": "me-1",
            "assistant_editor_id": "ae-1",
        },
    )
    monkeypatch.setattr(svc, "_ensure_internal_decision_access", lambda **_kwargs: None)
    monkeypatch.setattr(svc, "_list_current_round_review_assignments", lambda **_kwargs: [])
    monkeypatch.setattr(
        svc,
        "editorial",
        SimpleNamespace(
            update_status=lambda **_kwargs: (_ for _ in ()).throw(
                AssertionError("direct revision exit should not use editorial.update_status")
            )
        ),
    )

    revision_calls: list[dict[str, object]] = []

    class _FakeRevisionService:
        def create_revision_request(
            self,
            manuscript_id: str,
            decision_type: str,
            editor_comment: str,
        ) -> dict[str, object]:
            revision_calls.append(
                {
                    "manuscript_id": manuscript_id,
                    "decision_type": decision_type,
                    "editor_comment": editor_comment,
                }
            )
            return {
                "success": True,
                "data": {
                    "revision": {"id": "rev-1"},
                    "manuscript_status": expected_status,
                    "round_number": 3,
                },
            }

    monkeypatch.setattr("app.services.decision_service.RevisionService", lambda: _FakeRevisionService())

    audit_logs: list[dict[str, object]] = []
    monkeypatch.setattr(
        svc,
        "_safe_insert_audit_log",
        lambda **kwargs: audit_logs.append(kwargs),
    )
    monkeypatch.setattr(
        svc,
        "_send_direct_revision_request_email",
        lambda **_kwargs: ("submission@example.org", None),
    )

    out = svc.exit_review_stage(
        manuscript_id="ms-1",
        user_id="ae-1",
        profile_roles=["assistant_editor"],
        request=ReviewStageExitRequest(
            target_stage=target_stage,  # type: ignore[arg-type]
            note=f"AE requested {target_stage}",
            accepted_pending_resolutions=[],
        ),
    )

    assert revision_calls == [
        {
            "manuscript_id": "ms-1",
            "decision_type": decision_type,
            "editor_comment": f"AE requested {target_stage}",
        }
    ]
    assert out["manuscript_status"] == expected_status
    assert out["author_revision_email_sent_recipient"] == "submission@example.org"
    assert out["author_revision_email_failed_recipient"] is None
    assert len(audit_logs) == 1
    assert audit_logs[0]["to_status"] == expected_status
    assert isinstance(audit_logs[0]["payload"], dict)
    assert audit_logs[0]["payload"]["action"] == "review_stage_exit"


def test_exit_review_stage_persists_requested_outcome_in_transition_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    svc = _svc()
    monkeypatch.setattr(
        svc,
        "_get_manuscript",
        lambda _id: {
            "id": _id,
            "status": "under_review",
            "version": 2,
            "author_id": "author-1",
            "editor_id": "me-1",
            "assistant_editor_id": "ae-1",
        },
    )
    monkeypatch.setattr(svc, "_ensure_internal_decision_access", lambda **_kwargs: None)
    monkeypatch.setattr(svc, "_list_current_round_review_assignments", lambda **_kwargs: [])
    transitions: list[dict[str, object]] = []
    monkeypatch.setattr(
        svc,
        "editorial",
        SimpleNamespace(
            update_status=lambda **kwargs: transitions.append(kwargs) or {"status": kwargs["to_status"]}
        ),
    )

    out = svc.exit_review_stage(
        manuscript_id="ms-1",
        user_id="ae-1",
        profile_roles=["assistant_editor"],
        request=ReviewStageExitRequest(
            target_stage="first",
            requested_outcome="reject_resubmit",
            recipient_emails=["chief@example.com", "board@example.com"],
            note="AE recommends reject and resubmit but escalates for first decision",
            accepted_pending_resolutions=[],
        ),
    )

    assert out["manuscript_status"] == "decision"
    assert len(transitions) == 1
    payload = transitions[0]["payload"]
    assert isinstance(payload, dict)
    assert payload["target_stage"] == "first"
    assert payload["requested_outcome"] == "reject_resubmit"
    assert payload["recipient_emails"] == ["chief@example.com", "board@example.com"]


def test_exit_review_stage_returns_first_decision_email_delivery_summary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    svc = _svc()
    monkeypatch.setattr(
        svc,
        "_get_manuscript",
        lambda _id: {
            "id": _id,
            "status": "under_review",
            "version": 1,
            "title": "Demo Manuscript",
            "journal_id": "journal-1",
            "author_id": "author-1",
            "editor_id": "me-1",
            "assistant_editor_id": "ae-1",
        },
    )
    monkeypatch.setattr(svc, "_ensure_internal_decision_access", lambda **_kwargs: None)
    monkeypatch.setattr(svc, "_list_submitted_reports", lambda _id: [])
    monkeypatch.setattr(svc, "_list_current_round_review_assignments", lambda **_kwargs: [])
    monkeypatch.setattr(
        svc,
        "editorial",
        SimpleNamespace(
            update_status=lambda **kwargs: {"status": kwargs["to_status"]}
        ),
    )
    monkeypatch.setattr(
        svc,
        "_send_first_decision_request_emails",
        lambda **_kwargs: (["chief@example.com"], ["board@example.com"]),
    )

    out = svc.exit_review_stage(
        manuscript_id="ms-1",
        user_id="ae-1",
        profile_roles=["assistant_editor"],
        request=ReviewStageExitRequest(
            target_stage="first",
            requested_outcome="major_revision",
            recipient_emails=["chief@example.com", "board@example.com"],
            note="Route to first decision",
            accepted_pending_resolutions=[],
        ),
    )

    assert out["manuscript_status"] == "decision"
    assert out["first_decision_email_sent_recipients"] == ["chief@example.com"]
    assert out["first_decision_email_failed_recipients"] == ["board@example.com"]


def test_exit_review_stage_blocks_when_accepted_reviewer_marked_wait(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    svc = _svc()
    monkeypatch.setattr(
        svc,
        "_get_manuscript",
        lambda _id: {
            "id": _id,
            "status": "under_review",
            "version": 1,
            "author_id": "author-1",
            "editor_id": "me-1",
            "assistant_editor_id": "ae-1",
        },
    )
    monkeypatch.setattr(svc, "_ensure_internal_decision_access", lambda **_kwargs: None)
    monkeypatch.setattr(svc, "_list_submitted_reports", lambda _id: [{"id": "r1", "status": "submitted"}])
    monkeypatch.setattr(
        svc,
        "_list_current_round_review_assignments",
        lambda **_kwargs: [
            {"id": "acc-1", "status": "pending", "accepted_at": "2026-03-09T02:00:00Z"},
        ],
    )

    with pytest.raises(HTTPException) as exc:
        svc.exit_review_stage(
            manuscript_id="ms-1",
            user_id="ae-1",
            profile_roles=["assistant_editor"],
            request=ReviewStageExitRequest(
                target_stage="final",
                note="Need to hold",
                accepted_pending_resolutions=[
                    {"assignment_id": "acc-1", "action": "wait", "reason": ""}
                ],
            ),
        )
    assert exc.value.status_code == 409


def test_exit_review_stage_keeps_transition_when_cancellation_email_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    svc = _svc()
    monkeypatch.setattr(
        svc,
        "_get_manuscript",
        lambda _id: {
            "id": _id,
            "status": "under_review",
            "version": 2,
            "author_id": "author-1",
            "editor_id": "me-1",
            "assistant_editor_id": "ae-1",
        },
    )
    monkeypatch.setattr(svc, "_ensure_internal_decision_access", lambda **_kwargs: None)
    monkeypatch.setattr(svc, "_list_submitted_reports", lambda _id: [{"id": "r1", "status": "submitted"}])
    monkeypatch.setattr(
        svc,
        "_list_current_round_review_assignments",
        lambda **_kwargs: [
            {"id": "sel-1", "status": "selected"},
            {"id": "inv-1", "status": "invited", "invited_at": "2026-03-09T00:00:00Z"},
            {"id": "acc-1", "status": "pending", "accepted_at": "2026-03-09T02:00:00Z"},
            {"id": "sub-1", "status": "completed", "submitted_at": "2026-03-09T03:00:00Z"},
        ],
    )
    cancelled: list[tuple[str, str, str]] = []

    def _cancel(**kwargs):
        cancelled.append((kwargs["assignment_id"], kwargs["reason"], kwargs["via"]))

    monkeypatch.setattr(svc, "_cancel_assignment_for_stage_exit", _cancel)
    monkeypatch.setattr(
        svc,
        "_send_cancellation_email_for_stage_exit",
        lambda **kwargs: {
            "status": "failed",
            "error_message": f"failed:{kwargs['assignment'].get('id')}",
        },
    )
    monkeypatch.setattr(
        svc,
        "editorial",
        SimpleNamespace(update_status=lambda **kwargs: {"status": kwargs["to_status"]}),
    )

    out = svc.exit_review_stage(
        manuscript_id="ms-1",
        user_id="ae-1",
        profile_roles=["assistant_editor"],
            request=ReviewStageExitRequest(
                target_stage="first",
                requested_outcome="major_revision",
                recipient_emails=["chief@example.com"],
                note="Proceed with current evidence",
                accepted_pending_resolutions=[
                    {"assignment_id": "acc-1", "action": "cancel", "reason": "AE closed review stage"}
            ],
        ),
    )

    assert out["manuscript_status"] == "decision"
    assert cancelled == [
        ("sel-1", "Proceed with current evidence", "auto_stage_exit"),
        ("inv-1", "Proceed with current evidence", "auto_stage_exit"),
        ("acc-1", "AE closed review stage", "post_acceptance_cleanup"),
    ]
    assert out["cancellation_email_sent_assignment_ids"] == []
    assert out["cancellation_email_failed_assignment_ids"] == ["inv-1", "acc-1"]


def test_transition_final_revision_from_decision_done_never_uses_allow_skip(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    svc = _svc()
    calls: list[dict[str, object]] = []

    def _update_status(**kwargs):
        calls.append(kwargs)
        return {"status": kwargs["to_status"]}

    monkeypatch.setattr(svc, "editorial", SimpleNamespace(update_status=_update_status))

    out = svc._transition_for_final_decision(
        manuscript_id="ms-1",
        current_status="decision_done",
        decision="minor_revision",
        changed_by="eic-1",
        transition_payload={"action": "unit_test"},
    )

    assert out == "minor_revision"
    assert len(calls) == 1
    assert calls[0]["allow_skip"] is False
    assert calls[0]["to_status"] == "minor_revision"
