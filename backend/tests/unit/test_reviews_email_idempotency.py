from datetime import datetime, timezone

from app.api.v1.reviews import _build_assignment_email_idempotency_key


def test_invitation_idempotency_key_is_stable():
    assignment_id = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
    key1 = _build_assignment_email_idempotency_key(
        assignment_id=assignment_id,
        template_key="reviewer_invitation_standard",
        event_type="invitation",
        now=datetime(2026, 3, 6, 10, 0, tzinfo=timezone.utc),
    )
    key2 = _build_assignment_email_idempotency_key(
        assignment_id=assignment_id,
        template_key="reviewer_invitation_standard",
        event_type="invitation",
        now=datetime(2026, 3, 6, 23, 59, tzinfo=timezone.utc),
    )

    assert key1 == f"reviewer-invitation/{assignment_id}"
    assert key2 == key1


def test_reminder_idempotency_key_uses_hour_bucket():
    assignment_id = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
    key1 = _build_assignment_email_idempotency_key(
        assignment_id=assignment_id,
        template_key="reviewer_reminder_polite",
        event_type="reminder",
        now=datetime(2026, 3, 6, 10, 1, tzinfo=timezone.utc),
    )
    key2 = _build_assignment_email_idempotency_key(
        assignment_id=assignment_id,
        template_key="reviewer_reminder_polite",
        event_type="reminder",
        now=datetime(2026, 3, 6, 10, 59, tzinfo=timezone.utc),
    )
    key3 = _build_assignment_email_idempotency_key(
        assignment_id=assignment_id,
        template_key="reviewer_reminder_polite",
        event_type="reminder",
        now=datetime(2026, 3, 6, 11, 0, tzinfo=timezone.utc),
    )

    assert key1 == key2
    assert key1 != key3
