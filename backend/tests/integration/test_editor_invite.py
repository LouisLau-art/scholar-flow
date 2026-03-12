from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

import pytest
from httpx import AsyncClient
from unittest.mock import MagicMock, patch


class _Resp:
    def __init__(self, data: Any):
        self.data = data
        self.error = None


class _Table:
    def __init__(self, client: "_Client", name: str):
        self._client = client
        self._name = name
        self._pending_insert_payload = None
        self._pending_update_payload = None
        self._pending_delete = False

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

    def insert(self, payload=None, *_args, **_kwargs):
        self._pending_insert_payload = payload
        return self

    def update(self, payload=None, *_args, **_kwargs):
        self._pending_update_payload = payload
        return self

    def delete(self, *_args, **_kwargs):
        self._pending_delete = True
        return self

    def execute(self):
        if self._pending_insert_payload is not None:
            self._client._insert_calls.setdefault(self._name, []).append(self._pending_insert_payload)
            self._pending_insert_payload = None
        if self._pending_update_payload is not None:
            self._client._update_calls.setdefault(self._name, []).append(self._pending_update_payload)
            self._pending_update_payload = None
        if self._pending_delete:
            self._client._delete_calls[self._name] = self._client._delete_calls.get(self._name, 0) + 1
            self._pending_delete = False
        return _Resp(self._client._pop(self._name))


class _Client:
    def __init__(self, responses: dict[str, list[Any]]):
        self._responses = responses
        self._insert_calls: dict[str, list[Any]] = {}
        self._update_calls: dict[str, list[Any]] = {}
        self._delete_calls: dict[str, int] = {}

    def table(self, name: str):
        return _Table(self, name)

    def _pop(self, name: str):
        queue = self._responses.get(name) or []
        if not queue:
            return []  # safe default
        return queue.pop(0)


@pytest.mark.asyncio
async def test_editor_assign_creates_selected_assignment_without_sending_email(
    client: AsyncClient,
    auth_token: str,
    monkeypatch: pytest.MonkeyPatch,
):
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
                        "status": "selected",
                    }
                ],  # insert
            ],
            "user_profiles": [
                {"email": "reviewer@example.com"},
            ],
        }
    )

    send_mock = MagicMock(
        return_value={
            "ok": True,
            "status": "sent",
            "subject": "Invitation to Review",
            "provider_id": "re_mock_id",
            "error_message": None,
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
        patch("app.api.v1.reviews.email_service.send_email_background", send_mock),
    ):
        resp = await client.post("/api/v1/reviews/assign", json=body, headers=headers)
        assert resp.status_code == 200
        assert resp.json().get("success") is True

    assert send_mock.call_count == 0
    insert_payload = supabase_admin._insert_calls["review_assignments"][0]
    assert insert_payload["status"] == "selected"
    assert insert_payload["selected_by"] == editor_id
    assert insert_payload["selected_via"] == "editor_selection"
    assert "invited_at" not in insert_payload
    assert supabase_admin._update_calls.get("manuscripts") in (None, [])
    assert supabase_admin._insert_calls.get("status_transition_logs") in (None, [])


@pytest.mark.asyncio
async def test_editor_assign_allows_cooldown_without_override(
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

    now_iso = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
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
    ):
        resp = await client.post("/api/v1/reviews/assign", json=body, headers=headers)
        assert resp.status_code == 200
        payload = resp.json()
        assert payload.get("success") is True
        assert payload.get("policy", {}).get("cooldown_active") is True

    insert_payload = supabase_admin._insert_calls["review_assignments"][0]
    assert insert_payload["status"] == "selected"


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

    now_iso = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
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
                        "status": "selected",
                    }
                ],  # insert
            ],
            "manuscripts": [[{"id": cooldown_ms_id, "journal_id": "journal-1"}]],  # policy manuscript map
            "user_profiles": [
                {"email": "reviewer@example.com", "full_name": "Reviewer X"},
            ],
            "journals": [
                {"title": "Journal One"},
            ],
        }
    )

    send_mock = MagicMock(
        return_value={
            "ok": True,
            "status": "sent",
            "subject": "Invitation to Review",
            "provider_id": "re_mock_id",
            "error_message": None,
        }
    )
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
        patch("app.api.v1.reviews.email_service.send_email_background", send_mock),
    ):
        resp = await client.post("/api/v1/reviews/assign", json=body, headers=headers)
        assert resp.status_code == 200
        payload = resp.json()
        assert payload.get("success") is True
        assert payload.get("policy", {}).get("cooldown_active") is True

    assert send_mock.call_count == 0
    insert_payload = supabase_admin._insert_calls["review_assignments"][0]
    assert insert_payload["status"] == "selected"
    assert "invited_at" not in insert_payload


@pytest.mark.asyncio
async def test_editor_assign_allows_cooldown_override_for_assistant_editor_when_reason_provided(
    client: AsyncClient,
    auth_token: str,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("ADMIN_EMAILS", "test@example.com")
    monkeypatch.setenv("MAGIC_LINK_JWT_SECRET", "test-secret")
    monkeypatch.setenv("FRONTEND_BASE_URL", "http://localhost:3000")
    monkeypatch.setenv("REVIEW_INVITE_COOLDOWN_DAYS", "30")
    monkeypatch.setenv("REVIEW_INVITE_COOLDOWN_OVERRIDE_ROLES", "admin,managing_editor")

    manuscript_id = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaad")
    reviewer_id = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbe")
    editor_id = "00000000-0000-0000-0000-000000000000"
    assignment_id = UUID("cccccccc-cccc-cccc-cccc-ccccccccccce")

    now_iso = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    cooldown_ms_id = "99999999-9999-9999-9999-999999999997"

    supabase = _Client(
        {
            "user_profiles": [
                [{"id": editor_id, "email": "test@example.com", "roles": ["assistant_editor"]}],
            ],
            "manuscripts": [
                {
                    "id": str(manuscript_id),
                    "author_id": "dddddddd-dddd-dddd-dddd-dddddddddddd",
                    "title": "Cooldown Override AE Manuscript",
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
                [],
                [
                    {
                        "manuscript_id": cooldown_ms_id,
                        "reviewer_id": str(reviewer_id),
                        "status": "pending",
                        "due_at": None,
                        "invited_at": now_iso,
                        "created_at": now_iso,
                    }
                ],
                [
                    {
                        "id": str(assignment_id),
                        "manuscript_id": str(manuscript_id),
                        "reviewer_id": str(reviewer_id),
                        "status": "selected",
                    }
                ],
            ],
            "manuscripts": [[{"id": cooldown_ms_id, "journal_id": "journal-1"}]],
        }
    )

    headers = {"Authorization": f"Bearer {auth_token}"}
    body = {
        "manuscript_id": str(manuscript_id),
        "reviewer_id": str(reviewer_id),
        "override_cooldown": True,
        "override_reason": "AE manually approves cooldown override for urgent reassignment",
    }

    with (
        patch("app.api.v1.reviews.supabase", supabase),
        patch("app.api.v1.reviews.supabase_admin", supabase_admin),
        patch("app.services.reviewer_service.supabase_admin", supabase_admin),
        patch("app.lib.api_client.supabase", supabase),
        patch("app.lib.api_client.supabase_admin", supabase_admin),
        patch("app.core.roles.supabase", supabase),
    ):
        resp = await client.post("/api/v1/reviews/assign", json=body, headers=headers)
        assert resp.status_code == 200
        payload = resp.json()
        assert payload.get("success") is True
        assert payload.get("policy", {}).get("cooldown_active") is True
    assert supabase_admin._update_calls.get("manuscripts") in (None, [])
    assert supabase_admin._insert_calls.get("status_transition_logs") in (None, [])


@pytest.mark.asyncio
async def test_send_assignment_email_marks_invited_and_advances_manuscript(
    client: AsyncClient,
    auth_token: str,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("ADMIN_EMAILS", "test@example.com")
    monkeypatch.setenv("MAGIC_LINK_JWT_SECRET", "test-secret")
    monkeypatch.setenv("FRONTEND_BASE_URL", "http://localhost:3000")

    assignment_id = UUID("cccccccc-cccc-cccc-cccc-ccccccccccce")
    manuscript_id = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaf")
    reviewer_id = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbe")
    editor_id = "00000000-0000-0000-0000-000000000000"

    supabase = _Client(
        {
            "user_profiles": [
                [{"id": editor_id, "email": "test@example.com", "roles": ["managing_editor"]}],
            ],
        }
    )
    supabase_admin = _Client(
        {
            "email_templates": [],
            "review_assignments": [
                {
                    "id": str(assignment_id),
                    "manuscript_id": str(manuscript_id),
                    "reviewer_id": str(reviewer_id),
                    "status": "selected",
                    "due_at": "2026-03-20T00:00:00+00:00",
                    "invited_at": None,
                    "last_reminded_at": None,
                    "invited_by": None,
                    "invited_via": None,
                },
                [{}],
            ],
            "manuscripts": [
                {
                    "id": str(manuscript_id),
                    "title": "Selection First Workflow",
                    "journal_id": "journal-1",
                    "assistant_editor_id": editor_id,
                    "status": "pre_check",
                },
                [{}],
            ],
            "user_profiles": [
                {"email": "reviewer@example.com", "full_name": "Reviewer X"},
            ],
            "journals": [
                {"title": "Journal One"},
            ],
        }
    )

    send_mock = MagicMock(
        return_value={
            "ok": True,
            "status": "sent",
            "subject": "Invitation to Review",
            "provider_id": "re_mock_id",
            "error_message": None,
        }
    )
    headers = {"Authorization": f"Bearer {auth_token}"}

    with (
        patch("app.api.v1.reviews.supabase", supabase),
        patch("app.api.v1.reviews.supabase_admin", supabase_admin),
        patch("app.services.reviewer_service.supabase_admin", supabase_admin),
        patch("app.lib.api_client.supabase", supabase),
        patch("app.lib.api_client.supabase_admin", supabase_admin),
        patch("app.core.roles.supabase", supabase),
        patch("app.api.v1.reviews.email_service.send_inline_email", send_mock),
    ):
        resp = await client.post(
            f"/api/v1/reviews/assignments/{assignment_id}/send-email",
            json={"template_key": "reviewer_invitation_standard"},
            headers=headers,
        )

    assert resp.status_code == 200
    payload = resp.json()
    assert payload.get("success") is True
    assert payload["data"]["event_type"] == "invitation"
    assert payload["data"]["delivery_status"] == "sent"
    assert send_mock.call_count == 1

    assignment_patch = supabase_admin._update_calls["review_assignments"][0]
    assert assignment_patch["status"] == "invited"
    assert assignment_patch["invited_at"]
    assert assignment_patch["invited_by"] == editor_id
    assert assignment_patch["invited_via"] == "template_invitation"

    manuscript_patch = supabase_admin._update_calls["manuscripts"][0]
    assert manuscript_patch["status"] == "under_review"


@pytest.mark.asyncio
async def test_preview_assignment_email_returns_rendered_content(
    client: AsyncClient,
    auth_token: str,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("ADMIN_EMAILS", "test@example.com")
    monkeypatch.setenv("MAGIC_LINK_JWT_SECRET", "test-secret")
    monkeypatch.setenv("FRONTEND_BASE_URL", "https://scholar-flow-q1yw.vercel.app")

    assignment_id = UUID("cccccccc-cccc-cccc-cccc-ccccccccccaa")
    manuscript_id = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaacc")
    reviewer_id = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbaa")
    editor_id = "00000000-0000-0000-0000-000000000000"

    supabase = _Client(
        {
            "user_profiles": [
                [{"id": editor_id, "email": "test@example.com", "roles": ["managing_editor"]}],
            ],
        }
    )
    supabase_admin = _Client(
        {
            "email_templates": [],
            "review_assignments": [
                {
                    "id": str(assignment_id),
                    "manuscript_id": str(manuscript_id),
                    "reviewer_id": str(reviewer_id),
                    "status": "selected",
                    "due_at": "2026-03-20T00:00:00+00:00",
                    "invited_at": None,
                    "last_reminded_at": None,
                    "invited_by": None,
                    "invited_via": None,
                },
            ],
            "manuscripts": [
                {
                    "id": str(manuscript_id),
                    "title": "Preview Manuscript",
                    "journal_id": "journal-1",
                    "assistant_editor_id": editor_id,
                    "status": "pre_check",
                },
            ],
            "user_profiles": [
                {"email": "reviewer@example.com", "full_name": "Reviewer X"},
            ],
            "journals": [
                {"title": "Journal One"},
            ],
        }
    )

    headers = {"Authorization": f"Bearer {auth_token}"}

    with (
        patch("app.api.v1.reviews.supabase", supabase),
        patch("app.api.v1.reviews.supabase_admin", supabase_admin),
        patch("app.services.reviewer_service.supabase_admin", supabase_admin),
        patch("app.lib.api_client.supabase", supabase),
        patch("app.lib.api_client.supabase_admin", supabase_admin),
        patch("app.core.roles.supabase", supabase),
    ):
        resp = await client.post(
            f"/api/v1/reviews/assignments/{assignment_id}/preview-email",
            json={"template_key": "reviewer_invitation_standard"},
            headers=headers,
        )

    assert resp.status_code == 200
    payload = resp.json()
    assert payload.get("success") is True
    data = payload["data"]
    assert data["template_key"] == "reviewer_invitation_standard"
    assert data["reviewer_email"] == "reviewer@example.com"
    assert data["recipient_email"] == "reviewer@example.com"
    assert data["recipient_overridden"] is False
    assert "Invitation to Review" in data["subject"]
    assert "Preview Manuscript" in data["html"]
    assert "https://scholar-flow-q1yw.vercel.app/review/invite?token=" in data["review_url"]


@pytest.mark.asyncio
async def test_send_assignment_email_with_recipient_override_does_not_advance_assignment(
    client: AsyncClient,
    auth_token: str,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("ADMIN_EMAILS", "test@example.com")
    monkeypatch.setenv("MAGIC_LINK_JWT_SECRET", "test-secret")
    monkeypatch.setenv("FRONTEND_BASE_URL", "https://scholar-flow-q1yw.vercel.app")

    assignment_id = UUID("cccccccc-cccc-cccc-cccc-ccccccccccab")
    manuscript_id = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaacd")
    reviewer_id = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbab")
    editor_id = "00000000-0000-0000-0000-000000000000"

    supabase = _Client(
        {
            "user_profiles": [
                [{"id": editor_id, "email": "test@example.com", "roles": ["managing_editor"]}],
            ],
        }
    )
    supabase_admin = _Client(
        {
            "email_templates": [],
            "review_assignments": [
                {
                    "id": str(assignment_id),
                    "manuscript_id": str(manuscript_id),
                    "reviewer_id": str(reviewer_id),
                    "status": "selected",
                    "due_at": "2026-03-20T00:00:00+00:00",
                    "invited_at": None,
                    "last_reminded_at": None,
                    "invited_by": None,
                    "invited_via": None,
                },
            ],
            "manuscripts": [
                {
                    "id": str(manuscript_id),
                    "title": "Preview Override Manuscript",
                    "journal_id": "journal-1",
                    "assistant_editor_id": editor_id,
                    "status": "pre_check",
                },
            ],
            "user_profiles": [
                {"email": "reviewer@example.com", "full_name": "Reviewer X"},
            ],
            "journals": [
                {"title": "Journal One"},
            ],
        }
    )

    send_mock = MagicMock(
        return_value={
            "ok": True,
            "status": "sent",
            "subject": "Invitation to Review",
            "provider_id": "re_mock_id",
            "error_message": None,
        }
    )
    headers = {"Authorization": f"Bearer {auth_token}"}

    with (
        patch("app.api.v1.reviews.supabase", supabase),
        patch("app.api.v1.reviews.supabase_admin", supabase_admin),
        patch("app.services.reviewer_service.supabase_admin", supabase_admin),
        patch("app.lib.api_client.supabase", supabase),
        patch("app.lib.api_client.supabase_admin", supabase_admin),
        patch("app.core.roles.supabase", supabase),
        patch("app.api.v1.reviews.email_service.send_inline_email", send_mock),
    ):
        resp = await client.post(
            f"/api/v1/reviews/assignments/{assignment_id}/send-email",
            json={
                "template_key": "reviewer_invitation_standard",
                "recipient_email": "assistant@example.com",
            },
            headers=headers,
        )

    assert resp.status_code == 200
    payload = resp.json()
    assert payload.get("success") is True
    assert payload["data"]["delivery_status"] == "sent"
    assert payload["data"]["preview_send"] is True
    assert payload["data"]["recipient_overridden"] is True
    assert payload["data"]["recipient"] == "assistant@example.com"
    assert send_mock.call_args.kwargs["to_email"] == "assistant@example.com"
    assert supabase_admin._update_calls.get("review_assignments") in (None, [])
    assert supabase_admin._update_calls.get("manuscripts") in (None, [])


@pytest.mark.asyncio
async def test_preview_assignment_email_accepts_compose_overrides(
    client: AsyncClient,
    auth_token: str,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("ADMIN_EMAILS", "test@example.com")
    monkeypatch.setenv("MAGIC_LINK_JWT_SECRET", "test-secret")
    monkeypatch.setenv("FRONTEND_BASE_URL", "https://scholar-flow-q1yw.vercel.app")

    assignment_id = UUID("cccccccc-cccc-cccc-cccc-ccccccccccad")
    manuscript_id = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaace")
    reviewer_id = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbac")
    editor_id = "00000000-0000-0000-0000-000000000000"

    supabase = _Client(
        {
            "user_profiles": [
                [{"id": editor_id, "email": "test@example.com", "roles": ["managing_editor"]}],
            ],
        }
    )
    supabase_admin = _Client(
        {
            "email_templates": [],
            "review_assignments": [
                {
                    "id": str(assignment_id),
                    "manuscript_id": str(manuscript_id),
                    "reviewer_id": str(reviewer_id),
                    "status": "selected",
                    "due_at": "2026-03-20T00:00:00+00:00",
                    "invited_at": None,
                    "last_reminded_at": None,
                    "invited_by": None,
                    "invited_via": None,
                },
            ],
            "manuscripts": [
                {
                    "id": str(manuscript_id),
                    "title": "Preview Override Manuscript",
                    "journal_id": "journal-1",
                    "assistant_editor_id": editor_id,
                    "status": "pre_check",
                },
            ],
            "user_profiles": [
                {"email": "reviewer@example.com", "full_name": "Reviewer X"},
            ],
            "journals": [
                {"title": "Journal One"},
            ],
        }
    )

    headers = {"Authorization": f"Bearer {auth_token}"}

    with (
        patch("app.api.v1.reviews.supabase", supabase),
        patch("app.api.v1.reviews.supabase_admin", supabase_admin),
        patch("app.services.reviewer_service.supabase_admin", supabase_admin),
        patch("app.lib.api_client.supabase", supabase),
        patch("app.lib.api_client.supabase_admin", supabase_admin),
        patch("app.core.roles.supabase", supabase),
    ):
        resp = await client.post(
            f"/api/v1/reviews/assignments/{assignment_id}/preview-email",
            json={
                "template_key": "reviewer_invitation_standard",
                "subject_override": "Custom reviewer subject",
                "body_html_override": '<p>Hello <a href="https://example.com/review">Review Link</a></p>',
            },
            headers=headers,
        )

    assert resp.status_code == 200
    payload = resp.json()
    assert payload.get("success") is True
    data = payload["data"]
    assert data["subject"] == "Custom reviewer subject"
    assert data["html"] == '<p>Hello <a href="https://example.com/review">Review Link</a></p>'
    assert data["text"] == "Hello Review Link (https://example.com/review)"


@pytest.mark.asyncio
async def test_send_assignment_email_uses_compose_overrides_without_advancing_assignment(
    client: AsyncClient,
    auth_token: str,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("ADMIN_EMAILS", "test@example.com")
    monkeypatch.setenv("MAGIC_LINK_JWT_SECRET", "test-secret")
    monkeypatch.setenv("FRONTEND_BASE_URL", "https://scholar-flow-q1yw.vercel.app")

    assignment_id = UUID("cccccccc-cccc-cccc-cccc-ccccccccccae")
    manuscript_id = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaacf")
    reviewer_id = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbad")
    editor_id = "00000000-0000-0000-0000-000000000000"

    supabase = _Client(
        {
            "user_profiles": [
                [{"id": editor_id, "email": "test@example.com", "roles": ["managing_editor"]}],
            ],
        }
    )
    supabase_admin = _Client(
        {
            "email_templates": [],
            "review_assignments": [
                {
                    "id": str(assignment_id),
                    "manuscript_id": str(manuscript_id),
                    "reviewer_id": str(reviewer_id),
                    "status": "selected",
                    "due_at": "2026-03-20T00:00:00+00:00",
                    "invited_at": None,
                    "last_reminded_at": None,
                    "invited_by": None,
                    "invited_via": None,
                },
            ],
            "manuscripts": [
                {
                    "id": str(manuscript_id),
                    "title": "Override Send Manuscript",
                    "journal_id": "journal-1",
                    "assistant_editor_id": editor_id,
                    "status": "pre_check",
                },
            ],
            "user_profiles": [
                {"email": "reviewer@example.com", "full_name": "Reviewer X"},
            ],
            "journals": [
                {"title": "Journal One"},
            ],
        }
    )

    send_mock = MagicMock(
        return_value={
            "ok": True,
            "status": "sent",
            "subject": "Custom reviewer subject",
            "provider_id": "re_mock_id",
            "error_message": None,
        }
    )
    headers = {"Authorization": f"Bearer {auth_token}"}

    with (
        patch("app.api.v1.reviews.supabase", supabase),
        patch("app.api.v1.reviews.supabase_admin", supabase_admin),
        patch("app.services.reviewer_service.supabase_admin", supabase_admin),
        patch("app.lib.api_client.supabase", supabase),
        patch("app.lib.api_client.supabase_admin", supabase_admin),
        patch("app.core.roles.supabase", supabase),
        patch("app.api.v1.reviews.email_service.send_rendered_email", send_mock),
    ):
        resp = await client.post(
            f"/api/v1/reviews/assignments/{assignment_id}/send-email",
            json={
                "template_key": "reviewer_invitation_standard",
                "recipient_email": "assistant@example.com",
                "subject_override": "Custom reviewer subject",
                "body_html_override": '<p>Hello <a href="https://example.com/review">Review Link</a></p>',
            },
            headers=headers,
        )

    assert resp.status_code == 200
    payload = resp.json()
    assert payload.get("success") is True
    assert payload["data"]["delivery_status"] == "sent"
    assert payload["data"]["preview_send"] is True
    assert payload["data"]["recipient_overridden"] is True
    assert payload["data"]["recipient"] == "assistant@example.com"
    assert send_mock.call_args.kwargs["to_email"] == "assistant@example.com"
    assert send_mock.call_args.kwargs["subject"] == "Custom reviewer subject"
    assert send_mock.call_args.kwargs["html_body"] == '<p>Hello <a href="https://example.com/review">Review Link</a></p>'
    assert send_mock.call_args.kwargs["text_body"] == "Hello Review Link (https://example.com/review)"
    assert supabase_admin._update_calls.get("review_assignments") in (None, [])
    assert supabase_admin._update_calls.get("manuscripts") in (None, [])


@pytest.mark.asyncio
async def test_cancel_assignment_marks_cancel_audit_and_preserves_history(
    client: AsyncClient,
    auth_token: str,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("ADMIN_EMAILS", "test@example.com")

    assignment_id = UUID("cccccccc-cccc-cccc-cccc-cccccccccc11")
    manuscript_id = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaa11")
    reviewer_id = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbb111")
    editor_id = "00000000-0000-0000-0000-000000000000"

    supabase = _Client(
        {
            "user_profiles": [
                [{"id": editor_id, "email": "test@example.com", "roles": ["assistant_editor"]}],
            ],
        }
    )
    supabase_admin = _Client(
        {
            "review_assignments": [
                {
                    "id": str(assignment_id),
                    "manuscript_id": str(manuscript_id),
                    "reviewer_id": str(reviewer_id),
                    "status": "accepted",
                    "round_number": 2,
                    "due_at": "2026-03-19T00:00:00+00:00",
                    "invited_at": "2026-03-09T12:00:00+00:00",
                    "opened_at": "2026-03-09T12:10:00+00:00",
                    "accepted_at": "2026-03-09T12:20:00+00:00",
                },
                [{}],
            ],
            "manuscripts": [
                {
                    "id": str(manuscript_id),
                    "title": "Enough Reviews Manuscript",
                    "journal_id": "journal-1",
                    "assistant_editor_id": editor_id,
                    "status": "under_review",
                }
            ],
        }
    )

    headers = {"Authorization": f"Bearer {auth_token}"}
    body = {
        "reason": "Enough completed reviews received",
        "via": "post_acceptance_cleanup",
        "send_email": False,
    }

    with (
        patch("app.api.v1.reviews.supabase", supabase),
        patch("app.api.v1.reviews.supabase_admin", supabase_admin),
        patch("app.services.reviewer_service.supabase_admin", supabase_admin),
        patch("app.lib.api_client.supabase", supabase),
        patch("app.lib.api_client.supabase_admin", supabase_admin),
        patch("app.core.roles.supabase", supabase),
    ):
        resp = await client.post(
            f"/api/v1/reviews/assignments/{assignment_id}/cancel",
            json=body,
            headers=headers,
        )

    assert resp.status_code == 200
    payload = resp.json()
    assert payload.get("success") is True
    patch_payload = supabase_admin._update_calls["review_assignments"][0]
    assert patch_payload["status"] == "cancelled"
    assert patch_payload["cancel_reason"] == "Enough completed reviews received"
    assert patch_payload["cancel_via"] == "post_acceptance_cleanup"
    assert patch_payload["cancelled_by"] == editor_id
    assert patch_payload["cancelled_at"]
    assert supabase_admin._delete_calls.get("review_assignments") is None


@pytest.mark.asyncio
async def test_cancel_assignment_sends_cancellation_email_when_requested(
    client: AsyncClient,
    auth_token: str,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("ADMIN_EMAILS", "test@example.com")

    assignment_id = UUID("cccccccc-cccc-cccc-cccc-cccccccccc13")
    manuscript_id = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaa13")
    reviewer_id = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbb113")
    editor_id = "00000000-0000-0000-0000-000000000000"

    supabase = _Client(
        {
            "user_profiles": [
                [{"id": editor_id, "email": "test@example.com", "roles": ["assistant_editor"]}],
            ],
        }
    )
    supabase_admin = _Client(
        {
            "review_assignments": [
                {
                    "id": str(assignment_id),
                    "manuscript_id": str(manuscript_id),
                    "reviewer_id": str(reviewer_id),
                    "status": "accepted",
                    "round_number": 2,
                    "due_at": "2026-03-19T00:00:00+00:00",
                    "invited_at": "2026-03-09T12:00:00+00:00",
                    "opened_at": "2026-03-09T12:10:00+00:00",
                    "accepted_at": "2026-03-09T12:20:00+00:00",
                },
                [{}],
            ],
            "manuscripts": [
                {
                    "id": str(manuscript_id),
                    "title": "Enough Reviews Manuscript",
                    "journal_id": "journal-1",
                    "assistant_editor_id": editor_id,
                    "status": "under_review",
                }
            ],
        }
    )

    send_mock = MagicMock(
        return_value={
            "status": "sent",
            "template_key": "reviewer_cancellation_standard",
            "error_message": None,
        }
    )
    headers = {"Authorization": f"Bearer {auth_token}"}
    body = {
        "reason": "Enough completed reviews received",
        "via": "post_acceptance_cleanup",
        "send_email": True,
    }

    with (
        patch("app.api.v1.reviews.supabase", supabase),
        patch("app.api.v1.reviews.supabase_admin", supabase_admin),
        patch("app.services.reviewer_service.supabase_admin", supabase_admin),
        patch("app.lib.api_client.supabase", supabase),
        patch("app.lib.api_client.supabase_admin", supabase_admin),
        patch("app.core.roles.supabase", supabase),
        patch(
            "app.api.v1.reviews_handlers_assignment_manage.send_reviewer_assignment_cancellation_email",
            send_mock,
        ),
    ):
        resp = await client.post(
            f"/api/v1/reviews/assignments/{assignment_id}/cancel",
            json=body,
            headers=headers,
        )

    assert resp.status_code == 200
    payload = resp.json()
    assert payload["data"]["email_status"] == "sent"
    assert payload["data"]["email_error"] is None
    send_mock.assert_called_once()


@pytest.mark.asyncio
async def test_cancel_assignment_skips_email_for_selected_shortlist(
    client: AsyncClient,
    auth_token: str,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("ADMIN_EMAILS", "test@example.com")

    assignment_id = UUID("cccccccc-cccc-cccc-cccc-cccccccccc14")
    manuscript_id = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaa14")
    reviewer_id = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbb114")
    editor_id = "00000000-0000-0000-0000-000000000000"

    supabase = _Client(
        {
            "user_profiles": [
                [{"id": editor_id, "email": "test@example.com", "roles": ["assistant_editor"]}],
            ],
        }
    )
    supabase_admin = _Client(
        {
            "review_assignments": [
                {
                    "id": str(assignment_id),
                    "manuscript_id": str(manuscript_id),
                    "reviewer_id": str(reviewer_id),
                    "status": "selected",
                    "round_number": 2,
                    "due_at": "2026-03-19T00:00:00+00:00",
                },
                [{}],
            ],
            "manuscripts": [
                {
                    "id": str(manuscript_id),
                    "title": "Shortlist Manuscript",
                    "journal_id": "journal-1",
                    "assistant_editor_id": editor_id,
                    "status": "under_review",
                }
            ],
        }
    )

    send_mock = MagicMock(
        return_value={
            "status": "sent",
            "template_key": "reviewer_cancellation_standard",
            "error_message": None,
        }
    )
    headers = {"Authorization": f"Bearer {auth_token}"}
    body = {
        "reason": "External review stage ended",
        "via": "auto_stage_exit",
        "send_email": True,
    }

    with (
        patch("app.api.v1.reviews.supabase", supabase),
        patch("app.api.v1.reviews.supabase_admin", supabase_admin),
        patch("app.services.reviewer_service.supabase_admin", supabase_admin),
        patch("app.lib.api_client.supabase", supabase),
        patch("app.lib.api_client.supabase_admin", supabase_admin),
        patch("app.core.roles.supabase", supabase),
        patch(
            "app.api.v1.reviews_handlers_assignment_manage.send_reviewer_assignment_cancellation_email",
            send_mock,
        ),
    ):
        resp = await client.post(
            f"/api/v1/reviews/assignments/{assignment_id}/cancel",
            json=body,
            headers=headers,
        )

    assert resp.status_code == 200
    payload = resp.json()
    assert payload["data"]["email_status"] == "skipped"
    assert payload["data"]["email_error"] == "Reviewer was never invited"
    send_mock.assert_not_called()


@pytest.mark.asyncio
async def test_cancel_assignment_can_retry_cancellation_email_after_idempotent_cancel(
    client: AsyncClient,
    auth_token: str,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("ADMIN_EMAILS", "test@example.com")

    assignment_id = UUID("cccccccc-cccc-cccc-cccc-cccccccccc15")
    manuscript_id = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaa15")
    reviewer_id = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbb115")
    editor_id = "00000000-0000-0000-0000-000000000000"

    supabase = _Client(
        {
            "user_profiles": [
                [{"id": editor_id, "email": "test@example.com", "roles": ["assistant_editor"]}],
            ],
        }
    )
    supabase_admin = _Client(
        {
            "review_assignments": [
                {
                    "id": str(assignment_id),
                    "manuscript_id": str(manuscript_id),
                    "reviewer_id": str(reviewer_id),
                    "status": "cancelled",
                    "round_number": 2,
                    "due_at": "2026-03-19T00:00:00+00:00",
                    "invited_at": "2026-03-09T12:00:00+00:00",
                    "opened_at": "2026-03-09T12:10:00+00:00",
                    "cancel_reason": "Enough completed reviews received",
                    "cancel_via": "post_acceptance_cleanup",
                },
                [{}],
            ],
            "manuscripts": [
                {
                    "id": str(manuscript_id),
                    "title": "Enough Reviews Manuscript",
                    "journal_id": "journal-1",
                    "assistant_editor_id": editor_id,
                    "status": "under_review",
                }
            ],
        }
    )

    send_mock = MagicMock(
        return_value={
            "status": "sent",
            "template_key": "reviewer_cancellation_standard",
            "error_message": None,
        }
    )
    headers = {"Authorization": f"Bearer {auth_token}"}
    body = {
        "reason": "Retry cancellation notice",
        "via": "post_acceptance_cleanup",
        "send_email": True,
    }

    with (
        patch("app.api.v1.reviews.supabase", supabase),
        patch("app.api.v1.reviews.supabase_admin", supabase_admin),
        patch("app.services.reviewer_service.supabase_admin", supabase_admin),
        patch("app.lib.api_client.supabase", supabase),
        patch("app.lib.api_client.supabase_admin", supabase_admin),
        patch("app.core.roles.supabase", supabase),
        patch(
            "app.api.v1.reviews_handlers_assignment_manage.send_reviewer_assignment_cancellation_email",
            send_mock,
        ),
    ):
        resp = await client.post(
            f"/api/v1/reviews/assignments/{assignment_id}/cancel",
            json=body,
            headers=headers,
        )

    assert resp.status_code == 200
    payload = resp.json()
    assert payload["data"]["idempotent"] is True
    assert payload["data"]["email_status"] == "sent"
    assert payload["data"]["email_error"] is None
    send_mock.assert_called_once()


@pytest.mark.asyncio
async def test_unassign_reviewer_rejects_non_selected_assignment(
    client: AsyncClient,
    auth_token: str,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("ADMIN_EMAILS", "test@example.com")

    assignment_id = UUID("cccccccc-cccc-cccc-cccc-cccccccccc12")
    manuscript_id = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaa12")
    reviewer_id = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbb112")
    editor_id = "00000000-0000-0000-0000-000000000000"

    supabase = _Client(
        {
            "user_profiles": [
                [{"id": editor_id, "email": "test@example.com", "roles": ["assistant_editor"]}],
            ],
        }
    )
    supabase_admin = _Client(
        {
            "review_assignments": [
                {
                    "manuscript_id": str(manuscript_id),
                    "reviewer_id": str(reviewer_id),
                    "round_number": 2,
                    "status": "invited",
                }
            ],
            "manuscripts": [
                {
                    "id": str(manuscript_id),
                    "journal_id": "journal-1",
                    "assistant_editor_id": editor_id,
                }
            ],
        }
    )

    headers = {"Authorization": f"Bearer {auth_token}"}

    with (
        patch("app.api.v1.reviews.supabase", supabase),
        patch("app.api.v1.reviews.supabase_admin", supabase_admin),
        patch("app.services.reviewer_service.supabase_admin", supabase_admin),
        patch("app.lib.api_client.supabase", supabase),
        patch("app.lib.api_client.supabase_admin", supabase_admin),
        patch("app.core.roles.supabase", supabase),
    ):
        resp = await client.delete(
            f"/api/v1/reviews/assign/{assignment_id}",
            headers=headers,
        )

    assert resp.status_code == 409
    assert "Use cancel" in resp.json()["detail"]
    assert supabase_admin._delete_calls.get("review_assignments") is None


@pytest.mark.asyncio
async def test_unassign_last_selected_reviewer_keeps_manuscript_under_review(
    client: AsyncClient,
    auth_token: str,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("ADMIN_EMAILS", "test@example.com")

    assignment_id = UUID("cccccccc-cccc-cccc-cccc-cccccccccc13")
    manuscript_id = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaa13")
    reviewer_id = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbb113")
    editor_id = "00000000-0000-0000-0000-000000000000"

    supabase = _Client(
        {
            "user_profiles": [
                [{"id": editor_id, "email": "test@example.com", "roles": ["assistant_editor"]}],
            ],
        }
    )
    supabase_admin = _Client(
        {
            "review_assignments": [
                {
                    "manuscript_id": str(manuscript_id),
                    "reviewer_id": str(reviewer_id),
                    "round_number": 2,
                    "status": "selected",
                },
                [],
            ],
            "manuscripts": [
                {
                    "id": str(manuscript_id),
                    "journal_id": "journal-1",
                    "assistant_editor_id": editor_id,
                    "status": "under_review",
                }
            ],
        }
    )

    headers = {"Authorization": f"Bearer {auth_token}"}

    with (
        patch("app.api.v1.reviews.supabase", supabase),
        patch("app.api.v1.reviews.supabase_admin", supabase_admin),
        patch("app.services.reviewer_service.supabase_admin", supabase_admin),
        patch("app.lib.api_client.supabase", supabase),
        patch("app.lib.api_client.supabase_admin", supabase_admin),
        patch("app.core.roles.supabase", supabase),
    ):
        resp = await client.delete(
            f"/api/v1/reviews/assign/{assignment_id}",
            headers=headers,
        )

    assert resp.status_code == 200
    assert resp.json()["success"] is True
    assert supabase_admin._delete_calls.get("review_assignments") == 1
    assert supabase_admin._update_calls.get("manuscripts") in (None, [])


@pytest.mark.asyncio
async def test_send_assignment_email_uses_fresh_idempotency_key_for_reinvited_assignment(
    client: AsyncClient,
    auth_token: str,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("ADMIN_EMAILS", "test@example.com")
    monkeypatch.setenv("MAGIC_LINK_JWT_SECRET", "test-secret")
    monkeypatch.setenv("FRONTEND_BASE_URL", "https://scholar-flow-q1yw.vercel.app")

    assignment_id = UUID("cccccccc-cccc-cccc-cccc-cccccccccccf")
    manuscript_id = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaab0")
    reviewer_id = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbb0")
    editor_id = "00000000-0000-0000-0000-000000000000"

    supabase = _Client(
        {
            "user_profiles": [
                [{"id": editor_id, "email": "test@example.com", "roles": ["managing_editor"]}],
            ],
        }
    )
    supabase_admin = _Client(
        {
            "email_templates": [],
            "review_assignments": [
                {
                    "id": str(assignment_id),
                    "manuscript_id": str(manuscript_id),
                    "reviewer_id": str(reviewer_id),
                    "status": "invited",
                    "due_at": "2026-03-20T00:00:00+00:00",
                    "invited_at": "2026-03-09T06:00:00+00:00",
                    "last_reminded_at": None,
                    "invited_by": editor_id,
                    "invited_via": "template_invitation",
                },
                [{}],
            ],
            "manuscripts": [
                {
                    "id": str(manuscript_id),
                    "title": "Invitation Resend Workflow",
                    "journal_id": "journal-1",
                    "assistant_editor_id": editor_id,
                    "status": "under_review",
                },
            ],
            "user_profiles": [
                {"email": "reviewer@example.com", "full_name": "Reviewer X"},
            ],
            "journals": [
                {"title": "Journal One"},
            ],
        }
    )

    send_mock = MagicMock(
        return_value={
            "ok": True,
            "status": "sent",
            "subject": "Invitation to Review",
            "provider_id": "re_mock_id",
            "error_message": None,
        }
    )
    headers = {"Authorization": f"Bearer {auth_token}"}

    with (
        patch("app.api.v1.reviews.supabase", supabase),
        patch("app.api.v1.reviews.supabase_admin", supabase_admin),
        patch("app.services.reviewer_service.supabase_admin", supabase_admin),
        patch("app.lib.api_client.supabase", supabase),
        patch("app.lib.api_client.supabase_admin", supabase_admin),
        patch("app.core.roles.supabase", supabase),
        patch("app.api.v1.reviews.email_service.send_inline_email", send_mock),
    ):
        resp = await client.post(
            f"/api/v1/reviews/assignments/{assignment_id}/send-email",
            json={"template_key": "reviewer_invitation_standard"},
            headers=headers,
        )

    assert resp.status_code == 200
    assert send_mock.call_count == 1
    send_kwargs = send_mock.call_args.kwargs
    assert send_kwargs["idempotency_key"].startswith(f"reviewer-invitation-resend/{assignment_id}/")
    assert send_kwargs["context"]["review_url"].startswith("https://scholar-flow-q1yw.vercel.app/review/invite?token=")


@pytest.mark.asyncio
async def test_send_assignment_email_reinvites_declined_assignment_with_fresh_attempt(
    client: AsyncClient,
    auth_token: str,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("ADMIN_EMAILS", "test@example.com")
    monkeypatch.setenv("MAGIC_LINK_JWT_SECRET", "test-secret")
    monkeypatch.setenv("FRONTEND_BASE_URL", "http://localhost:3000")

    declined_assignment_id = UUID("dddddddd-dddd-dddd-dddd-ddddddddddde")
    fresh_assignment_id = UUID("eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeef")
    manuscript_id = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaba")
    reviewer_id = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbba")
    editor_id = "00000000-0000-0000-0000-000000000000"

    supabase = _Client(
        {
            "user_profiles": [
                [{"id": editor_id, "email": "test@example.com", "roles": ["managing_editor"]}],
            ],
        }
    )
    supabase_admin = _Client(
        {
            "email_templates": [],
            "review_assignments": [
                {
                    "id": str(declined_assignment_id),
                    "manuscript_id": str(manuscript_id),
                    "reviewer_id": str(reviewer_id),
                    "status": "declined",
                    "due_at": "2026-03-21T00:00:00+00:00",
                    "invited_at": "2026-03-10T00:00:00+00:00",
                    "last_reminded_at": None,
                    "invited_by": editor_id,
                    "invited_via": "template_invitation",
                    "round_number": 1,
                    "selected_by": editor_id,
                    "selected_via": "editor_selection",
                    "declined_at": "2026-03-11T00:00:00+00:00",
                },
                [
                    {
                        "id": str(fresh_assignment_id),
                        "manuscript_id": str(manuscript_id),
                        "reviewer_id": str(reviewer_id),
                        "status": "invited",
                    }
                ],
            ],
            "manuscripts": [
                {
                    "id": str(manuscript_id),
                    "title": "Declined Reinvite Workflow",
                    "journal_id": "journal-1",
                    "assistant_editor_id": editor_id,
                    "status": "pre_check",
                },
                [{}],
            ],
            "user_profiles": [
                {"email": "reviewer@example.com", "full_name": "Reviewer X"},
            ],
            "journals": [
                {"title": "Journal One"},
            ],
        }
    )

    send_mock = MagicMock(
        return_value={
            "ok": True,
            "status": "sent",
            "subject": "Invitation to Review",
            "provider_id": "re_mock_id",
            "error_message": None,
        }
    )
    headers = {"Authorization": f"Bearer {auth_token}"}

    with (
        patch("app.api.v1.reviews.supabase", supabase),
        patch("app.api.v1.reviews.supabase_admin", supabase_admin),
        patch("app.services.reviewer_service.supabase_admin", supabase_admin),
        patch("app.lib.api_client.supabase", supabase),
        patch("app.lib.api_client.supabase_admin", supabase_admin),
        patch("app.core.roles.supabase", supabase),
        patch("app.api.v1.reviews.email_service.send_inline_email", send_mock),
    ):
        resp = await client.post(
            f"/api/v1/reviews/assignments/{declined_assignment_id}/send-email",
            json={"template_key": "reviewer_invitation_standard"},
            headers=headers,
        )

    assert resp.status_code == 200
    payload = resp.json()
    assert payload.get("success") is True
    assert payload["data"]["event_type"] == "invitation"
    assert payload["data"]["assignment_id"] == str(fresh_assignment_id)
    assert payload["data"]["delivery_status"] == "sent"
    assert send_mock.call_count == 1

    reinsert_payload = supabase_admin._insert_calls["review_assignments"][0]
    assert reinsert_payload["status"] == "selected"
    assert reinsert_payload["manuscript_id"] == str(manuscript_id)
    assert reinsert_payload["reviewer_id"] == str(reviewer_id)
    assert reinsert_payload["selected_by"] == editor_id
    assert reinsert_payload["selected_via"] == "system_reinvite"
    assert reinsert_payload["invited_at"] is None
    assert reinsert_payload["declined_at"] is None
    assert reinsert_payload["decline_reason"] is None

    assignment_patch = supabase_admin._update_calls["review_assignments"][0]
    assert assignment_patch["status"] == "invited"
    assert assignment_patch["invited_at"]
    assert assignment_patch["invited_by"] == editor_id
    assert assignment_patch["invited_via"] == "template_invitation"
    manuscript_patch = supabase_admin._update_calls["manuscripts"][0]
    assert manuscript_patch["status"] == "under_review"


@pytest.mark.asyncio
async def test_send_assignment_email_blocks_reminder_for_declined_assignment(
    client: AsyncClient,
    auth_token: str,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("ADMIN_EMAILS", "test@example.com")

    declined_assignment_id = UUID("dddddddd-dddd-dddd-dddd-dddddddddddf")
    manuscript_id = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaabb")
    reviewer_id = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
    editor_id = "00000000-0000-0000-0000-000000000000"

    supabase = _Client(
        {
            "user_profiles": [
                [{"id": editor_id, "email": "test@example.com", "roles": ["managing_editor"]}],
            ],
        }
    )
    supabase_admin = _Client(
        {
            "email_templates": [],
            "review_assignments": [
                {
                    "id": str(declined_assignment_id),
                    "manuscript_id": str(manuscript_id),
                    "reviewer_id": str(reviewer_id),
                    "status": "declined",
                    "due_at": "2026-03-21T00:00:00+00:00",
                    "invited_at": "2026-03-10T00:00:00+00:00",
                    "last_reminded_at": None,
                    "invited_by": editor_id,
                    "invited_via": "template_invitation",
                    "round_number": 1,
                    "selected_by": editor_id,
                    "selected_via": "editor_selection",
                    "declined_at": "2026-03-11T00:00:00+00:00",
                },
            ],
            "manuscripts": [
                {
                    "id": str(manuscript_id),
                    "title": "Declined Reminder Block",
                    "journal_id": "journal-1",
                    "assistant_editor_id": editor_id,
                    "status": "under_review",
                },
            ],
        }
    )

    send_mock = MagicMock()
    headers = {"Authorization": f"Bearer {auth_token}"}

    with (
        patch("app.api.v1.reviews.supabase", supabase),
        patch("app.api.v1.reviews.supabase_admin", supabase_admin),
        patch("app.services.reviewer_service.supabase_admin", supabase_admin),
        patch("app.lib.api_client.supabase", supabase),
        patch("app.lib.api_client.supabase_admin", supabase_admin),
        patch("app.core.roles.supabase", supabase),
        patch("app.api.v1.reviews.email_service.send_inline_email", send_mock),
    ):
        resp = await client.post(
            f"/api/v1/reviews/assignments/{declined_assignment_id}/send-email",
            json={"template_key": "reviewer_reminder_polite"},
            headers=headers,
        )

    assert resp.status_code == 409
    assert "declined" in str(resp.json().get("detail", "")).lower()
    assert send_mock.call_count == 0
    assert supabase_admin._insert_calls.get("email_logs") in (None, [])
    assert supabase_admin._insert_calls.get("review_assignments") in (None, [])


@pytest.mark.asyncio
async def test_send_assignment_email_declined_invitation_does_not_create_fresh_attempt_when_reviewer_email_missing(
    client: AsyncClient,
    auth_token: str,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("ADMIN_EMAILS", "test@example.com")

    declined_assignment_id = UUID("dddddddd-dddd-dddd-dddd-ddddddddddda")
    manuscript_id = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaabc")
    reviewer_id = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbc")
    editor_id = "00000000-0000-0000-0000-000000000000"

    supabase = _Client(
        {
            "user_profiles": [
                [{"id": editor_id, "email": "test@example.com", "roles": ["managing_editor"]}],
            ],
        }
    )
    supabase_admin = _Client(
        {
            "email_templates": [],
            "review_assignments": [
                {
                    "id": str(declined_assignment_id),
                    "manuscript_id": str(manuscript_id),
                    "reviewer_id": str(reviewer_id),
                    "status": "declined",
                    "due_at": "2026-03-21T00:00:00+00:00",
                    "invited_at": "2026-03-10T00:00:00+00:00",
                    "last_reminded_at": None,
                    "invited_by": editor_id,
                    "invited_via": "template_invitation",
                    "round_number": 1,
                    "selected_by": editor_id,
                    "selected_via": "editor_selection",
                    "declined_at": "2026-03-11T00:00:00+00:00",
                },
            ],
            "manuscripts": [
                {
                    "id": str(manuscript_id),
                    "title": "Declined Missing Reviewer Email",
                    "journal_id": "journal-1",
                    "assistant_editor_id": editor_id,
                    "status": "pre_check",
                },
            ],
            "user_profiles": [
                {"email": "", "full_name": "Reviewer Missing Email"},
            ],
        }
    )

    send_mock = MagicMock()
    headers = {"Authorization": f"Bearer {auth_token}"}

    with (
        patch("app.api.v1.reviews.supabase", supabase),
        patch("app.api.v1.reviews.supabase_admin", supabase_admin),
        patch("app.services.reviewer_service.supabase_admin", supabase_admin),
        patch("app.lib.api_client.supabase", supabase),
        patch("app.lib.api_client.supabase_admin", supabase_admin),
        patch("app.core.roles.supabase", supabase),
        patch("app.api.v1.reviews.email_service.send_inline_email", send_mock),
    ):
        resp = await client.post(
            f"/api/v1/reviews/assignments/{declined_assignment_id}/send-email",
            json={"template_key": "reviewer_invitation_standard"},
            headers=headers,
        )

    assert resp.status_code == 400
    assert "email" in str(resp.json().get("detail", "")).lower()
    assert send_mock.call_count == 0
    assert supabase_admin._insert_calls.get("review_assignments") in (None, [])
    assert supabase_admin._insert_calls.get("email_logs") in (None, [])


@pytest.mark.asyncio
async def test_send_assignment_email_does_not_mark_invited_when_delivery_fails(
    client: AsyncClient,
    auth_token: str,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("ADMIN_EMAILS", "test@example.com")
    monkeypatch.setenv("MAGIC_LINK_JWT_SECRET", "test-secret")
    monkeypatch.setenv("FRONTEND_BASE_URL", "http://localhost:3000")

    assignment_id = UUID("cccccccc-cccc-cccc-cccc-cccccccccccf")
    manuscript_id = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaad")
    reviewer_id = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbb0")
    editor_id = "00000000-0000-0000-0000-000000000000"

    supabase = _Client(
        {
            "user_profiles": [
                [{"id": editor_id, "email": "test@example.com", "roles": ["managing_editor"]}],
            ],
        }
    )
    supabase_admin = _Client(
        {
            "email_templates": [],
            "review_assignments": [
                {
                    "id": str(assignment_id),
                    "manuscript_id": str(manuscript_id),
                    "reviewer_id": str(reviewer_id),
                    "status": "selected",
                    "due_at": "2026-03-20T00:00:00+00:00",
                    "invited_at": None,
                    "last_reminded_at": None,
                    "invited_by": None,
                    "invited_via": None,
                },
            ],
            "manuscripts": [
                {
                    "id": str(manuscript_id),
                    "title": "Selection First Workflow",
                    "journal_id": "journal-1",
                    "assistant_editor_id": editor_id,
                    "status": "pre_check",
                },
            ],
            "user_profiles": [
                {"email": "reviewer@example.com", "full_name": "Reviewer X"},
            ],
            "journals": [
                {"title": "Journal One"},
            ],
        }
    )

    send_mock = MagicMock(
        return_value={
            "ok": False,
            "status": "failed",
            "subject": "Invitation to Review",
            "provider_id": None,
            "error_message": "The send.example.com domain is not verified.",
        }
    )
    headers = {"Authorization": f"Bearer {auth_token}"}

    with (
        patch("app.api.v1.reviews.supabase", supabase),
        patch("app.api.v1.reviews.supabase_admin", supabase_admin),
        patch("app.services.reviewer_service.supabase_admin", supabase_admin),
        patch("app.lib.api_client.supabase", supabase),
        patch("app.lib.api_client.supabase_admin", supabase_admin),
        patch("app.core.roles.supabase", supabase),
        patch("app.api.v1.reviews.email_service.send_inline_email", send_mock),
    ):
        resp = await client.post(
            f"/api/v1/reviews/assignments/{assignment_id}/send-email",
            json={"template_key": "reviewer_invitation_standard"},
            headers=headers,
        )

    assert resp.status_code == 200
    payload = resp.json()
    assert payload.get("success") is True
    assert payload["data"]["delivery_status"] == "failed"
    assert "not verified" in str(payload["data"]["delivery_error"]).lower()
    assert supabase_admin._update_calls.get("review_assignments") in (None, [])
    assert supabase_admin._update_calls.get("manuscripts") in (None, [])


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
    ):
        resp = await client.post("/api/v1/reviews/assign", json=body, headers=headers)
        assert resp.status_code == 403
        assert "assistant editor" in str(resp.json().get("detail", "")).lower()


@pytest.mark.asyncio
async def test_reviewer_history_includes_assignment_email_delivery_events(
    client: AsyncClient,
    auth_token: str,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("ADMIN_EMAILS", "test@example.com")

    reviewer_id = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbb1")
    manuscript_id = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa1")
    assignment_id = UUID("cccccccc-cccc-cccc-cccc-ccccccccccc1")
    editor_id = "00000000-0000-0000-0000-000000000000"
    selector_id = "11111111-1111-1111-1111-111111111111"
    inviter_id = "22222222-2222-2222-2222-222222222222"

    supabase = _Client(
        {
            "user_profiles": [
                [{"id": editor_id, "email": "test@example.com", "roles": ["managing_editor"]}],
            ],
        }
    )
    supabase_admin = _Client(
        {
            "review_assignments": [
                [
                    {
                        "id": str(assignment_id),
                        "manuscript_id": str(manuscript_id),
                        "reviewer_id": str(reviewer_id),
                        "status": "invited",
                        "due_at": "2026-03-20T00:00:00+00:00",
                        "invited_at": "2026-03-10T00:00:00+00:00",
                        "opened_at": None,
                        "accepted_at": None,
                        "declined_at": None,
                        "decline_reason": None,
                        "decline_note": None,
                        "last_reminded_at": None,
                        "created_at": "2026-03-10T00:00:00+00:00",
                        "round_number": 1,
                        "selected_by": selector_id,
                        "selected_via": "editor_selection",
                        "invited_by": inviter_id,
                        "invited_via": "template_invitation",
                    }
                ],
            ],
            "manuscripts": [
                [
                    {
                        "id": str(manuscript_id),
                        "title": "History Manuscript",
                        "status": "under_review",
                        "journal_id": "journal-1",
                        "assistant_editor_id": editor_id,
                    }
                ]
            ],
            "review_reports": [[]],
            "email_logs": [
                [
                    {
                        "assignment_id": str(assignment_id),
                        "manuscript_id": str(manuscript_id),
                        "template_name": "reviewer_invitation_standard",
                        "status": "sent",
                        "event_type": "invitation",
                        "actor_user_id": inviter_id,
                        "error_message": None,
                        "created_at": "2026-03-10T00:00:03+00:00",
                    },
                    {
                        "assignment_id": str(assignment_id),
                        "manuscript_id": str(manuscript_id),
                        "template_name": "reviewer_invitation_standard",
                        "status": "queued",
                        "event_type": "invitation",
                        "actor_user_id": inviter_id,
                        "error_message": None,
                        "created_at": "2026-03-10T00:00:01+00:00",
                    },
                ]
            ],
            "user_profiles": [
                [
                    {"id": selector_id, "full_name": "Selector User", "email": "selector@example.com"},
                    {"id": inviter_id, "full_name": "Inviter User", "email": "inviter@example.com"},
                ]
            ],
        }
    )

    with (
        patch("app.api.v1.reviews.supabase", supabase),
        patch("app.api.v1.reviews.supabase_admin", supabase_admin),
        patch("app.services.reviewer_service.supabase_admin", supabase_admin),
        patch("app.lib.api_client.supabase", supabase),
        patch("app.lib.api_client.supabase_admin", supabase_admin),
        patch("app.core.roles.supabase", supabase),
    ):
        resp = await client.get(
            f"/api/v1/reviews/reviewer-history/{reviewer_id}?limit=20",
            headers={"Authorization": f"Bearer {auth_token}"},
        )

    assert resp.status_code == 200, resp.text
    payload = resp.json()
    assert payload.get("success") is True
    rows = payload.get("data") or []
    assert len(rows) == 1
    assert rows[0]["latest_email_status"] == "sent"
    assert rows[0]["latest_email_at"] == "2026-03-10T00:00:03+00:00"
    assert rows[0]["added_by"]["full_name"] == "Selector User"
    assert rows[0]["added_via"] == "editor_selection"
    assert rows[0]["invited_by"]["full_name"] == "Inviter User"
    assert rows[0]["invited_via"] == "template_invitation"
    assert [event["status"] for event in rows[0]["email_events"]] == ["sent", "queued"]
    assert rows[0]["email_events"][0]["actor"]["full_name"] == "Inviter User"
    assert rows[0]["assignment_state"] == "invited"


@pytest.mark.asyncio
async def test_reviewer_history_derives_accepted_state_from_pending_assignment(
    client: AsyncClient,
    auth_token: str,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("ADMIN_EMAILS", "test@example.com")

    reviewer_id = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbb2")
    manuscript_id = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa2")
    assignment_id = UUID("cccccccc-cccc-cccc-cccc-ccccccccccc2")
    editor_id = "00000000-0000-0000-0000-000000000000"

    supabase = _Client(
        {
            "user_profiles": [
                [{"id": editor_id, "email": "test@example.com", "roles": ["assistant_editor"]}],
            ],
        }
    )
    supabase_admin = _Client(
        {
            "review_assignments": [
                [
                    {
                        "id": str(assignment_id),
                        "manuscript_id": str(manuscript_id),
                        "reviewer_id": str(reviewer_id),
                        "status": "pending",
                        "due_at": "2026-03-20T00:00:00+00:00",
                        "invited_at": "2026-03-10T00:00:00+00:00",
                        "opened_at": "2026-03-10T00:05:00+00:00",
                        "accepted_at": "2026-03-10T00:06:00+00:00",
                        "declined_at": None,
                        "decline_reason": None,
                        "decline_note": None,
                        "last_reminded_at": None,
                        "created_at": "2026-03-10T00:00:00+00:00",
                        "round_number": 2,
                    }
                ],
            ],
            "manuscripts": [
                [
                    {
                        "id": str(manuscript_id),
                        "title": "Accepted State Manuscript",
                        "status": "under_review",
                        "journal_id": "journal-1",
                        "assistant_editor_id": editor_id,
                    }
                ]
            ],
            "review_reports": [[]],
            "email_logs": [[]],
            "user_profiles": [[]],
        }
    )

    with (
        patch("app.api.v1.reviews.supabase", supabase),
        patch("app.api.v1.reviews.supabase_admin", supabase_admin),
        patch("app.services.reviewer_service.supabase_admin", supabase_admin),
        patch("app.lib.api_client.supabase", supabase),
        patch("app.lib.api_client.supabase_admin", supabase_admin),
        patch("app.core.roles.supabase", supabase),
    ):
        resp = await client.get(
            f"/api/v1/reviews/reviewer-history/{reviewer_id}?limit=20",
            headers={"Authorization": f"Bearer {auth_token}"},
        )

    assert resp.status_code == 200, resp.text
    payload = resp.json()
    rows = payload.get("data") or []
    assert len(rows) == 1
    assert rows[0]["assignment_status"] == "pending"
    assert rows[0]["assignment_state"] == "accepted"
