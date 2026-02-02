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
async def test_reviewer_submits_dual_channel_review(
    client: AsyncClient,
    supabase_admin_client,
):
    """
    US1：Reviewer 通过 token 提交双通道评论（含机密评论）
    """

    author = make_user(email="author_dual@example.com")
    reviewer = make_user(email="reviewer_dual@example.com")

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
        title="Dual Channel Review Manuscript",
    )

    supabase_admin_client.table("review_reports").insert(
        {
            "id": review_report_id,
            "manuscript_id": manuscript_id,
            "reviewer_id": reviewer.id,
            "token": token,
            "expiry_date": expiry,
            "status": "invited",
        }
    ).execute()

    try:
        res = await client.post(
            f"/api/v1/reviews/token/{token}/submit",
            data={
                "content": "Public comments to the author.",
                "score": "4",
                "confidential_comments_to_editor": "Confidential notes for editor only.",
            },
        )
        assert res.status_code == 200, res.text
        body = res.json()
        assert body["success"] is True

        rr = (
            supabase_admin_client.table("review_reports")
            .select("status,content,confidential_comments_to_editor,score")
            .eq("id", review_report_id)
            .single()
            .execute()
            .data
        )
        assert rr["status"] == "completed"
        assert rr["content"] == "Public comments to the author."
        assert rr["confidential_comments_to_editor"] == "Confidential notes for editor only."
        assert rr["score"] == 4
    finally:
        _cleanup(supabase_admin_client, manuscript_id, review_report_id)

