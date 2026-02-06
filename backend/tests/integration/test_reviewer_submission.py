from types import SimpleNamespace
from uuid import UUID

import pytest


@pytest.mark.asyncio
async def test_workspace_submit_review_success(client, monkeypatch: pytest.MonkeyPatch):
    assignment_id = "00000000-0000-0000-0000-000000000123"

    async def _allow(*, assignment_id, magic_token):
        return SimpleNamespace(
            assignment_id=UUID(str(assignment_id)),
            reviewer_id=UUID("00000000-0000-0000-0000-000000000777"),
            manuscript_id=UUID("00000000-0000-0000-0000-000000000888"),
        )

    class _Svc:
        def submit_review(self, *, assignment_id, reviewer_id, payload):
            assert str(assignment_id) == "00000000-0000-0000-0000-000000000123"
            assert str(reviewer_id) == "00000000-0000-0000-0000-000000000777"
            assert payload.comments_for_author == "public comments"
            return {"status": "completed"}

    monkeypatch.setattr("app.api.v1.reviews._require_magic_link_scope", _allow)
    monkeypatch.setattr("app.api.v1.reviews.ReviewerWorkspaceService", lambda: _Svc())

    res = await client.post(
        f"/api/v1/reviewer/assignments/{assignment_id}/submit",
        cookies={"sf_review_magic": "token"},
        json={
            "comments_for_author": "public comments",
            "confidential_comments_to_editor": "private note",
            "recommendation": "minor_revision",
            "attachments": [],
        },
    )
    assert res.status_code == 200
    body = res.json()
    assert body["success"] is True
    assert body["data"]["status"] == "completed"


@pytest.mark.asyncio
async def test_workspace_submit_review_forbidden(client, monkeypatch: pytest.MonkeyPatch):
    assignment_id = "00000000-0000-0000-0000-000000000123"

    async def _allow(*, assignment_id, magic_token):
        return SimpleNamespace(
            assignment_id=UUID(str(assignment_id)),
            reviewer_id=UUID("00000000-0000-0000-0000-000000000777"),
            manuscript_id=UUID("00000000-0000-0000-0000-000000000888"),
        )

    class _Svc:
        def submit_review(self, *, assignment_id, reviewer_id, payload):
            raise PermissionError("forbidden")

    monkeypatch.setattr("app.api.v1.reviews._require_magic_link_scope", _allow)
    monkeypatch.setattr("app.api.v1.reviews.ReviewerWorkspaceService", lambda: _Svc())

    res = await client.post(
        f"/api/v1/reviewer/assignments/{assignment_id}/submit",
        cookies={"sf_review_magic": "token"},
        json={
            "comments_for_author": "public comments",
            "confidential_comments_to_editor": "",
            "recommendation": "reject",
            "attachments": [],
        },
    )
    assert res.status_code == 403
