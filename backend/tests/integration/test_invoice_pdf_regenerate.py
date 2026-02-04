import pytest
from httpx import AsyncClient
from uuid import uuid4

from postgrest.exceptions import APIError

from .test_utils import insert_manuscript, make_user


def _require_invoice_pdf_schema(db) -> None:
    try:
        db.table("invoices").select(
            "id,manuscript_id,status,confirmed_at,invoice_number,pdf_path,pdf_generated_at,pdf_error"
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
async def test_regenerate_requires_internal_role_and_preserves_payment_status(
    client: AsyncClient,
    supabase_admin_client,
    set_admin_emails,
):
    try:
        import weasyprint  # noqa: F401
    except Exception as e:
        pytest.skip(f"WeasyPrint 不可用（缺系统依赖？）：{e}")

    editor = make_user(email="editor_invoice_regen@example.com")
    set_admin_emails([editor.email])

    author = make_user(email="author_invoice_regen@example.com")

    manuscript_id = str(uuid4())
    _require_invoice_pdf_schema(supabase_admin_client)
    insert_manuscript(
        supabase_admin_client,
        manuscript_id=manuscript_id,
        author_id=author.id,
        status="decision",
        title="Invoice Regenerate Manuscript",
    )

    try:
        res = await client.post(
            "/api/v1/editor/decision",
            headers={"Authorization": f"Bearer {editor.token}"},
            json={"manuscript_id": manuscript_id, "decision": "accept", "apc_amount": 1000},
        )
        assert res.status_code == 200, res.text

        inv = (
            supabase_admin_client.table("invoices")
            .select("id,status,confirmed_at")
            .eq("manuscript_id", manuscript_id)
            .single()
            .execute()
            .data
        )
        invoice_id = inv["id"]

        # Author cannot regenerate
        r_forbidden = await client.post(
            f"/api/v1/invoices/{invoice_id}/pdf/regenerate",
            headers={"Authorization": f"Bearer {author.token}"},
        )
        assert r_forbidden.status_code == 403, r_forbidden.text

        # Mark paid first; regeneration must not change it
        supabase_admin_client.table("invoices").update(
            {"status": "paid", "confirmed_at": "2026-02-03T00:00:00Z"}
        ).eq("id", invoice_id).execute()

        r_ok = await client.post(
            f"/api/v1/invoices/{invoice_id}/pdf/regenerate",
            headers={"Authorization": f"Bearer {editor.token}"},
        )
        assert r_ok.status_code == 200, r_ok.text
        data = r_ok.json()["data"]
        assert data["pdf_path"]
        assert data["pdf_generated_at"]

        inv_after = (
            supabase_admin_client.table("invoices")
            .select("status,confirmed_at,pdf_path,pdf_error")
            .eq("id", invoice_id)
            .single()
            .execute()
            .data
        )
        assert inv_after["status"] == "paid"
        assert inv_after.get("confirmed_at")
        assert (inv_after.get("pdf_error") or "").strip() == ""
        assert (inv_after.get("pdf_path") or "").strip() != ""
    finally:
        _cleanup(supabase_admin_client, manuscript_id)
