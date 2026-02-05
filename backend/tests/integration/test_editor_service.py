import pytest
from uuid import uuid4

from .test_utils import make_user


def _cleanup(db, manuscript_ids: list[str], journal_id: str) -> None:
    for mid in manuscript_ids:
        try:
            db.table("manuscripts").delete().eq("id", mid).execute()
        except Exception:
            pass
    try:
        db.table("journals").delete().eq("id", journal_id).execute()
    except Exception:
        pass


@pytest.mark.integration
@pytest.mark.asyncio
async def test_process_list_filters_by_q_and_multi_status(
    client,
    supabase_admin_client,
    set_admin_emails,
):
    editor = make_user(email="editor_process_filters@example.com")
    set_admin_emails([editor.email])

    journal_id = str(uuid4())
    supabase_admin_client.table("journals").insert(
        {"id": journal_id, "title": "Journal A", "slug": f"journal-a-{journal_id[:8]}"}
    ).execute()

    author_id = str(uuid4())
    m1 = str(uuid4())
    m2 = str(uuid4())
    m3 = str(uuid4())
    manuscript_ids = [m1, m2, m3]

    supabase_admin_client.table("manuscripts").insert(
        [
            {
                "id": m1,
                "author_id": author_id,
                "title": "Sustainable Energy Solutions",
                "abstract": "a",
                "status": "pre_check",
                "version": 1,
                "journal_id": journal_id,
            },
            {
                "id": m2,
                "author_id": author_id,
                "title": "Urban Development Policy",
                "abstract": "b",
                "status": "under_review",
                "version": 1,
                "journal_id": journal_id,
            },
            {
                "id": m3,
                "author_id": author_id,
                "title": "Energy Storage Systems",
                "abstract": "c",
                "status": "decision",
                "version": 1,
                "journal_id": journal_id,
            },
        ]
    ).execute()

    try:
        # q=Energy 应匹配 m1/m3（title ilike），并且 status 多选过滤只保留 pre_check/decision
        res = await client.get(
            "/api/v1/editor/manuscripts/process?q=Energy&status=pre_check&status=decision",
            headers={"Authorization": f"Bearer {editor.token}"},
        )
        assert res.status_code == 200, res.text
        body = res.json()
        assert body.get("success") is True
        ids = {r.get("id") for r in (body.get("data") or [])}
        assert m1 in ids
        assert m3 in ids
        assert m2 not in ids
    finally:
        _cleanup(supabase_admin_client, manuscript_ids, journal_id)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_process_list_filters_by_editor_id(
    client,
    supabase_admin_client,
    set_admin_emails,
):
    editor = make_user(email="editor_process_editor_filter@example.com")
    set_admin_emails([editor.email])

    author_id = str(uuid4())
    journal_id = str(uuid4())
    supabase_admin_client.table("journals").insert(
        {"id": journal_id, "title": "Journal B", "slug": f"journal-b-{journal_id[:8]}"}
    ).execute()

    assigned_editor_id = str(uuid4())
    other_editor_id = str(uuid4())
    m1 = str(uuid4())
    m2 = str(uuid4())
    manuscript_ids = [m1, m2]

    supabase_admin_client.table("manuscripts").insert(
        [
            {
                "id": m1,
                "author_id": author_id,
                "title": "Editor Filter 1",
                "abstract": "a",
                "status": "pre_check",
                "version": 1,
                "journal_id": journal_id,
                "editor_id": assigned_editor_id,
            },
            {
                "id": m2,
                "author_id": author_id,
                "title": "Editor Filter 2",
                "abstract": "b",
                "status": "pre_check",
                "version": 1,
                "journal_id": journal_id,
                "editor_id": other_editor_id,
            },
        ]
    ).execute()

    try:
        res = await client.get(
            f"/api/v1/editor/manuscripts/process?editor_id={assigned_editor_id}",
            headers={"Authorization": f"Bearer {editor.token}"},
        )
        assert res.status_code == 200, res.text
        ids = {r.get("id") for r in (res.json().get("data") or [])}
        assert ids == {m1}
    finally:
        _cleanup(supabase_admin_client, manuscript_ids, journal_id)

