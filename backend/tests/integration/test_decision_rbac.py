from __future__ import annotations

from uuid import uuid4

import pytest
from postgrest.exceptions import APIError

from .test_utils import insert_manuscript, make_user


def _cleanup(db, manuscript_id: str, user_ids: list[str]) -> None:
    for table, column in (
        ("decision_letters", "manuscript_id"),
        ("review_reports", "manuscript_id"),
        ("manuscripts", "id"),
    ):
        try:
            db.table(table).delete().eq(column, manuscript_id).execute()
        except Exception:
            pass
    for user_id in user_ids:
        try:
            db.table("user_profiles").delete().eq("id", user_id).execute()
        except Exception:
            pass


def _require_decision_schema(db) -> None:
    checks = [
        ("decision_letters", "id,manuscript_id,editor_id,status"),
        ("manuscripts", "id,editor_id"),
    ]
    for table, cols in checks:
        try:
            db.table(table).select(cols).limit(1).execute()
        except APIError as e:
            pytest.skip(f"数据库缺少决策 RBAC 测试所需 schema（{table}/{cols}）：{getattr(e, 'message', str(e))}")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_decision_workspace_rbac_assigned_editor_and_admin_allowed(
    client,
    supabase_admin_client,
    set_admin_emails,
):
    assigned_editor = make_user(email="decision_assigned_editor@example.com")
    outsider_editor = make_user(email="decision_outsider_editor@example.com")
    admin_editor = make_user(email="decision_admin_editor@example.com")
    author = make_user(email="decision_rbac_author@example.com")
    reviewer = make_user(email="decision_rbac_reviewer@example.com")
    _require_decision_schema(supabase_admin_client)

    manuscript_id = str(uuid4())
    insert_manuscript(
        supabase_admin_client,
        manuscript_id=manuscript_id,
        author_id=author.id,
        status="decision",
        title="Decision RBAC Manuscript",
        file_path=f"manuscripts/{manuscript_id}/v1.pdf",
    )
    supabase_admin_client.table("manuscripts").update({"editor_id": assigned_editor.id}).eq(
        "id", manuscript_id
    ).execute()
    supabase_admin_client.table("review_reports").insert(
        {
            "manuscript_id": manuscript_id,
            "reviewer_id": reviewer.id,
            "status": "completed",
            "content": "Looks okay.",
            "score": 4,
        }
    ).execute()

    # 非 ADMIN_EMAILS 用户，需要显式 profile.roles 才能通过 require_any_role
    for user in (assigned_editor, outsider_editor):
        supabase_admin_client.table("user_profiles").upsert(
            {"id": user.id, "email": user.email, "roles": ["managing_editor"]}
        ).execute()

    set_admin_emails([admin_editor.email])

    try:
        ok_assigned = await client.get(
            f"/api/v1/editor/manuscripts/{manuscript_id}/decision-context",
            headers={"Authorization": f"Bearer {assigned_editor.token}"},
        )
        assert ok_assigned.status_code == 200, ok_assigned.text

        forbidden_outsider = await client.get(
            f"/api/v1/editor/manuscripts/{manuscript_id}/decision-context",
            headers={"Authorization": f"Bearer {outsider_editor.token}"},
        )
        assert forbidden_outsider.status_code == 403, forbidden_outsider.text

        ok_admin = await client.get(
            f"/api/v1/editor/manuscripts/{manuscript_id}/decision-context",
            headers={"Authorization": f"Bearer {admin_editor.token}"},
        )
        assert ok_admin.status_code == 200, ok_admin.text

        forbidden_author = await client.get(
            f"/api/v1/editor/manuscripts/{manuscript_id}/decision-context",
            headers={"Authorization": f"Bearer {author.token}"},
        )
        assert forbidden_author.status_code == 403, forbidden_author.text
    finally:
        _cleanup(
            supabase_admin_client,
            manuscript_id,
            [assigned_editor.id, outsider_editor.id, admin_editor.id, author.id, reviewer.id],
        )
