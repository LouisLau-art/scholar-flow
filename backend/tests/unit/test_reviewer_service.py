from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

import app.services.reviewer_service as reviewer_service_module
from app.schemas.reviewer import ReviewerCreate, ReviewerUpdate


class _Resp:
    def __init__(self, *, data=None):
        self.data = data


def _chain():
    q = MagicMock()
    for method in (
        "select",
        "eq",
        "ilike",
        "maybe_single",
        "single",
        "update",
        "upsert",
        "contains",
        "limit",
        "order",
        "or_",
        "execute",
    ):
        getattr(q, method).return_value = q
    return q


@pytest.fixture
def supabase_admin(monkeypatch: pytest.MonkeyPatch):
    client = MagicMock()
    tables: dict[str, MagicMock] = {}

    def _table(name: str):
        tables.setdefault(name, _chain())
        return tables[name]

    client.table.side_effect = _table
    client._tables = tables  # type: ignore[attr-defined]

    # auth admin stubs
    auth = MagicMock()
    admin = MagicMock()
    auth.admin = admin
    client.auth = auth

    monkeypatch.setattr(reviewer_service_module, "supabase_admin", client)
    return client


def test_add_to_library_links_existing_profile_and_updates_metadata(supabase_admin):
    svc = reviewer_service_module.ReviewerService()

    profiles = supabase_admin.table("user_profiles")
    profiles.execute.return_value = _Resp(
        data={
            "id": "u1",
            "email": "a@b.com",
            "full_name": "Old",
            "roles": ["author"],
            "is_reviewer_active": True,
        }
    )

    payload = ReviewerCreate(
        email="a@b.com",
        full_name="New Name",
        title="Dr.",
        affiliation="Uni",
        homepage_url="https://example.com",
        research_interests=["NLP"],
    )
    out = svc.add_to_library(payload)
    assert str(out["id"]) == "u1"
    assert "reviewer" in (out.get("roles") or [])
    assert out.get("full_name") == "New Name"
    assert profiles.update.called is True
    assert supabase_admin.auth.admin.create_user.called is False


def test_add_to_library_creates_auth_user_and_upserts_profile(supabase_admin):
    svc = reviewer_service_module.ReviewerService()

    # No existing profile
    profiles = supabase_admin.table("user_profiles")
    profiles.execute.return_value = _Resp(data=None)

    supabase_admin.auth.admin.create_user.return_value = SimpleNamespace(user=SimpleNamespace(id="new-id"))

    payload = ReviewerCreate(email="x@y.com", full_name="X", title="Prof.")
    out = svc.add_to_library(payload)
    assert out["id"] == "new-id"
    assert out["email"] == "x@y.com"
    assert out["roles"] == ["reviewer"]
    assert profiles.upsert.called is True


def test_search_fallbacks_when_generated_column_missing(supabase_admin):
    svc = reviewer_service_module.ReviewerService()

    profiles = supabase_admin.table("user_profiles")

    # First attempt (reviewer_search_text) raises missing column error
    def _ilike(*args, **kwargs):
        raise RuntimeError('column "reviewer_search_text" does not exist')

    profiles.ilike.side_effect = _ilike
    profiles.execute.return_value = _Resp(data=[{"id": "u1"}])

    out = svc.search(query="nlp", limit=10)
    assert out == [{"id": "u1"}]
    assert profiles.or_.called is True


def test_update_reviewer_converts_homepage_url_to_string(supabase_admin):
    svc = reviewer_service_module.ReviewerService()

    profiles = supabase_admin.table("user_profiles")
    profiles.execute.return_value = _Resp(data=[{"id": "u1", "homepage_url": "https://x.com"}])

    out = svc.update_reviewer(
        reviewer_id=reviewer_service_module.UUID("00000000-0000-0000-0000-000000000001"),
        payload=ReviewerUpdate(homepage_url="https://x.com"),
    )
    assert out["id"] == "u1"

