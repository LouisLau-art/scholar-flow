import pytest
from httpx import AsyncClient
from unittest.mock import MagicMock, patch
from main import app
from app.api.v1.users import get_user_service

def auth_headers(token: str | None) -> dict[str, str]:
    if not token:
        return {}
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def mock_user_service_fixture():
    mock = MagicMock()
    app.dependency_overrides[get_user_service] = lambda: mock
    yield mock
    app.dependency_overrides.pop(get_user_service, None)

@pytest.mark.asyncio
async def test_profile_update_triggers_reviewer_indexing(client: AsyncClient, auth_token: str, mock_user_service_fixture):
    # Mock update_profile to return a profile with "reviewer" role
    mock_user_service_fixture.update_profile.return_value = {
        "id": "u", 
        "name": "n", 
        "roles": ["reviewer"]
    }

    with patch("app.api.v1.users.MatchmakingService") as svc:
        svc.return_value.index_reviewer.return_value = None
        resp = await client.put(
            "/api/v1/user/profile",
            headers=auth_headers(auth_token),
            json={"research_interests": ["Machine Learning"]},
        )

    assert resp.status_code == 200
    assert svc.return_value.index_reviewer.called

@pytest.mark.asyncio
async def test_profile_update_does_not_trigger_indexing_for_author(client: AsyncClient, auth_token: str, mock_user_service_fixture):
    # Mock update_profile to return a profile with "author" role (no reviewer)
    mock_user_service_fixture.update_profile.return_value = {
        "id": "u", 
        "name": "n", 
        "roles": ["author"]
    }

    with patch("app.api.v1.users.MatchmakingService") as svc:
        resp = await client.put(
            "/api/v1/user/profile",
            headers=auth_headers(auth_token),
            json={"research_interests": ["ML"]},
        )

    assert resp.status_code == 200
    assert not svc.return_value.index_reviewer.called