import pytest
from httpx import AsyncClient
from unittest.mock import MagicMock
from uuid import uuid4
from main import app
from app.api.v1.users import get_user_service
from app.core.roles import get_current_profile

@pytest.fixture
def mock_user_service():
    mock = MagicMock()
    app.dependency_overrides[get_user_service] = lambda: mock
    yield mock
    app.dependency_overrides.pop(get_user_service, None)

@pytest.fixture
def mock_user_profile():
    user_id = str(uuid4())
    email = "test@example.com" # Matches auth_token default
    app.dependency_overrides[get_current_profile] = lambda: {
        "id": user_id,
        "email": email,
        "full_name": "Test User",
        "roles": ["author"]
    }
    yield {"id": user_id, "email": email}
    app.dependency_overrides.pop(get_current_profile, None)

@pytest.mark.asyncio
async def test_get_profile_success(client: AsyncClient, auth_token, mock_user_profile):
    """Test getting user profile"""
    response = await client.get(
        "/api/v1/user/profile",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["email"] == "test@example.com"
    assert data["data"]["full_name"] == "Test User"

@pytest.mark.asyncio
async def test_update_profile_success(client: AsyncClient, auth_token, mock_user_service, mock_user_profile):
    """Test updating user profile"""
    payload = {
        "full_name": "Updated Name",
        "affiliation": "New Univ",
        "research_interests": ["AI", "ML"]
    }
    
    mock_user_service.update_profile.return_value = {
        "id": mock_user_profile["id"],
        "email": mock_user_profile["email"],
        "full_name": "Updated Name",
        "affiliation": "New Univ",
        "roles": ["author"]
    }
    
    response = await client.put(
        "/api/v1/user/profile",
        headers={"Authorization": f"Bearer {auth_token}"},
        json=payload
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["data"]["full_name"] == "Updated Name"
    mock_user_service.update_profile.assert_called_once()

@pytest.mark.asyncio
async def test_update_profile_accepts_empty_optional_fields(client: AsyncClient, auth_token, mock_user_service, mock_user_profile):
    """
    空字符串的可选字段不应触发 422（前端可能会提交空字符串）。
    期望后端将其规范化为 None，并完成更新流程。
    """
    payload = {
        "orcid_id": "",
        "google_scholar_url": "",
    }

    mock_user_service.update_profile.return_value = {
        "id": mock_user_profile["id"],
        "email": mock_user_profile["email"],
        "full_name": "Test User",
        "roles": ["author"],
        "orcid_id": None,
        "google_scholar_url": None,
    }

    response = await client.put(
        "/api/v1/user/profile",
        headers={"Authorization": f"Bearer {auth_token}"},
        json=payload,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    mock_user_service.update_profile.assert_called_once()

@pytest.mark.asyncio
async def test_update_profile_validation_error(client: AsyncClient, auth_token):
    """Test validation (e.g., tag length)"""
    payload = {
        "research_interests": ["A" * 51] # Too long
    }
    response = await client.put(
        "/api/v1/user/profile",
        headers={"Authorization": f"Bearer {auth_token}"},
        json=payload
    )
    assert response.status_code == 422

@pytest.mark.asyncio
async def test_change_password_success(client: AsyncClient, auth_token, mock_user_service, mock_user_profile):
    """Test password change"""
    payload = {
        "password": "newpassword123",
        "confirm_password": "newpassword123"
    }
    
    mock_user_service.change_password.return_value = True
    
    response = await client.put(
        "/api/v1/user/security/password",
        headers={"Authorization": f"Bearer {auth_token}"},
        json=payload
    )
    
    assert response.status_code == 200
    mock_user_service.change_password.assert_called_once()

@pytest.mark.asyncio
async def test_change_password_mismatch(client: AsyncClient, auth_token):
    """Test password mismatch validation"""
    payload = {
        "password": "password123",
        "confirm_password": "password456"
    }
    response = await client.put(
        "/api/v1/user/security/password",
        headers={"Authorization": f"Bearer {auth_token}"},
        json=payload
    )
    assert response.status_code == 422
