"""
Tests for UserManagementService
Coverage target: 80%+
"""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from uuid import UUID
from datetime import datetime

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
            service = UserManagementService()

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

    def test_log_role_change_failure(self, mock_env, capsys):
        """Test role change logging failure"""
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
            assert "Failed to log role change" in captured.out


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

    def test_log_account_creation_failure(self, mock_env, capsys):
        """Test account creation logging failure"""
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
            assert "Failed to log account creation" in captured.out


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

    def test_log_email_notification_failure(self, mock_env, capsys):
        """Test email notification logging failure"""
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
            assert "Failed to log email notification" in captured.out


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

    def test_get_users_pagination(self, mock_env):
        """Test user retrieval with pagination"""
        users_data = [
            {
                "id": str(i),
                "email": f"user{i}@test.com",
                "name": f"User {i}",
                "roles": ["author"],
                "created_at": "2024-01-01",
            }
            for i in range(5)
        ]

        with patch("app.services.user_management.create_client") as mock_create:
            mock_query = MockQueryBuilder(return_data=users_data)
            mock_query._count = 25  # Total count
            mock_client = MockAdminClient(mock_query)
            mock_create.return_value = mock_client

            service = UserManagementService()
            result = service.get_users(page=2, per_page=5)

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
                data={"id": "user-1", "email": "user@test.com"}
            )
            mock_client.table.return_value = mock_table
            mock_client.auth.admin.update_user_by_id.return_value = MagicMock()
            mock_create.return_value = mock_client

            service = UserManagementService()
            result = service.reset_user_password(
                target_user_id=UUID("00000000-0000-0000-0000-000000000001"),
                changed_by=UUID("00000000-0000-0000-0000-000000000002"),
                temporary_password="12345678",
            )

            assert result["temporary_password"] == "12345678"
            assert result["must_change_password"] is True
            mock_client.auth.admin.update_user_by_id.assert_called_once()

    def test_reset_password_short_password(self, mock_env):
        with patch("app.services.user_management.create_client") as mock_create:
            mock_client = MagicMock()
            mock_create.return_value = mock_client

            service = UserManagementService()
            with pytest.raises(ValueError) as exc_info:
                service.reset_user_password(
                    target_user_id=UUID("00000000-0000-0000-0000-000000000001"),
                    changed_by=UUID("00000000-0000-0000-0000-000000000002"),
                    temporary_password="123",
                )
            assert "at least 8 characters" in str(exc_info.value)

    def test_reset_password_user_not_found(self, mock_env):
        with patch("app.services.user_management.create_client") as mock_create:
            mock_client = MagicMock()
            mock_table = MagicMock()
            mock_table.select.return_value = mock_table
            mock_table.eq.return_value = mock_table
            mock_table.maybe_single.return_value = mock_table
            mock_table.execute.return_value = MockSupabaseResponse(data=None)
            mock_client.table.return_value = mock_table
            mock_client.auth.admin.update_user_by_id.side_effect = Exception("User not found")
            mock_create.return_value = mock_client

            service = UserManagementService()
            with pytest.raises(ValueError) as exc_info:
                service.reset_user_password(
                    target_user_id=UUID("00000000-0000-0000-0000-000000000001"),
                    changed_by=UUID("00000000-0000-0000-0000-000000000002"),
                    temporary_password="12345678",
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

    def test_get_role_changes_error(self, mock_env, capsys):
        """Test role change history retrieval error"""
        with patch("app.services.user_management.create_client") as mock_create:
            mock_query = MockQueryBuilder(raise_error=RuntimeError("DB error"))
            mock_client = MockAdminClient(mock_query)
            mock_create.return_value = mock_client

            service = UserManagementService()
            result = service.get_role_changes(UUID(int=1))

            assert result == []
            captured = capsys.readouterr()
            assert "Failed to fetch role history" in captured.out


class TestCreateInternalUser:
    """Test internal user creation"""

    def test_create_internal_user_success(self, mock_env, capsys):
        """Test successful internal user creation"""
        with patch("app.services.user_management.create_client") as mock_create:
            mock_client = MagicMock()

            # Mock auth.admin.create_user
            mock_user = MagicMock()
            mock_user.id = "00000000-0000-0000-0000-000000000099"  # Valid UUID
            mock_auth_response = MagicMock()
            mock_auth_response.user = mock_user
            mock_client.auth.admin.create_user.return_value = mock_auth_response

            # Mock table operations
            mock_table = MagicMock()
            mock_table.select.return_value = mock_table
            mock_table.eq.return_value = mock_table
            mock_table.maybe_single.return_value = mock_table
            mock_table.execute.return_value = MockSupabaseResponse(
                data=None
            )  # No existing user
            mock_table.upsert.return_value = mock_table
            mock_table.insert.return_value = mock_table
            mock_client.table.return_value = mock_table

            mock_create.return_value = mock_client

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
            assert "internal user created" in captured.out.lower()

    def test_create_internal_user_already_exists(self, mock_env):
        """Test user creation when email already exists"""
        with patch("app.services.user_management.create_client") as mock_create:
            mock_client = MagicMock()
            mock_table = MagicMock()
            mock_table.select.return_value = mock_table
            mock_table.eq.return_value = mock_table
            mock_table.maybe_single.return_value = mock_table
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

    def test_create_internal_user_auth_fails(self, mock_env):
        """Test user creation when auth fails"""
        with patch("app.services.user_management.create_client") as mock_create:
            mock_client = MagicMock()
            mock_table = MagicMock()
            mock_table.select.return_value = mock_table
            mock_table.eq.return_value = mock_table
            mock_table.maybe_single.return_value = mock_table
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

    def test_invite_reviewer_success(self, mock_env, capsys):
        """Test successful reviewer invitation"""
        with patch("app.services.user_management.create_client") as mock_create:
            mock_client = MagicMock()

            # Mock table for checking existence
            mock_table = MagicMock()
            mock_table.select.return_value = mock_table
            mock_table.eq.return_value = mock_table
            mock_table.maybe_single.return_value = mock_table
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

            # Mock generate_link
            mock_link_response = MagicMock()
            mock_link_response.properties = {
                "action_link": "https://test.com/magic-link"
            }
            mock_client.auth.admin.generate_link.return_value = mock_link_response

            mock_create.return_value = mock_client

            service = UserManagementService()
            result = service.invite_reviewer(
                email="reviewer@test.com",
                full_name="New Reviewer",
                invited_by=UUID("00000000-0000-0000-0000-000000000001"),
            )

            assert result["email"] == "reviewer@test.com"
            assert result["roles"] == ["reviewer"]

            captured = capsys.readouterr()
            assert "reviewer invite link generated" in captured.out.lower()

    def test_invite_reviewer_already_exists(self, mock_env):
        """Test invite when reviewer already exists"""
        with patch("app.services.user_management.create_client") as mock_create:
            mock_client = MagicMock()
            mock_table = MagicMock()
            mock_table.select.return_value = mock_table
            mock_table.eq.return_value = mock_table
            mock_table.maybe_single.return_value = mock_table
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

    def test_invite_reviewer_auth_fails(self, mock_env):
        """Test invite when auth user creation fails"""
        with patch("app.services.user_management.create_client") as mock_create:
            mock_client = MagicMock()
            mock_table = MagicMock()
            mock_table.select.return_value = mock_table
            mock_table.eq.return_value = mock_table
            mock_table.maybe_single.return_value = mock_table
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

            assert "Failed to create shadow user" in str(
                exc_info.value
            ) or "Internal error" in str(exc_info.value)
