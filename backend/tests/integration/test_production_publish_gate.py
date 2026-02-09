from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from postgrest.exceptions import APIError

from .test_utils import insert_manuscript, make_user


def _cleanup(db, manuscript_id: str, *, user_ids: list[str]) -> None:
    for table, column in (
        ("production_correction_items", "id"),
        ("production_proofreading_responses", "manuscript_id"),
        ("production_cycles", "manuscript_id"),
        ("status_transition_logs", "manuscript_id"),
        ("notifications", "manuscript_id"),
        ("invoices", "manuscript_id"),
        ("manuscripts", "id"),
    ):
        try:
            if table == "production_correction_items":
                # correction items 通过 response 级联删除；这里不做全表删除
                continue
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
        ("production_cycles", "id,manuscript_id,cycle_no,status,galley_path"),
        ("invoices", "id,manuscript_id,amount,status"),
        ("manuscripts", "id,status,final_pdf_path"),
    ]
    for table, cols in checks:
        try:
            db.table(table).select(cols).limit(1).execute()
        except APIError as e:
            pytest.skip(f"数据库缺少发布门禁测试所需 schema（{table}/{cols}）：{getattr(e, 'message', str(e))}")


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


def _seed_invoice_paid(db, *, manuscript_id: str) -> None:
    db.table("invoices").upsert(
        {
            "manuscript_id": manuscript_id,
            "amount": 100,
            "status": "paid",
            "updated_at": datetime.now(timezone.utc).isoformat(),
        },
        on_conflict="manuscript_id",
    ).execute()


def _seed_cycle(db, *, manuscript_id: str, editor_id: str, author_id: str, status: str) -> None:
    db.table("production_cycles").insert(
        {
            "manuscript_id": manuscript_id,
            "cycle_no": 1,
            "status": status,
            "layout_editor_id": editor_id,
            "proofreader_author_id": author_id,
            "galley_bucket": "production-proofs",
            "galley_path": f"production_cycles/{manuscript_id}/cycle-1/proof.pdf",
            "version_note": "v1",
            "proof_due_at": datetime.now(timezone.utc).isoformat(),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "approved_by": editor_id if status == "approved_for_publish" else None,
            "approved_at": datetime.now(timezone.utc).isoformat() if status == "approved_for_publish" else None,
        }
    ).execute()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_publish_requires_approved_production_cycle(
    client,
    supabase_admin_client,
    set_admin_emails,
):
    editor = make_user(email="publish_gate_editor_required@example.com")
    author = make_user(email="publish_gate_author_required@example.com")
    set_admin_emails([editor.email])
    _require_schema(supabase_admin_client)

    manuscript_id = str(uuid4())
    insert_manuscript(
        supabase_admin_client,
        manuscript_id=manuscript_id,
        author_id=author.id,
        status="proofreading",
        title="Publish Gate Required",
        file_path=f"manuscripts/{manuscript_id}/v1.pdf",
    )
    _ensure_profile(supabase_admin_client, user_id=editor.id, email=editor.email, roles=["admin", "editor", "author"])
    _ensure_profile(supabase_admin_client, user_id=author.id, email=author.email, roles=["author"])

    try:
        # 满足既有门禁：支付 + final_pdf_path
        _seed_invoice_paid(supabase_admin_client, manuscript_id=manuscript_id)
        supabase_admin_client.table("manuscripts").update(
            {"final_pdf_path": f"production/{manuscript_id}/final.pdf"}
        ).eq("id", manuscript_id).execute()

        _seed_cycle(
            supabase_admin_client,
            manuscript_id=manuscript_id,
            editor_id=editor.id,
            author_id=author.id,
            status="awaiting_author",
        )

        res = await client.post(
            f"/api/v1/editor/manuscripts/{manuscript_id}/production/advance",
            headers={"Authorization": f"Bearer {editor.token}"},
        )
        assert res.status_code == 403, res.text
        assert "not approved" in res.text.lower() or "approval" in res.text.lower()
    finally:
        _cleanup(supabase_admin_client, manuscript_id, user_ids=[editor.id, author.id])


@pytest.mark.integration
@pytest.mark.asyncio
async def test_publish_succeeds_with_approved_production_cycle(
    client,
    supabase_admin_client,
    set_admin_emails,
):
    editor = make_user(email="publish_gate_editor_success@example.com")
    author = make_user(email="publish_gate_author_success@example.com")
    set_admin_emails([editor.email])
    _require_schema(supabase_admin_client)

    manuscript_id = str(uuid4())
    insert_manuscript(
        supabase_admin_client,
        manuscript_id=manuscript_id,
        author_id=author.id,
        status="proofreading",
        title="Publish Gate Success",
        file_path=f"manuscripts/{manuscript_id}/v1.pdf",
    )
    _ensure_profile(supabase_admin_client, user_id=editor.id, email=editor.email, roles=["admin", "editor", "author"])
    _ensure_profile(supabase_admin_client, user_id=author.id, email=author.email, roles=["author"])

    try:
        _seed_invoice_paid(supabase_admin_client, manuscript_id=manuscript_id)
        supabase_admin_client.table("manuscripts").update(
            {"final_pdf_path": f"production/{manuscript_id}/final.pdf"}
        ).eq("id", manuscript_id).execute()

        _seed_cycle(
            supabase_admin_client,
            manuscript_id=manuscript_id,
            editor_id=editor.id,
            author_id=author.id,
            status="approved_for_publish",
        )

        res = await client.post(
            f"/api/v1/editor/manuscripts/{manuscript_id}/production/advance",
            headers={"Authorization": f"Bearer {editor.token}"},
        )
        assert res.status_code == 200, res.text
        assert res.json()["data"]["new_status"] == "published"
    finally:
        _cleanup(supabase_admin_client, manuscript_id, user_ids=[editor.id, author.id])
