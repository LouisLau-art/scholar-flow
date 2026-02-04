import pytest
from httpx import AsyncClient
from uuid import uuid4

from postgrest.exceptions import APIError

from .test_utils import insert_manuscript, make_user


def _require_finance_schema(db) -> None:
    try:
        db.table("invoices").select("id,manuscript_id,amount,status,confirmed_at").limit(1).execute()
    except APIError as e:
        pytest.skip(f"数据库缺少 APC 测试所需 schema（invoices）：{getattr(e, 'message', str(e))}")


def _cleanup(db, manuscript_id: str) -> None:
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
async def test_apc_confirmation_upserts_invoice(
    client: AsyncClient,
    supabase_admin_client,
    set_admin_emails,
):
    """
    US2：Accept 时必须创建/更新 invoice，并允许编辑修改 APC（upsert）
    """

    editor = make_user(email="editor_apc@example.com")
    set_admin_emails([editor.email])

    author = make_user(email="author_apc@example.com")

    manuscript_id = str(uuid4())
    _require_finance_schema(supabase_admin_client)
    insert_manuscript(
        supabase_admin_client,
        manuscript_id=manuscript_id,
        author_id=author.id,
        status="decision",
        title="APC Confirmation Manuscript",
    )

    try:
        # 1) First accept with APC 1500
        res1 = await client.post(
            "/api/v1/editor/decision",
            headers={"Authorization": f"Bearer {editor.token}"},
            json={"manuscript_id": manuscript_id, "decision": "accept", "apc_amount": 1500},
        )
        assert res1.status_code == 200, res1.text

        inv1 = (
            supabase_admin_client.table("invoices")
            .select("amount,status")
            .eq("manuscript_id", manuscript_id)
            .single()
            .execute()
            .data
        )
        assert float(inv1["amount"]) == 1500
        assert inv1["status"] == "unpaid"

        # 2) Re-accept with APC 0 (waive)
        res2 = await client.post(
            "/api/v1/editor/decision",
            headers={"Authorization": f"Bearer {editor.token}"},
            json={"manuscript_id": manuscript_id, "decision": "accept", "apc_amount": 0},
        )
        assert res2.status_code == 200, res2.text

        inv2 = (
            supabase_admin_client.table("invoices")
            .select("amount,status,confirmed_at")
            .eq("manuscript_id", manuscript_id)
            .single()
            .execute()
            .data
        )
        assert float(inv2["amount"]) == 0
        assert inv2["status"] == "paid"
        assert inv2.get("confirmed_at")
    finally:
        _cleanup(supabase_admin_client, manuscript_id)
