import pytest
from uuid import uuid4

from main import app
from app.core.roles import get_current_profile


@pytest.fixture
def override_profile():
    def _set(profile: dict):
        app.dependency_overrides[get_current_profile] = lambda: profile

    yield _set
    app.dependency_overrides.pop(get_current_profile, None)


@pytest.mark.asyncio
async def test_reviewer_library_add_and_search(client, override_profile, monkeypatch: pytest.MonkeyPatch):
    override_profile({"id": str(uuid4()), "email": "editor@example.com", "roles": ["editor"]})

    reviewer_id = str(uuid4())

    class _StubSvc:
        def add_to_library(self, payload):
            return {"id": reviewer_id, "email": str(payload.email), "full_name": payload.full_name, "roles": ["reviewer"], "is_reviewer_active": True}

        def search(self, query: str = "", limit: int = 50):
            assert query == "nlp"
            assert limit == 50
            return [{"id": reviewer_id, "email": "r@example.com", "full_name": "R", "roles": ["reviewer"], "is_reviewer_active": True}]

    monkeypatch.setattr("app.api.v1.editor.ReviewerService", lambda: _StubSvc())

    res = await client.post(
        "/api/v1/editor/reviewer-library",
        json={"email": "r@example.com", "full_name": "R", "title": "Dr."},
    )
    assert res.status_code == 201
    body = res.json()
    assert body["success"] is True
    assert body["data"]["email"] == "r@example.com"

    res2 = await client.get("/api/v1/editor/reviewer-library?query=nlp&limit=50")
    assert res2.status_code == 200
    body2 = res2.json()
    assert body2["success"] is True
    assert isinstance(body2["data"], list)


@pytest.mark.asyncio
async def test_reviewer_library_requires_editor_or_admin(client, override_profile, auth_token):
    override_profile({"id": str(uuid4()), "email": "author@example.com", "roles": ["author"]})
    res = await client.get(
        "/api/v1/editor/reviewer-library",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert res.status_code == 403
