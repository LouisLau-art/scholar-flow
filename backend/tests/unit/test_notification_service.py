from unittest.mock import MagicMock, patch

import pytest
from postgrest.exceptions import APIError


def _make_admin_client_raising(error: Exception) -> MagicMock:
    client = MagicMock()
    chain = MagicMock()
    client.table.return_value = chain
    chain.insert.return_value = chain
    chain.execute.side_effect = error
    return client


def test_create_notification_suppresses_fk_errors_for_orphan_users():
    """
    中文注释:
    - 允许保留“仅展示用途”的 mock user_profiles（不对应 auth.users）。
    - 写 notifications 时遇到外键错误应静默忽略，避免刷屏。
    """

    from app.services.notification_service import NotificationService

    api_error = APIError(
        {
            "code": "23503",
            "message": 'insert or update on table "notifications" violates foreign key constraint "notifications_user_id_fkey"',
            "details": None,
            "hint": None,
        }
    )

    with (
        patch(
            "app.services.notification_service.supabase_admin",
            _make_admin_client_raising(api_error),
        ),
        patch("builtins.print") as print_mock,
    ):
        res = NotificationService().create_notification(
            user_id="00000000-0000-0000-0000-000000000000",
            manuscript_id=None,
            type="system",
            title="t",
            content="c",
        )
        assert res is None
        print_mock.assert_not_called()


def test_create_notification_logs_other_api_errors():
    from app.services.notification_service import NotificationService

    api_error = APIError(
        {"code": "PGRST000", "message": "some api error", "details": None, "hint": None}
    )

    with (
        patch(
            "app.services.notification_service.supabase_admin",
            _make_admin_client_raising(api_error),
        ),
        patch("builtins.print") as print_mock,
    ):
        res = NotificationService().create_notification(
            user_id="any",
            manuscript_id=None,
            type="system",
            title="t",
            content="c",
        )
        assert res is None
        assert print_mock.called is True

