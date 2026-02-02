import pytest
from httpx import AsyncClient
from uuid import uuid4
from datetime import datetime, timedelta, timezone

from postgrest.exceptions import APIError

from .test_utils import insert_manuscript, make_user


def _require_dual_review_schema(db) -> None:
    try:
        db.table("review_reports").select(
            "id,manuscript_id,token,expiry_date,status,content,confidential_comments_to_editor,attachment_path,score"
        ).limit(1).execute()
    except APIError as e:
        pytest.skip(
            f"数据库缺少 Reviewer Privacy 测试所需 schema（review_reports 新字段）：{getattr(e, 'message', str(e))}"
        )


def _cleanup(db, manuscript_id: str, review_report_id: str) -> None:
    try:
        db.table("review_reports").delete().eq("id", review_report_id).execute()
    except Exception:
        pass
    try:
        db.table("manuscripts").delete().eq("id", manuscript_id).execute()
    except Exception:
        pass


@pytest.mark.integration
@pytest.mark.asyncio
async def test_author_cannot_see_confidential_review_fields(
    client: AsyncClient,
    supabase_admin_client,
    set_admin_emails,
):
    """
    US1：Author 获取审稿反馈时，必须看不到机密字段（confidential_comments_to_editor / attachment_path）
    """

    editor = make_user(email="editor_privacy@example.com")
    set_admin_emails([editor.email])

    author = make_user(email="author_privacy@example.com")
    reviewer = make_user(email="reviewer_privacy@example.com")

    manuscript_id = str(uuid4())
    review_report_id = str(uuid4())
    token = "tok_" + uuid4().hex
    expiry = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()

    _require_dual_review_schema(supabase_admin_client)
    insert_manuscript(
        supabase_admin_client,
        manuscript_id=manuscript_id,
        author_id=author.id,
        status="under_review",
        title="Privacy Review Manuscript",
    )

    supabase_admin_client.table("review_reports").insert(
        {
            "id": review_report_id,
            "manuscript_id": manuscript_id,
            "reviewer_id": reviewer.id,
            "token": token,
            "expiry_date": expiry,
            "status": "completed",
            "content": "Public comments only.",
            "confidential_comments_to_editor": "Do NOT show to author.",
            "attachment_path": "review_attachments/secret.pdf",
            "score": 5,
        }
    ).execute()

    try:
        # Author view: must be sanitized
        res1 = await client.get(
            f"/api/v1/reviews/feedback/{manuscript_id}",
            headers={"Authorization": f"Bearer {author.token}"},
        )
        assert res1.status_code == 200, res1.text
        body1 = res1.json()
        assert body1["success"] is True
        assert body1["data"] and isinstance(body1["data"], list)
        item = body1["data"][0]
        assert item.get("content") == "Public comments only."
        assert "confidential_comments_to_editor" not in item
        assert "attachment_path" not in item

        # Editor view: can see confidential fields
        res2 = await client.get(
            f"/api/v1/reviews/feedback/{manuscript_id}",
            headers={"Authorization": f"Bearer {editor.token}"},
        )
        assert res2.status_code == 200, res2.text
        body2 = res2.json()
        assert body2["success"] is True
        item2 = body2["data"][0]
        assert item2.get("confidential_comments_to_editor") == "Do NOT show to author."
        assert item2.get("attachment_path") == "review_attachments/secret.pdf"
    finally:
        _cleanup(supabase_admin_client, manuscript_id, review_report_id)

