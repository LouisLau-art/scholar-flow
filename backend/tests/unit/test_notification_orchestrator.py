from unittest.mock import MagicMock

from app.services.email_recipient_resolver import EmailRecipientResolver
from app.services.notification_orchestrator import NotificationOrchestrator


class _Resp:
    def __init__(self, data=None):
        self.data = data


def _chain_mock(responses):
    mock = MagicMock()
    for name in ("table", "select", "eq", "single", "execute"):
        getattr(mock, name).return_value = mock
    mock.execute.side_effect = [_Resp(data=item) for item in responses]
    return mock


def test_email_recipient_resolver_adds_journal_mailbox_to_cc_and_reply_to():
    resolver = EmailRecipientResolver()
    supabase = _chain_mock(
        [
            {
                "public_editorial_email": "office@example.org",
            }
        ]
    )

    target = resolver.resolve_author_email_targets(
        manuscript={
            "journal_id": "journal-1",
            "submission_email": "login@example.org",
            "author_contacts": [
                {
                    "name": "Corr Author",
                    "email": "corr@example.org",
                    "is_corresponding": True,
                },
                {
                    "name": "Co Author",
                    "email": "co@example.org",
                    "is_corresponding": False,
                },
            ],
        },
        supabase_client=supabase,
    )

    assert target["to_recipients"] == ["corr@example.org"]
    assert target["cc_recipients"] == ["co@example.org", "office@example.org"]
    assert target["reply_to_recipients"] == ["office@example.org"]
    assert target["journal_public_editorial_email"] == "office@example.org"


def test_email_recipient_resolver_uses_preloaded_journal_mailbox_without_refetch():
    resolver = EmailRecipientResolver()
    supabase = MagicMock()

    target = resolver.resolve_author_email_targets(
        manuscript={
            "journal_id": "journal-1",
            "journal_public_editorial_email": "office@example.org",
            "submission_email": "login@example.org",
            "author_contacts": [
                {
                    "name": "Corr Author",
                    "email": "corr@example.org",
                    "is_corresponding": True,
                },
                {
                    "name": "Co Author",
                    "email": "co@example.org",
                    "is_corresponding": False,
                },
            ],
        },
        supabase_client=supabase,
    )

    assert target["cc_recipients"] == ["co@example.org", "office@example.org"]
    assert target["reply_to_recipients"] == ["office@example.org"]
    supabase.table.assert_not_called()


def test_notification_orchestrator_delegates_author_resolution_to_recipient_resolver():
    resolver = MagicMock()
    resolver.resolve_author_email_targets.return_value = {
        "recipient_email": "corr@example.org",
        "to_recipients": ["corr@example.org"],
    }
    orchestrator = NotificationOrchestrator(recipient_resolver=resolver)

    result = orchestrator.resolve_author_notification_target(
        manuscript={"submission_email": "login@example.org"},
        manuscript_id="manuscript-1",
        supabase_client=MagicMock(),
        author_profile={"email": "author@example.org"},
    )

    resolver.resolve_author_email_targets.assert_called_once()
    assert result["recipient_email"] == "corr@example.org"
    assert result["to_recipients"] == ["corr@example.org"]
