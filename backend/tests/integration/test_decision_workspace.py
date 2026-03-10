from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from postgrest.exceptions import APIError

from .test_utils import insert_manuscript, make_user


def _cleanup(db, manuscript_id: str) -> None:
    for table, column in (
        ("notifications", "manuscript_id"),
        ("status_transition_logs", "manuscript_id"),
        ("decision_letters", "manuscript_id"),
        ("revisions", "manuscript_id"),
        ("review_reports", "manuscript_id"),
        ("review_assignments", "manuscript_id"),
        ("manuscripts", "id"),
    ):
        try:
            db.table(table).delete().eq(column, manuscript_id).execute()
        except Exception:
            pass


def _require_decision_schema(db) -> None:
    checks = [
        ("decision_letters", "id,manuscript_id,editor_id,content,decision,status,attachment_paths,updated_at"),
        ("manuscripts", "id,status,version"),
        ("review_reports", "id,manuscript_id,status"),
        ("revisions", "id,manuscript_id,status,submitted_at"),
    ]
    for table, cols in checks:
        try:
            db.table(table).select(cols).limit(1).execute()
        except APIError as e:
            pytest.skip(f"数据库缺少决策工作台测试所需 schema（{table}/{cols}）：{getattr(e, 'message', str(e))}")


def _require_review_assignment_schema(db) -> None:
    checks = [
        (
            "review_assignments",
            "id,manuscript_id,reviewer_id,status,round_number,invited_at,opened_at,accepted_at,declined_at,submitted_at,cancelled_at",
        ),
    ]
    for table, cols in checks:
        try:
            db.table(table).select(cols).limit(1).execute()
        except APIError as e:
            pytest.skip(f"数据库缺少外审退出测试所需 schema（{table}/{cols}）：{getattr(e, 'message', str(e))}")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_submit_final_accept_persists_decision_letter_and_updates_status(
    client,
    supabase_admin_client,
    set_admin_emails,
):
    editor = make_user(email="decision_editor_accept@example.com")
    author = make_user(email="decision_author_accept@example.com")
    reviewer = make_user(email="decision_reviewer_accept@example.com")
    set_admin_emails([editor.email])
    _require_decision_schema(supabase_admin_client)

    manuscript_id = str(uuid4())
    insert_manuscript(
        supabase_admin_client,
        manuscript_id=manuscript_id,
        author_id=author.id,
        status="resubmitted",
        title="Decision Accept Manuscript",
        version=2,
        file_path=f"manuscripts/{manuscript_id}/v2.pdf",
    )
    supabase_admin_client.table("revisions").insert(
        {
            "manuscript_id": manuscript_id,
            "round_number": 1,
            "decision_type": "major",
            "editor_comment": "Please revise and resubmit.",
            "status": "submitted",
            "response_letter": "Author addressed all comments.",
            "submitted_at": datetime.now(timezone.utc).isoformat(),
        }
    ).execute()
    supabase_admin_client.table("review_reports").insert(
        {
            "manuscript_id": manuscript_id,
            "reviewer_id": reviewer.id,
            "status": "completed",
            "content": "Looks publishable with minor edits.",
            "score": 4,
        }
    ).execute()

    try:
        res = await client.post(
            f"/api/v1/editor/manuscripts/{manuscript_id}/submit-decision",
            headers={"Authorization": f"Bearer {editor.token}"},
            json={
                "content": "Final decision: accept.",
                "decision": "accept",
                "is_final": True,
                "attachment_paths": [],
                "last_updated_at": None,
            },
        )
        assert res.status_code == 200, res.text
        payload = res.json()
        assert payload["success"] is True
        assert payload["data"]["status"] == "final"
        assert payload["data"]["manuscript_status"] == "approved"

        ms = (
            supabase_admin_client.table("manuscripts")
            .select("status")
            .eq("id", manuscript_id)
            .single()
            .execute()
            .data
        )
        assert ms["status"] == "approved"

        letters = (
            supabase_admin_client.table("decision_letters")
            .select("status,decision,content")
            .eq("manuscript_id", manuscript_id)
            .order("updated_at", desc=True)
            .limit(1)
            .execute()
            .data
            or []
        )
        assert letters and letters[0]["status"] == "final"
        assert letters[0]["decision"] == "accept"
        assert "accept" in (letters[0]["content"] or "").lower()
    finally:
        _cleanup(supabase_admin_client, manuscript_id)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_reject_blocked_outside_decision_stage(
    client,
    supabase_admin_client,
    set_admin_emails,
):
    editor = make_user(email="decision_editor_reject_block@example.com")
    author = make_user(email="decision_author_reject_block@example.com")
    reviewer = make_user(email="decision_reviewer_reject_block@example.com")
    set_admin_emails([editor.email])
    _require_decision_schema(supabase_admin_client)

    manuscript_id = str(uuid4())
    insert_manuscript(
        supabase_admin_client,
        manuscript_id=manuscript_id,
        author_id=author.id,
        status="under_review",
        title="Reject Stage Gate Manuscript",
        file_path=f"manuscripts/{manuscript_id}/v1.pdf",
    )
    supabase_admin_client.table("review_reports").insert(
        {
            "manuscript_id": manuscript_id,
            "reviewer_id": reviewer.id,
            "status": "completed",
            "content": "Strong reject recommendation.",
            "score": 2,
        }
    ).execute()

    try:
        res = await client.post(
            f"/api/v1/editor/manuscripts/{manuscript_id}/submit-decision",
            headers={"Authorization": f"Bearer {editor.token}"},
            json={
                "content": "Reject due to critical flaws.",
                "decision": "reject",
                "is_final": True,
                "attachment_paths": [],
                "last_updated_at": None,
            },
        )
        assert res.status_code == 422, res.text
        assert "after author resubmission" in (res.text.lower())
    finally:
        _cleanup(supabase_admin_client, manuscript_id)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_draft_optimistic_lock_conflict_returns_409(
    client,
    supabase_admin_client,
    set_admin_emails,
):
    editor = make_user(email="decision_editor_conflict@example.com")
    author = make_user(email="decision_author_conflict@example.com")
    set_admin_emails([editor.email])
    _require_decision_schema(supabase_admin_client)

    manuscript_id = str(uuid4())
    insert_manuscript(
        supabase_admin_client,
        manuscript_id=manuscript_id,
        author_id=author.id,
        status="decision",
        title="Optimistic Lock Manuscript",
    )

    try:
        first = await client.post(
            f"/api/v1/editor/manuscripts/{manuscript_id}/submit-decision",
            headers={"Authorization": f"Bearer {editor.token}"},
            json={
                "content": "Draft v1",
                "decision": "minor_revision",
                "is_final": False,
                "attachment_paths": [],
                "last_updated_at": None,
            },
        )
        assert first.status_code == 200, first.text
        stale_ts = first.json()["data"]["updated_at"]
        assert stale_ts

        second = await client.post(
            f"/api/v1/editor/manuscripts/{manuscript_id}/submit-decision",
            headers={"Authorization": f"Bearer {editor.token}"},
            json={
                "content": "Draft v2",
                "decision": "minor_revision",
                "is_final": False,
                "attachment_paths": [],
                "last_updated_at": stale_ts,
            },
        )
        assert second.status_code == 200, second.text

        third = await client.post(
            f"/api/v1/editor/manuscripts/{manuscript_id}/submit-decision",
            headers={"Authorization": f"Bearer {editor.token}"},
            json={
                "content": "Draft stale write",
                "decision": "minor_revision",
                "is_final": False,
                "attachment_paths": [],
                "last_updated_at": stale_ts,
            },
        )
        assert third.status_code == 409, third.text
    finally:
        _cleanup(supabase_admin_client, manuscript_id)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_review_stage_exit_moves_to_decision_and_cancels_pending_reviewers(
    client,
    supabase_admin_client,
    set_admin_emails,
):
    editor = make_user(email="decision_editor_exit@example.com")
    author = make_user(email="decision_author_exit@example.com")
    reviewer_selected = make_user(email="decision_reviewer_selected@example.com")
    reviewer_invited = make_user(email="decision_reviewer_invited@example.com")
    reviewer_opened = make_user(email="decision_reviewer_opened@example.com")
    reviewer_accepted = make_user(email="decision_reviewer_accepted@example.com")
    reviewer_submitted = make_user(email="decision_reviewer_submitted@example.com")
    set_admin_emails([editor.email])
    _require_decision_schema(supabase_admin_client)
    _require_review_assignment_schema(supabase_admin_client)

    manuscript_id = str(uuid4())
    insert_manuscript(
        supabase_admin_client,
        manuscript_id=manuscript_id,
        author_id=author.id,
        status="under_review",
        title="Review Stage Exit Manuscript",
        version=2,
        file_path=f"manuscripts/{manuscript_id}/v2.pdf",
    )
    assignments = [
        {
            "manuscript_id": manuscript_id,
            "reviewer_id": reviewer_selected.id,
            "round_number": 2,
            "status": "selected",
        },
        {
            "manuscript_id": manuscript_id,
            "reviewer_id": reviewer_invited.id,
            "round_number": 2,
            "status": "invited",
            "invited_at": datetime.now(timezone.utc).isoformat(),
        },
        {
            "manuscript_id": manuscript_id,
            "reviewer_id": reviewer_opened.id,
            "round_number": 2,
            "status": "opened",
            "invited_at": datetime.now(timezone.utc).isoformat(),
            "opened_at": datetime.now(timezone.utc).isoformat(),
        },
        {
            "manuscript_id": manuscript_id,
            "reviewer_id": reviewer_accepted.id,
            "round_number": 2,
            "status": "pending",
            "invited_at": datetime.now(timezone.utc).isoformat(),
            "opened_at": datetime.now(timezone.utc).isoformat(),
            "accepted_at": datetime.now(timezone.utc).isoformat(),
        },
        {
            "manuscript_id": manuscript_id,
            "reviewer_id": reviewer_submitted.id,
            "round_number": 2,
            "status": "completed",
            "invited_at": datetime.now(timezone.utc).isoformat(),
            "opened_at": datetime.now(timezone.utc).isoformat(),
            "accepted_at": datetime.now(timezone.utc).isoformat(),
            "submitted_at": datetime.now(timezone.utc).isoformat(),
        },
    ]
    inserted = (
        supabase_admin_client.table("review_assignments")
        .insert(assignments)
        .execute()
        .data
        or []
    )
    accepted_assignment_id = next(
        row["id"] for row in inserted if row["reviewer_id"] == reviewer_accepted.id
    )
    supabase_admin_client.table("review_reports").insert(
        {
            "manuscript_id": manuscript_id,
            "reviewer_id": reviewer_submitted.id,
            "status": "completed",
            "content": "Proceed to decision",
        }
    ).execute()

    try:
        res = await client.post(
            f"/api/v1/editor/manuscripts/{manuscript_id}/review-stage-exit",
            headers={"Authorization": f"Bearer {editor.token}"},
            json={
                "target_stage": "first",
                "note": "Enough review evidence collected",
                "accepted_pending_resolutions": [
                    {
                        "assignment_id": accepted_assignment_id,
                        "action": "cancel",
                        "reason": "Two completed reports are sufficient",
                    }
                ],
            },
        )
        assert res.status_code == 200, res.text
        payload = res.json()
        assert payload["success"] is True
        assert payload["data"]["manuscript_status"] == "decision"
        assert accepted_assignment_id in payload["data"]["manually_cancelled_assignment_ids"]

        manuscript = (
            supabase_admin_client.table("manuscripts")
            .select("status")
            .eq("id", manuscript_id)
            .single()
            .execute()
            .data
        )
        assert manuscript["status"] == "decision"

        rows = (
            supabase_admin_client.table("review_assignments")
            .select("reviewer_id,status,cancel_reason")
            .eq("manuscript_id", manuscript_id)
            .execute()
            .data
            or []
        )
        status_map = {row["reviewer_id"]: row["status"] for row in rows}
        assert status_map[reviewer_selected.id] == "cancelled"
        assert status_map[reviewer_invited.id] == "cancelled"
        assert status_map[reviewer_opened.id] == "cancelled"
        assert status_map[reviewer_accepted.id] == "cancelled"
        assert status_map[reviewer_submitted.id] == "completed"
    finally:
        _cleanup(supabase_admin_client, manuscript_id)
