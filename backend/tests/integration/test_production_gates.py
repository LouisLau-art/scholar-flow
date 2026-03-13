from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from httpx import AsyncClient

from .test_utils import insert_manuscript, make_user
from .test_production_workspace_api import _require_schema


def _load_transition_logs_or_skip(db, manuscript_id: str) -> list[dict]:
    try:
        resp = (
            db.table("status_transition_logs")
            .select("id,manuscript_id,from_status,to_status,comment,created_at")
            .eq("manuscript_id", manuscript_id)
            .execute()
        )
    except Exception as exc:
        pytest.skip(f"status_transition_logs schema unavailable for production gate assertions: {exc}")
    return getattr(resp, "data", None) or []


@pytest.mark.integration
@pytest.mark.asyncio
async def test_production_advance_enforces_gates_and_writes_audit_logs(
    client: AsyncClient,
    supabase_admin_client,
    set_admin_emails,
    monkeypatch,
):
    editor = make_user(email="editor_prod_flow@example.com")
    set_admin_emails([editor.email])
    author = make_user(email="author_prod_flow@example.com")

    manuscript_id = str(uuid4())
    _require_schema(supabase_admin_client)

    insert_manuscript(
        supabase_admin_client,
        manuscript_id=manuscript_id,
        author_id=author.id,
        status="approved_for_publish",
        title="Production Flow Manuscript",
    )

    try:
        inv_id = str(uuid4())
        supabase_admin_client.table("invoices").insert(
            {
                "id": inv_id,
                "manuscript_id": manuscript_id,
                "amount": 1000,
                "status": "paid",
                "confirmed_at": datetime.now(timezone.utc).isoformat(),
            }
        ).execute()

        monkeypatch.setenv("PRODUCTION_GATE_ENABLED", "1")
        supabase_admin_client.table("manuscripts").update(
            {"final_pdf_path": f"production/{manuscript_id}/final.pdf"}
        ).eq("id", manuscript_id).execute()
        
        # We need a cycle to pass assert_publish_gate_ready
        supabase_admin_client.table("production_cycles").insert(
            {
                "manuscript_id": manuscript_id,
                "cycle_no": 1,
                "status": "approved_for_publish",
                "stage": "ready_to_publish",
                "layout_editor_id": editor.id,
                "proofreader_author_id": author.id,
                "galley_path": "fake/path.pdf"
            }
        ).execute()

        res = await client.post(
            f"/api/v1/editor/manuscripts/{manuscript_id}/production/advance",
            headers={"Authorization": f"Bearer {editor.token}"},
        )
        assert res.status_code == 200, res.text
        assert res.json()["data"]["new_status"] == "published"
        transition_logs = _load_transition_logs_or_skip(supabase_admin_client, manuscript_id)
        assert any(
            str(row.get("from_status") or "").strip().lower() == "approved_for_publish"
            and str(row.get("to_status") or "").strip().lower() == "published"
            for row in transition_logs
        )
    finally:
        supabase_admin_client.table("production_cycles").delete().eq("manuscript_id", manuscript_id).execute()
        supabase_admin_client.table("status_transition_logs").delete().eq("manuscript_id", manuscript_id).execute()
        supabase_admin_client.table("invoices").delete().eq("manuscript_id", manuscript_id).execute()
        supabase_admin_client.table("manuscripts").delete().eq("id", manuscript_id).execute()
        supabase_admin_client.table("user_profiles").delete().in_("id", [editor.id, author.id]).execute()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_payment_gate_blocks_publish_step(
    client: AsyncClient,
    supabase_admin_client,
    set_admin_emails,
    monkeypatch,
):
    editor = make_user(email="editor_prod_gate_pay@example.com")
    set_admin_emails([editor.email])
    author = make_user(email="author_prod_gate_pay@example.com")

    manuscript_id = str(uuid4())
    _require_schema(supabase_admin_client)
    insert_manuscript(
        supabase_admin_client,
        manuscript_id=manuscript_id,
        author_id=author.id,
        status="approved_for_publish",
        title="Payment Gate Manuscript",
    )

    try:
        supabase_admin_client.table("invoices").insert(
            {
                "id": str(uuid4()),
                "manuscript_id": manuscript_id,
                "amount": 1000,
                "status": "unpaid",
            }
        ).execute()

        monkeypatch.setenv("PRODUCTION_GATE_ENABLED", "0")
        res = await client.post(
            f"/api/v1/editor/manuscripts/{manuscript_id}/production/advance",
            headers={"Authorization": f"Bearer {editor.token}"},
        )
        assert res.status_code == 403, res.text
        assert "Payment Required" in res.json()["detail"]
    finally:
        supabase_admin_client.table("status_transition_logs").delete().eq("manuscript_id", manuscript_id).execute()
        supabase_admin_client.table("invoices").delete().eq("manuscript_id", manuscript_id).execute()
        supabase_admin_client.table("manuscripts").delete().eq("id", manuscript_id).execute()
        supabase_admin_client.table("user_profiles").delete().in_("id", [editor.id, author.id]).execute()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_production_gate_can_be_disabled(
    client: AsyncClient,
    supabase_admin_client,
    set_admin_emails,
    monkeypatch,
):
    editor = make_user(email="editor_prod_gate_off@example.com")
    set_admin_emails([editor.email])
    author = make_user(email="author_prod_gate_off@example.com")

    manuscript_id = str(uuid4())
    _require_schema(supabase_admin_client)
    insert_manuscript(
        supabase_admin_client,
        manuscript_id=manuscript_id,
        author_id=author.id,
        status="approved_for_publish",
        title="Production Gate Off Manuscript",
    )

    try:
        supabase_admin_client.table("invoices").insert(
            {
                "id": str(uuid4()),
                "manuscript_id": manuscript_id,
                "amount": 1000,
                "status": "paid",
                "confirmed_at": datetime.now(timezone.utc).isoformat(),
            }
        ).execute()
        
        # We need a cycle to pass assert_publish_gate_ready
        supabase_admin_client.table("production_cycles").insert(
            {
                "manuscript_id": manuscript_id,
                "cycle_no": 1,
                "status": "approved_for_publish",
                "stage": "ready_to_publish",
                "layout_editor_id": editor.id,
                "proofreader_author_id": author.id,
                "galley_path": "fake/path.pdf"
            }
        ).execute()

        monkeypatch.setenv("PRODUCTION_GATE_ENABLED", "0")
        res = await client.post(
            f"/api/v1/editor/manuscripts/{manuscript_id}/production/advance",
            headers={"Authorization": f"Bearer {editor.token}"},
        )
        assert res.status_code == 200, res.text
        assert res.json()["data"]["new_status"] == "published"
    finally:
        supabase_admin_client.table("production_cycles").delete().eq("manuscript_id", manuscript_id).execute()
        supabase_admin_client.table("status_transition_logs").delete().eq("manuscript_id", manuscript_id).execute()
        supabase_admin_client.table("invoices").delete().eq("manuscript_id", manuscript_id).execute()
        supabase_admin_client.table("manuscripts").delete().eq("id", manuscript_id).execute()
        supabase_admin_client.table("user_profiles").delete().in_("id", [editor.id, author.id]).execute()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_production_revert_route_explicitly_rejects_legacy_status_revert(
    client: AsyncClient,
    supabase_admin_client,
    set_admin_emails,
):
    editor = make_user(email="editor_prod_revert_blocked@example.com")
    set_admin_emails([editor.email])
    author = make_user(email="author_prod_revert_blocked@example.com")

    manuscript_id = str(uuid4())
    _require_schema(supabase_admin_client)
    insert_manuscript(
        supabase_admin_client,
        manuscript_id=manuscript_id,
        author_id=author.id,
        status="approved_for_publish",
        title="Production Revert Blocked Manuscript",
    )

    try:
        res = await client.post(
            f"/api/v1/editor/manuscripts/{manuscript_id}/production/revert",
            headers={"Authorization": f"Bearer {editor.token}"},
        )
        assert res.status_code == 400, res.text
        detail = res.json()["detail"]
        assert "no longer supported" in detail
        assert "Production Workspace" in detail
        manuscript_row = (
            supabase_admin_client.table("manuscripts")
            .select("id,status")
            .eq("id", manuscript_id)
            .single()
            .execute()
        )
        manuscript = getattr(manuscript_row, "data", None) or {}
        assert manuscript.get("status") == "approved_for_publish"
        transition_logs = _load_transition_logs_or_skip(supabase_admin_client, manuscript_id)
        assert transition_logs == []
    finally:
        supabase_admin_client.table("status_transition_logs").delete().eq("manuscript_id", manuscript_id).execute()
        supabase_admin_client.table("manuscripts").delete().eq("id", manuscript_id).execute()
        supabase_admin_client.table("user_profiles").delete().in_("id", [editor.id, author.id]).execute()
