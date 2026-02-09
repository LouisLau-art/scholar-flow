from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from postgrest.exceptions import APIError

from .test_utils import insert_manuscript, make_user


def _cleanup(db, manuscript_id: str, *, user_ids: list[str]) -> None:
    tables = [
        ("production_proofreading_responses", "manuscript_id", manuscript_id),
        ("production_cycles", "manuscript_id", manuscript_id),
        ("status_transition_logs", "manuscript_id", manuscript_id),
        ("notifications", "manuscript_id", manuscript_id),
        ("invoices", "manuscript_id", manuscript_id),
        ("manuscripts", "id", manuscript_id),
    ]
    for table, column, value in tables:
        try:
            q = db.table(table).delete()
            if value is not None:
                q = q.eq(column, value)
            q.execute()
        except Exception:
            pass

    for uid in user_ids:
        try:
            db.table("user_profiles").delete().eq("id", uid).execute()
        except Exception:
            pass


def _require_schema(db) -> None:
    checks = [
        ("production_cycles", "id,manuscript_id,cycle_no,status,galley_path"),
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


@pytest.mark.integration
@pytest.mark.asyncio
async def test_editor_can_create_cycle_and_upload_galley(
    client,
    supabase_admin_client,
    set_admin_emails,
):
    editor = make_user(email="prod_editor_workspace@example.com")
    author = make_user(email="prod_author_workspace@example.com")
    set_admin_emails([editor.email])
    _require_schema(supabase_admin_client)

    manuscript_id = str(uuid4())
    insert_manuscript(
        supabase_admin_client,
        manuscript_id=manuscript_id,
        author_id=author.id,
        status="approved",
        title="Production Workspace Manuscript",
        file_path=f"manuscripts/{manuscript_id}/v1.pdf",
    )
    _ensure_profile(supabase_admin_client, user_id=editor.id, email=editor.email, roles=["admin", "editor", "author"])
    _ensure_profile(supabase_admin_client, user_id=author.id, email=author.email, roles=["author"])

    try:
        due = (datetime.now(timezone.utc) + timedelta(days=3)).isoformat()
        create_res = await client.post(
            f"/api/v1/editor/manuscripts/{manuscript_id}/production-cycles",
            headers={"Authorization": f"Bearer {editor.token}"},
            json={
                "layout_editor_id": editor.id,
                "proofreader_author_id": author.id,
                "proof_due_at": due,
            },
        )
        assert create_res.status_code == 201, create_res.text
        create_data = create_res.json()["data"]["cycle"]
        assert create_data["status"] == "draft"
        cycle_id = create_data["id"]

        upload_res = await client.post(
            f"/api/v1/editor/manuscripts/{manuscript_id}/production-cycles/{cycle_id}/galley",
            headers={"Authorization": f"Bearer {editor.token}"},
            data={
                "version_note": "v1 galley",
                "proof_due_at": due,
            },
            files={"file": ("proof.pdf", b"%PDF-1.4\n%mock", "application/pdf")},
        )
        assert upload_res.status_code == 200, upload_res.text
        uploaded = upload_res.json()["data"]["cycle"]
        assert uploaded["status"] == "awaiting_author"
        assert uploaded["galley_path"]

        ctx_res = await client.get(
            f"/api/v1/editor/manuscripts/{manuscript_id}/production-workspace",
            headers={"Authorization": f"Bearer {editor.token}"},
        )
        assert ctx_res.status_code == 200, ctx_res.text
        ctx = ctx_res.json()["data"]
        assert ctx["active_cycle"]["id"] == cycle_id
        assert ctx["active_cycle"]["status"] == "awaiting_author"

        approve_res = await client.post(
            f"/api/v1/editor/manuscripts/{manuscript_id}/production-cycles/{cycle_id}/approve",
            headers={"Authorization": f"Bearer {editor.token}"},
        )
        assert approve_res.status_code == 422, approve_res.text
    finally:
        _cleanup(supabase_admin_client, manuscript_id, user_ids=[editor.id, author.id])


@pytest.mark.integration
@pytest.mark.asyncio
async def test_create_cycle_blocks_when_active_cycle_exists(
    client,
    supabase_admin_client,
    set_admin_emails,
):
    editor = make_user(email="prod_editor_active_cycle@example.com")
    author = make_user(email="prod_author_active_cycle@example.com")
    set_admin_emails([editor.email])
    _require_schema(supabase_admin_client)

    manuscript_id = str(uuid4())
    insert_manuscript(
        supabase_admin_client,
        manuscript_id=manuscript_id,
        author_id=author.id,
        status="layout",
        title="Cycle Conflict Manuscript",
    )
    _ensure_profile(supabase_admin_client, user_id=editor.id, email=editor.email, roles=["admin", "editor", "author"])
    _ensure_profile(supabase_admin_client, user_id=author.id, email=author.email, roles=["author"])

    try:
        due = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()
        first = await client.post(
            f"/api/v1/editor/manuscripts/{manuscript_id}/production-cycles",
            headers={"Authorization": f"Bearer {editor.token}"},
            json={
                "layout_editor_id": editor.id,
                "proofreader_author_id": author.id,
                "proof_due_at": due,
            },
        )
        assert first.status_code == 201, first.text

        second = await client.post(
            f"/api/v1/editor/manuscripts/{manuscript_id}/production-cycles",
            headers={"Authorization": f"Bearer {editor.token}"},
            json={
                "layout_editor_id": editor.id,
                "proofreader_author_id": author.id,
                "proof_due_at": due,
            },
        )
        assert second.status_code == 409, second.text
    finally:
        _cleanup(supabase_admin_client, manuscript_id, user_ids=[editor.id, author.id])
