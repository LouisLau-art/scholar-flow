from __future__ import annotations

from uuid import uuid4

import pytest
from postgrest.exceptions import APIError

from .test_utils import insert_manuscript, make_user


def _cleanup(db, manuscript_id: str) -> None:
    for table, column in (
        ("decision_letters", "manuscript_id"),
        ("review_reports", "manuscript_id"),
        ("manuscripts", "id"),
    ):
        try:
            db.table(table).delete().eq(column, manuscript_id).execute()
        except Exception:
            pass
    # 清理测试用的 decision-attachments 对象（避免 storage 泄漏）。
    try:
        db.storage.from_("decision-attachments").remove(
            [f"decision_letters/{manuscript_id}/att-123_demo.pdf"]
        )
    except Exception:
        pass


def _require_decision_schema(db) -> None:
    try:
        db.table("decision_letters").select("id,manuscript_id,status,attachment_paths").limit(1).execute()
    except APIError as e:
        pytest.skip(f"数据库缺少决策附件可见性测试所需 schema：{getattr(e, 'message', str(e))}")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_author_can_only_access_attachment_after_final_submit(
    client,
    supabase_admin_client,
    set_admin_emails,
):
    editor = make_user(email="decision_visibility_editor@example.com")
    author = make_user(email="decision_visibility_author@example.com")
    reviewer = make_user(email="decision_visibility_reviewer@example.com")
    set_admin_emails([editor.email])
    _require_decision_schema(supabase_admin_client)

    manuscript_id = str(uuid4())
    attachment_ref = f"att-123|decision_letters/{manuscript_id}/att-123_demo.pdf"
    # Seed: 决策附件必须在 Storage 里存在，否则 Supabase 的 sign 接口可能返回 400。
    try:
        supabase_admin_client.storage.from_("decision-attachments").upload(
            f"decision_letters/{manuscript_id}/att-123_demo.pdf",
            b"%PDF-1.4\n%decision-visibility\n",
            {"content-type": "application/pdf", "upsert": "true"},
        )
    except Exception:
        pass
    insert_manuscript(
        supabase_admin_client,
        manuscript_id=manuscript_id,
        author_id=author.id,
        status="decision",
        title="Decision Visibility Manuscript",
    )
    supabase_admin_client.table("review_reports").insert(
        {
            "manuscript_id": manuscript_id,
            "reviewer_id": reviewer.id,
            "status": "completed",
            "content": "Please revise references.",
            "score": 3,
        }
    ).execute()

    try:
        save_draft = await client.post(
            f"/api/v1/editor/manuscripts/{manuscript_id}/submit-decision",
            headers={"Authorization": f"Bearer {editor.token}"},
            json={
                "content": "Draft with attachment",
                "decision": "minor_revision",
                "is_final": False,
                "attachment_paths": [attachment_ref],
                "last_updated_at": None,
            },
        )
        assert save_draft.status_code == 200, save_draft.text
        attachment_id = "att-123"

        before_final = await client.get(
            f"/api/v1/manuscripts/{manuscript_id}/decision-attachments/{attachment_id}/signed-url",
            headers={"Authorization": f"Bearer {author.token}"},
        )
        assert before_final.status_code == 403, before_final.text

        final_submit = await client.post(
            f"/api/v1/editor/manuscripts/{manuscript_id}/submit-decision",
            headers={"Authorization": f"Bearer {editor.token}"},
            json={
                "content": "Final revision decision",
                "decision": "minor_revision",
                "is_final": True,
                "attachment_paths": [attachment_ref],
                "last_updated_at": save_draft.json()["data"]["updated_at"],
            },
        )
        assert final_submit.status_code == 200, final_submit.text

        after_final = await client.get(
            f"/api/v1/manuscripts/{manuscript_id}/decision-attachments/{attachment_id}/signed-url",
            headers={"Authorization": f"Bearer {author.token}"},
        )
        assert after_final.status_code == 200, after_final.text
        assert after_final.json().get("success") is True
    finally:
        _cleanup(supabase_admin_client, manuscript_id)
