import pytest
from httpx import AsyncClient
from uuid import uuid4
from datetime import datetime, timezone

from postgrest.exceptions import APIError

from .test_utils import insert_manuscript, make_user


def _require_finance_schema(db) -> None:
    try:
        db.table("invoices").select("id,manuscript_id,amount,status,confirmed_at").limit(1).execute()
    except APIError as e:
        pytest.skip(f"数据库缺少财务 gate 测试所需 schema（invoices）：{getattr(e, 'message', str(e))}")


def _cleanup_financial_artifacts(db, manuscript_id: str) -> None:
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
async def test_financial_gate_blocks_unpaid_publish(
    client: AsyncClient,
    supabase_admin_client,
    set_admin_emails,
):
    """
    US2 场景：Accept -> APC > 0 -> Publish 失败(403) -> 支付 -> Publish 成功
    """

    editor = make_user(email="editor_finance@example.com")
    set_admin_emails([editor.email])

    author = make_user(email="author_finance@example.com")

    manuscript_id = str(uuid4())
    _require_finance_schema(supabase_admin_client)
    insert_manuscript(
        supabase_admin_client,
        manuscript_id=manuscript_id,
        author_id=author.id,
        status="pending_decision",
        title="Financial Gate Manuscript",
    )

    try:
        # 1) Accept + APC
        res = await client.post(
            "/api/v1/editor/decision",
            headers={"Authorization": f"Bearer {editor.token}"},
            json={"manuscript_id": manuscript_id, "decision": "accept", "apc_amount": 1500},
        )
        assert res.status_code == 200, res.text

        ms = (
            supabase_admin_client.table("manuscripts")
            .select("status")
            .eq("id", manuscript_id)
            .single()
            .execute()
            .data
        )
        assert ms["status"] == "approved"

        inv = (
            supabase_admin_client.table("invoices")
            .select("amount,status")
            .eq("manuscript_id", manuscript_id)
            .single()
            .execute()
            .data
        )
        assert float(inv["amount"]) == 1500
        assert inv["status"] == "unpaid"

        # 2) Publish should be blocked
        res2 = await client.post(
            "/api/v1/editor/publish",
            headers={"Authorization": f"Bearer {editor.token}"},
            json={"manuscript_id": manuscript_id},
        )
        assert res2.status_code == 403, res2.text

        # 3) Simulate payment
        supabase_admin_client.table("invoices").update(
            {"status": "paid", "confirmed_at": datetime.now(timezone.utc).isoformat()}
        ).eq("manuscript_id", manuscript_id).execute()

        # 4) Publish should succeed
        res3 = await client.post(
            "/api/v1/editor/publish",
            headers={"Authorization": f"Bearer {editor.token}"},
            json={"manuscript_id": manuscript_id},
        )
        assert res3.status_code == 200, res3.text
        body3 = res3.json()
        assert body3["success"] is True
        assert body3["data"]["status"] == "published"
        # 中文注释: 部分环境 manuscripts 表可能缺少 doi/published_at 字段，
        # editor.publish 会降级为仅更新 status；因此这里不强制断言 doi/published_at。
    finally:
        _cleanup_financial_artifacts(supabase_admin_client, manuscript_id)
