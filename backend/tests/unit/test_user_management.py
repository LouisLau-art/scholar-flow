"""
Tests for UserManagementService
Coverage target: 80%+
"""

import pytest
import logging
from unittest.mock import MagicMock, patch
from uuid import UUID

from app.services.user_management import UserManagementService


class MockSupabaseResponse:
    """Mock Supabase response"""

    def __init__(self, data=None, count=None, error=None):
        self.data = data or []
        self.count = count or len(self.data)
        self.error = error


class MockQueryBuilder:
    """Mock Supabase query builder chain"""

    def __init__(self, return_data=None, raise_error=None):
        self._data = return_data or []
        self._raise_error = raise_error
        self._count = len(self._data) if isinstance(self._data, list) else 0

    def select(self, *args, **kwargs):
        return self

    def insert(self, data):
        return self

    def update(self, data):
        return self

    def upsert(self, data):
        return self

    def eq(self, *args):
        return self

    def contains(self, *args):
        return self

    def or_(self, *args):
        return self

    def range(self, *args):
        return self

    def order(self, *args, **kwargs):
        return self

    def single(self):
        return self

    def maybe_single(self):
        return self

    def execute(self):
        if self._raise_error:
            raise self._raise_error
        return MockSupabaseResponse(data=self._data, count=self._count)


class MockAdminClient:
    """Mock Supabase admin client"""

    def __init__(self, query_builder=None):
        self._query_builder = query_builder or MockQueryBuilder()
        self.auth = MagicMock()

    def table(self, name):
        return self._query_builder


@pytest.fixture
def mock_env(monkeypatch):
    """Set up environment variables"""
    monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "test-service-key")


class TestUserManagementServiceInit:
    """Test service initialization"""

    def test_init_with_missing_env(self, monkeypatch, capsys):
        """Test init with missing environment variables"""
        monkeypatch.delenv("SUPABASE_URL", raising=False)
        monkeypatch.delenv("SUPABASE_SERVICE_ROLE_KEY", raising=False)

        with patch("app.services.user_management.create_client") as mock_create:
            mock_create.return_value = MagicMock()
            UserManagementService()

            captured = capsys.readouterr()
            assert "WARNING" in captured.out or mock_create.called


class TestLogRoleChange:
    """Test role change logging"""

    def test_log_role_change_success(self, mock_env):
        """Test successful role change logging"""
        with patch("app.services.user_management.create_client") as mock_create:
            mock_client = MockAdminClient()
            mock_create.return_value = mock_client

            service = UserManagementService()
            service.log_role_change(
                user_id=UUID(int=1),
                changed_by=UUID(int=2),
                old_role="author",
                new_role="managing_editor",
                reason="promotion",
            )
            # Should not raise

    def test_log_role_change_failure(self, mock_env, capsys, caplog):
        """Test role change logging failure"""
        caplog.set_level(logging.WARNING, logger="scholarflow.user_management")
        with patch("app.services.user_management.create_client") as mock_create:
            mock_query = MockQueryBuilder(raise_error=RuntimeError("DB error"))
            mock_client = MockAdminClient(mock_query)
            mock_create.return_value = mock_client

            service = UserManagementService()
            service.log_role_change(
                user_id=UUID(int=1),
                changed_by=UUID(int=2),
                old_role="author",
                new_role="managing_editor",
                reason="promotion",
            )

            captured = capsys.readouterr()
            combined = f"{caplog.text}\n{captured.out}\n{captured.err}"
            assert "Failed to log role change" in combined


class TestLogAccountCreation:
    """Test account creation logging"""

    def test_log_account_creation_success(self, mock_env):
        """Test successful account creation logging"""
        with patch("app.services.user_management.create_client") as mock_create:
            mock_client = MockAdminClient()
            mock_create.return_value = mock_client

            service = UserManagementService()
            service.log_account_creation(
                created_user_id=UUID(int=1),
                created_by=UUID(int=2),
                initial_role="reviewer",
            )
            # Should not raise

    def test_log_account_creation_failure(self, mock_env, capsys, caplog):
        """Test account creation logging failure"""
        caplog.set_level(logging.WARNING, logger="scholarflow.user_management")
        with patch("app.services.user_management.create_client") as mock_create:
            mock_query = MockQueryBuilder(raise_error=RuntimeError("DB error"))
            mock_client = MockAdminClient(mock_query)
            mock_create.return_value = mock_client

            service = UserManagementService()
            service.log_account_creation(
                created_user_id=UUID(int=1),
                created_by=UUID(int=2),
                initial_role="reviewer",
            )

            captured = capsys.readouterr()
            combined = f"{caplog.text}\n{captured.out}\n{captured.err}"
            assert "Failed to log account creation" in combined


class TestLogEmailNotification:
    """Test email notification logging"""

    def test_log_email_notification_success(self, mock_env):
        """Test successful email notification logging"""
        with patch("app.services.user_management.create_client") as mock_create:
            mock_client = MockAdminClient()
            mock_create.return_value = mock_client

            service = UserManagementService()
            service.log_email_notification(
                recipient_email="test@example.com",
                notification_type="welcome",
                status="sent",
            )
            # Should not raise

    def test_log_email_notification_with_error(self, mock_env):
        """Test email notification logging with error message"""
        with patch("app.services.user_management.create_client") as mock_create:
            mock_client = MockAdminClient()
            mock_create.return_value = mock_client

            service = UserManagementService()
            service.log_email_notification(
                recipient_email="test@example.com",
                notification_type="welcome",
                status="failed",
                error_message="SMTP timeout",
            )
            # Should not raise

    def test_log_email_notification_failure(self, mock_env, capsys, caplog):
        """Test email notification logging failure"""
        caplog.set_level(logging.WARNING, logger="scholarflow.user_management")
        with patch("app.services.user_management.create_client") as mock_create:
            mock_query = MockQueryBuilder(raise_error=RuntimeError("DB error"))
            mock_client = MockAdminClient(mock_query)
            mock_create.return_value = mock_client

            service = UserManagementService()
            service.log_email_notification(
                recipient_email="test@example.com",
                notification_type="welcome",
                status="sent",
            )

            captured = capsys.readouterr()
            combined = f"{caplog.text}\n{captured.out}\n{captured.err}"
            assert "Failed to log email notification" in combined


class TestGetUsers:
    """Test get users functionality"""

    def test_get_users_basic(self, mock_env):
        """Test basic user retrieval"""
        users_data = [
            {
                "id": "1",
                "email": "user1@test.com",
                "name": "User 1",
                "roles": ["author"],
                "created_at": "2024-01-01",
            }
        ]

        with patch("app.services.user_management.create_client") as mock_create:
            mock_query = MockQueryBuilder(return_data=users_data)
            mock_query._count = 1
            mock_client = MockAdminClient(mock_query)
            mock_create.return_value = mock_client

            service = UserManagementService()
            result = service.get_users()

            assert "data" in result
            assert "pagination" in result
            assert result["pagination"]["total"] == 1
            assert result["pagination"]["per_page"] == 25

    def test_get_users_with_filters(self, mock_env):
        """Test user retrieval with search and role filters"""
        users_data = [
            {
                "id": "1",
                "email": "editor@test.com",
                "name": "Editor",
                "roles": ["managing_editor"],
                "created_at": "2024-01-01",
            }
        ]

        with patch("app.services.user_management.create_client") as mock_create:
            mock_query = MockQueryBuilder(return_data=users_data)
            mock_query._count = 1
            mock_client = MockAdminClient(mock_query)
            mock_create.return_value = mock_client

            service = UserManagementService()
            result = service.get_users(
                page=1,
                per_page=10,
                search="editor",
                role="managing_editor",
            )

            assert "data" in result
            assert len(result["data"]) == 1

    def test_get_users_empty(self, mock_env):
        """Test user retrieval with empty result"""
        with patch("app.services.user_management.create_client") as mock_create:
            mock_query = MockQueryBuilder(return_data=[])
            mock_query._count = 0
            mock_client = MockAdminClient(mock_query)
            mock_create.return_value = mock_client

            service = UserManagementService()
            result = service.get_users()

            assert result["data"] == []
            assert result["pagination"]["total"] == 0
            assert result["pagination"]["total_pages"] == 0

    def test_get_users_pagination_applies_filter_before_paginating(self, mock_env):
        """默认隐藏测试 profile 时，应先过滤再分页。"""
        visible_users = [
            {
                "id": f"visible-{i}",
                "email": f"user{i}@test.com",
                "full_name": f"User {i}",
                "roles": ["author"],
                "created_at": "2024-01-01",
            }
            for i in range(8)
        ]
        hidden_users = [
            {
                "id": f"orphan-{i}",
                "email": f"editor_e2e_{i}@example.com",
                "full_name": f"Hidden User {i}",
                "roles": ["managing_editor"],
                "created_at": "2024-01-01",
            }
            for i in range(2)
        ]
        users_data = visible_users + hidden_users

        with patch("app.services.user_management.create_client") as mock_create:
            mock_query = MockQueryBuilder(return_data=users_data)
            mock_query._count = len(users_data)
            mock_client = MockAdminClient(mock_query)
            mock_client.auth.admin.list_users.return_value = []
            mock_create.return_value = mock_client

            service = UserManagementService()
            result = service.get_users(page=2, per_page=5)

            assert result["pagination"]["total"] == 8
            assert result["pagination"]["page"] == 2
            assert result["pagination"]["per_page"] == 5
            assert result["pagination"]["total_pages"] == 2
            assert len(result["data"]) == 3

    def test_get_users_pagination_with_include_test_profiles_uses_backend_count(self, mock_env):
        """显式包含测试 profile 时，应保留后端 count 语义。"""
        users_data = [
            {
                "id": str(i),
                "email": f"user{i}@test.com",
                "full_name": f"User {i}",
                "roles": ["author"],
                "created_at": "2024-01-01",
            }
            for i in range(5)
        ]

        with patch("app.services.user_management.create_client") as mock_create:
            mock_query = MockQueryBuilder(return_data=users_data)
            mock_query._count = 25
            mock_client = MockAdminClient(mock_query)
            mock_create.return_value = mock_client

            service = UserManagementService()
            result = service.get_users(page=2, per_page=5, include_test_profiles=True)

            assert result["pagination"]["total"] == 25
            assert result["pagination"]["page"] == 2
            assert result["pagination"]["per_page"] == 5
            assert result["pagination"]["total_pages"] == 5

    def test_get_users_error(self, mock_env):
        """Test user retrieval error handling"""
        with patch("app.services.user_management.create_client") as mock_create:
            mock_query = MockQueryBuilder(
                raise_error=RuntimeError("DB connection failed")
            )
            mock_client = MockAdminClient(mock_query)
            mock_create.return_value = mock_client

            service = UserManagementService()

            with pytest.raises(Exception) as exc_info:
                service.get_users()

            assert "Internal server error" in str(exc_info.value)

    def test_get_users_hides_orphan_example_profiles_by_default(self, mock_env):
        users_data = [
            {
                "id": "auth-user-1",
                "email": "real@test.com",
                "full_name": "Real User",
                "roles": ["author"],
                "created_at": "2024-01-02",
            },
            {
                "id": "orphan-user-1",
                "email": "editor_e2e@example.com",
                "full_name": "Orphan Test User",
                "roles": ["managing_editor"],
                "created_at": "2024-01-01",
            },
        ]

        with patch("app.services.user_management.create_client") as mock_create:
            mock_query = MockQueryBuilder(return_data=users_data)
            mock_query._count = 2
            mock_client = MockAdminClient(mock_query)
            mock_client.auth.admin.list_users.return_value = [type("AuthUser", (), {"id": "auth-user-1"})()]
            mock_create.return_value = mock_client

            service = UserManagementService()
            result = service.get_users()

            assert result["pagination"]["total"] == 1
            assert [item["email"] for item in result["data"]] == ["real@test.com"]

    def test_get_users_keeps_example_profile_when_auth_user_exists(self, mock_env):
        users_data = [
            {
                "id": "auth-user-1",
                "email": "real@example.com",
                "full_name": "Real Example User",
                "roles": ["author"],
                "created_at": "2024-01-02",
            },
            {
                "id": "orphan-user-1",
                "email": "editor_e2e@example.com",
                "full_name": "Orphan Test User",
                "roles": ["managing_editor"],
                "created_at": "2024-01-01",
            },
        ]

        with patch("app.services.user_management.create_client") as mock_create:
            mock_query = MockQueryBuilder(return_data=users_data)
            mock_query._count = 2
            mock_client = MockAdminClient(mock_query)
            mock_client.auth.admin.list_users.return_value = [
                type("AuthUser", (), {"id": "auth-user-1"})()
            ]
            mock_create.return_value = mock_client

            service = UserManagementService()
            result = service.get_users()

            assert result["pagination"]["total"] == 1
            assert [item["email"] for item in result["data"]] == ["real@example.com"]

    def test_get_users_can_include_hidden_test_profiles(self, mock_env):
        users_data = [
            {
                "id": "auth-user-1",
                "email": "real@test.com",
                "full_name": "Real User",
                "roles": ["author"],
                "created_at": "2024-01-02",
            },
            {
                "id": "orphan-user-1",
                "email": "editor_e2e@example.com",
                "full_name": "Orphan Test User",
                "roles": ["managing_editor"],
                "created_at": "2024-01-01",
            },
        ]

        with patch("app.services.user_management.create_client") as mock_create:
            mock_query = MockQueryBuilder(return_data=users_data)
            mock_query._count = 2
            mock_client = MockAdminClient(mock_query)
            mock_create.return_value = mock_client

            service = UserManagementService()
            result = service.get_users(include_test_profiles=True)

            assert result["pagination"]["total"] == 2
            assert [item["email"] for item in result["data"]] == ["real@test.com", "editor_e2e@example.com"]


class TestUpdateUserRole:
    """Test role update functionality"""

    def test_update_role_success(self, mock_env):
        """Test successful role update"""
        user_data = {
            "id": "user-1",
            "email": "user@test.com",
            "name": "Test User",
            "roles": ["author"],
            "created_at": "2024-01-01",
        }
        updated_data = {
            "id": "user-1",
            "email": "user@test.com",
            "name": "Test User",
            "roles": ["managing_editor"],
            "created_at": "2024-01-01",
        }

        with patch("app.services.user_management.create_client") as mock_create:
            # Create a more sophisticated mock
            mock_client = MagicMock()

            # First call: select for checking user exists
            select_response = MockSupabaseResponse(data=user_data)
            # Second call: update
            update_response = MockSupabaseResponse(data=[updated_data])
            # Third call: insert log
            log_response = MockSupabaseResponse(data=[{}])

            call_count = [0]

            def table_side_effect(name):
                mock_table = MagicMock()
                mock_table.select.return_value = mock_table
                mock_table.update.return_value = mock_table
                mock_table.insert.return_value = mock_table
                mock_table.eq.return_value = mock_table
                mock_table.single.return_value = mock_table

                if name == "user_profiles":
                    if call_count[0] == 0:
                        mock_table.execute.return_value = select_response
                    else:
                        mock_table.execute.return_value = update_response
                    call_count[0] += 1
                else:
                    mock_table.execute.return_value = log_response
                return mock_table

            mock_client.table.side_effect = table_side_effect
            mock_create.return_value = mock_client

            service = UserManagementService()
            result = service.update_user_role(
                target_user_id=UUID("00000000-0000-0000-0000-000000000001"),
                new_role="managing_editor",
                reason="Promotion",
                changed_by=UUID("00000000-0000-0000-0000-000000000002"),
            )

            assert result["roles"] == ["managing_editor"]

    def test_update_role_self_addition_allowed(self, mock_env):
        """Test self role update allows additive-only changes"""
        user_data = {
            "id": "user-1",
            "email": "user@test.com",
            "name": "Test User",
            "roles": ["admin"],
            "created_at": "2024-01-01",
        }
        updated_data = {
            "id": "user-1",
            "email": "user@test.com",
            "name": "Test User",
            "roles": ["admin", "managing_editor"],
            "created_at": "2024-01-01",
        }

        with patch("app.services.user_management.create_client") as mock_create:
            mock_client = MagicMock()
            select_response = MockSupabaseResponse(data=user_data)
            update_response = MockSupabaseResponse(data=[updated_data])
            log_response = MockSupabaseResponse(data=[{}])
            call_count = [0]

            def table_side_effect(name):
                mock_table = MagicMock()
                mock_table.select.return_value = mock_table
                mock_table.update.return_value = mock_table
                mock_table.insert.return_value = mock_table
                mock_table.eq.return_value = mock_table
                mock_table.single.return_value = mock_table
                if name == "user_profiles":
                    if call_count[0] == 0:
                        mock_table.execute.return_value = select_response
                    else:
                        mock_table.execute.return_value = update_response
                    call_count[0] += 1
                else:
                    mock_table.execute.return_value = log_response
                return mock_table

            mock_client.table.side_effect = table_side_effect
            mock_create.return_value = mock_client

            service = UserManagementService()
            user_id = UUID("00000000-0000-0000-0000-000000000001")
            result = service.update_user_role(
                target_user_id=user_id,
                new_role=None,
                new_roles=["admin", "managing_editor"],
                reason="Self add editor role",
                changed_by=user_id,  # Same user
            )

            assert result["roles"] == ["admin", "managing_editor"]

    def test_update_role_self_remove_admin_forbidden(self, mock_env):
        """Test self role update cannot remove own admin role"""
        user_data = {
            "id": "user-1",
            "email": "user@test.com",
            "name": "Test User",
            "roles": ["admin", "managing_editor"],
            "created_at": "2024-01-01",
        }

        with patch("app.services.user_management.create_client") as mock_create:
            mock_client = MagicMock()
            mock_table = MagicMock()
            mock_table.select.return_value = mock_table
            mock_table.eq.return_value = mock_table
            mock_table.single.return_value = mock_table
            mock_table.execute.return_value = MockSupabaseResponse(data=user_data)
            mock_client.table.return_value = mock_table
            mock_create.return_value = mock_client

            service = UserManagementService()
            user_id = UUID("00000000-0000-0000-0000-000000000001")

            with pytest.raises(ValueError) as exc_info:
                service.update_user_role(
                    target_user_id=user_id,
                    new_role=None,
                    new_roles=["managing_editor"],
                    reason="Self remove admin role",
                    changed_by=user_id,  # Same user
                )

            assert "Cannot remove your own admin role" in str(exc_info.value)

    def test_update_role_self_remove_non_admin_forbidden(self, mock_env):
        """Test self role update cannot remove existing non-admin roles either"""
        user_data = {
            "id": "user-1",
            "email": "user@test.com",
            "name": "Test User",
            "roles": ["author", "reviewer"],
            "created_at": "2024-01-01",
        }

        with patch("app.services.user_management.create_client") as mock_create:
            mock_client = MagicMock()
            mock_table = MagicMock()
            mock_table.select.return_value = mock_table
            mock_table.eq.return_value = mock_table
            mock_table.single.return_value = mock_table
            mock_table.execute.return_value = MockSupabaseResponse(data=user_data)
            mock_client.table.return_value = mock_table
            mock_create.return_value = mock_client

            service = UserManagementService()
            user_id = UUID("00000000-0000-0000-0000-000000000001")

            with pytest.raises(ValueError) as exc_info:
                service.update_user_role(
                    target_user_id=user_id,
                    new_role=None,
                    new_roles=["author"],
                    reason="Self remove reviewer role",
                    changed_by=user_id,  # Same user
                )

            assert "You can only add roles to yourself" in str(exc_info.value)

    def test_update_role_user_not_found(self, mock_env):
        """Test role update for non-existent user"""
        with patch("app.services.user_management.create_client") as mock_create:
            mock_client = MagicMock()
            mock_table = MagicMock()
            mock_table.select.return_value = mock_table
            mock_table.eq.return_value = mock_table
            mock_table.single.return_value = mock_table
            mock_table.execute.return_value = MockSupabaseResponse(data=None)
            mock_client.table.return_value = mock_table
            mock_create.return_value = mock_client

            service = UserManagementService()

            with pytest.raises(ValueError) as exc_info:
                service.update_user_role(
                    target_user_id=UUID("00000000-0000-0000-0000-000000000001"),
                    new_role="managing_editor",
                    reason="Promotion",
                    changed_by=UUID("00000000-0000-0000-0000-000000000002"),
                )

            assert "User not found" in str(exc_info.value)


class TestResetUserPassword:
    """Test admin reset password functionality"""

    def test_reset_password_success(self, mock_env):
        with patch("app.services.user_management.create_client") as mock_create:
            mock_client = MagicMock()
            mock_table = MagicMock()
            mock_table.select.return_value = mock_table
            mock_table.eq.return_value = mock_table
            mock_table.maybe_single.return_value = mock_table
            mock_table.execute.return_value = MockSupabaseResponse(
                data={"id": "user-1", "email": "user@test.com", "full_name": "Test User"}
            )
            mock_client.table.return_value = mock_table
            mock_client.auth.admin.get_user_by_id.return_value = MagicMock(
                user=MagicMock(user_metadata={"must_change_password": True})
            )
            mock_create.return_value = mock_client

            with patch(
                "app.services.user_management.UserManagementService._send_inline_email",
                return_value=(True, None),
            ), patch(
                "app.services.user_management.UserManagementService._load_email_template",
                return_value={
                    "template_key": "admin_password_reset_link",
                    "subject_template": "Reset",
                    "body_html_template": "<p>{{ default_password }}</p>",
                    "body_text_template": "Reset {{ default_password }}",
                },
            ):
                service = UserManagementService()
                result = service.reset_user_password(
                    target_user_id=UUID("00000000-0000-0000-0000-000000000001"),
                    changed_by=UUID("00000000-0000-0000-0000-000000000002"),
                )

            assert result["reset_link_sent"] is False
            assert result["delivery_status"] == "sent"
            assert result["must_change_password"] is False
            assert result["temporary_password"] == "12345678"
            mock_client.auth.admin.update_user_by_id.assert_called_once()

    def test_reset_password_delivery_failed(self, mock_env):
        with patch("app.services.user_management.create_client") as mock_create:
            mock_client = MagicMock()
            mock_table = MagicMock()
            mock_table.select.return_value = mock_table
            mock_table.eq.return_value = mock_table
            mock_table.maybe_single.return_value = mock_table
            mock_table.execute.return_value = MockSupabaseResponse(
                data={"id": "user-1", "email": "user@test.com", "full_name": "Test User"}
            )
            mock_client.table.return_value = mock_table
            mock_client.auth.admin.get_user_by_id.return_value = MagicMock(
                user=MagicMock(user_metadata={})
            )
            mock_create.return_value = mock_client

            with patch(
                "app.services.user_management.UserManagementService._send_inline_email",
                return_value=(False, "Resend domain is not verified"),
            ), patch(
                "app.services.user_management.UserManagementService._load_email_template",
                return_value={
                    "template_key": "admin_password_reset_link",
                    "subject_template": "Reset",
                    "body_html_template": "<p>{{ default_password }}</p>",
                    "body_text_template": "Reset {{ default_password }}",
                },
            ):
                service = UserManagementService()
                result = service.reset_user_password(
                    target_user_id=UUID("00000000-0000-0000-0000-000000000001"),
                    changed_by=UUID("00000000-0000-0000-0000-000000000002"),
                )
            assert result["reset_link_sent"] is False
            assert result["delivery_status"] == "pending_retry"
            assert result["temporary_password"] == "12345678"
            mock_client.auth.admin.update_user_by_id.assert_called_once()

    def test_reset_password_user_not_found(self, mock_env):
        with patch("app.services.user_management.create_client") as mock_create:
            mock_client = MagicMock()
            mock_table = MagicMock()
            mock_table.select.return_value = mock_table
            mock_table.eq.return_value = mock_table
            mock_table.maybe_single.return_value = mock_table
            mock_table.execute.return_value = MockSupabaseResponse(data=None)
            mock_client.table.return_value = mock_table
            mock_create.return_value = mock_client

            service = UserManagementService()
            with pytest.raises(ValueError) as exc_info:
                service.reset_user_password(
                    target_user_id=UUID("00000000-0000-0000-0000-000000000001"),
                    changed_by=UUID("00000000-0000-0000-0000-000000000002"),
                )
            assert "User not found" in str(exc_info.value)


class TestGetRoleChanges:
    """Test role change history retrieval"""

    def test_get_role_changes_success(self, mock_env):
        """Test successful role change history retrieval"""
        logs_data = [
            {
                "user_id": "1",
                "old_role": "author",
                "new_role": "managing_editor",
                "created_at": "2024-01-01",
            }
        ]

        with patch("app.services.user_management.create_client") as mock_create:
            mock_query = MockQueryBuilder(return_data=logs_data)
            mock_client = MockAdminClient(mock_query)
            mock_create.return_value = mock_client

            service = UserManagementService()
            result = service.get_role_changes(UUID(int=1))

            assert len(result) == 1

    def test_get_role_changes_empty(self, mock_env):
        """Test role change history for user with no changes"""
        with patch("app.services.user_management.create_client") as mock_create:
            mock_query = MockQueryBuilder(return_data=[])
            mock_client = MockAdminClient(mock_query)
            mock_create.return_value = mock_client

            service = UserManagementService()
            result = service.get_role_changes(UUID(int=1))

            assert result == []

    def test_get_role_changes_error(self, mock_env, capsys, caplog):
        """Test role change history retrieval error"""
        caplog.set_level(logging.WARNING, logger="scholarflow.user_management")
        with patch("app.services.user_management.create_client") as mock_create:
            mock_query = MockQueryBuilder(raise_error=RuntimeError("DB error"))
            mock_client = MockAdminClient(mock_query)
            mock_create.return_value = mock_client

            service = UserManagementService()
            result = service.get_role_changes(UUID(int=1))

            assert result == []
            captured = capsys.readouterr()
            combined = f"{caplog.text}\n{captured.out}\n{captured.err}"
            assert "Failed to fetch role history" in combined


class TestCreateInternalUser:
    """Test internal user creation"""

    def test_create_internal_user_success(self, mock_env, capsys, caplog):
        """Test successful internal user creation"""
        caplog.set_level(logging.INFO, logger="scholarflow.user_management")
        with patch("app.services.user_management.create_client") as mock_create:
            mock_client = MagicMock()

            # Mock auth.admin.create_user
            mock_user = MagicMock()
            mock_user.id = "00000000-0000-0000-0000-000000000099"  # Valid UUID
            mock_auth_response = MagicMock()
            mock_auth_response.user = mock_user
            mock_client.auth.admin.create_user.return_value = mock_auth_response
            mock_link_response = MagicMock()
            mock_link_response.properties = {
                "action_link": "https://test.com/onboarding-link"
            }
            mock_client.auth.admin.generate_link.return_value = mock_link_response

            # Mock table operations
            mock_table = MagicMock()
            mock_table.select.return_value = mock_table
            mock_table.ilike.return_value = mock_table
            mock_table.execute.return_value = MockSupabaseResponse(
                data=None
            )  # No existing user
            mock_table.upsert.return_value = mock_table
            mock_table.insert.return_value = mock_table
            mock_client.table.return_value = mock_table

            mock_create.return_value = mock_client

            with patch("app.services.user_management.email_service.is_configured", return_value=True), patch(
                "app.services.user_management.email_service.send_email", return_value=True
            ):
                service = UserManagementService()
                result = service.create_internal_user(
                    email="newuser@test.com",
                    full_name="New User",
                    role="managing_editor",
                    created_by=UUID("00000000-0000-0000-0000-000000000001"),
                )

            assert result["email"] == "newuser@test.com"
            assert result["roles"] == ["managing_editor"]

            # Verify console output
            captured = capsys.readouterr()
            combined = f"{caplog.text}\n{captured.out}\n{captured.err}".lower()
            assert "internal user created" in combined

    def test_create_internal_user_already_exists(self, mock_env):
        """Test user creation when email already exists"""
        with patch("app.services.user_management.create_client") as mock_create:
            mock_client = MagicMock()
            mock_table = MagicMock()
            mock_table.select.return_value = mock_table
            mock_table.ilike.return_value = mock_table
            mock_table.execute.return_value = MockSupabaseResponse(
                data={"id": "existing"}
            )
            mock_client.table.return_value = mock_table
            mock_create.return_value = mock_client

            service = UserManagementService()

            with pytest.raises(ValueError) as exc_info:
                service.create_internal_user(
                    email="existing@test.com",
                    full_name="Existing User",
                    role="managing_editor",
                    created_by=UUID("00000000-0000-0000-0000-000000000001"),
                )

            assert "already exists" in str(exc_info.value)

    def test_create_internal_user_normalizes_email_before_uniqueness_check(self, mock_env):
        with patch("app.services.user_management.create_client") as mock_create:
            mock_client = MagicMock()
            mock_table = MagicMock()
            mock_table.select.return_value = mock_table
            mock_table.ilike.return_value = mock_table
            mock_table.execute.return_value = MockSupabaseResponse(data=[{"id": "existing"}])
            mock_client.table.return_value = mock_table
            mock_create.return_value = mock_client

            service = UserManagementService()

            with pytest.raises(ValueError) as exc_info:
                service.create_internal_user(
                    email=" Existing@Test.COM ",
                    full_name="Existing User",
                    role="managing_editor",
                    created_by=UUID("00000000-0000-0000-0000-000000000001"),
                )

            assert "already exists" in str(exc_info.value)
            mock_table.ilike.assert_called_once_with("email", "existing@test.com")

    def test_create_internal_user_auth_fails(self, mock_env):
        """Test user creation when auth fails"""
        with patch("app.services.user_management.create_client") as mock_create:
            mock_client = MagicMock()
            mock_table = MagicMock()
            mock_table.select.return_value = mock_table
            mock_table.ilike.return_value = mock_table
            mock_table.execute.return_value = MockSupabaseResponse(data=None)
            mock_client.table.return_value = mock_table

            # Auth returns no user
            mock_auth_response = MagicMock()
            mock_auth_response.user = None
            mock_client.auth.admin.create_user.return_value = mock_auth_response

            mock_create.return_value = mock_client

            service = UserManagementService()

            with pytest.raises(Exception) as exc_info:
                service.create_internal_user(
                    email="new@test.com",
                    full_name="New User",
                    role="managing_editor",
                    created_by=UUID("00000000-0000-0000-0000-000000000001"),
                )

            assert "Failed to create user" in str(
                exc_info.value
            ) or "Internal error" in str(exc_info.value)


class TestInviteReviewer:
    """Test reviewer invitation"""

    def test_invite_reviewer_success(self, mock_env, capsys, caplog):
        """Test successful reviewer invitation"""
        caplog.set_level(logging.INFO, logger="scholarflow.user_management")
        with patch("app.services.user_management.create_client") as mock_create:
            mock_client = MagicMock()

            # Mock table for checking existence
            mock_table = MagicMock()
            mock_table.select.return_value = mock_table
            mock_table.ilike.return_value = mock_table
            mock_table.execute.return_value = MockSupabaseResponse(data=None)
            mock_table.upsert.return_value = mock_table
            mock_table.insert.return_value = mock_table
            mock_client.table.return_value = mock_table

            # Mock auth.admin.create_user
            mock_user = MagicMock()
            mock_user.id = "00000000-0000-0000-0000-000000000098"  # Valid UUID
            mock_auth_response = MagicMock()
            mock_auth_response.user = mock_user
            mock_client.auth.admin.create_user.return_value = mock_auth_response
            mock_client.auth.admin.get_user_by_id.return_value = MagicMock(
                user=MagicMock(user_metadata={"sf_reviewer_activation_required": True})
            )

            # Mock generate_link
            mock_link_response = MagicMock()
            mock_link_response.properties = {
                "action_link": "https://test.com/magic-link"
            }
            mock_client.auth.admin.generate_link.return_value = mock_link_response

            mock_create.return_value = mock_client

            with patch.object(
                UserManagementService,
                "_load_email_template",
                return_value={
                    "body_html_template": "<p>{{ activation_link }}</p>",
                    "body_text_template": "{{ activation_link }}",
                    "subject_template": "Reviewer activation",
                },
            ), patch("app.services.user_management.email_service.is_configured", return_value=True), patch(
                "app.services.user_management.email_service.send_email", return_value=True
            ) as mock_send_email:
                service = UserManagementService()
                result = service.invite_reviewer(
                    email="reviewer@test.com",
                    full_name="New Reviewer",
                    invited_by=UUID("00000000-0000-0000-0000-000000000001"),
                )

            assert result["email"] == "reviewer@test.com"
            assert result["roles"] == ["reviewer"]
            create_payload = mock_client.auth.admin.create_user.call_args.args[0]
            assert "password" not in create_payload
            assert create_payload["email_confirm"] is True
            assert create_payload["user_metadata"]["sf_reviewer_activation_required"] is True
            mock_client.auth.admin.generate_link.assert_called_once()
            html_body = mock_send_email.call_args.kwargs["html_body"]
            assert "Default password" not in html_body
            assert "https://test.com/magic-link" in html_body

            captured = capsys.readouterr()
            combined = f"{caplog.text}\n{captured.out}\n{captured.err}".lower()
            assert "reviewer activation link generated" in combined

    def test_invite_reviewer_already_exists(self, mock_env):
        """Test invite when reviewer already exists"""
        with patch("app.services.user_management.create_client") as mock_create:
            mock_client = MagicMock()
            mock_table = MagicMock()
            mock_table.select.return_value = mock_table
            mock_table.ilike.return_value = mock_table
            mock_table.execute.return_value = MockSupabaseResponse(
                data={"id": "existing"}
            )
            mock_client.table.return_value = mock_table
            mock_create.return_value = mock_client

            service = UserManagementService()

            with pytest.raises(ValueError) as exc_info:
                service.invite_reviewer(
                    email="existing@test.com",
                    full_name="Existing Reviewer",
                    invited_by=UUID("00000000-0000-0000-0000-000000000001"),
                )

            assert "already exists" in str(exc_info.value)

    def test_invite_reviewer_normalizes_email_before_auth_create(self, mock_env):
        with patch("app.services.user_management.create_client") as mock_create:
            mock_client = MagicMock()
            mock_table = MagicMock()
            mock_table.select.return_value = mock_table
            mock_table.ilike.return_value = mock_table
            mock_table.execute.return_value = MockSupabaseResponse(data=None)
            mock_table.upsert.return_value = mock_table
            mock_table.insert.return_value = mock_table
            mock_client.table.return_value = mock_table

            mock_user = MagicMock()
            mock_user.id = "00000000-0000-0000-0000-000000000098"
            mock_auth_response = MagicMock()
            mock_auth_response.user = mock_user
            mock_client.auth.admin.create_user.return_value = mock_auth_response
            mock_client.auth.admin.get_user_by_id.return_value = MagicMock(
                user=MagicMock(user_metadata={"sf_reviewer_activation_required": True})
            )
            mock_link_response = MagicMock()
            mock_link_response.properties = {"action_link": "https://test.com/magic-link"}
            mock_client.auth.admin.generate_link.return_value = mock_link_response
            mock_create.return_value = mock_client

            with patch.object(
                UserManagementService,
                "_load_email_template",
                return_value={
                    "body_html_template": "<p>{{ activation_link }}</p>",
                    "body_text_template": "{{ activation_link }}",
                    "subject_template": "Reviewer activation",
                },
            ), patch("app.services.user_management.email_service.is_configured", return_value=True), patch(
                "app.services.user_management.email_service.send_email", return_value=True
            ):
                service = UserManagementService()
                result = service.invite_reviewer(
                    email=" Reviewer@Test.COM ",
                    full_name="New Reviewer",
                    invited_by=UUID("00000000-0000-0000-0000-000000000001"),
                )

            assert result["email"] == "reviewer@test.com"
            create_payload = mock_client.auth.admin.create_user.call_args.args[0]
            assert create_payload["email"] == "reviewer@test.com"
            mock_table.ilike.assert_called_once_with("email", "reviewer@test.com")

    def test_invite_reviewer_auth_fails(self, mock_env):
        """Test invite when auth user creation fails"""
        with patch("app.services.user_management.create_client") as mock_create:
            mock_client = MagicMock()
            mock_table = MagicMock()
            mock_table.select.return_value = mock_table
            mock_table.ilike.return_value = mock_table
            mock_table.execute.return_value = MockSupabaseResponse(data=None)
            mock_client.table.return_value = mock_table

            # Auth returns no user
            mock_auth_response = MagicMock()
            mock_auth_response.user = None
            mock_client.auth.admin.create_user.return_value = mock_auth_response

            mock_create.return_value = mock_client

            service = UserManagementService()

            with pytest.raises(Exception) as exc_info:
                service.invite_reviewer(
                    email="new@test.com",
                    full_name="New Reviewer",
                    invited_by=UUID("00000000-0000-0000-0000-000000000001"),
                )

            assert "Failed to create reviewer user" in str(
                exc_info.value
            ) or "Internal error" in str(exc_info.value)
