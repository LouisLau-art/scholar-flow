from types import SimpleNamespace

import pytest

import app.api.v1.editor_detail as editor_detail_api


class _FakeQuery:
    def __init__(self, table: str, dataset: dict[str, list[dict]]):
        self.table = table
        self.dataset = dataset

    def select(self, *_args, **_kwargs):
        return self

    def eq(self, *_args, **_kwargs):
        return self

    def in_(self, *_args, **_kwargs):
        return self

    def order(self, *_args, **_kwargs):
        return self

    def limit(self, *_args, **_kwargs):
        return self

    def single(self, *_args, **_kwargs):
        return self

    def execute(self):
        rows = self.dataset.get(self.table, [])
        if self.table in {"manuscripts", "invoices"}:
            return SimpleNamespace(data=(rows[0] if rows else None))
        return SimpleNamespace(data=rows)


class _FakeSupabase:
    def __init__(self, dataset: dict[str, list[dict]]):
        self.dataset = dataset
        self.call_count: dict[str, int] = {}

    def table(self, name: str):
        self.call_count[name] = self.call_count.get(name, 0) + 1
        return _FakeQuery(name, self.dataset)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_editor_detail_returns_reviewer_timeline(client, auth_token, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("ADMIN_EMAILS", "test@example.com")
    monkeypatch.setattr(editor_detail_api, "_get_signed_url", lambda *_args, **_kwargs: "https://example.com/signed")

    fake_db = _FakeSupabase(
        {
            "manuscripts": [
                {
                    "id": "ms-1",
                    "title": "Timeline Test Manuscript",
                    "status": "under_review",
                    "owner_id": "owner-1",
                    "editor_id": "editor-1",
                    "file_path": "manuscripts/ms-1/v1.pdf",
                    "created_at": "2026-02-01T00:00:00Z",
                    "updated_at": "2026-02-02T00:00:00Z",
                    "journals": {"title": "Journal"},
                }
            ],
            "invoices": [],
            "manuscript_files": [],
            "review_assignments": [
                {
                    "id": "ra-1",
                    "reviewer_id": "reviewer-1",
                    "status": "pending",
                    "due_at": "2026-02-10T00:00:00Z",
                    "invited_at": "2026-02-01T00:00:00Z",
                    "opened_at": "2026-02-01T01:00:00Z",
                    "accepted_at": "2026-02-01T02:00:00Z",
                    "declined_at": None,
                    "decline_reason": None,
                    "decline_note": None,
                    "created_at": "2026-02-01T00:00:00Z",
                }
            ],
            "review_reports": [
                {
                    "id": "rr-1",
                    "reviewer_id": "reviewer-1",
                    "status": "completed",
                    "created_at": "2026-02-05T00:00:00Z",
                }
            ],
            "user_profiles": [
                {"id": "owner-1", "full_name": "Owner User", "email": "owner@example.com"},
                {"id": "editor-1", "full_name": "Editor User", "email": "editor@example.com"},
                {"id": "reviewer-1", "full_name": "Reviewer User", "email": "reviewer@example.com"},
            ],
        }
    )
    monkeypatch.setattr(editor_detail_api, "supabase_admin", fake_db)

    res = await client.get(
        "/api/v1/editor/manuscripts/ms-1",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert res.status_code == 200, res.text
    payload = res.json()
    assert payload["success"] is True
    invites = payload["data"].get("reviewer_invites") or []
    assert len(invites) == 1
    assert invites[0]["status"] == "accepted"
    assert invites[0]["reviewer_name"] == "Reviewer User"
    assert invites[0]["submitted_at"] == "2026-02-05T00:00:00Z"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_editor_detail_skip_cards_lightweight_skips_heavy_blocks(client, auth_token, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("ADMIN_EMAILS", "test@example.com")
    monkeypatch.setattr(editor_detail_api, "_get_signed_url", lambda *_args, **_kwargs: "https://example.com/signed")

    fake_db = _FakeSupabase(
        {
            "manuscripts": [
                {
                    "id": "ms-2",
                    "title": "Lightweight Detail Manuscript",
                    "status": "under_review",
                    "owner_id": "owner-1",
                    "editor_id": "editor-1",
                    "file_path": "manuscripts/ms-2/v1.pdf",
                    "created_at": "2026-02-01T00:00:00Z",
                    "updated_at": "2026-02-02T00:00:00Z",
                    "journals": {"title": "Journal"},
                }
            ],
            "invoices": [],
            "manuscript_files": [{"id": "mf-1"}],
            "review_assignments": [{"id": "ra-1", "reviewer_id": "reviewer-1"}],
            "review_reports": [{"id": "rr-1", "reviewer_id": "reviewer-1"}],
            "revisions": [{"id": "rev-1", "response_letter": "hello", "created_at": "2026-02-03T00:00:00Z"}],
            "user_profiles": [
                {"id": "owner-1", "full_name": "Owner User", "email": "owner@example.com"},
                {"id": "editor-1", "full_name": "Editor User", "email": "editor@example.com"},
            ],
        }
    )
    monkeypatch.setattr(editor_detail_api, "supabase_admin", fake_db)

    res = await client.get(
        "/api/v1/editor/manuscripts/ms-2?skip_cards=true",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert res.status_code == 200, res.text
    payload = res.json()
    data = payload.get("data") or {}
    assert payload["success"] is True
    assert data.get("is_deferred_context_loaded") is False
    assert (data.get("reviewer_invites") or []) == []
    assert (data.get("author_response_history") or []) == []
    assert fake_db.call_count.get("manuscript_files", 0) == 0
    assert fake_db.call_count.get("review_reports", 0) == 0
    assert fake_db.call_count.get("review_assignments", 0) == 0
    assert fake_db.call_count.get("revisions", 0) == 0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_editor_detail_skip_cards_with_include_heavy_loads_reviewer_timeline(
    client,
    auth_token,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("ADMIN_EMAILS", "test@example.com")
    monkeypatch.setattr(editor_detail_api, "_get_signed_url", lambda *_args, **_kwargs: "https://example.com/signed")

    fake_db = _FakeSupabase(
        {
            "manuscripts": [
                {
                    "id": "ms-3",
                    "title": "Deferred Heavy Detail Manuscript",
                    "status": "under_review",
                    "owner_id": "owner-1",
                    "editor_id": "editor-1",
                    "file_path": "manuscripts/ms-3/v1.pdf",
                    "created_at": "2026-02-01T00:00:00Z",
                    "updated_at": "2026-02-02T00:00:00Z",
                    "journals": {"title": "Journal"},
                }
            ],
            "invoices": [],
            "manuscript_files": [],
            "review_assignments": [
                {
                    "id": "ra-1",
                    "reviewer_id": "reviewer-1",
                    "status": "pending",
                    "due_at": "2026-02-10T00:00:00Z",
                    "invited_at": "2026-02-01T00:00:00Z",
                    "opened_at": "2026-02-01T01:00:00Z",
                    "accepted_at": "2026-02-01T02:00:00Z",
                    "declined_at": None,
                    "decline_reason": None,
                    "decline_note": None,
                    "created_at": "2026-02-01T00:00:00Z",
                }
            ],
            "review_reports": [
                {
                    "id": "rr-1",
                    "reviewer_id": "reviewer-1",
                    "status": "completed",
                    "created_at": "2026-02-05T00:00:00Z",
                }
            ],
            "revisions": [],
            "user_profiles": [
                {"id": "owner-1", "full_name": "Owner User", "email": "owner@example.com"},
                {"id": "editor-1", "full_name": "Editor User", "email": "editor@example.com"},
                {"id": "reviewer-1", "full_name": "Reviewer User", "email": "reviewer@example.com"},
            ],
        }
    )
    monkeypatch.setattr(editor_detail_api, "supabase_admin", fake_db)

    res = await client.get(
        "/api/v1/editor/manuscripts/ms-3?skip_cards=true&include_heavy=true",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert res.status_code == 200, res.text
    payload = res.json()
    data = payload.get("data") or {}
    invites = data.get("reviewer_invites") or []
    assert payload["success"] is True
    assert data.get("is_deferred_context_loaded") is True
    assert len(invites) == 1
    assert invites[0]["status"] == "accepted"
    assert fake_db.call_count.get("review_assignments", 0) >= 1
