import pytest
from httpx import AsyncClient
from uuid import uuid4

from .test_utils import insert_manuscript, make_user


def _cleanup(db, manuscript_id: str) -> None:
    try:
        db.table("manuscripts").delete().eq("id", manuscript_id).execute()
    except Exception:
        pass


@pytest.mark.integration
@pytest.mark.asyncio
async def test_author_cannot_upload_editor_review_attachment(
    client: AsyncClient,
    supabase_admin_client,
):
    """
    Feature 033 / Security:
    - Peer Review Files 仅 Editor/Admin 可上传（Author 禁止）。
    """
    author = make_user(email="author_no_review_upload@example.com")
    manuscript_id = str(uuid4())
    insert_manuscript(
        supabase_admin_client,
        manuscript_id=manuscript_id,
        author_id=author.id,
        status="under_review",
        title="No Review Upload",
    )

    try:
        res = await client.post(
            f"/api/v1/editor/manuscripts/{manuscript_id}/files/review-attachment",
            headers={"Authorization": f"Bearer {author.token}"},
            files={"file": ("peer_review.pdf", b"%PDF-1.4 dummy", "application/pdf")},
        )
        assert res.status_code == 403, res.text
    finally:
        _cleanup(supabase_admin_client, manuscript_id)

