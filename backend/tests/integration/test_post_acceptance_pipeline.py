import pytest
from httpx import AsyncClient
from uuid import uuid4
from datetime import datetime, timezone

from postgrest.exceptions import APIError

from .test_utils import insert_manuscript, make_user


def _require_post_acceptance_schema(db) -> None:
    try:
        db.table("manuscripts").select("final_pdf_path,doi,published_at").limit(1).execute()
        db.table("invoices").select("id,manuscript_id,amount,status,confirmed_at").limit(1).execute()
    except APIError as e:
        pytest.skip(
            f"数据库缺少 Feature 024 所需 schema（final_pdf_path/doi/published_at/invoices）：{getattr(e, 'message', str(e))}"
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
async def test_invoice_download_returns_pdf(
    client: AsyncClient,
    supabase_admin_client,
    set_admin_emails,
):
    editor = make_user(email="editor_invoice@example.com")
    set_admin_emails([editor.email])
    author = make_user(email="author_invoice@example.com")

    manuscript_id = str(uuid4())
    _require_post_acceptance_schema(supabase_admin_client)
    insert_manuscript(
        supabase_admin_client,
        manuscript_id=manuscript_id,
        author_id=author.id,
        status="decision",
        title="Invoice Download Manuscript",
    )

    try:
        # Accept -> create invoice
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
        assert inv["id"]

        pdf = await client.get(
            f"/api/v1/manuscripts/{manuscript_id}/invoice",
            headers={"Authorization": f"Bearer {author.token}"},
        )
        assert pdf.status_code == 200, pdf.text
        assert "application/pdf" in (pdf.headers.get("content-type") or "")
        assert pdf.content and len(pdf.content) > 200
    finally:
        _cleanup(supabase_admin_client, manuscript_id)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_mark_invoice_paid_endpoint(
    client: AsyncClient,
    supabase_admin_client,
    set_admin_emails,
):
    editor = make_user(email="editor_pay@example.com")
    set_admin_emails([editor.email])
    author = make_user(email="author_pay@example.com")

    manuscript_id = str(uuid4())
    _require_post_acceptance_schema(supabase_admin_client)
    insert_manuscript(
        supabase_admin_client,
        manuscript_id=manuscript_id,
        author_id=author.id,
        status="decision",
        title="Invoice Pay Manuscript",
    )

    try:
        # Accept -> create invoice
        res = await client.post(
            "/api/v1/editor/decision",
            headers={"Authorization": f"Bearer {editor.token}"},
            json={"manuscript_id": manuscript_id, "decision": "accept", "apc_amount": 1000},
        )
        assert res.status_code == 200, res.text

        inv = (
            supabase_admin_client.table("invoices")
            .select("id,status")
            .eq("manuscript_id", manuscript_id)
            .single()
            .execute()
            .data
        )
        assert inv["status"] in {"unpaid", "paid"}

        pay = await client.post(
            f"/api/v1/invoices/{inv['id']}/pay",
            headers={"Authorization": f"Bearer {editor.token}"},
        )
        assert pay.status_code == 200, pay.text
        body = pay.json()
        assert body["success"] is True
        assert body["data"]["status"] == "paid"
    finally:
        _cleanup(supabase_admin_client, manuscript_id)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_production_gate_blocks_until_final_pdf_present(
    client: AsyncClient,
    supabase_admin_client,
    set_admin_emails,
):
    editor = make_user(email="editor_production@example.com")
    set_admin_emails([editor.email])
    author = make_user(email="author_production@example.com")

    manuscript_id = str(uuid4())
    _require_post_acceptance_schema(supabase_admin_client)
    insert_manuscript(
        supabase_admin_client,
        manuscript_id=manuscript_id,
        author_id=author.id,
        status="decision",
        title="Production Gate Manuscript",
    )

    try:
        # Accept -> create invoice
        res = await client.post(
            "/api/v1/editor/decision",
            headers={"Authorization": f"Bearer {editor.token}"},
            json={"manuscript_id": manuscript_id, "decision": "accept", "apc_amount": 1000},
        )
        assert res.status_code == 200, res.text

        # Mark invoice paid
        supabase_admin_client.table("invoices").update(
            {"status": "paid", "confirmed_at": datetime.now(timezone.utc).isoformat()}
        ).eq("manuscript_id", manuscript_id).execute()

        # Publish without final pdf -> 400
        res2 = await client.post(
            "/api/v1/editor/publish",
            headers={"Authorization": f"Bearer {editor.token}"},
            json={"manuscript_id": manuscript_id},
        )
        assert res2.status_code == 400, res2.text

        # Upload minimal PDF bytes
        pdf_bytes = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF\n"
        files = {"file": ("final.pdf", pdf_bytes, "application/pdf")}
        up = await client.post(
            f"/api/v1/manuscripts/{manuscript_id}/production-file",
            headers={"Authorization": f"Bearer {editor.token}"},
            files=files,
        )
        assert up.status_code == 200, up.text
        body_up = up.json()
        assert body_up["success"] is True
        assert body_up["data"]["final_pdf_path"]

        # Publish should succeed now
        res3 = await client.post(
            "/api/v1/editor/publish",
            headers={"Authorization": f"Bearer {editor.token}"},
            json={"manuscript_id": manuscript_id},
        )
        assert res3.status_code == 200, res3.text
        body3 = res3.json()
        assert body3["success"] is True
        assert body3["data"]["status"] == "published"
    finally:
        _cleanup(supabase_admin_client, manuscript_id)
