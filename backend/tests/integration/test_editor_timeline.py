from types import SimpleNamespace

import pytest

import app.api.v1.editor as editor_api


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

    def table(self, name: str):
        return _FakeQuery(name, self.dataset)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_editor_detail_returns_reviewer_timeline(client, auth_token, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("ADMIN_EMAILS", "test@example.com")
    monkeypatch.setattr(editor_api, "_get_signed_url", lambda *_args, **_kwargs: "https://example.com/signed")

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
    monkeypatch.setattr(editor_api, "supabase_admin", fake_db)

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

