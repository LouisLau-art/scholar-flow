import pytest
from datetime import datetime, timedelta, timezone
from httpx import AsyncClient
from uuid import uuid4

from postgrest.exceptions import APIError

from .test_utils import insert_manuscript, make_user, safe_delete_by_id


def _require_schema(db) -> None:
    try:
        db.table("manuscripts").select("id,assistant_editor_id").limit(1).execute()
        db.table("review_reports").select(
            "id,manuscript_id,reviewer_id,status,comments_for_author,content,confidential_comments_to_editor,attachment_path,score"
        ).limit(1).execute()
    except APIError as e:
        pytest.skip(f"数据库缺少审稿反馈访问测试所需 schema：{getattr(e, 'message', str(e))}")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_assistant_editor_can_only_read_reviews_for_assigned_manuscript(
    client: AsyncClient,
    supabase_admin_client,
):
    _require_schema(supabase_admin_client)

    author = make_user(email=f"author_{uuid4().hex[:8]}@example.com")
    reviewer = make_user(email=f"reviewer_{uuid4().hex[:8]}@example.com")
    assigned_ae = make_user(email=f"assigned_ae_{uuid4().hex[:8]}@example.com")
    other_ae = make_user(email=f"other_ae_{uuid4().hex[:8]}@example.com")

    manuscript_id = str(uuid4())
    review_report_id = str(uuid4())
    token = "tok_" + uuid4().hex
    expiry = (datetime.now(timezone.utc) + timedelta(hours=6)).isoformat()

    for identity, name in (
        (author, "Author"),
        (reviewer, "Reviewer"),
        (assigned_ae, "Assigned AE"),
        (other_ae, "Other AE"),
    ):
        supabase_admin_client.table("user_profiles").insert(
            {
                "id": identity.id,
                "email": identity.email,
                "full_name": name,
                "roles": ["assistant_editor"] if identity in (assigned_ae, other_ae) else ["author"],
            }
        ).execute()

    insert_manuscript(
        supabase_admin_client,
        manuscript_id=manuscript_id,
        author_id=author.id,
        status="under_review",
        title="AE Review Access Manuscript",
    )
    supabase_admin_client.table("manuscripts").update(
        {"assistant_editor_id": assigned_ae.id}
    ).eq("id", manuscript_id).execute()

    supabase_admin_client.table("review_reports").insert(
        {
            "id": review_report_id,
            "manuscript_id": manuscript_id,
            "reviewer_id": reviewer.id,
            "token": token,
            "expiry_date": expiry,
            "status": "completed",
            "content": "Public feedback",
            "comments_for_author": "Public feedback",
            "confidential_comments_to_editor": "Internal notes for editor only",
            "attachment_path": "review_attachments/internal.pdf",
            "score": 4,
        }
    ).execute()

    try:
        assigned_res = await client.get(
            f"/api/v1/manuscripts/{manuscript_id}/reviews",
            headers={"Authorization": f"Bearer {assigned_ae.token}"},
        )
        assert assigned_res.status_code == 200, assigned_res.text
        assigned_body = assigned_res.json()
        assert assigned_body["success"] is True
        assert isinstance(assigned_body.get("data"), list)
        assert assigned_body["data"], "Expected at least one review report"
        first = assigned_body["data"][0]
        assert first.get("comments_for_author") == "Public feedback"
        assert first.get("confidential_comments_to_editor") == "Internal notes for editor only"

        other_res = await client.get(
            f"/api/v1/manuscripts/{manuscript_id}/reviews",
            headers={"Authorization": f"Bearer {other_ae.token}"},
        )
        assert other_res.status_code == 403, other_res.text
    finally:
        safe_delete_by_id(supabase_admin_client, "review_reports", review_report_id)
        safe_delete_by_id(supabase_admin_client, "manuscripts", manuscript_id)
        safe_delete_by_id(supabase_admin_client, "user_profiles", author.id)
        safe_delete_by_id(supabase_admin_client, "user_profiles", reviewer.id)
        safe_delete_by_id(supabase_admin_client, "user_profiles", assigned_ae.id)
        safe_delete_by_id(supabase_admin_client, "user_profiles", other_ae.id)
