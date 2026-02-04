import pytest
from httpx import AsyncClient
from uuid import uuid4

from .test_utils import insert_manuscript, make_user


def _cleanup(db, manuscript_id: str) -> None:
    try:
        db.table("status_transition_logs").delete().eq("manuscript_id", manuscript_id).execute()
    except Exception:
        pass
    try:
        db.table("manuscripts").delete().eq("id", manuscript_id).execute()
    except Exception:
        pass


@pytest.mark.integration
@pytest.mark.asyncio
async def test_editor_manuscript_detail_includes_invoice_metadata_and_signed_files(
    client: AsyncClient,
    supabase_admin_client,
    set_admin_emails,
):
    editor = make_user(email="editor_details@example.com")
    set_admin_emails([editor.email])
    author = make_user(email="author_details@example.com")

    manuscript_id = str(uuid4())
    insert_manuscript(
        supabase_admin_client,
        manuscript_id=manuscript_id,
        author_id=author.id,
        status="decision",
        title="Details Manuscript",
        file_path="manuscripts/demo.pdf",
    )

    try:
        res = await client.get(
            f"/api/v1/editor/manuscripts/{manuscript_id}",
            headers={"Authorization": f"Bearer {editor.token}"},
        )
        assert res.status_code == 200, res.text
        body = res.json()
        assert body.get("success") is True
        data = body.get("data") or {}
        assert data.get("id") == manuscript_id
        assert "invoice_metadata" in data

        signed = (data.get("signed_files") or {}).get("original_manuscript") or {}
        assert signed.get("bucket") == "manuscripts"
        assert signed.get("path") == "manuscripts/demo.pdf"
        assert "signed_url" in signed
    finally:
        _cleanup(supabase_admin_client, manuscript_id)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_editor_can_update_invoice_info_and_audit_log_written(
    client: AsyncClient,
    supabase_admin_client,
    set_admin_emails,
):
    editor = make_user(email="editor_invoice_update@example.com")
    set_admin_emails([editor.email])
    author = make_user(email="author_invoice_update@example.com")

    manuscript_id = str(uuid4())
    insert_manuscript(
        supabase_admin_client,
        manuscript_id=manuscript_id,
        author_id=author.id,
        status="decision",
        title="Invoice Update Manuscript",
    )

    try:
        res = await client.put(
            f"/api/v1/editor/manuscripts/{manuscript_id}/invoice-info",
            headers={"Authorization": f"Bearer {editor.token}"},
            json={
                "authors": "John Doe, Jane Smith",
                "affiliation": "University of Science",
                "apc_amount": 1000.0,
                "funding_info": "Grant #12345",
            },
        )
        assert res.status_code == 200, res.text
        body = res.json()
        assert body.get("success") is True

        ms = (
            supabase_admin_client.table("manuscripts")
            .select("invoice_metadata")
            .eq("id", manuscript_id)
            .single()
            .execute()
            .data
        )
        meta = ms.get("invoice_metadata") or {}
        assert meta.get("authors") == "John Doe, Jane Smith"
        assert meta.get("affiliation") == "University of Science"
        assert float(meta.get("apc_amount")) == 1000.0
        assert meta.get("funding_info") == "Grant #12345"

        logs = (
            supabase_admin_client.table("status_transition_logs")
            .select("id,comment")
            .eq("manuscript_id", manuscript_id)
            .order("created_at", desc=True)
            .limit(5)
            .execute()
            .data
        )
        assert any("invoice_metadata updated" == (r.get("comment") or "") for r in (logs or []))
    finally:
        _cleanup(supabase_admin_client, manuscript_id)

