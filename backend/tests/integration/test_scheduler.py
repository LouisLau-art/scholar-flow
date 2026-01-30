from unittest.mock import MagicMock, patch

from app.core.scheduler import ChaseScheduler


def _chainable_table(execute_data):
    table = MagicMock()
    table.select.return_value = table
    table.eq.return_value = table
    table.is_.return_value = table
    table.lte.return_value = table
    table.update.return_value = table
    table.execute.return_value = MagicMock(data=execute_data)
    table.single.return_value = table
    return table


def test_chase_scheduler_idempotency_marks_only_on_success():
    # 1) 只有 1 个待催办任务
    review_assignments_table = _chainable_table(
        execute_data=[
            {
                "id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
                "reviewer_id": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
                "manuscript_id": "cccccccc-cccc-cccc-cccc-cccccccccccc",
                "due_at": "2026-01-31T00:00:00Z",
                "last_reminded_at": None,
                "manuscripts": {"title": "Test Paper"},
            }
        ]
    )
    user_profiles_table = _chainable_table(execute_data={"email": "rev@example.com"})

    email_service = MagicMock()
    email_service.send_template_email.return_value = True

    def table_side_effect(name: str):
        if name == "review_assignments":
            return review_assignments_table
        if name == "user_profiles":
            return user_profiles_table
        raise AssertionError(f"unexpected table: {name}")

    with patch("app.core.scheduler.supabase_admin") as admin:
        admin.table.side_effect = table_side_effect

        scheduler = ChaseScheduler(email_service=email_service)
        result = scheduler.run()

        assert result["processed_count"] == 1
        assert result["emails_sent"] == 1
        # 发送成功才写 last_reminded_at
        assert review_assignments_table.update.called is True


def test_chase_scheduler_does_not_mark_when_email_fails():
    review_assignments_table = _chainable_table(
        execute_data=[
            {
                "id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
                "reviewer_id": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
                "manuscript_id": "cccccccc-cccc-cccc-cccc-cccccccccccc",
                "due_at": "2026-01-31T00:00:00Z",
                "last_reminded_at": None,
                "manuscripts": {"title": "Test Paper"},
            }
        ]
    )
    user_profiles_table = _chainable_table(execute_data={"email": "rev@example.com"})

    email_service = MagicMock()
    email_service.send_template_email.return_value = False

    def table_side_effect(name: str):
        if name == "review_assignments":
            return review_assignments_table
        if name == "user_profiles":
            return user_profiles_table
        raise AssertionError(f"unexpected table: {name}")

    with patch("app.core.scheduler.supabase_admin") as admin:
        admin.table.side_effect = table_side_effect

        scheduler = ChaseScheduler(email_service=email_service)
        result = scheduler.run()

        assert result["processed_count"] == 1
        assert result["emails_sent"] == 0
        assert review_assignments_table.update.called is False

