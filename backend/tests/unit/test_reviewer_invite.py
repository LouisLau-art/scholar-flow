from datetime import date, timedelta
from unittest.mock import MagicMock

import pytest

import app.services.reviewer_service as reviewer_service_module
from app.schemas.review import InviteAcceptPayload, InviteDeclinePayload


class _Resp:
    def __init__(self, *, data=None):
        self.data = data


def _chain():
    q = MagicMock()
    for method in (
        "select",
        "eq",
        "single",
        "limit",
        "order",
        "update",
        "execute",
    ):
        getattr(q, method).return_value = q
    return q


@pytest.fixture
def supabase_admin(monkeypatch: pytest.MonkeyPatch):
    client = MagicMock()
    tables: dict[str, MagicMock] = {}

    def _table(name: str):
        tables.setdefault(name, _chain())
        return tables[name]

    client.table.side_effect = _table
    client._tables = tables  # type: ignore[attr-defined]
    monkeypatch.setattr(reviewer_service_module, "supabase_admin", client)
    return client


def _assignment_row(status: str = "pending", accepted_at=None, declined_at=None):
    return {
        "id": "00000000-0000-0000-0000-000000000001",
        "manuscript_id": "00000000-0000-0000-0000-000000000011",
        "reviewer_id": "00000000-0000-0000-0000-000000000022",
        "status": status,
        "due_at": None,
        "invited_at": "2026-02-01T00:00:00Z",
        "opened_at": None,
        "accepted_at": accepted_at,
        "declined_at": declined_at,
        "decline_reason": None,
        "decline_note": None,
    }


def test_accept_invitation_transitions_to_accepted(supabase_admin, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("REVIEW_INVITE_DUE_MIN_DAYS", "1")
    monkeypatch.setenv("REVIEW_INVITE_DUE_MAX_DAYS", "10")
    svc = reviewer_service_module.ReviewerInviteService()

    assignments = supabase_admin.table("review_assignments")
    assignments.execute.side_effect = [
        _Resp(data=_assignment_row(status="pending", accepted_at=None, declined_at=None)),
        _Resp(data=[{"id": "ok"}]),
    ]

    out = svc.accept_invitation(
        assignment_id=reviewer_service_module.UUID("00000000-0000-0000-0000-000000000001"),
        reviewer_id=reviewer_service_module.UUID("00000000-0000-0000-0000-000000000022"),
        payload=InviteAcceptPayload(due_date=date.today() + timedelta(days=1)),
    )

    assert out["status"] == "accepted"
    assert out["idempotent"] is False
    assert assignments.update.called is True


def test_accept_invitation_idempotent_when_already_accepted(supabase_admin):
    svc = reviewer_service_module.ReviewerInviteService()
    assignments = supabase_admin.table("review_assignments")
    assignments.execute.return_value = _Resp(
        data=_assignment_row(status="pending", accepted_at="2026-02-01T00:00:00Z", declined_at=None)
    )

    out = svc.accept_invitation(
        assignment_id=reviewer_service_module.UUID("00000000-0000-0000-0000-000000000001"),
        reviewer_id=reviewer_service_module.UUID("00000000-0000-0000-0000-000000000022"),
        payload=InviteAcceptPayload(due_date=date.today() + timedelta(days=1)),
    )
    assert out["status"] == "accepted"
    assert out["idempotent"] is True
    assert assignments.update.called is False


def test_decline_invitation_transitions_to_declined(supabase_admin):
    svc = reviewer_service_module.ReviewerInviteService()
    assignments = supabase_admin.table("review_assignments")
    assignments.execute.side_effect = [
        _Resp(data=_assignment_row(status="pending", accepted_at=None, declined_at=None)),
        _Resp(data=[{"id": "ok"}]),
    ]

    out = svc.decline_invitation(
        assignment_id=reviewer_service_module.UUID("00000000-0000-0000-0000-000000000001"),
        reviewer_id=reviewer_service_module.UUID("00000000-0000-0000-0000-000000000022"),
        payload=InviteDeclinePayload(reason="too_busy", note="No bandwidth"),
    )
    assert out["status"] == "declined"
    assert out["idempotent"] is False
    assert assignments.update.called is True


def test_decline_invitation_idempotent_when_already_declined(supabase_admin):
    svc = reviewer_service_module.ReviewerInviteService()
    assignments = supabase_admin.table("review_assignments")
    assignments.execute.return_value = _Resp(
        data=_assignment_row(status="declined", accepted_at=None, declined_at="2026-02-01T00:00:00Z")
    )

    out = svc.decline_invitation(
        assignment_id=reviewer_service_module.UUID("00000000-0000-0000-0000-000000000001"),
        reviewer_id=reviewer_service_module.UUID("00000000-0000-0000-0000-000000000022"),
        payload=InviteDeclinePayload(reason="too_busy", note="No bandwidth"),
    )
    assert out["status"] == "declined"
    assert out["idempotent"] is True
    assert assignments.update.called is False
