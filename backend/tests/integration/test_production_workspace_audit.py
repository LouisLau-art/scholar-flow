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
        ("production_cycles", "id,manuscript_id,status"),
        ("production_proofreading_responses", "id,cycle_id,decision"),
        ("status_transition_logs", "id,manuscript_id,comment,payload,created_at"),
    ]
    for table, cols in checks:
        try:
            db.table(table).select(cols).limit(1).execute()
        except APIError as e:
            pytest.skip(f"数据库缺少审计测试所需 schema（{table}/{cols}）：{getattr(e, 'message', str(e))}")


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
async def test_production_audit_events_cover_full_cycle(
    client,
    supabase_admin_client,
    set_admin_emails,
):
    editor = make_user(email="prod_audit_editor@example.com")
    author = make_user(email="prod_audit_author@example.com")
    set_admin_emails([editor.email])
    _require_schema(supabase_admin_client)

    manuscript_id = str(uuid4())
    insert_manuscript(
        supabase_admin_client,
        manuscript_id=manuscript_id,
        author_id=author.id,
        status="approved",
        title="Production Audit Manuscript",
        file_path=f"manuscripts/{manuscript_id}/v1.pdf",
    )
    _ensure_profile(supabase_admin_client, user_id=editor.id, email=editor.email, roles=["admin", "editor", "author"])
    _ensure_profile(supabase_admin_client, user_id=author.id, email=author.email, roles=["author"])

    try:
        due = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()

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
        cycle_id = create_res.json()["data"]["cycle"]["id"]

        upload_res = await client.post(
            f"/api/v1/editor/manuscripts/{manuscript_id}/production-cycles/{cycle_id}/galley",
            headers={"Authorization": f"Bearer {editor.token}"},
            data={
                "version_note": "audit version",
                "proof_due_at": due,
            },
            files={"file": ("proof.pdf", b"%PDF-1.4\n%audit", "application/pdf")},
        )
        assert upload_res.status_code == 200, upload_res.text

        submit_res = await client.post(
            f"/api/v1/manuscripts/{manuscript_id}/production-cycles/{cycle_id}/proofreading",
            headers={"Authorization": f"Bearer {author.token}"},
            json={
                "decision": "confirm_clean",
                "summary": "All good",
                "corrections": [],
            },
        )
        assert submit_res.status_code == 200, submit_res.text

        approve_res = await client.post(
            f"/api/v1/editor/manuscripts/{manuscript_id}/production-cycles/{cycle_id}/approve",
            headers={"Authorization": f"Bearer {editor.token}"},
        )
        assert approve_res.status_code == 200, approve_res.text

        logs = (
            supabase_admin_client.table("status_transition_logs")
            .select("comment,payload,created_at")
            .eq("manuscript_id", manuscript_id)
            .order("created_at", desc=False)
            .execute()
            .data
            or []
        )

        event_types: list[str] = []
        for row in logs:
            payload = row.get("payload") or {}
            if isinstance(payload, dict) and payload.get("event_type"):
                event_types.append(str(payload.get("event_type")))

        # 需要包含完整关键事件；允许期间夹杂其他日志。
        for expected in [
            "production_cycle_created",
            "galley_uploaded",
            "proofreading_submitted",
            "production_approved",
        ]:
            assert expected in event_types

        # 确保大体顺序正确（递增索引）
        indexes = [event_types.index(name) for name in ["production_cycle_created", "galley_uploaded", "proofreading_submitted", "production_approved"]]
        assert indexes == sorted(indexes)
    finally:
        _cleanup(supabase_admin_client, manuscript_id, user_ids=[editor.id, author.id])
