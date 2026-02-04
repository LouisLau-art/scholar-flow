import pytest
from httpx import AsyncClient
from uuid import uuid4

from postgrest.exceptions import APIError

from .test_utils import insert_manuscript, make_user


def _require_invoice_pdf_schema(db) -> None:
    try:
        db.table("invoices").select("id,manuscript_id,pdf_path,pdf_error").limit(1).execute()
    except APIError as e:
        pytest.skip(
            f"数据库缺少 Feature 026 所需 schema（invoices.pdf_path/pdf_error）：{getattr(e, 'message', str(e))}"
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
async def test_invoice_pdf_signed_url_access_control(
    client: AsyncClient,
    supabase_admin_client,
    set_admin_emails,
):
    try:
        import weasyprint  # noqa: F401
    except Exception as e:
        pytest.skip(f"WeasyPrint 不可用（缺系统依赖？）：{e}")

    editor = make_user(email="editor_invoice_dl@example.com")
    set_admin_emails([editor.email])

    author = make_user(email="author_invoice_dl@example.com")
    other = make_user(email="other_invoice_dl@example.com")

    manuscript_id = str(uuid4())
    _require_invoice_pdf_schema(supabase_admin_client)
    insert_manuscript(
        supabase_admin_client,
        manuscript_id=manuscript_id,
        author_id=author.id,
        status="pending_decision",
        title="Invoice Download Manuscript",
    )

    try:
        # Accept to create invoice (PDF generation may be async, but endpoints can self-heal)
        res = await client.post(
            "/api/v1/editor/decision",
            headers={"Authorization": f"Bearer {editor.token}"},
            json={"manuscript_id": manuscript_id, "decision": "accept", "apc_amount": 1000},
        )
        assert res.status_code == 200, res.text

        inv = (
            supabase_admin_client.table("invoices")
            .select("id")
            .eq("manuscript_id", manuscript_id)
            .single()
            .execute()
            .data
        )
        invoice_id = inv["id"]

        # Author can get signed URL
        r1 = await client.get(
            f"/api/v1/invoices/{invoice_id}/pdf-signed",
            headers={"Authorization": f"Bearer {author.token}"},
        )
        assert r1.status_code == 200, r1.text
        assert r1.json()["data"]["signed_url"]

        # Other user forbidden
        r2 = await client.get(
            f"/api/v1/invoices/{invoice_id}/pdf-signed",
            headers={"Authorization": f"Bearer {other.token}"},
        )
        assert r2.status_code == 403, r2.text

        # Editor can get signed URL
        r3 = await client.get(
            f"/api/v1/invoices/{invoice_id}/pdf-signed",
            headers={"Authorization": f"Bearer {editor.token}"},
        )
        assert r3.status_code == 200, r3.text

        # Manuscript-based download returns a PDF for author
        r4 = await client.get(
            f"/api/v1/manuscripts/{manuscript_id}/invoice",
            headers={"Authorization": f"Bearer {author.token}"},
        )
        assert r4.status_code == 200, r4.text
        assert r4.headers.get("content-type", "").startswith("application/pdf")
        assert r4.content.startswith(b"%PDF")

        # Other user forbidden
        r5 = await client.get(
            f"/api/v1/manuscripts/{manuscript_id}/invoice",
            headers={"Authorization": f"Bearer {other.token}"},
        )
        assert r5.status_code == 403, r5.text
    finally:
        _cleanup(supabase_admin_client, manuscript_id)

