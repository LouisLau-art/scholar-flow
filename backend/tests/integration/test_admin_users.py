import pytest
from httpx import AsyncClient
from unittest.mock import MagicMock, patch
from uuid import uuid4
from main import app
from app.api.v1.admin.users import get_user_management_service
from app.core.roles import get_current_profile

# === Test Configuration & Fixtures ===

@pytest.fixture
def mock_admin_service():
    mock = MagicMock()
    app.dependency_overrides[get_user_management_service] = lambda: mock
    yield mock
    app.dependency_overrides.pop(get_user_management_service, None)

@pytest.fixture
def mock_admin_role():
    # Helper to simulate admin role
    app.dependency_overrides[get_current_profile] = lambda: {
        "id": "admin-id", "email": "admin@example.com", "roles": ["admin"]
    }
    yield
    app.dependency_overrides.pop(get_current_profile, None)

@pytest.fixture
def mock_author_role():
    # Helper to simulate author role
    app.dependency_overrides[get_current_profile] = lambda: {
        "id": "author-id", "email": "author@example.com", "roles": ["author"]
    }
    yield
    app.dependency_overrides.pop(get_current_profile, None)

# === T023-T031: User Story 1 (User List) ===

@pytest.mark.asyncio
async def test_get_users_unauthenticated(client: AsyncClient):
    """T025: Security test: Unauthenticated access returns 401"""
    response = await client.get("/api/v1/admin/users")
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_get_users_unauthorized_as_author(client: AsyncClient, auth_token, mock_author_role):
    """T024: Authorization test: Non-admin users cannot access user list"""
    response = await client.get(
        "/api/v1/admin/users",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 403

@pytest.mark.asyncio
async def test_get_users_authorized_admin(client: AsyncClient, auth_token, mock_admin_role, mock_admin_service):
    """T023: Authentication test: GET /api/v1/admin/users requires valid JWT and admin role"""
    mock_users_data = [
        {"id": str(uuid4()), "email": "user1@example.com", "full_name": "User One", "roles": ["author"], "created_at": "2026-01-01T00:00:00Z", "is_verified": True},
        {"id": str(uuid4()), "email": "user2@example.com", "full_name": "User Two", "roles": ["editor"], "created_at": "2026-01-02T00:00:00Z", "is_verified": True},
    ]
    
    mock_admin_service.get_users.return_value = {
        "data": mock_users_data,
        "pagination": {"total": 2, "page": 1, "per_page": 10, "total_pages": 1}
    }
    
    response = await client.get(
        "/api/v1/admin/users",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["data"]) == 2
    assert data["data"][0]["email"] == "user1@example.com"

@pytest.mark.asyncio
async def test_get_users_invalid_pagination(client: AsyncClient, auth_token, mock_admin_role, mock_admin_service):
    """T028: Validation test: Verify pagination parameters"""
    # Test negative page
    response = await client.get(
        "/api/v1/admin/users?page=-1",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 422 
    
    # Test too large per_page
    response = await client.get(
        "/api/v1/admin/users?per_page=1000",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 422

@pytest.mark.asyncio
async def test_get_users_with_real_db(client: AsyncClient, auth_token, mock_admin_role, db_connection):
    """T030: Integration test: Use REAL database connection to fetch users"""
    user_id = str(uuid4())
    test_email = f"real_db_test_{user_id[:8]}@example.com"
    profile_data = {
        "id": user_id,
        "email": test_email,
        "full_name": "Real DB Test User",
        "roles": ["reviewer"]
    }
    
    db_connection.table("user_profiles").insert(profile_data).execute()
    
    try:
        # We assume the service initializes correctly (which might fail if key missing in env, but let's test logic)
        # If key missing, it raises 500, which catches config issues.
        response = await client.get(
            f"/api/v1/admin/users?search={test_email}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        # If SUPABASE_SERVICE_ROLE_KEY is missing, this will be 500
        if response.status_code == 500 and "supabase_key is required" in response.text:
            pytest.skip("Skipping real DB test due to missing SUPABASE_SERVICE_ROLE_KEY")
            
        assert response.status_code == 200
        data = response.json()
        assert any(u["email"] == test_email for u in data["data"])
        
    finally:
        db_connection.table("user_profiles").delete().eq("id", user_id).execute()

# === T046-T054: User Story 2 (Role Modification) ===

@pytest.mark.asyncio
async def test_update_role_unauthorized(client: AsyncClient, auth_token, mock_author_role):
    """T047: Authorization test: Non-admin users cannot modify roles"""
    user_id = str(uuid4())
    payload = {"new_role": "editor", "reason": "Promoting for test"}
    
    response = await client.put(
        f"/api/v1/admin/users/{user_id}/role",
        headers={"Authorization": f"Bearer {auth_token}"},
        json=payload
    )
    assert response.status_code == 403

@pytest.mark.asyncio
async def test_update_role_validation(client: AsyncClient, auth_token, mock_admin_role, mock_admin_service):
    """T049, T054: Validation test: Reason length and valid role"""
    user_id = str(uuid4())
    
    # Test short reason
    response = await client.put(
        f"/api/v1/admin/users/{user_id}/role",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={"new_role": "editor", "reason": "short"}
    )
    assert response.status_code == 422
    
    # Test invalid role
    response = await client.put(
        f"/api/v1/admin/users/{user_id}/role",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={"new_role": "superman", "reason": "Valid reason for invalid role"}
    )
    assert response.status_code == 422

@pytest.mark.asyncio
async def test_update_role_success(client: AsyncClient, auth_token, mock_admin_role, mock_admin_service):
    """T052: HTTP method test: Test PUT /api/v1/admin/users/{id}/role"""
    user_id = str(uuid4())
    payload = {"new_role": "editor", "reason": "Valid reason for promotion"}
    
    mock_admin_service.update_user_role.return_value = {
        "id": user_id,
        "email": "target@example.com",
        "roles": ["editor"],
        "created_at": "2026-01-01T00:00:00Z"
    }
    
    response = await client.put(
        f"/api/v1/admin/users/{user_id}/role",
        headers={"Authorization": f"Bearer {auth_token}"},
        json=payload
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "editor" in data["roles"]
    mock_admin_service.update_user_role.assert_called_once()

@pytest.mark.asyncio
async def test_update_role_self_prevention(client: AsyncClient, auth_token, mock_admin_service):
    """T048: Security test: User cannot modify their own role"""
    admin_id = str(uuid4())
    # Mock profile to match target user_id
    app.dependency_overrides[get_current_profile] = lambda: {
        "id": admin_id, "email": "admin@example.com", "roles": ["admin"]
    }
    
    payload = {"new_role": "author", "reason": "Demoting myself"}
    
    # Simulate service raising ValueError (which API maps to 403)
    mock_admin_service.update_user_role.side_effect = ValueError("Cannot modify your own role")
    
    response = await client.put(
        f"/api/v1/admin/users/{admin_id}/role",
        headers={"Authorization": f"Bearer {auth_token}"},
        json=payload
    )
    assert response.status_code == 403
    
    app.dependency_overrides.pop(get_current_profile, None)

# === T073-T081: User Story 3 (Direct Member Invitation) ===

@pytest.mark.asyncio
async def test_create_user_unauthorized(client: AsyncClient, auth_token, mock_author_role):
    """T074: Authorization test: Non-admin users cannot create users"""
    payload = {"email": "new@example.com", "full_name": "New Editor", "role": "editor"}
    response = await client.post(
        "/api/v1/admin/users",
        headers={"Authorization": f"Bearer {auth_token}"},
        json=payload
    )
    assert response.status_code == 403

@pytest.mark.asyncio
async def test_create_user_validation(client: AsyncClient, auth_token, mock_admin_role, mock_admin_service):
    """T078: Validation test: Invalid email or name"""
    # Invalid email
    response = await client.post(
        "/api/v1/admin/users",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={"email": "not-an-email", "full_name": "Name", "role": "editor"}
    )
    assert response.status_code == 422
    
    # Invalid role (must be editor/reviewer/admin)
    response = await client.post(
        "/api/v1/admin/users",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={"email": "valid@example.com", "full_name": "Name", "role": "author"}
    )
    assert response.status_code == 422

@pytest.mark.asyncio
async def test_create_user_duplicate_email(client: AsyncClient, auth_token, mock_admin_role, mock_admin_service):
    """T077: Error handling test: Email already exists"""
    payload = {"email": "duplicate@example.com", "full_name": "Duplicate", "role": "editor"}
    
    mock_admin_service.create_internal_user.side_effect = ValueError("User with this email already exists")
    
    response = await client.post(
        "/api/v1/admin/users",
        headers={"Authorization": f"Bearer {auth_token}"},
        json=payload
    )
    # The API might map ValueError to 400 or 409 depending on implementation. 
    # Usually duplicate resource is 409 Conflict.
    # Let's assume we map "already exists" to 409.
    assert response.status_code == 409

@pytest.mark.asyncio
async def test_create_user_success(client: AsyncClient, auth_token, mock_admin_role, mock_admin_service):
    """T079: HTTP method test: Test POST /api/v1/admin/users"""
    payload = {"email": "success@example.com", "full_name": "Success", "role": "editor"}
    
    mock_admin_service.create_internal_user.return_value = {
        "id": str(uuid4()),
        "email": payload["email"],
        "full_name": payload["full_name"],
        "roles": ["editor"],
        "created_at": "2026-01-01T00:00:00Z",
        "is_verified": True
    }
    
    response = await client.post(
        "/api/v1/admin/users",
        headers={"Authorization": f"Bearer {auth_token}"},
        json=payload
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == payload["email"]
    mock_admin_service.create_internal_user.assert_called_once()

# === T096-T104: User Story 4 (Reviewer Onboarding) ===

@pytest.mark.asyncio
async def test_invite_reviewer_unauthorized(client: AsyncClient, auth_token, mock_author_role):
    """T097: Authorization test: Only editors and admins can invite reviewers"""
    payload = {"email": "rev@example.com", "full_name": "Reviewer"}
    response = await client.post(
        "/api/v1/admin/users/invite-reviewer",
        headers={"Authorization": f"Bearer {auth_token}"},
        json=payload
    )
    assert response.status_code == 403

@pytest.mark.asyncio
async def test_invite_reviewer_validation(client: AsyncClient, auth_token, mock_admin_role, mock_admin_service):
    """T099: Validation test: Invalid email"""
    response = await client.post(
        "/api/v1/admin/users/invite-reviewer",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={"email": "not-email", "full_name": "Name"}
    )
    assert response.status_code == 422

@pytest.mark.asyncio
async def test_invite_reviewer_success(client: AsyncClient, auth_token, mock_admin_role, mock_admin_service):
    """T102: HTTP method test: Test POST /api/v1/admin/users/invite-reviewer"""
    payload = {"email": "reviewer@example.com", "full_name": "Reviewer One"}
    
    mock_admin_service.invite_reviewer.return_value = {
        "id": str(uuid4()),
        "email": payload["email"],
        "full_name": payload["full_name"],
        "roles": ["reviewer"],
        "created_at": "2026-01-01T00:00:00Z",
        "is_verified": False # Invited but not claimed
    }
    
    response = await client.post(
        "/api/v1/admin/users/invite-reviewer",
        headers={"Authorization": f"Bearer {auth_token}"},
        json=payload
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == payload["email"]
    mock_admin_service.invite_reviewer.assert_called_once()


# === GAP-P1-05: Journal Scope Admin APIs ===

@pytest.mark.asyncio
async def test_list_journal_scopes_unauthorized(client: AsyncClient, auth_token, mock_author_role):
    response = await client.get(
        "/api/v1/admin/journal-scopes",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_list_journal_scopes_success(client: AsyncClient, auth_token, mock_admin_role):
    scope_id = str(uuid4())
    user_id = str(uuid4())
    journal_id = str(uuid4())
    row = {
        "id": scope_id,
        "user_id": user_id,
        "journal_id": journal_id,
        "role": "managing_editor",
        "is_active": True,
        "created_by": str(uuid4()),
        "created_at": "2026-02-10T00:00:00Z",
        "updated_at": "2026-02-10T00:00:00Z",
    }

    with patch("app.api.v1.admin.users.supabase_admin") as mock_db:
        table = MagicMock()
        query = MagicMock()
        mock_db.table.return_value = table
        table.select.return_value = query
        query.order.return_value = query
        query.execute.return_value = MagicMock(data=[row])

        response = await client.get(
            "/api/v1/admin/journal-scopes",
            headers={"Authorization": f"Bearer {auth_token}"},
        )

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == scope_id
    assert data[0]["role"] == "managing_editor"


@pytest.mark.asyncio
async def test_upsert_journal_scope_validation(client: AsyncClient, auth_token, mock_admin_role):
    payload = {
        "user_id": str(uuid4()),
        "journal_id": str(uuid4()),
        "role": "invalid_role",
        "is_active": True,
    }
    response = await client.post(
        "/api/v1/admin/journal-scopes",
        headers={"Authorization": f"Bearer {auth_token}"},
        json=payload,
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_upsert_journal_scope_success(client: AsyncClient, auth_token, mock_admin_role):
    payload = {
        "user_id": str(uuid4()),
        "journal_id": str(uuid4()),
        "role": "assistant_editor",
        "is_active": True,
    }
    row = {
        "id": str(uuid4()),
        "user_id": payload["user_id"],
        "journal_id": payload["journal_id"],
        "role": payload["role"],
        "is_active": True,
        "created_by": str(uuid4()),
        "created_at": "2026-02-10T00:00:00Z",
        "updated_at": "2026-02-10T00:00:00Z",
    }

    with patch("app.api.v1.admin.users.supabase_admin") as mock_db:
        table = MagicMock()
        upsert_q = MagicMock()
        execute_q = MagicMock()
        mock_db.table.return_value = table
        table.upsert.return_value = upsert_q
        upsert_q.execute.return_value = MagicMock(data=[row])

        response = await client.post(
            "/api/v1/admin/journal-scopes",
            headers={"Authorization": f"Bearer {auth_token}"},
            json=payload,
        )

    assert response.status_code == 201
    data = response.json()
    assert data["journal_id"] == payload["journal_id"]
    assert data["role"] == payload["role"]


@pytest.mark.asyncio
async def test_deactivate_journal_scope_not_found(client: AsyncClient, auth_token, mock_admin_role):
    scope_id = str(uuid4())
    with patch("app.api.v1.admin.users.supabase_admin") as mock_db:
        table = MagicMock()
        update_q = MagicMock()
        eq_q = MagicMock()
        mock_db.table.return_value = table
        table.update.return_value = update_q
        update_q.eq.return_value = eq_q
        eq_q.execute.return_value = MagicMock(data=[])

        response = await client.delete(
            f"/api/v1/admin/journal-scopes/{scope_id}",
            headers={"Authorization": f"Bearer {auth_token}"},
        )

    assert response.status_code == 404
