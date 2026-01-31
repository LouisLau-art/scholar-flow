"""
Tests for UserService
Coverage target: 80%+
"""

import pytest
from unittest.mock import MagicMock, patch
from uuid import UUID
from datetime import datetime, timezone

from app.services.user_service import UserService
from app.schemas.user import UserProfileUpdate


class MockSupabaseResponse:
    """Mock Supabase response"""

    def __init__(self, data=None):
        self.data = data


class MockQueryBuilder:
    """Mock Supabase query builder chain"""

    def __init__(self, return_data=None, raise_error=None):
        self._data = return_data
        self._raise_error = raise_error

    def update(self, data):
        return self

    def insert(self, data):
        return self

    def eq(self, *args):
        return self

    def execute(self):
        if self._raise_error:
            raise self._raise_error
        return MockSupabaseResponse(data=self._data)


class TestUserServiceUpdateProfile:
    """Test profile update functionality"""

    def test_update_profile_success(self):
        """Test successful profile update"""
        updated_data = {
            "id": "user-1",
            "email": "test@example.com",
            "full_name": "Updated Name",
            "affiliation": "Test University",
        }

        with patch(
            "app.services.user_service.create_user_supabase_client"
        ) as mock_create:
            mock_client = MagicMock()
            mock_table = MagicMock()
            mock_table.update.return_value = mock_table
            mock_table.eq.return_value = mock_table
            mock_table.execute.return_value = MockSupabaseResponse(data=[updated_data])
            mock_client.table.return_value = mock_table
            mock_create.return_value = mock_client

            service = UserService()
            update_data = UserProfileUpdate(
                full_name="Updated Name", affiliation="Test University"
            )

            result = service.update_profile(
                user_id=UUID("00000000-0000-0000-0000-000000000001"),
                update_data=update_data,
                access_token="test-token",
            )

            assert result["full_name"] == "Updated Name"

    def test_update_profile_with_urls(self):
        """Test profile update with URL fields"""
        updated_data = {
            "id": "user-1",
            "google_scholar_url": "https://scholar.google.com/user",
            "avatar_url": "https://example.com/avatar.jpg",
        }

        with patch(
            "app.services.user_service.create_user_supabase_client"
        ) as mock_create:
            mock_client = MagicMock()
            mock_table = MagicMock()
            mock_table.update.return_value = mock_table
            mock_table.eq.return_value = mock_table
            mock_table.execute.return_value = MockSupabaseResponse(data=[updated_data])
            mock_client.table.return_value = mock_table
            mock_create.return_value = mock_client

            service = UserService()
            update_data = UserProfileUpdate(
                google_scholar_url="https://scholar.google.com/user",
                avatar_url="https://example.com/avatar.jpg",
            )

            result = service.update_profile(
                user_id=UUID("00000000-0000-0000-0000-000000000001"),
                update_data=update_data,
                access_token="test-token",
            )

            assert "google_scholar_url" in result

    def test_update_profile_creates_new_if_not_exists(self):
        """Test profile creation when update returns no rows"""
        new_profile = {
            "id": "user-1",
            "email": "new@example.com",
            "full_name": "New User",
        }

        with patch(
            "app.services.user_service.create_user_supabase_client"
        ) as mock_create:
            mock_client = MagicMock()
            mock_table = MagicMock()

            # First call: update returns empty
            # Second call: insert returns new profile
            call_count = [0]

            def execute_side_effect():
                call_count[0] += 1
                if call_count[0] == 1:
                    return MockSupabaseResponse(data=[])  # Empty on update
                return MockSupabaseResponse(data=[new_profile])  # Success on insert

            mock_table.update.return_value = mock_table
            mock_table.insert.return_value = mock_table
            mock_table.eq.return_value = mock_table
            mock_table.execute.side_effect = execute_side_effect
            mock_client.table.return_value = mock_table
            mock_create.return_value = mock_client

            service = UserService()
            update_data = UserProfileUpdate(full_name="New User")

            result = service.update_profile(
                user_id=UUID("00000000-0000-0000-0000-000000000001"),
                update_data=update_data,
                access_token="test-token",
                email="new@example.com",
            )

            assert result["email"] == "new@example.com"

    def test_update_profile_no_email_for_new(self):
        """Test that email is required for creating new profile"""
        with patch(
            "app.services.user_service.create_user_supabase_client"
        ) as mock_create:
            mock_client = MagicMock()
            mock_table = MagicMock()
            mock_table.update.return_value = mock_table
            mock_table.eq.return_value = mock_table
            mock_table.execute.return_value = MockSupabaseResponse(
                data=[]
            )  # Empty = no rows updated
            mock_client.table.return_value = mock_table
            mock_create.return_value = mock_client

            service = UserService()
            update_data = UserProfileUpdate(full_name="New User")

            with pytest.raises(ValueError) as exc_info:
                service.update_profile(
                    user_id=UUID("00000000-0000-0000-0000-000000000001"),
                    update_data=update_data,
                    access_token="test-token",
                    # No email provided
                )

            assert "Email required" in str(exc_info.value)

    def test_update_profile_error(self, capsys):
        """Test profile update error handling"""
        with patch(
            "app.services.user_service.create_user_supabase_client"
        ) as mock_create:
            mock_client = MagicMock()
            mock_table = MagicMock()
            mock_table.update.return_value = mock_table
            mock_table.eq.return_value = mock_table
            mock_table.execute.side_effect = RuntimeError("DB connection failed")
            mock_client.table.return_value = mock_table
            mock_create.return_value = mock_client

            service = UserService()
            update_data = UserProfileUpdate(full_name="Test")

            with pytest.raises(RuntimeError):
                service.update_profile(
                    user_id=UUID("00000000-0000-0000-0000-000000000001"),
                    update_data=update_data,
                    access_token="test-token",
                )

            captured = capsys.readouterr()
            assert "Error updating profile" in captured.out


class TestUserServiceChangePassword:
    """Test password change functionality"""

    def test_change_password_success(self):
        """Test successful password change"""
        with patch("app.services.user_service.supabase_admin") as mock_admin:
            mock_admin.auth.admin.update_user_by_id.return_value = MagicMock()

            service = UserService()
            result = service.change_password(
                user_id=UUID("00000000-0000-0000-0000-000000000001"),
                new_password="NewSecurePassword123!",
            )

            assert result is True
            mock_admin.auth.admin.update_user_by_id.assert_called_once()

    def test_change_password_error(self, capsys):
        """Test password change error handling"""
        with patch("app.services.user_service.supabase_admin") as mock_admin:
            mock_admin.auth.admin.update_user_by_id.side_effect = RuntimeError(
                "Auth service error"
            )

            service = UserService()

            with pytest.raises(RuntimeError):
                service.change_password(
                    user_id=UUID("00000000-0000-0000-0000-000000000001"),
                    new_password="NewPassword",
                )

            captured = capsys.readouterr()
            assert "Error changing password" in captured.out
