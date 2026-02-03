"""
Tests for auth module (get_current_user, require_roles, _get_user_roles)
Coverage target: 80%+
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app.core.auth import (
    get_current_user,
    require_roles,
    _get_user_roles,
    get_supabase_admin,
)


class MockSupabaseResponse:
    """Mock Supabase response"""

    def __init__(self, data=None):
        self.data = data


class MockUser:
    """Mock Supabase user"""

    def __init__(self, user_id, email):
        self.id = user_id
        self.email = email


class MockAuthResponse:
    """Mock Supabase auth response"""

    def __init__(self, user=None):
        self.user = user


@pytest.fixture
def mock_credentials():
    """Create mock HTTP credentials"""
    creds = MagicMock(spec=HTTPAuthorizationCredentials)
    creds.credentials = "test-jwt-token"
    return creds


class TestGetSupabaseAdmin:
    """Test get_supabase_admin function"""

    def test_returns_none_when_no_url(self, monkeypatch):
        """Test returns None when SUPABASE_URL is not set"""
        # Patch module-level variables directly
        with patch("app.core.auth.SUPABASE_URL", ""):
            with patch("app.core.auth.SUPABASE_SERVICE_KEY", "key"):
                result = get_supabase_admin()
                assert result is None

    def test_returns_none_when_no_key(self, monkeypatch):
        """Test returns None when SUPABASE_SERVICE_ROLE_KEY is not set"""
        with patch("app.core.auth.SUPABASE_URL", "https://test.supabase.co"):
            with patch("app.core.auth.SUPABASE_SERVICE_KEY", ""):
                result = get_supabase_admin()
                assert result is None

    def test_returns_client_when_configured(self):
        """Test returns client when properly configured"""
        with patch("app.core.auth.SUPABASE_URL", "https://test.supabase.co"):
            with patch("app.core.auth.SUPABASE_SERVICE_KEY", "test-key"):
                with patch("app.core.auth.create_client") as mock_create:
                    mock_client = MagicMock()
                    mock_create.return_value = mock_client

                    result = get_supabase_admin()

                    assert result == mock_client
                    mock_create.assert_called_once()


class TestGetUserRoles:
    """Test _get_user_roles function"""

    @pytest.mark.asyncio
    async def test_returns_default_when_no_supabase(self):
        """Test returns default roles when Supabase not configured"""
        with patch("app.core.auth.get_supabase_admin") as mock_get_admin:
            mock_get_admin.return_value = None

            roles = await _get_user_roles("user-123")

            assert roles == ["author"]

    @pytest.mark.asyncio
    async def test_returns_roles_from_db(self):
        """Test returns roles from database"""
        with patch("app.core.auth.get_supabase_admin") as mock_get_admin:
            mock_client = MagicMock()
            mock_table = MagicMock()
            mock_table.select.return_value = mock_table
            mock_table.eq.return_value = mock_table
            mock_table.single.return_value = mock_table
            mock_table.execute.return_value = MockSupabaseResponse(
                data={"roles": ["editor", "reviewer"]}
            )
            mock_client.table.return_value = mock_table
            mock_get_admin.return_value = mock_client

            roles = await _get_user_roles("user-123")

            assert roles == ["editor", "reviewer"]

    @pytest.mark.asyncio
    async def test_returns_default_when_no_roles_in_db(self):
        """Test returns default when no roles found"""
        with patch("app.core.auth.get_supabase_admin") as mock_get_admin:
            mock_client = MagicMock()
            mock_table = MagicMock()
            mock_table.select.return_value = mock_table
            mock_table.eq.return_value = mock_table
            mock_table.single.return_value = mock_table
            mock_table.execute.return_value = MockSupabaseResponse(data=None)
            mock_client.table.return_value = mock_table
            mock_get_admin.return_value = mock_client

            roles = await _get_user_roles("user-123")

            assert roles == ["author"]

    @pytest.mark.asyncio
    async def test_returns_default_on_exception(self):
        """Test returns default roles on exception"""
        with patch("app.core.auth.get_supabase_admin") as mock_get_admin:
            mock_client = MagicMock()
            mock_client.table.side_effect = RuntimeError("DB error")
            mock_get_admin.return_value = mock_client

            roles = await _get_user_roles("user-123")

            assert roles == ["author"]


class TestGetCurrentUser:
    """Test get_current_user function"""

    @pytest.mark.asyncio
    async def test_jwt_decode_success(self, mock_credentials):
        """Test successful JWT decode"""
        with patch("app.core.auth.SUPABASE_JWT_SECRET", "test-secret"):
            with patch("app.core.auth.jwt.decode") as mock_decode:
                mock_decode.return_value = {
                    "sub": "user-123",
                    "email": "test@example.com",
                }

                with patch(
                    "app.core.auth._get_user_roles", new_callable=AsyncMock
                ) as mock_roles:
                    mock_roles.return_value = ["author", "reviewer"]

                    result = await get_current_user(mock_credentials)

                    assert result["id"] == "user-123"
                    assert result["email"] == "test@example.com"
                    assert result["roles"] == ["author", "reviewer"]

    @pytest.mark.asyncio
    async def test_jwt_missing_sub(self, mock_credentials):
        """Test JWT without sub claim"""
        with patch("app.core.auth.SUPABASE_JWT_SECRET", "test-secret"):
            with patch("app.core.auth.jwt.decode") as mock_decode:
                mock_decode.return_value = {"email": "test@example.com"}  # No 'sub'

                with pytest.raises(HTTPException) as exc_info:
                    await get_current_user(mock_credentials)

                assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_jwt_fallback_to_supabase_auth(self, mock_credentials):
        """Test fallback to Supabase Auth API when JWT decode fails"""
        from jose import JWTError

        with patch("app.core.auth.SUPABASE_JWT_SECRET", "test-secret"):
            with patch("app.core.auth.jwt.decode") as mock_decode:
                mock_decode.side_effect = JWTError("Invalid token")

                with patch("app.core.auth.get_supabase_admin") as mock_get_admin:
                    mock_client = MagicMock()
                    mock_user = MockUser("user-456", "fallback@example.com")
                    mock_client.auth.get_user.return_value = MockAuthResponse(
                        user=mock_user
                    )
                    mock_get_admin.return_value = mock_client

                    with patch(
                        "app.core.auth._get_user_roles", new_callable=AsyncMock
                    ) as mock_roles:
                        mock_roles.return_value = ["author"]

                        result = await get_current_user(mock_credentials)

                        assert result["id"] == "user-456"
                        assert result["email"] == "fallback@example.com"

    @pytest.mark.asyncio
    async def test_all_auth_methods_fail(self, mock_credentials):
        """Test when all authentication methods fail"""
        from jose import JWTError

        with patch("app.core.auth.SUPABASE_JWT_SECRET", "test-secret"):
            with patch("app.core.auth.jwt.decode") as mock_decode:
                mock_decode.side_effect = JWTError("Invalid")

                with patch("app.core.auth.get_supabase_admin") as mock_get_admin:
                    mock_client = MagicMock()
                    mock_client.auth.get_user.return_value = MockAuthResponse(user=None)
                    mock_get_admin.return_value = mock_client

                    with pytest.raises(HTTPException) as exc_info:
                        await get_current_user(mock_credentials)

                    assert exc_info.value.status_code == 401
                    assert "验证失败" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_no_jwt_secret_uses_supabase_directly(self, mock_credentials):
        """Test when no JWT secret, uses Supabase directly"""
        with patch("app.core.auth.SUPABASE_JWT_SECRET", ""):
            with patch("app.core.auth.get_supabase_admin") as mock_get_admin:
                mock_client = MagicMock()
                mock_user = MockUser("user-789", "direct@example.com")
                mock_client.auth.get_user.return_value = MockAuthResponse(
                    user=mock_user
                )
                mock_get_admin.return_value = mock_client

                with patch(
                    "app.core.auth._get_user_roles", new_callable=AsyncMock
                ) as mock_roles:
                    mock_roles.return_value = ["admin"]

                    result = await get_current_user(mock_credentials)

                    assert result["id"] == "user-789"

    @pytest.mark.asyncio
    async def test_supabase_auth_exception(self, mock_credentials):
        """Test exception in Supabase auth fallback"""
        with patch("app.core.auth.SUPABASE_JWT_SECRET", ""):
            with patch("app.core.auth.get_supabase_admin") as mock_get_admin:
                mock_client = MagicMock()
                mock_client.auth.get_user.side_effect = RuntimeError(
                    "Auth service down"
                )
                mock_get_admin.return_value = mock_client

                with pytest.raises(HTTPException) as exc_info:
                    await get_current_user(mock_credentials)

                assert exc_info.value.status_code == 401
                assert "验证失败" in exc_info.value.detail


class TestRequireRoles:
    """Test require_roles decorator factory"""

    @pytest.mark.asyncio
    async def test_user_has_required_role(self):
        """Test access granted when user has required role"""
        checker = require_roles(["editor", "admin"])

        mock_user = {"id": "user-1", "email": "test@example.com", "roles": ["editor"]}

        with patch(
            "app.core.auth.get_current_user", new_callable=AsyncMock
        ) as mock_get_user:
            mock_get_user.return_value = mock_user

            # Create mock credentials
            mock_creds = MagicMock()

            result = await checker(current_user=mock_user)

            assert result == mock_user

    @pytest.mark.asyncio
    async def test_user_missing_required_role(self):
        """Test access denied when user lacks required role"""
        checker = require_roles(["admin"])

        mock_user = {"id": "user-1", "email": "test@example.com", "roles": ["author"]}

        with pytest.raises(HTTPException) as exc_info:
            await checker(current_user=mock_user)

        assert exc_info.value.status_code == 403
        assert "权限不足" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_user_with_multiple_roles(self):
        """Test user with multiple roles, one matching"""
        checker = require_roles(["reviewer"])

        mock_user = {
            "id": "user-1",
            "email": "test@example.com",
            "roles": ["author", "reviewer"],
        }

        result = await checker(current_user=mock_user)

        assert result == mock_user

    @pytest.mark.asyncio
    async def test_user_with_no_roles(self):
        """Test user with empty roles list"""
        checker = require_roles(["editor"])

        mock_user = {"id": "user-1", "email": "test@example.com", "roles": []}

        with pytest.raises(HTTPException) as exc_info:
            await checker(current_user=mock_user)

        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_user_without_roles_key(self):
        """Test user dict without roles key"""
        checker = require_roles(["editor"])

        mock_user = {"id": "user-1", "email": "test@example.com"}  # No 'roles' key

        with pytest.raises(HTTPException) as exc_info:
            await checker(current_user=mock_user)

        assert exc_info.value.status_code == 403
