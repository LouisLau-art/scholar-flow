from types import SimpleNamespace

import pytest

import app.api.v1.editor_detail as editor_detail_api


class _FakeQuery:
    def __init__(self, table: str, dataset: dict[str, list[dict]]):
        self.table = table
        self.dataset = dataset
        self.select_clause = ""

    def select(self, *args, **_kwargs):
        if args:
            self.select_clause = str(args[0] or "")
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


class _ReviewAssignmentsCompatQuery(_FakeQuery):
    def execute(self):
        if self.table == "review_assignments" and any(
            column in self.select_clause
            for column in (
                "selected_by",
                "selected_via",
                "invited_by",
                "invited_via",
                "cancelled_at",
                "cancelled_by",
                "cancel_reason",
                "cancel_via",
            )
        ):
            raise RuntimeError("PGRST204: column review_assignments.selected_by does not exist")
        return super().execute()


class _ReviewAssignmentsCompatSupabase(_FakeSupabase):
    def table(self, name: str):
        self.call_count[name] = self.call_count.get(name, 0) + 1
        return _ReviewAssignmentsCompatQuery(name, self.dataset)


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
                    "round_number": 1,
                    "selected_by": "selector-1",
                    "selected_via": "editor_selection",
                    "invited_by": "inviter-1",
                    "invited_via": "template_invitation",
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
            "email_logs": [
                {
                    "assignment_id": "ra-1",
                    "manuscript_id": "ms-1",
                    "template_name": "reviewer_invitation_standard",
                    "status": "sent",
                    "event_type": "invitation",
                    "actor_user_id": "inviter-1",
                    "created_at": "2026-02-01T00:00:12Z",
                    "error_message": None,
                    "provider_id": "email-1",
                    "idempotency_key": "reviewer-invitation/ra-1",
                },
                {
                    "assignment_id": "ra-1",
                    "manuscript_id": "ms-1",
                    "template_name": "reviewer_invitation_standard",
                    "status": "queued",
                    "event_type": "invitation",
                    "actor_user_id": "inviter-1",
                    "created_at": "2026-02-01T00:00:10Z",
                    "error_message": None,
                    "provider_id": None,
                    "idempotency_key": "reviewer-invitation/ra-1",
                },
            ],
            "user_profiles": [
                {"id": "owner-1", "full_name": "Owner User", "email": "owner@example.com"},
                {"id": "editor-1", "full_name": "Editor User", "email": "editor@example.com"},
                {"id": "reviewer-1", "full_name": "Reviewer User", "email": "reviewer@example.com"},
                {"id": "selector-1", "full_name": "Selector User", "email": "selector@example.com"},
                {"id": "inviter-1", "full_name": "Inviter User", "email": "inviter@example.com"},
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
    assert invites[0]["status"] == "submitted"
    assert invites[0]["reviewer_name"] == "Reviewer User"
    assert invites[0]["submitted_at"] == "2026-02-05T00:00:00Z"
    assert invites[0]["added_by_name"] == "Selector User"
    assert invites[0]["added_via"] == "editor_selection"
    assert invites[0]["invited_by_name"] == "Inviter User"
    assert invites[0]["invited_via"] == "template_invitation"
    assert invites[0]["latest_email_status"] == "sent"
    assert invites[0]["latest_email_at"] == "2026-02-01T00:00:12Z"
    assert [event["status"] for event in invites[0]["email_events"]] == ["sent", "queued"]
    assert invites[0]["email_events"][0]["actor"]["full_name"] == "Inviter User"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_editor_detail_returns_cancel_audit_for_cancelled_assignment(
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
                    "id": "ms-cancelled",
                    "title": "Cancelled Reviewer Manuscript",
                    "status": "under_review",
                    "owner_id": "owner-1",
                    "editor_id": "editor-1",
                    "file_path": "manuscripts/ms-cancelled/v1.pdf",
                    "created_at": "2026-02-01T00:00:00Z",
                    "updated_at": "2026-02-02T00:00:00Z",
                    "journals": {"title": "Journal"},
                }
            ],
            "invoices": [],
            "manuscript_files": [],
            "review_assignments": [
                {
                    "id": "ra-cancelled",
                    "reviewer_id": "reviewer-1",
                    "status": "cancelled",
                    "due_at": "2026-03-20T00:00:00Z",
                    "invited_at": "2026-03-09T12:00:00Z",
                    "opened_at": "2026-03-09T12:10:00Z",
                    "accepted_at": "2026-03-09T12:20:00Z",
                    "declined_at": None,
                    "decline_reason": None,
                    "decline_note": None,
                    "cancelled_at": "2026-03-09T13:00:00Z",
                    "cancelled_by": "editor-2",
                    "cancel_reason": "Enough reviews received",
                    "cancel_via": "post_acceptance_cleanup",
                    "created_at": "2026-03-09T12:00:00Z",
                    "round_number": 2,
                }
            ],
            "review_reports": [],
            "email_logs": [],
            "user_profiles": [
                {"id": "owner-1", "full_name": "Owner User", "email": "owner@example.com"},
                {"id": "editor-1", "full_name": "Editor User", "email": "editor@example.com"},
                {"id": "editor-2", "full_name": "Cancelling Editor", "email": "cancel@example.com"},
                {"id": "reviewer-1", "full_name": "Reviewer User", "email": "reviewer@example.com"},
            ],
        }
    )
    monkeypatch.setattr(editor_detail_api, "supabase_admin", fake_db)

    res = await client.get(
        "/api/v1/editor/manuscripts/ms-cancelled?skip_cards=true&include_heavy=true",
        headers={"Authorization": f"Bearer {auth_token}"},
    )

    assert res.status_code == 200, res.text
    payload = res.json()
    invites = payload["data"].get("reviewer_invites") or []
    assert len(invites) == 1
    assert invites[0]["status"] == "cancelled"
    assert invites[0]["cancelled_at"] == "2026-03-09T13:00:00Z"
    assert invites[0]["cancel_reason"] == "Enough reviews received"
    assert invites[0]["cancel_via"] == "post_acceptance_cleanup"
    assert invites[0]["cancelled_by_name"] == "Cancelling Editor"




@pytest.mark.integration
@pytest.mark.asyncio
async def test_editor_detail_and_cards_context_use_bound_academic_editor_for_role_queue(
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
                    "id": "ms-academic-role-queue",
                    "title": "Academic Bound Manuscript",
                    "status": "pre_check",
                    "pre_check_status": "academic",
                    "owner_id": "owner-1",
                    "editor_id": "editor-1",
                    "assistant_editor_id": "ae-1",
                    "academic_editor_id": "academic-1",
                    "academic_submitted_at": "2026-03-11T09:30:00Z",
                    "academic_completed_at": None,
                    "file_path": "manuscripts/ms-academic-role-queue/v1.pdf",
                    "created_at": "2026-03-11T09:00:00Z",
                    "updated_at": "2026-03-11T09:35:00Z",
                    "journals": {"title": "Journal"},
                }
            ],
            "invoices": [],
            "manuscript_files": [],
            "review_assignments": [],
            "review_reports": [],
            "email_logs": [],
            "status_transition_logs": [
                {
                    "id": "tl-1",
                    "created_at": "2026-03-11T09:30:00Z",
                    "comment": "sent to academic",
                    "payload": {
                        "action": "precheck_technical_pass",
                        "academic_editor_after": "academic-1",
                    },
                }
            ],
            "user_profiles": [
                {"id": "owner-1", "full_name": "Owner User", "email": "owner@example.com"},
                {"id": "editor-1", "full_name": "Editor User", "email": "editor@example.com"},
                {"id": "ae-1", "full_name": "Assistant Editor", "email": "ae@example.com"},
                {"id": "academic-1", "full_name": "Academic Editor", "email": "academic@example.com"},
            ],
        }
    )
    monkeypatch.setattr(editor_detail_api, "supabase_admin", fake_db)

    detail_res = await client.get(
        "/api/v1/editor/manuscripts/ms-academic-role-queue",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert detail_res.status_code == 200, detail_res.text
    detail_role_queue = (detail_res.json().get("data") or {}).get("role_queue") or {}
    assert detail_role_queue.get("current_role") == "academic_editor"
    assert (detail_role_queue.get("current_assignee") or {}).get("id") == "academic-1"
    assert detail_role_queue.get("current_assignee_label") in {None, "Assigned Academic Editor"}
    assert detail_role_queue.get("academic_submitted_at") == "2026-03-11T09:30:00Z"

    cards_res = await client.get(
        "/api/v1/editor/manuscripts/ms-academic-role-queue/cards-context",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert cards_res.status_code == 200, cards_res.text
    cards_role_queue = ((cards_res.json().get("data") or {}).get("role_queue") or {})
    assert cards_role_queue.get("current_role") == "academic_editor"
    assert (cards_role_queue.get("current_assignee") or {}).get("id") == "academic-1"
    assert cards_role_queue.get("academic_submitted_at") == "2026-03-11T09:30:00Z"


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
async def test_editor_detail_does_not_mark_all_rounds_submitted_when_same_reviewer_has_multiple_assignments(client, auth_token, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("ADMIN_EMAILS", "test@example.com")
    monkeypatch.setattr(editor_detail_api, "_get_signed_url", lambda *_args, **_kwargs: "https://example.com/signed")

    fake_db = _FakeSupabase(
        {
            "manuscripts": [
                {
                    "id": "ms-ambiguous",
                    "title": "Ambiguous Reviewer Submission Manuscript",
                    "status": "under_review",
                    "owner_id": "owner-1",
                    "editor_id": "editor-1",
                    "file_path": "manuscripts/ms-ambiguous/v1.pdf",
                    "created_at": "2026-02-01T00:00:00Z",
                    "updated_at": "2026-02-02T00:00:00Z",
                    "journals": {"title": "Journal"},
                }
            ],
            "invoices": [],
            "manuscript_files": [],
            "review_assignments": [
                {
                    "id": "ra-old",
                    "reviewer_id": "reviewer-1",
                    "status": "declined",
                    "due_at": None,
                    "invited_at": "2026-02-01T00:00:00Z",
                    "opened_at": "2026-02-01T01:00:00Z",
                    "accepted_at": None,
                    "declined_at": "2026-02-01T02:00:00Z",
                    "decline_reason": "too_busy",
                    "decline_note": None,
                    "created_at": "2026-02-01T00:00:00Z",
                },
                {
                    "id": "ra-new",
                    "reviewer_id": "reviewer-1",
                    "status": "accepted",
                    "due_at": "2026-02-10T00:00:00Z",
                    "invited_at": "2026-02-03T00:00:00Z",
                    "opened_at": "2026-02-03T01:00:00Z",
                    "accepted_at": "2026-02-03T02:00:00Z",
                    "declined_at": None,
                    "decline_reason": None,
                    "decline_note": None,
                    "created_at": "2026-02-03T00:00:00Z",
                },
            ],
            "review_reports": [
                {
                    "id": "rr-ambiguous",
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
        "/api/v1/editor/manuscripts/ms-ambiguous",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert res.status_code == 200, res.text
    payload = res.json()
    invites = payload["data"].get("reviewer_invites") or []
    assert len(invites) == 2
    assert all(invite.get("submitted_at") is None for invite in invites)
    invite_map = {str(invite["id"]): invite for invite in invites}
    assert invite_map["ra-new"]["status"] == "accepted"
    assert invite_map["ra-old"]["status"] == "declined"


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
    assert invites[0]["status"] == "submitted"
    assert fake_db.call_count.get("review_assignments", 0) >= 1


@pytest.mark.integration
@pytest.mark.asyncio
async def test_editor_detail_reviewer_timeline_falls_back_when_assignment_audit_columns_missing(
    client,
    auth_token,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("ADMIN_EMAILS", "test@example.com")
    monkeypatch.setattr(editor_detail_api, "_get_signed_url", lambda *_args, **_kwargs: "https://example.com/signed")

    fake_db = _ReviewAssignmentsCompatSupabase(
        {
            "manuscripts": [
                {
                    "id": "ms-compat",
                    "title": "Compat Reviewer Timeline Manuscript",
                    "status": "under_review",
                    "owner_id": "owner-1",
                    "editor_id": "editor-1",
                    "file_path": "manuscripts/ms-compat/v1.pdf",
                    "created_at": "2026-02-01T00:00:00Z",
                    "updated_at": "2026-02-02T00:00:00Z",
                    "journals": {"title": "Journal"},
                }
            ],
            "invoices": [],
            "manuscript_files": [],
            "review_assignments": [
                {
                    "id": "ra-selected",
                    "reviewer_id": "reviewer-1",
                    "status": "selected",
                    "due_at": None,
                    "invited_at": None,
                    "opened_at": None,
                    "accepted_at": None,
                    "declined_at": None,
                    "last_reminded_at": None,
                    "created_at": "2026-03-09T10:00:00Z",
                }
            ],
            "review_reports": [],
            "email_logs": [],
            "user_profiles": [
                {"id": "owner-1", "full_name": "Owner User", "email": "owner@example.com"},
                {"id": "editor-1", "full_name": "Editor User", "email": "editor@example.com"},
                {"id": "reviewer-1", "full_name": "Reviewer User", "email": "reviewer@example.com"},
            ],
        }
    )
    monkeypatch.setattr(editor_detail_api, "supabase_admin", fake_db)

    res = await client.get(
        "/api/v1/editor/manuscripts/ms-compat?skip_cards=true&include_heavy=true",
        headers={"Authorization": f"Bearer {auth_token}"},
    )

    assert res.status_code == 200, res.text
    payload = res.json()
    invites = payload["data"].get("reviewer_invites") or []
    assert len(invites) == 1
    assert invites[0]["id"] == "ra-selected"
    assert invites[0]["status"] == "selected"
    assert invites[0]["reviewer_name"] == "Reviewer User"
