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
async def test_author_cannot_access_editor_manuscript_detail_or_edit_invoice(
    client: AsyncClient,
    supabase_admin_client,
):
    author = make_user(email="author_forbidden@example.com")
    other = make_user(email="other@example.com")

    manuscript_id = str(uuid4())
    insert_manuscript(
        supabase_admin_client,
        manuscript_id=manuscript_id,
        author_id=other.id,
        status="decision",
        title="Forbidden Manuscript",
    )

    try:
        res1 = await client.get(
            f"/api/v1/editor/manuscripts/{manuscript_id}",
            headers={"Authorization": f"Bearer {author.token}"},
        )
        assert res1.status_code == 403, res1.text

        res2 = await client.put(
            f"/api/v1/editor/manuscripts/{manuscript_id}/invoice-info",
            headers={"Authorization": f"Bearer {author.token}"},
            json={"authors": "X", "affiliation": "Y", "apc_amount": 1},
        )
        assert res2.status_code == 403, res2.text
    finally:
        _cleanup(supabase_admin_client, manuscript_id)

