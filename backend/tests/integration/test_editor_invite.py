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
                [{"id": editor_id, "email": "test@example.com", "roles": ["managing_editor"]}],
            ],
            "manuscripts": [
                {
                    "id": str(manuscript_id),
                    "author_id": "dddddddd-dddd-dddd-dddd-dddddddddddd",
                    "title": "Test Manuscript",
                    "version": 1,
                    "status": "pre_check",
                    "owner_id": editor_id,
                    "file_path": "manuscripts/x.pdf",
                    "journal_id": None,
                }
            ],
        }
    )

    supabase_admin = _Client(
        {
            "review_assignments": [
                [],  # existing check
                [],  # policy check
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
        patch("app.services.reviewer_service.supabase_admin", supabase_admin),
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


@pytest.mark.asyncio
async def test_editor_assign_blocked_by_cooldown_without_override(
    client: AsyncClient,
    auth_token: str,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("ADMIN_EMAILS", "test@example.com")
    monkeypatch.setenv("REVIEW_INVITE_COOLDOWN_DAYS", "30")
    monkeypatch.setenv("REVIEW_INVITE_COOLDOWN_OVERRIDE_ROLES", "admin,managing_editor")

    manuscript_id = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaab")
    reviewer_id = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbc")
    editor_id = "00000000-0000-0000-0000-000000000000"

    now_iso = "2026-02-09T00:00:00+00:00"
    cooldown_ms_id = "99999999-9999-9999-9999-999999999999"

    supabase = _Client(
        {
            "user_profiles": [
                [{"id": editor_id, "email": "test@example.com", "roles": ["managing_editor"]}],
            ],
            "manuscripts": [
                {
                    "id": str(manuscript_id),
                    "author_id": "dddddddd-dddd-dddd-dddd-dddddddddddd",
                    "title": "Cooldown Manuscript",
                    "version": 1,
                    "status": "pre_check",
                    "owner_id": editor_id,
                    "file_path": "manuscripts/x.pdf",
                    "journal_id": "journal-1",
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
                        "manuscript_id": cooldown_ms_id,
                        "reviewer_id": str(reviewer_id),
                        "status": "pending",
                        "due_at": None,
                        "invited_at": now_iso,
                        "created_at": now_iso,
                    }
                ],  # policy check
            ],
            "manuscripts": [
                [{"id": cooldown_ms_id, "journal_id": "journal-1"}],  # policy manuscript map
            ],
        }
    )

    headers = {"Authorization": f"Bearer {auth_token}"}
    body = {"manuscript_id": str(manuscript_id), "reviewer_id": str(reviewer_id)}

    with (
        patch("app.api.v1.reviews.supabase", supabase),
        patch("app.api.v1.reviews.supabase_admin", supabase_admin),
        patch("app.services.reviewer_service.supabase_admin", supabase_admin),
        patch("app.lib.api_client.supabase", supabase),
        patch("app.lib.api_client.supabase_admin", supabase_admin),
        patch("app.core.roles.supabase", supabase),
        patch("app.api.v1.reviews.NotificationService.create_notification", lambda *args, **kwargs: None),
    ):
        resp = await client.post("/api/v1/reviews/assign", json=body, headers=headers)
        assert resp.status_code == 409
        assert "cooldown" in str(resp.json().get("detail", "")).lower()


@pytest.mark.asyncio
async def test_editor_assign_allows_cooldown_override_for_high_privilege_role(
    client: AsyncClient,
    auth_token: str,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("ADMIN_EMAILS", "test@example.com")
    monkeypatch.setenv("MAGIC_LINK_JWT_SECRET", "test-secret")
    monkeypatch.setenv("FRONTEND_BASE_URL", "http://localhost:3000")
    monkeypatch.setenv("REVIEW_INVITE_COOLDOWN_DAYS", "30")

    manuscript_id = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaac")
    reviewer_id = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbd")
    editor_id = "00000000-0000-0000-0000-000000000000"
    assignment_id = UUID("cccccccc-cccc-cccc-cccc-cccccccccccd")

    now_iso = "2026-02-09T00:00:00+00:00"
    cooldown_ms_id = "99999999-9999-9999-9999-999999999998"

    supabase = _Client(
        {
            "user_profiles": [
                [{"id": editor_id, "email": "test@example.com", "roles": ["managing_editor"]}],
            ],
            "manuscripts": [
                {
                    "id": str(manuscript_id),
                    "author_id": "dddddddd-dddd-dddd-dddd-dddddddddddd",
                    "title": "Cooldown Override Manuscript",
                    "version": 1,
                    "status": "pre_check",
                    "owner_id": editor_id,
                    "file_path": "manuscripts/x.pdf",
                    "journal_id": "journal-1",
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
                        "manuscript_id": cooldown_ms_id,
                        "reviewer_id": str(reviewer_id),
                        "status": "pending",
                        "due_at": None,
                        "invited_at": now_iso,
                        "created_at": now_iso,
                    }
                ],  # policy check
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
                [{"id": cooldown_ms_id, "journal_id": "journal-1"}],  # policy manuscript map
                [{}],  # update under_review
            ],
            "status_transition_logs": [
                [{}],  # override audit insert
            ],
            "user_profiles": [
                {"email": "reviewer@example.com", "full_name": "Reviewer X"},
            ],
            "journals": [
                {"title": "Journal One"},
            ],
        }
    )

    send_mock = MagicMock()
    headers = {"Authorization": f"Bearer {auth_token}"}
    body = {
        "manuscript_id": str(manuscript_id),
        "reviewer_id": str(reviewer_id),
        "override_cooldown": True,
        "override_reason": "Need niche expertise for this round",
    }

    with (
        patch("app.api.v1.reviews.supabase", supabase),
        patch("app.api.v1.reviews.supabase_admin", supabase_admin),
        patch("app.services.reviewer_service.supabase_admin", supabase_admin),
        patch("app.lib.api_client.supabase", supabase),
        patch("app.lib.api_client.supabase_admin", supabase_admin),
        patch("app.core.roles.supabase", supabase),
        patch("app.api.v1.reviews.NotificationService.create_notification", lambda *args, **kwargs: None),
        patch("app.api.v1.reviews.email_service.send_email_background", send_mock),
    ):
        resp = await client.post("/api/v1/reviews/assign", json=body, headers=headers)
        assert resp.status_code == 200
        payload = resp.json()
        assert payload.get("success") is True
        assert payload.get("policy", {}).get("cooldown_active") is True

    assert send_mock.call_count == 1


@pytest.mark.asyncio
async def test_editor_assign_requires_assistant_editor_ownership_for_assignment(
    client: AsyncClient,
    auth_token: str,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("ADMIN_EMAILS", "nobody@example.com")

    manuscript_id = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaae")
    reviewer_id = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbf")
    profile_user_id = "00000000-0000-0000-0000-000000000222"
    foreign_ae_id = "11111111-1111-1111-1111-111111111111"

    supabase = _Client(
        {
            "user_profiles": [
                [{"id": profile_user_id, "email": "assistant@example.com", "roles": ["assistant_editor"]}],
            ],
            "manuscripts": [
                {
                    "id": str(manuscript_id),
                    "author_id": "dddddddd-dddd-dddd-dddd-dddddddddddd",
                    "title": "RBAC Ownership Check",
                    "version": 1,
                    "status": "under_review",
                    "owner_id": profile_user_id,
                    "assistant_editor_id": foreign_ae_id,
                    "file_path": "manuscripts/x.pdf",
                    "journal_id": "journal-1",
                }
            ],
        }
    )
    supabase_admin = _Client({"review_assignments": [], "manuscripts": []})

    headers = {"Authorization": f"Bearer {auth_token}"}
    body = {
        "manuscript_id": str(manuscript_id),
        "reviewer_id": str(reviewer_id),
        "override_cooldown": True,
        "override_reason": "should fail before policy",
    }

    with (
        patch("app.api.v1.reviews.supabase", supabase),
        patch("app.api.v1.reviews.supabase_admin", supabase_admin),
        patch("app.services.reviewer_service.supabase_admin", supabase_admin),
        patch("app.lib.api_client.supabase", supabase),
        patch("app.lib.api_client.supabase_admin", supabase_admin),
        patch("app.core.roles.supabase", supabase),
        patch("app.api.v1.reviews.NotificationService.create_notification", lambda *args, **kwargs: None),
    ):
        resp = await client.post("/api/v1/reviews/assign", json=body, headers=headers)
        assert resp.status_code == 403
        assert "assistant editor" in str(resp.json().get("detail", "")).lower()
