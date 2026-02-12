from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from postgrest.exceptions import APIError

from .test_utils import insert_manuscript, make_user


def _cleanup(db, manuscript_id: str, *, user_ids: list[str]) -> None:
    for table, column in (
        ("production_proofreading_responses", "manuscript_id"),
        ("production_cycles", "manuscript_id"),
        ("status_transition_logs", "manuscript_id"),
        ("notifications", "manuscript_id"),
        ("invoices", "manuscript_id"),
        ("manuscripts", "id"),
    ):
        try:
            db.table(table).delete().eq(column, manuscript_id).execute()
        except Exception:
            pass

    for uid in user_ids:
        try:
            db.table("user_profiles").delete().eq("id", uid).execute()
        except Exception:
            pass


def _require_schema(db) -> None:
    checks = [
        ("production_cycles", "id,manuscript_id,status,proof_due_at"),
        ("production_proofreading_responses", "id,cycle_id,decision,submitted_at"),
        ("production_correction_items", "id,response_id,suggested_text"),
    ]
    for table, cols in checks:
        try:
            db.table(table).select(cols).limit(1).execute()
        except APIError as e:
            pytest.skip(f"数据库缺少 Feature 042 schema（{table}/{cols}）：{getattr(e, 'message', str(e))}")


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


async def _prepare_awaiting_author_cycle(*, client, manuscript_id: str, editor_token: str, editor_id: str, author_id: str) -> str:
    due = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()
    create = await client.post(
        f"/api/v1/editor/manuscripts/{manuscript_id}/production-cycles",
        headers={"Authorization": f"Bearer {editor_token}"},
        json={
            "layout_editor_id": editor_id,
            "proofreader_author_id": author_id,
            "proof_due_at": due,
        },
    )
    assert create.status_code == 201, create.text
    cycle_id = create.json()["data"]["cycle"]["id"]

    upload = await client.post(
        f"/api/v1/editor/manuscripts/{manuscript_id}/production-cycles/{cycle_id}/galley",
        headers={"Authorization": f"Bearer {editor_token}"},
        data={
            "version_note": "proof draft",
            "proof_due_at": due,
        },
        files={"file": ("proof.pdf", b"%PDF-1.4\n%mock", "application/pdf")},
    )
    assert upload.status_code == 200, upload.text
    return cycle_id


@pytest.mark.integration
@pytest.mark.asyncio
async def test_author_submit_confirm_clean_updates_cycle(
    client,
    supabase_admin_client,
    set_admin_emails,
):
    editor = make_user(email="proof_editor_confirm@example.com")
    author = make_user(email="proof_author_confirm@example.com")
    set_admin_emails([editor.email])
    _require_schema(supabase_admin_client)

    manuscript_id = str(uuid4())
    insert_manuscript(
        supabase_admin_client,
        manuscript_id=manuscript_id,
        author_id=author.id,
        status="approved",
        title="Proof Confirm Manuscript",
    )
    _ensure_profile(supabase_admin_client, user_id=editor.id, email=editor.email, roles=["admin", "editor", "author"])
    _ensure_profile(supabase_admin_client, user_id=author.id, email=author.email, roles=["author"])

    try:
        cycle_id = await _prepare_awaiting_author_cycle(
            client=client,
            manuscript_id=manuscript_id,
            editor_token=editor.token,
            editor_id=editor.id,
            author_id=author.id,
        )

        submit = await client.post(
            f"/api/v1/manuscripts/{manuscript_id}/production-cycles/{cycle_id}/proofreading",
            headers={"Authorization": f"Bearer {author.token}"},
            json={
                "decision": "confirm_clean",
                "summary": "Looks good.",
                "corrections": [],
            },
        )
        assert submit.status_code == 200, submit.text
        assert submit.json()["data"]["decision"] == "confirm_clean"

        cycle = (
            supabase_admin_client.table("production_cycles")
            .select("status")
            .eq("id", cycle_id)
            .single()
            .execute()
            .data
        )
        assert cycle["status"] == "author_confirmed"
    finally:
        _cleanup(supabase_admin_client, manuscript_id, user_ids=[editor.id, author.id])


@pytest.mark.integration
@pytest.mark.asyncio
async def test_author_submit_corrections_persists_items(
    client,
    supabase_admin_client,
    set_admin_emails,
):
    editor = make_user(email="proof_editor_corrections@example.com")
    author = make_user(email="proof_author_corrections@example.com")
    intruder = make_user(email="proof_intruder@example.com")
    set_admin_emails([editor.email])
    _require_schema(supabase_admin_client)

    manuscript_id = str(uuid4())
    insert_manuscript(
        supabase_admin_client,
        manuscript_id=manuscript_id,
        author_id=author.id,
        status="layout",
        title="Proof Corrections Manuscript",
    )
    _ensure_profile(supabase_admin_client, user_id=editor.id, email=editor.email, roles=["admin", "editor", "author"])
    _ensure_profile(supabase_admin_client, user_id=author.id, email=author.email, roles=["author"])
    _ensure_profile(supabase_admin_client, user_id=intruder.id, email=intruder.email, roles=["author"])

    try:
        cycle_id = await _prepare_awaiting_author_cycle(
            client=client,
            manuscript_id=manuscript_id,
            editor_token=editor.token,
            editor_id=editor.id,
            author_id=author.id,
        )

        denied = await client.post(
            f"/api/v1/manuscripts/{manuscript_id}/production-cycles/{cycle_id}/proofreading",
            headers={"Authorization": f"Bearer {intruder.token}"},
            json={
                "decision": "submit_corrections",
                "summary": "Need changes",
                "corrections": [{"suggested_text": "Replace typo"}],
            },
        )
        assert denied.status_code == 403, denied.text

        submit = await client.post(
            f"/api/v1/manuscripts/{manuscript_id}/production-cycles/{cycle_id}/proofreading",
            headers={"Authorization": f"Bearer {author.token}"},
            json={
                "decision": "submit_corrections",
                "summary": "Need two fixes",
                "corrections": [
                    {
                        "line_ref": "Page 2 para 1",
                        "original_text": "Teh result",
                        "suggested_text": "The result",
                        "reason": "Typo",
                    },
                    {
                        "line_ref": "Page 5 figure caption",
                        "suggested_text": "Update caption wording",
                        "reason": "Clarify meaning",
                    },
                ],
            },
        )
        assert submit.status_code == 200, submit.text
        assert submit.json()["data"]["decision"] == "submit_corrections"

        cycle = (
            supabase_admin_client.table("production_cycles")
            .select("status")
            .eq("id", cycle_id)
            .single()
            .execute()
            .data
        )
        assert cycle["status"] == "author_corrections_submitted"

        responses = (
            supabase_admin_client.table("production_proofreading_responses")
            .select("id")
            .eq("cycle_id", cycle_id)
            .execute()
            .data
            or []
        )
        assert len(responses) == 1
        response_id = responses[0]["id"]

        items = (
            supabase_admin_client.table("production_correction_items")
            .select("id,suggested_text")
            .eq("response_id", response_id)
            .execute()
            .data
            or []
        )
        assert len(items) == 2
    finally:
        _cleanup(supabase_admin_client, manuscript_id, user_ids=[editor.id, author.id, intruder.id])


@pytest.mark.integration
@pytest.mark.asyncio
async def test_proofreading_context_keeps_readonly_after_author_submit(
    client,
    supabase_admin_client,
    set_admin_emails,
):
    editor = make_user(email="proof_editor_context_after_submit@example.com")
    author = make_user(email="proof_author_context_after_submit@example.com")
    set_admin_emails([editor.email])
    _require_schema(supabase_admin_client)

    manuscript_id = str(uuid4())
    insert_manuscript(
        supabase_admin_client,
        manuscript_id=manuscript_id,
        author_id=author.id,
        status="layout",
        title="Proof Context After Submit",
    )
    _ensure_profile(
        supabase_admin_client,
        user_id=editor.id,
        email=editor.email,
        roles=["admin", "managing_editor", "author"],
    )
    _ensure_profile(supabase_admin_client, user_id=author.id, email=author.email, roles=["author"])

    try:
        cycle_id = await _prepare_awaiting_author_cycle(
            client=client,
            manuscript_id=manuscript_id,
            editor_token=editor.token,
            editor_id=editor.id,
            author_id=author.id,
        )

        submit = await client.post(
            f"/api/v1/manuscripts/{manuscript_id}/production-cycles/{cycle_id}/proofreading",
            headers={"Authorization": f"Bearer {author.token}"},
            json={
                "decision": "submit_corrections",
                "summary": "Need small fixes",
                "corrections": [{"suggested_text": "Fix typo in abstract"}],
            },
        )
        assert submit.status_code == 200, submit.text

        ctx = await client.get(
            f"/api/v1/manuscripts/{manuscript_id}/proofreading-context",
            headers={"Authorization": f"Bearer {author.token}"},
        )
        assert ctx.status_code == 200, ctx.text
        data = ctx.json()["data"]
        assert data["cycle"]["status"] == "author_corrections_submitted"
        assert data["is_read_only"] is True
        assert data["can_submit"] is False
    finally:
        _cleanup(supabase_admin_client, manuscript_id, user_ids=[editor.id, author.id])
