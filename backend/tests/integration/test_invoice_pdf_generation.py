import pytest
from httpx import AsyncClient
from uuid import uuid4

from postgrest.exceptions import APIError

from .test_utils import insert_manuscript, make_user


def _require_invoice_pdf_schema(db) -> None:
    try:
        db.table("invoices").select(
            "id,manuscript_id,invoice_number,pdf_path,pdf_generated_at,pdf_error"
        ).limit(1).execute()
    except APIError as e:
        pytest.skip(
            f"数据库缺少 Feature 026 所需 schema（invoices.invoice_number/pdf_path/...）：{getattr(e, 'message', str(e))}"
        )


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
async def test_accept_triggers_invoice_pdf_generation(
    client: AsyncClient,
    supabase_admin_client,
    set_admin_emails,
):
    """
    Feature 026 / US1：录用后自动生成并持久化 Invoice PDF（回填 pdf_path / invoice_number）。
    """
    try:
        import weasyprint  # noqa: F401
    except Exception as e:
        pytest.skip(f"WeasyPrint 不可用（缺系统依赖？）：{e}")

    editor = make_user(email="editor_invoice_pdf@example.com")
    set_admin_emails([editor.email])

    author = make_user(email="author_invoice_pdf@example.com")

    manuscript_id = str(uuid4())
    _require_invoice_pdf_schema(supabase_admin_client)
    insert_manuscript(
        supabase_admin_client,
        manuscript_id=manuscript_id,
        author_id=author.id,
        status="pending_decision",
        title="Invoice PDF Manuscript",
    )

    try:
        res = await client.post(
            "/api/v1/editor/decision",
            headers={"Authorization": f"Bearer {editor.token}"},
            json={"manuscript_id": manuscript_id, "decision": "accept", "apc_amount": 1000},
        )
        assert res.status_code == 200, res.text

        # 由于 PDF 生成在 BackgroundTasks 中执行，这里做短轮询等待回填字段
        inv = None
        for _ in range(25):
            inv = (
                supabase_admin_client.table("invoices")
                .select("id,invoice_number,pdf_path,pdf_error")
                .eq("manuscript_id", manuscript_id)
                .single()
                .execute()
                .data
            )
            if (inv.get("pdf_path") or "").strip() or (inv.get("pdf_error") or "").strip():
                break
            import asyncio

            await asyncio.sleep(0.2)

        assert inv is not None
        assert (inv.get("pdf_error") or "").strip() == ""
        assert (inv.get("invoice_number") or "").startswith("INV-")
        assert (inv.get("pdf_path") or "").strip() != ""
    finally:
        _cleanup(supabase_admin_client, manuscript_id)

