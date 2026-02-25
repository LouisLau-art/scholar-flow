import pytest
from uuid import uuid4
from unittest.mock import MagicMock

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
    override_profile({"id": str(uuid4()), "email": "editor@example.com", "roles": ["managing_editor"]})

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
    assert body2["pagination"]["page"] == 1
    assert body2["pagination"]["page_size"] == 50
    assert body2["pagination"]["returned"] == len(body2["data"])


@pytest.mark.asyncio
async def test_reviewer_library_requires_editor_or_admin(client, override_profile, auth_token):
    override_profile({"id": str(uuid4()), "email": "author@example.com", "roles": ["author"]})
    res = await client.get(
        "/api/v1/editor/reviewer-library",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_reviewer_library_returns_invite_policy_when_manuscript_context_provided(
    client, override_profile, monkeypatch: pytest.MonkeyPatch
):
    override_profile({"id": str(uuid4()), "email": "editor@example.com", "roles": ["managing_editor"]})

    class _StubSvc:
        def search(self, query: str = "", limit: int = 50):
            assert query == "policy"
            assert limit == 20
            return [
                {"id": "r-1", "email": "r1@example.com", "full_name": "Reviewer 1", "roles": ["reviewer"]},
                {"id": "r-2", "email": "r2@example.com", "full_name": "Reviewer 2", "roles": ["reviewer"]},
            ]

    class _StubPolicySvc:
        def evaluate_candidates(self, *, manuscript, reviewer_ids):
            assert manuscript["id"] == "m-1"
            assert reviewer_ids == ["r-1", "r-2"]
            return {
                "r-1": {
                    "can_assign": False,
                    "allow_override": True,
                    "cooldown_active": True,
                    "conflict": False,
                    "overdue_risk": False,
                    "overdue_open_count": 0,
                    "hits": [{"code": "cooldown", "label": "Cooldown active", "blocking": True}],
                },
                "r-2": {
                    "can_assign": True,
                    "allow_override": False,
                    "cooldown_active": False,
                    "conflict": False,
                    "overdue_risk": True,
                    "overdue_open_count": 1,
                    "hits": [{"code": "overdue_risk", "label": "Overdue risk", "blocking": False}],
                },
            }

        def cooldown_days(self):
            return 30

        def cooldown_override_roles(self):
            return ["admin", "managing_editor"]

    fake_db = MagicMock()
    fake_db.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = {
        "id": "m-1",
        "author_id": "a-1",
        "journal_id": "j-1",
        "status": "under_review",
    }

    monkeypatch.setattr("app.api.v1.editor.ReviewerService", lambda: _StubSvc())
    monkeypatch.setattr("app.api.v1.editor.ReviewPolicyService", lambda: _StubPolicySvc())
    monkeypatch.setattr("app.api.v1.editor.supabase_admin", fake_db)

    res = await client.get("/api/v1/editor/reviewer-library?query=policy&limit=20&manuscript_id=m-1")
    assert res.status_code == 200
    body = res.json()
    assert body["success"] is True
    assert body["policy"]["cooldown_days"] == 30
    assert body["data"][0]["invite_policy"]["cooldown_active"] is True
    assert body["data"][1]["invite_policy"]["overdue_risk"] is True
    assert body["pagination"]["page"] == 1
    assert body["pagination"]["page_size"] == 20


@pytest.mark.asyncio
async def test_reviewer_library_supports_page_and_page_size(client, override_profile, monkeypatch: pytest.MonkeyPatch):
    override_profile({"id": str(uuid4()), "email": "editor@example.com", "roles": ["managing_editor"]})

    class _StubSvc:
        def search_page(self, query: str = "", page: int = 1, page_size: int = 50):
            assert query == "nlp"
            assert page == 2
            assert page_size == 10
            return {
                "items": [{"id": "r-10", "email": "r10@example.com", "full_name": "R10", "roles": ["reviewer"]}],
                "page": page,
                "page_size": page_size,
                "returned": 1,
                "has_more": True,
            }

    monkeypatch.setattr("app.api.v1.editor.ReviewerService", lambda: _StubSvc())

    res = await client.get("/api/v1/editor/reviewer-library?query=nlp&page=2&page_size=10")
    assert res.status_code == 200
    body = res.json()
    assert body["success"] is True
    assert body["pagination"]["page"] == 2
    assert body["pagination"]["page_size"] == 10
    assert body["pagination"]["has_more"] is True
    assert len(body["data"]) == 1
