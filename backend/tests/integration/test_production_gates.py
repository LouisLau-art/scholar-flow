import os
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from httpx import AsyncClient
from postgrest.exceptions import APIError

from .test_utils import insert_manuscript, make_user


def _require_schema(db) -> None:
    try:
        db.table("manuscripts").select("id,status,final_pdf_path,doi,published_at").limit(1).execute()
        db.table("invoices").select("id,manuscript_id,amount,status,confirmed_at").limit(1).execute()
    except APIError as e:
        pytest.skip(f"数据库缺少 Feature 031 所需 schema: {getattr(e, 'message', str(e))}")


def _has_transition_logs(db) -> bool:
    try:
        db.table("status_transition_logs").select("id").limit(1).execute()
        return True
    except Exception:
        return False


def _cleanup(db, manuscript_id: str) -> None:
    try:
        db.table("status_transition_logs").delete().eq("manuscript_id", manuscript_id).execute()
    except Exception:
        pass
    try:
        db.table("invoices").delete().eq("manuscript_id", manuscript_id).execute()
    except Exception:
        pass
    try:
        db.table("manuscripts").delete().eq("id", manuscript_id).execute()
    except Exception:
        pass


@pytest.mark.integration
@pytest.mark.asyncio
async def test_production_advance_enforces_gates_and_writes_audit_logs(
    client: AsyncClient,
    supabase_admin_client,
    set_admin_emails,
    monkeypatch,
):
    """
    端到端（后端侧）验证：
    - approved -> layout -> english_editing -> proofreading -> published
    - publish 前强制 Payment Gate（invoice paid/waived）
    - PRODUCTION_GATE_ENABLED=1 时强制 final_pdf_path
    - status_transition_logs（若存在）应记录每一步
    """
    editor = make_user(email="editor_prod_flow@example.com")
    set_admin_emails([editor.email])
    author = make_user(email="author_prod_flow@example.com")

    manuscript_id = str(uuid4())
    _require_schema(supabase_admin_client)

    insert_manuscript(
        supabase_admin_client,
        manuscript_id=manuscript_id,
        author_id=author.id,
        status="approved",
        title="Production Flow Manuscript",
    )

    try:
        # paid invoice
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

        # enable production gate + attach final pdf path
        monkeypatch.setenv("PRODUCTION_GATE_ENABLED", "1")
        supabase_admin_client.table("manuscripts").update(
            {"final_pdf_path": f"production/{manuscript_id}/final.pdf"}
        ).eq("id", manuscript_id).execute()

        for expected in ["layout", "english_editing", "proofreading", "published"]:
            res = await client.post(
                f"/api/v1/editor/manuscripts/{manuscript_id}/production/advance",
                headers={"Authorization": f"Bearer {editor.token}"},
            )
            assert res.status_code == 200, res.text
            body = res.json()
            assert body["success"] is True
            assert body["data"]["new_status"] == expected

            ms = (
                supabase_admin_client.table("manuscripts")
                .select("status")
                .eq("id", manuscript_id)
                .single()
                .execute()
                .data
            )
            assert ms["status"] == expected

        # audit log (best-effort: 若表不存在则不强制)
        if _has_transition_logs(supabase_admin_client):
            logs = (
                supabase_admin_client.table("status_transition_logs")
                .select("from_status,to_status,comment")
                .eq("manuscript_id", manuscript_id)
                .execute()
                .data
                or []
            )
            to_statuses = {row.get("to_status") for row in logs}
            assert {"layout", "english_editing", "proofreading", "published"}.issubset(to_statuses)
    finally:
        _cleanup(supabase_admin_client, manuscript_id)


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
        status="proofreading",
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
    finally:
        _cleanup(supabase_admin_client, manuscript_id)


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
        status="proofreading",
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

        # gate off + final_pdf_path missing should still publish
        monkeypatch.setenv("PRODUCTION_GATE_ENABLED", "0")
        res = await client.post(
            f"/api/v1/editor/manuscripts/{manuscript_id}/production/advance",
            headers={"Authorization": f"Bearer {editor.token}"},
        )
        assert res.status_code == 200, res.text
        body = res.json()
        assert body["success"] is True
        assert body["data"]["new_status"] == "published"
    finally:
        _cleanup(supabase_admin_client, manuscript_id)

