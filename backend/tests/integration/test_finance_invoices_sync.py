from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from httpx import AsyncClient
from postgrest.exceptions import APIError

from .test_utils import insert_manuscript, make_user


def _require_finance_schema(db) -> None:
    try:
        db.table("invoices").select("id,manuscript_id,amount,status,confirmed_at,created_at").limit(1).execute()
    except APIError as e:
        pytest.skip(f"数据库缺少 Feature 046 所需 schema（invoices）：{getattr(e, 'message', str(e))}")


def _cleanup(db, manuscript_ids: list[str]) -> None:
    for manuscript_id in manuscript_ids:
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


def _seed_invoice(
    db,
    *,
    manuscript_id: str,
    amount: float,
    status: str,
    invoice_number: str,
) -> None:
    db.table("invoices").upsert(
        {
            "manuscript_id": manuscript_id,
            "amount": amount,
            "status": status,
            "invoice_number": invoice_number,
            "confirmed_at": datetime.now(timezone.utc).isoformat() if status == "paid" else None,
        },
        on_conflict="manuscript_id",
    ).execute()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_finance_invoices_list_returns_real_data(
    client: AsyncClient,
    supabase_admin_client,
    set_admin_emails,
):
    editor = make_user(email="editor_finance_list@example.com")
    set_admin_emails([editor.email])
    author = make_user(email="author_finance_list@example.com")

    manuscript_id = str(uuid4())
    _require_finance_schema(supabase_admin_client)
    insert_manuscript(
        supabase_admin_client,
        manuscript_id=manuscript_id,
        author_id=author.id,
        status="approved",
        title="Finance Real Data Manuscript",
    )
    _seed_invoice(
        supabase_admin_client,
        manuscript_id=manuscript_id,
        amount=1200,
        status="unpaid",
        invoice_number="INV-F046-001",
    )

    try:
        res = await client.get(
            "/api/v1/editor/finance/invoices?status=all&page=1&page_size=20",
            headers={"Authorization": f"Bearer {editor.token}"},
        )
        assert res.status_code == 200, res.text
        body = res.json()
        assert body["success"] is True
        rows = body["data"]
        assert isinstance(rows, list)
        target = next((r for r in rows if r.get("manuscript_id") == manuscript_id), None)
        assert target is not None
        assert target["invoice_number"] == "INV-F046-001"
        assert target["effective_status"] == "unpaid"
    finally:
        _cleanup(supabase_admin_client, [manuscript_id])


@pytest.mark.integration
@pytest.mark.asyncio
async def test_finance_invoices_permissions(
    client: AsyncClient,
    supabase_admin_client,
    set_admin_emails,
):
    editor = make_user(email="editor_finance_permissions@example.com")
    set_admin_emails([editor.email])
    outsider = make_user(email="author_only_finance_permissions@example.com")
    _require_finance_schema(supabase_admin_client)

    # 未登录 -> 401
    res_unauth = await client.get("/api/v1/editor/finance/invoices")
    assert res_unauth.status_code == 401

    # 非内部角色 -> 403
    res_forbidden = await client.get(
        "/api/v1/editor/finance/invoices",
        headers={"Authorization": f"Bearer {outsider.token}"},
    )
    assert res_forbidden.status_code == 403

    # 内部角色 -> 200
    res_ok = await client.get(
        "/api/v1/editor/finance/invoices",
        headers={"Authorization": f"Bearer {editor.token}"},
    )
    assert res_ok.status_code == 200


@pytest.mark.integration
@pytest.mark.asyncio
async def test_finance_filters_and_export_follow_same_snapshot_rules(
    client: AsyncClient,
    supabase_admin_client,
    set_admin_emails,
):
    editor = make_user(email="editor_finance_filter_export@example.com")
    set_admin_emails([editor.email])
    author = make_user(email="author_finance_filter_export@example.com")
    _require_finance_schema(supabase_admin_client)

    paid_ms = str(uuid4())
    unpaid_ms = str(uuid4())
    waived_ms = str(uuid4())

    insert_manuscript(supabase_admin_client, manuscript_id=paid_ms, author_id=author.id, status="approved", title="Paid Manuscript")
    insert_manuscript(supabase_admin_client, manuscript_id=unpaid_ms, author_id=author.id, status="approved", title="Unpaid Manuscript")
    insert_manuscript(supabase_admin_client, manuscript_id=waived_ms, author_id=author.id, status="approved", title="Waived Manuscript")

    _seed_invoice(supabase_admin_client, manuscript_id=paid_ms, amount=1000, status="paid", invoice_number="INV-F046-PAID")
    _seed_invoice(supabase_admin_client, manuscript_id=unpaid_ms, amount=800, status="unpaid", invoice_number="INV-F046-UNPAID")
    # amount=0 + raw paid => effective waived
    _seed_invoice(supabase_admin_client, manuscript_id=waived_ms, amount=0, status="paid", invoice_number="INV-F046-WAIVED")

    try:
        res_waived = await client.get(
            "/api/v1/editor/finance/invoices?status=waived",
            headers={"Authorization": f"Bearer {editor.token}"},
        )
        assert res_waived.status_code == 200, res_waived.text
        rows = res_waived.json()["data"]
        ids = {r.get("manuscript_id") for r in rows}
        assert waived_ms in ids

        res_export_empty = await client.get(
            "/api/v1/editor/finance/invoices/export?status=paid&q=NOT_MATCH_ANYTHING",
            headers={"Authorization": f"Bearer {editor.token}"},
        )
        assert res_export_empty.status_code == 200
        assert res_export_empty.headers.get("x-export-empty") == "1"
        assert "invoice_id,manuscript_id" in res_export_empty.text

        res_export_paid = await client.get(
            "/api/v1/editor/finance/invoices/export?status=paid",
            headers={"Authorization": f"Bearer {editor.token}"},
        )
        assert res_export_paid.status_code == 200
        assert res_export_paid.headers.get("x-export-snapshot-at")
        assert "INV-F046-PAID" in res_export_paid.text
        assert "INV-F046-UNPAID" not in res_export_paid.text
    finally:
        _cleanup(supabase_admin_client, [paid_ms, unpaid_ms, waived_ms])


@pytest.mark.integration
@pytest.mark.asyncio
async def test_mark_paid_consistency_conflict_and_audit_log(
    client: AsyncClient,
    supabase_admin_client,
    set_admin_emails,
):
    editor = make_user(email="editor_finance_consistency@example.com")
    set_admin_emails([editor.email])
    author = make_user(email="author_finance_consistency@example.com")
    _require_finance_schema(supabase_admin_client)

    manuscript_id = str(uuid4())
    insert_manuscript(
        supabase_admin_client,
        manuscript_id=manuscript_id,
        author_id=author.id,
        status="approved",
        title="Consistency Manuscript",
    )
    _seed_invoice(
        supabase_admin_client,
        manuscript_id=manuscript_id,
        amount=1500,
        status="unpaid",
        invoice_number="INV-F046-CONSIST",
    )

    try:
        # 1) Editor Pipeline 路径确认支付
        res_confirm = await client.post(
            "/api/v1/editor/invoices/confirm",
            headers={"Authorization": f"Bearer {editor.token}"},
            json={
                "manuscript_id": manuscript_id,
                "expected_status": "unpaid",
                "source": "editor_pipeline",
            },
        )
        assert res_confirm.status_code == 200, res_confirm.text
        body_confirm = res_confirm.json()
        assert body_confirm["success"] is True
        assert body_confirm["data"]["current_status"] == "paid"

        # 2) Finance 列表应读取到 paid
        res_list_paid = await client.get(
            "/api/v1/editor/finance/invoices?status=paid",
            headers={"Authorization": f"Bearer {editor.token}"},
        )
        assert res_list_paid.status_code == 200, res_list_paid.text
        rows_paid = res_list_paid.json()["data"]
        hit = next((r for r in rows_paid if r.get("manuscript_id") == manuscript_id), None)
        assert hit is not None
        assert hit.get("effective_status") == "paid"

        # 3) 并发冲突：期望旧状态 unpaid，再次确认应 409
        res_conflict = await client.post(
            "/api/v1/editor/invoices/confirm",
            headers={"Authorization": f"Bearer {editor.token}"},
            json={
                "manuscript_id": manuscript_id,
                "expected_status": "unpaid",
                "source": "finance_page",
            },
        )
        assert res_conflict.status_code == 409, res_conflict.text

        # 4) 审计日志存在 finance action（若 payload 列可用）
        try:
            logs = (
                supabase_admin_client.table("status_transition_logs")
                .select("payload,manuscript_id")
                .eq("manuscript_id", manuscript_id)
                .execute()
            )
            rows = getattr(logs, "data", None) or []
            assert any(
                isinstance(r.get("payload"), dict)
                and r["payload"].get("action") == "finance_invoice_confirm_paid"
                for r in rows
            )
        except APIError as e:
            # 云端若缺 payload 字段，跳过该断言（接口本身应仍可工作）
            if "payload" in str(getattr(e, "message", str(e))).lower():
                pytest.skip("status_transition_logs.payload not available in current schema")
            raise
    finally:
        _cleanup(supabase_admin_client, [manuscript_id])
