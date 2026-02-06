from __future__ import annotations

from typing import Any
from urllib.parse import parse_qs, unquote, urlparse
from uuid import UUID

import pytest
from httpx import AsyncClient
from unittest.mock import MagicMock, patch

from app.core.security import decode_magic_link_jwt


class _Resp:
    def __init__(self, data: Any):
        self.data = data
        self.error = None


class _Table:
    def __init__(self, client: "_Client", name: str):
        self._client = client
        self._name = name

    # Chainable query builder
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

    def single(self):
        return self

    def insert(self, *_args, **_kwargs):
        return self

    def update(self, *_args, **_kwargs):
        return self

    def delete(self, *_args, **_kwargs):
        return self

    def execute(self):
        return _Resp(self._client._pop(self._name))


class _Client:
    def __init__(self, responses: dict[str, list[Any]]):
        self._responses = responses

    def table(self, name: str):
        return _Table(self, name)

    def _pop(self, name: str):
        queue = self._responses.get(name) or []
        if not queue:
            return []  # safe default
        return queue.pop(0)


@pytest.mark.asyncio
async def test_editor_assign_sends_magic_link(client: AsyncClient, auth_token: str, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("ADMIN_EMAILS", "test@example.com")
    monkeypatch.setenv("MAGIC_LINK_JWT_SECRET", "test-secret")
    monkeypatch.setenv("FRONTEND_BASE_URL", "http://localhost:3000")

    manuscript_id = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    reviewer_id = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
    editor_id = "00000000-0000-0000-0000-000000000000"
    assignment_id = UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")

    supabase = _Client(
        {
            "user_profiles": [
                [{"id": editor_id, "email": "test@example.com", "roles": ["editor"]}],
            ],
            "manuscripts": [
                {
                    "author_id": "dddddddd-dddd-dddd-dddd-dddddddddddd",
                    "title": "Test Manuscript",
                    "version": 1,
                    "status": "pre_check",
                    "owner_id": editor_id,
                    "file_path": "manuscripts/x.pdf",
                }
            ],
        }
    )

    supabase_admin = _Client(
        {
            "review_assignments": [
                [],  # existing check
                [
                    {
                        "id": str(assignment_id),
                        "manuscript_id": str(manuscript_id),
                        "reviewer_id": str(reviewer_id),
                        "status": "pending",
                    }
                ],  # insert
            ],
            "manuscripts": [
                [{}],  # update under_review
            ],
            "user_profiles": [
                {"email": "reviewer@example.com"},
            ],
        }
    )

    send_mock = MagicMock()

    headers = {"Authorization": f"Bearer {auth_token}"}
    body = {"manuscript_id": str(manuscript_id), "reviewer_id": str(reviewer_id)}

    with (
        patch("app.api.v1.reviews.supabase", supabase),
        patch("app.api.v1.reviews.supabase_admin", supabase_admin),
        patch("app.lib.api_client.supabase", supabase),
        patch("app.lib.api_client.supabase_admin", supabase_admin),
        patch("app.core.roles.supabase", supabase),
        patch("app.api.v1.reviews.NotificationService.create_notification", lambda *args, **kwargs: None),
        patch("app.api.v1.reviews.email_service.send_email_background", send_mock),
    ):
        resp = await client.post("/api/v1/reviews/assign", json=body, headers=headers)
        assert resp.status_code == 200
        assert resp.json().get("success") is True

    assert send_mock.call_count == 1
    kwargs = send_mock.call_args.kwargs
    context = kwargs.get("context") or {}
    review_url = str(context.get("review_url") or "")
    assert "/review/invite" in review_url

    parsed = urlparse(review_url)
    qs = parse_qs(parsed.query)
    token = unquote((qs.get("token") or [""])[0])
    assert token

    payload = decode_magic_link_jwt(token)
    assert payload.reviewer_id == reviewer_id
    assert payload.manuscript_id == manuscript_id
    assert payload.assignment_id == assignment_id

