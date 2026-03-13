from __future__ import annotations

from datetime import datetime, timezone
import re
from uuid import uuid4

import pytest
from postgrest.exceptions import APIError

from .test_utils import insert_manuscript, make_user


def _ensure_profile(db, *, user_id: str, email: str, roles: list[str]) -> None:
    db.table("user_profiles").upsert(
        {
            "id": user_id,
            "email": email,
            "roles": roles,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        },
        on_conflict="id",
    ).execute()


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


def _require_precheck_schema(db) -> None:
    checks = [
        ("manuscripts", "id,status,pre_check_status,academic_editor_id"),
        ("status_transition_logs", "manuscript_id,payload,created_at"),
        ("user_profiles", "id,email,roles"),
    ]
    for table, cols in checks:
        try:
            db.table(table).select(cols).limit(1).execute()
        except APIError as e:
            pytest.skip(f"数据库缺少 academic smoke 所需 schema（{table}/{cols}）：{getattr(e, 'message', str(e))}")


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
    select_variants = [
        "id,manuscript_id,reviewer_id,status,round_number,created_at,invited_at,opened_at,accepted_at,declined_at,submitted_at,cancelled_at",
        "id,manuscript_id,reviewer_id,status,round_number,created_at,invited_at,opened_at,accepted_at,declined_at,cancelled_at",
        "id,manuscript_id,reviewer_id,status,round_number,created_at,invited_at,opened_at,accepted_at,declined_at",
        "id,manuscript_id,reviewer_id,status,round_number,created_at,invited_at,opened_at,accepted_at",
        "id,manuscript_id,reviewer_id,status,round_number,created_at,invited_at,opened_at",
        "id,manuscript_id,reviewer_id,status,round_number,created_at,invited_at",
        "id,manuscript_id,reviewer_id,status,round_number,created_at",
    ]
    last_error: APIError | None = None
    for cols in select_variants:
        try:
            db.table("review_assignments").select(cols).limit(1).execute()
            return
        except APIError as e:
            last_error = e
    pytest.skip(
        "数据库缺少外审退出测试所需 schema（review_assignments）："
        f"{getattr(last_error, 'message', str(last_error)) if last_error is not None else 'unknown error'}"
    )


def _insert_review_assignments_compatible(db, rows: list[dict]) -> list[dict]:
    payloads = [dict(row) for row in rows]
    while True:
        try:
            return db.table("review_assignments").insert(payloads).execute().data or []
        except APIError as e:
            message = getattr(e, "message", str(e))
            if "review_assignments" not in message or "schema cache" not in message:
                raise
            match = re.search(r"'([^']+)'", message)
            missing_column = match.group(1) if match else ""
            if not missing_column:
                raise
            changed = False
            next_payloads: list[dict] = []
            for row in payloads:
                next_row = dict(row)
                if missing_column in next_row:
                    next_row.pop(missing_column, None)
                    changed = True
                next_payloads.append(next_row)
            if not changed:
                raise
            payloads = next_payloads


@pytest.mark.integration
@pytest.mark.asyncio
async def test_submit_final_accept_persists_decision_letter_and_updates_status(
    client,
    supabase_admin_client,
    set_admin_emails,
):
    suffix = uuid4().hex[:8]
    editor = make_user(email=f"decision_editor_accept_{suffix}@example.com")
    author = make_user(email=f"decision_author_accept_{suffix}@example.com")
    reviewer = make_user(email=f"decision_reviewer_accept_{suffix}@example.com")
    set_admin_emails([editor.email])
    _require_decision_schema(supabase_admin_client)
    _ensure_profile(
        supabase_admin_client,
        user_id=editor.id,
        email=editor.email,
        roles=["managing_editor"],
    )
    _ensure_profile(
        supabase_admin_client,
        user_id=author.id,
        email=author.email,
        roles=["author"],
    )

    manuscript_id = str(uuid4())
    insert_manuscript(
        supabase_admin_client,
        manuscript_id=manuscript_id,
        author_id=author.id,
        status="decision_done",
        title="Decision Accept Manuscript",
        version=2,
        file_path=f"manuscripts/{manuscript_id}/v2.pdf",
    )
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
    suffix = uuid4().hex[:8]
    editor = make_user(email=f"decision_editor_reject_block_{suffix}@example.com")
    author = make_user(email=f"decision_author_reject_block_{suffix}@example.com")
    reviewer = make_user(email=f"decision_reviewer_reject_block_{suffix}@example.com")
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
        assert "exit review stage first" in (res.text.lower())
    finally:
        _cleanup(supabase_admin_client, manuscript_id)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_draft_optimistic_lock_conflict_returns_409(
    client,
    supabase_admin_client,
    set_admin_emails,
):
    suffix = uuid4().hex[:8]
    editor = make_user(email=f"decision_editor_conflict_{suffix}@example.com")
    author = make_user(email=f"decision_author_conflict_{suffix}@example.com")
    set_admin_emails([editor.email])
    _require_decision_schema(supabase_admin_client)
    _ensure_profile(
        supabase_admin_client,
        user_id=editor.id,
        email=editor.email,
        roles=["managing_editor"],
    )
    _ensure_profile(
        supabase_admin_client,
        user_id=author.id,
        email=author.email,
        roles=["author"],
    )

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
async def test_academic_recommendation_then_editorial_execute_to_decision_writes_precheck_actions(
    client,
    supabase_admin_client,
    set_admin_emails,
):
    suffix = uuid4().hex[:8]
    editor = make_user(email=f"decision_editor_academic_execute_{suffix}@example.com")
    academic = make_user(email=f"decision_academic_execute_{suffix}@example.com")
    author = make_user(email=f"decision_author_academic_execute_{suffix}@example.com")
    set_admin_emails([editor.email])
    _require_precheck_schema(supabase_admin_client)

    _ensure_profile(
        supabase_admin_client,
        user_id=academic.id,
        email=academic.email,
        roles=["academic_editor"],
    )
    _ensure_profile(
        supabase_admin_client,
        user_id=editor.id,
        email=editor.email,
        roles=["managing_editor"],
    )
    _ensure_profile(
        supabase_admin_client,
        user_id=author.id,
        email=author.email,
        roles=["author"],
    )

    manuscript_id = str(uuid4())
    insert_manuscript(
        supabase_admin_client,
        manuscript_id=manuscript_id,
        author_id=author.id,
        status="pre_check",
        title="Academic Recommendation Execute Manuscript",
        version=1,
        file_path=f"manuscripts/{manuscript_id}/v1.pdf",
    )
    supabase_admin_client.table("manuscripts").update(
        {
            "pre_check_status": "academic",
            "academic_editor_id": academic.id,
        }
    ).eq("id", manuscript_id).execute()

    try:
        academic_res = await client.post(
            f"/api/v1/editor/manuscripts/{manuscript_id}/academic-check",
            headers={"Authorization": f"Bearer {academic.token}"},
            json={
                "decision": "decision_phase",
                "comment": "Recommend editorial decision without external review.",
            },
        )
        assert academic_res.status_code == 200, academic_res.text

        manuscript_after_recommendation = (
            supabase_admin_client.table("manuscripts")
            .select("status,pre_check_status")
            .eq("id", manuscript_id)
            .single()
            .execute()
            .data
        )
        assert manuscript_after_recommendation["status"] == "pre_check"
        assert manuscript_after_recommendation["pre_check_status"] == "academic"

        execute_res = await client.patch(
            f"/api/v1/editor/manuscripts/{manuscript_id}/status",
            headers={"Authorization": f"Bearer {editor.token}"},
            json={
                "status": "decision",
                "comment": "Editorial office accepted academic recommendation and moved to decision.",
            },
        )
        assert execute_res.status_code == 200, execute_res.text

        manuscript_after_execute = (
            supabase_admin_client.table("manuscripts")
            .select("status,pre_check_status")
            .eq("id", manuscript_id)
            .single()
            .execute()
            .data
        )
        assert manuscript_after_execute["status"] == "decision"
        assert manuscript_after_execute["pre_check_status"] is None

        logs = (
            supabase_admin_client.table("status_transition_logs")
            .select("payload,comment")
            .eq("manuscript_id", manuscript_id)
            .order("created_at", desc=False)
            .execute()
            .data
            or []
        )
        actions = [
            str((row.get("payload") or {}).get("action") or "")
            for row in logs
            if isinstance(row.get("payload"), dict)
        ]
        assert "precheck_academic_recommendation_submitted" in actions
        assert "precheck_academic_to_decision" in actions
    finally:
        _cleanup(supabase_admin_client, manuscript_id)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_academic_recommendation_then_editorial_execute_to_review_writes_precheck_actions(
    client,
    supabase_admin_client,
    set_admin_emails,
):
    suffix = uuid4().hex[:8]
    editor = make_user(email=f"decision_editor_academic_review_{suffix}@example.com")
    academic = make_user(email=f"decision_academic_review_{suffix}@example.com")
    author = make_user(email=f"decision_author_academic_review_{suffix}@example.com")
    set_admin_emails([editor.email])
    _require_precheck_schema(supabase_admin_client)

    _ensure_profile(
        supabase_admin_client,
        user_id=academic.id,
        email=academic.email,
        roles=["academic_editor"],
    )
    _ensure_profile(
        supabase_admin_client,
        user_id=editor.id,
        email=editor.email,
        roles=["managing_editor"],
    )
    _ensure_profile(
        supabase_admin_client,
        user_id=author.id,
        email=author.email,
        roles=["author"],
    )

    manuscript_id = str(uuid4())
    insert_manuscript(
        supabase_admin_client,
        manuscript_id=manuscript_id,
        author_id=author.id,
        status="pre_check",
        title="Academic Recommendation Review Manuscript",
        version=1,
        file_path=f"manuscripts/{manuscript_id}/v1.pdf",
    )
    supabase_admin_client.table("manuscripts").update(
        {
            "pre_check_status": "academic",
            "academic_editor_id": academic.id,
            "assistant_editor_id": editor.id,
        }
    ).eq("id", manuscript_id).execute()

    try:
        academic_res = await client.post(
            f"/api/v1/editor/manuscripts/{manuscript_id}/academic-check",
            headers={"Authorization": f"Bearer {academic.token}"},
            json={
                "decision": "review",
                "comment": "Recommend external review after academic pre-check.",
            },
        )
        assert academic_res.status_code == 200, academic_res.text

        execute_res = await client.patch(
            f"/api/v1/editor/manuscripts/{manuscript_id}/status",
            headers={"Authorization": f"Bearer {editor.token}"},
            json={
                "status": "under_review",
                "comment": "Editorial office accepted academic recommendation and moved to review.",
            },
        )
        assert execute_res.status_code == 200, execute_res.text

        manuscript_after_execute = (
            supabase_admin_client.table("manuscripts")
            .select("status,pre_check_status")
            .eq("id", manuscript_id)
            .single()
            .execute()
            .data
        )
        assert manuscript_after_execute["status"] == "under_review"
        assert manuscript_after_execute["pre_check_status"] is None

        logs = (
            supabase_admin_client.table("status_transition_logs")
            .select("payload,comment")
            .eq("manuscript_id", manuscript_id)
            .order("created_at", desc=False)
            .execute()
            .data
            or []
        )
        actions = [
            str((row.get("payload") or {}).get("action") or "")
            for row in logs
            if isinstance(row.get("payload"), dict)
        ]
        assert "precheck_academic_recommendation_submitted" in actions
        assert "precheck_academic_to_review" in actions
    finally:
        _cleanup(supabase_admin_client, manuscript_id)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_review_stage_exit_moves_to_decision_and_cancels_pending_reviewers(
    client,
    supabase_admin_client,
    set_admin_emails,
    monkeypatch: pytest.MonkeyPatch,
):
    suffix = uuid4().hex[:8]
    editor = make_user(email=f"decision_editor_exit_{suffix}@example.com")
    author = make_user(email=f"decision_author_exit_{suffix}@example.com")
    recipient = make_user(email=f"decision_recipient_exit_{suffix}@example.com")
    reviewer_selected = make_user(email=f"decision_reviewer_selected_{suffix}@example.com")
    reviewer_invited = make_user(email=f"decision_reviewer_invited_{suffix}@example.com")
    reviewer_opened = make_user(email=f"decision_reviewer_opened_{suffix}@example.com")
    reviewer_accepted = make_user(email=f"decision_reviewer_accepted_{suffix}@example.com")
    reviewer_submitted = make_user(email=f"decision_reviewer_submitted_{suffix}@example.com")
    set_admin_emails([editor.email])
    _require_decision_schema(supabase_admin_client)
    _require_review_assignment_schema(supabase_admin_client)
    _ensure_profile(
        supabase_admin_client,
        user_id=editor.id,
        email=editor.email,
        roles=["managing_editor"],
    )
    _ensure_profile(
        supabase_admin_client,
        user_id=author.id,
        email=author.email,
        roles=["author"],
    )

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
    inserted = _insert_review_assignments_compatible(supabase_admin_client, assignments)
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
    email_calls: list[dict[str, object]] = []
    monkeypatch.setattr(
        "app.services.first_decision_request_email.email_service.send_inline_email",
        lambda **kwargs: email_calls.append(kwargs) or {"status": "sent", "ok": True},
    )

    try:
        res = await client.post(
            f"/api/v1/editor/manuscripts/{manuscript_id}/review-stage-exit",
            headers={"Authorization": f"Bearer {editor.token}"},
            json={
                "target_stage": "first",
                "requested_outcome": "major_revision",
                "recipient_emails": [recipient.email],
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
        assert payload["data"]["first_decision_email_sent_recipients"] == [recipient.email]
        assert payload["data"]["first_decision_email_failed_recipients"] == []
        assert email_calls
        assert email_calls[0]["to_email"] == recipient.email

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


@pytest.mark.integration
@pytest.mark.asyncio
async def test_final_decision_prefers_latest_recommendation_template_for_author_email(
    client,
    supabase_admin_client,
    set_admin_emails,
    monkeypatch: pytest.MonkeyPatch,
):
    suffix = uuid4().hex[:8]
    editor = make_user(email=f"decision_editor_email_template_{suffix}@example.com")
    author = make_user(email=f"decision_author_email_template_{suffix}@example.com")
    set_admin_emails([editor.email])
    _require_decision_schema(supabase_admin_client)

    _ensure_profile(
        supabase_admin_client,
        user_id=author.id,
        email=author.email,
        roles=["author"],
    )

    manuscript_id = str(uuid4())
    insert_manuscript(
        supabase_admin_client,
        manuscript_id=manuscript_id,
        author_id=author.id,
        status="decision_done",
        title="Decision Email Template Manuscript",
        version=2,
        file_path=f"manuscripts/{manuscript_id}/v2.pdf",
    )
    supabase_admin_client.table("status_transition_logs").insert(
        {
            "manuscript_id": manuscript_id,
            "from_status": "decision_done",
            "to_status": "decision_done",
            "comment": "Academic board recommends reject and encourage resubmission.",
            "changed_by": None,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "payload": {
                "action": "decision_recommendation_submitted",
                "decision": "reject_resubmit",
                "workflow_decision": "reject",
                "decision_stage": "final",
            },
        }
    ).execute()

    email_calls: list[dict[str, object]] = []
    monkeypatch.setattr(
        "app.services.decision_service_transitions.email_service.send_inline_email",
        lambda **kwargs: email_calls.append(kwargs) or {"status": "sent", "ok": True},
    )

    try:
        res = await client.post(
            f"/api/v1/editor/manuscripts/{manuscript_id}/submit-decision",
            headers={"Authorization": f"Bearer {editor.token}"},
            json={
                "content": "Final reject decision recorded by editorial office.",
                "decision": "reject",
                "is_final": True,
                "decision_stage": "final",
                "attachment_paths": [],
                "last_updated_at": None,
            },
        )
        assert res.status_code == 200, res.text
        payload = res.json()
        assert payload["success"] is True
        assert payload["data"]["manuscript_status"] == "rejected"
        assert email_calls
        assert email_calls[0]["to_email"] == author.email
        assert email_calls[0]["template_key"] == "decision_reject_resubmit"
        assert email_calls[0]["context"]["decision_label"] == "Reject and Encourage Resubmitting after Revision"
    finally:
        _cleanup(supabase_admin_client, manuscript_id)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_review_stage_exit_allows_zero_submitted_reports(
    client,
    supabase_admin_client,
    set_admin_emails,
    monkeypatch: pytest.MonkeyPatch,
):
    suffix = uuid4().hex[:8]
    editor = make_user(email=f"decision_editor_zero_reports_{suffix}@example.com")
    author = make_user(email=f"decision_author_zero_reports_{suffix}@example.com")
    recipient = make_user(email=f"decision_recipient_zero_reports_{suffix}@example.com")
    reviewer_selected = make_user(email=f"decision_reviewer_zero_selected_{suffix}@example.com")
    reviewer_invited = make_user(email=f"decision_reviewer_zero_invited_{suffix}@example.com")
    set_admin_emails([editor.email])
    _require_decision_schema(supabase_admin_client)
    _require_review_assignment_schema(supabase_admin_client)
    _ensure_profile(
        supabase_admin_client,
        user_id=editor.id,
        email=editor.email,
        roles=["managing_editor"],
    )
    _ensure_profile(
        supabase_admin_client,
        user_id=author.id,
        email=author.email,
        roles=["author"],
    )

    manuscript_id = str(uuid4())
    insert_manuscript(
        supabase_admin_client,
        manuscript_id=manuscript_id,
        author_id=author.id,
        status="under_review",
        title="Review Stage Exit Without Reports Manuscript",
        version=2,
        file_path=f"manuscripts/{manuscript_id}/v2.pdf",
    )
    _insert_review_assignments_compatible(
        supabase_admin_client,
        [
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
        ]
    )

    email_calls: list[dict[str, object]] = []
    monkeypatch.setattr(
        "app.services.first_decision_request_email.email_service.send_inline_email",
        lambda **kwargs: email_calls.append(kwargs) or {"status": "sent", "ok": True},
    )

    try:
        res = await client.post(
            f"/api/v1/editor/manuscripts/{manuscript_id}/review-stage-exit",
            headers={"Authorization": f"Bearer {editor.token}"},
            json={
                "target_stage": "first",
                "requested_outcome": "accept_after_minor_revision",
                "recipient_emails": [recipient.email],
                "note": "Proceed without waiting for reviewer reports",
                "accepted_pending_resolutions": [],
            },
        )
        assert res.status_code == 200, res.text
        payload = res.json()
        assert payload["success"] is True
        assert payload["data"]["manuscript_status"] == "decision"
        assert payload["data"]["auto_cancelled_assignment_ids"]
        assert payload["data"]["manually_cancelled_assignment_ids"] == []
        assert payload["data"]["first_decision_email_sent_recipients"] == [recipient.email]
        assert payload["data"]["first_decision_email_failed_recipients"] == []
        assert email_calls
        assert email_calls[0]["to_email"] == recipient.email

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
            .select("reviewer_id,status")
            .eq("manuscript_id", manuscript_id)
            .execute()
            .data
            or []
        )
        status_map = {row["reviewer_id"]: row["status"] for row in rows}
        assert status_map[reviewer_selected.id] == "cancelled"
        assert status_map[reviewer_invited.id] == "cancelled"
    finally:
        _cleanup(supabase_admin_client, manuscript_id)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_review_stage_exit_first_decision_sends_request_email_with_academic_recommendation(
    client,
    supabase_admin_client,
    set_admin_emails,
    monkeypatch: pytest.MonkeyPatch,
):
    suffix = uuid4().hex[:8]
    editor = make_user(email=f"decision_editor_first_email_{suffix}@example.com")
    author = make_user(email=f"decision_author_first_email_{suffix}@example.com")
    recipient = make_user(email=f"decision_recipient_first_email_{suffix}@example.com")
    reviewer_selected = make_user(email=f"decision_reviewer_first_email_selected_{suffix}@example.com")
    reviewer_invited = make_user(email=f"decision_reviewer_first_email_invited_{suffix}@example.com")
    set_admin_emails([editor.email])
    _require_decision_schema(supabase_admin_client)
    _require_review_assignment_schema(supabase_admin_client)

    manuscript_id = str(uuid4())
    insert_manuscript(
        supabase_admin_client,
        manuscript_id=manuscript_id,
        author_id=author.id,
        status="under_review",
        title="Review Stage Exit First Decision Email Manuscript",
        version=2,
        file_path=f"manuscripts/{manuscript_id}/v2.pdf",
    )
    supabase_admin_client.table("review_assignments").insert(
        [
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
        ]
    ).execute()

    email_calls: list[dict[str, object]] = []
    monkeypatch.setattr(
        "app.services.first_decision_request_email.email_service.send_inline_email",
        lambda **kwargs: email_calls.append(kwargs) or {"status": "sent", "ok": True},
    )

    try:
        res = await client.post(
            f"/api/v1/editor/manuscripts/{manuscript_id}/review-stage-exit",
            headers={"Authorization": f"Bearer {editor.token}"},
            json={
                "target_stage": "first",
                "requested_outcome": "accept_after_minor_revision",
                "recipient_emails": [recipient.email],
                "note": "Route to first decision with accept-after-minor recommendation",
                "accepted_pending_resolutions": [],
            },
        )
        assert res.status_code == 200, res.text
        payload = res.json()
        assert payload["success"] is True
        assert payload["data"]["manuscript_status"] == "decision"
        assert payload["data"]["first_decision_email_sent_recipients"] == [recipient.email]
        assert payload["data"]["first_decision_email_failed_recipients"] == []
        assert email_calls
        assert email_calls[0]["to_email"] == recipient.email
        assert email_calls[0]["template_key"] == "first_decision_request_standard"
        assert email_calls[0]["context"]["requested_outcome"] == "accept_after_minor_revision"
        assert (
            email_calls[0]["context"]["requested_outcome_label"]
            == "Accept After Minor Revision"
        )
    finally:
        _cleanup(supabase_admin_client, manuscript_id)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_review_stage_exit_direct_minor_revision_returns_author_email_delivery_summary(
    client,
    supabase_admin_client,
    set_admin_emails,
    monkeypatch: pytest.MonkeyPatch,
):
    suffix = uuid4().hex[:8]
    editor = make_user(email=f"decision_editor_direct_minor_{suffix}@example.com")
    author = make_user(email=f"decision_author_direct_minor_{suffix}@example.com")
    set_admin_emails([editor.email])
    _require_decision_schema(supabase_admin_client)

    _ensure_profile(
        supabase_admin_client,
        user_id=editor.id,
        email=editor.email,
        roles=["managing_editor"],
    )
    _ensure_profile(
        supabase_admin_client,
        user_id=author.id,
        email=author.email,
        roles=["author"],
    )

    manuscript_id = str(uuid4())
    insert_manuscript(
        supabase_admin_client,
        manuscript_id=manuscript_id,
        author_id=author.id,
        status="under_review",
        title="Review Stage Exit Direct Minor Revision Manuscript",
        version=2,
        file_path=f"manuscripts/{manuscript_id}/v2.pdf",
        submission_email=author.email,
    )

    email_calls: list[dict[str, object]] = []
    monkeypatch.setattr(
        "app.services.decision_service.email_service.send_inline_email",
        lambda **kwargs: email_calls.append(kwargs) or {"status": "sent", "ok": True},
    )

    try:
        res = await client.post(
            f"/api/v1/editor/manuscripts/{manuscript_id}/review-stage-exit",
            headers={"Authorization": f"Bearer {editor.token}"},
            json={
                "target_stage": "minor_revision",
                "note": "Move directly to minor revision after editorial synthesis.",
                "accepted_pending_resolutions": [],
            },
        )
        assert res.status_code == 200, res.text
        payload = res.json()
        assert payload["success"] is True
        assert payload["data"]["manuscript_status"] == "minor_revision"
        assert payload["data"]["author_revision_email_sent_recipient"] == author.email
        assert payload["data"]["author_revision_email_failed_recipient"] is None
        assert email_calls
        assert email_calls[0]["to_email"] == author.email
        assert email_calls[0]["template_key"] == "direct_revision_request"

        manuscript = (
            supabase_admin_client.table("manuscripts")
            .select("status")
            .eq("id", manuscript_id)
            .single()
            .execute()
            .data
        )
        assert manuscript["status"] == "minor_revision"
    finally:
        _cleanup(supabase_admin_client, manuscript_id)
