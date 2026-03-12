from __future__ import annotations

from unittest.mock import MagicMock, patch

from app.services.first_decision_request_email import (
    _DEFAULT_FIRST_DECISION_TEMPLATE,
    send_first_decision_request_email,
)
from app.services.reviewer_assignment_cancellation_email import (
    _DEFAULT_REVIEWER_CANCELLATION_TEMPLATE,
    send_reviewer_assignment_cancellation_email,
)


class _Resp:
    def __init__(self, data=None):
        self.data = data


def _chain_mock(responses):
    mock = MagicMock()
    for name in ("table", "select", "eq", "single", "execute"):
        getattr(mock, name).return_value = mock
    mock.execute.side_effect = [_Resp(data=item) for item in responses]
    return mock


def test_send_first_decision_request_email_adds_journal_mailbox_cc_and_reply_to():
    supabase = _chain_mock(
        [
            {
                "title": "Journal One",
                "public_editorial_email": "office@example.org",
            }
        ]
    )
    send_mock = MagicMock(
        return_value={
            "status": "sent",
            "subject": "First Decision Request",
            "provider_id": "re_fd_123",
            "error_message": None,
        }
    )

    with (
        patch("app.services.first_decision_request_email.supabase_admin", supabase),
        patch(
            "app.services.first_decision_request_email._load_first_decision_template",
            return_value=dict(_DEFAULT_FIRST_DECISION_TEMPLATE),
        ),
        patch("app.services.first_decision_request_email._resolve_user_name", return_value="AE User"),
        patch("app.services.first_decision_request_email.email_service.send_rendered_email", send_mock),
    ):
        result = send_first_decision_request_email(
            manuscript={
                "id": "manuscript-1",
                "title": "Decision Manuscript",
                "journal_id": "journal-1",
            },
            recipient_email="ae@example.org",
            requested_outcome="major_revision",
            requested_by="user-1",
            ae_note="Please handle this first decision.",
        )

    assert result["status"] == "sent"
    send_kwargs = send_mock.call_args.kwargs
    assert send_kwargs["to_email"] == "ae@example.org"
    assert send_kwargs["cc_emails"] == ["office@example.org"]
    assert send_kwargs["reply_to_emails"] == ["office@example.org"]
    assert send_kwargs["audit_context"]["delivery_mode"] == "auto"
    assert send_kwargs["audit_context"]["communication_status"] == "system_sent"


def test_send_reviewer_assignment_cancellation_email_adds_journal_mailbox_cc_and_reply_to():
    supabase = _chain_mock(
        [
            {
                "email": "reviewer@example.org",
                "full_name": "Reviewer One",
            },
            {
                "title": "Journal One",
                "public_editorial_email": "office@example.org",
            },
        ]
    )
    send_mock = MagicMock(
        return_value={
            "status": "sent",
            "subject": "Review Assignment Cancelled",
            "provider_id": "re_cancel_123",
            "error_message": None,
        }
    )

    with (
        patch("app.services.reviewer_assignment_cancellation_email.supabase_admin", supabase),
        patch(
            "app.services.reviewer_assignment_cancellation_email._load_cancellation_template",
            return_value=dict(_DEFAULT_REVIEWER_CANCELLATION_TEMPLATE),
        ),
        patch("app.services.reviewer_assignment_cancellation_email.email_service.send_rendered_email", send_mock),
    ):
        result = send_reviewer_assignment_cancellation_email(
            assignment={
                "id": "assignment-1",
                "reviewer_id": "reviewer-1",
                "manuscript_id": "manuscript-1",
                "status": "invited",
            },
            manuscript={
                "id": "manuscript-1",
                "title": "Cancellation Manuscript",
                "journal_id": "journal-1",
            },
            cancel_reason="Editorial scope updated.",
            cancelled_by="user-1",
        )

    assert result["status"] == "sent"
    send_kwargs = send_mock.call_args.kwargs
    assert send_kwargs["to_email"] == "reviewer@example.org"
    assert send_kwargs["cc_emails"] == ["office@example.org"]
    assert send_kwargs["reply_to_emails"] == ["office@example.org"]
    assert send_kwargs["audit_context"]["delivery_mode"] == "auto"
    assert send_kwargs["audit_context"]["communication_status"] == "system_sent"
