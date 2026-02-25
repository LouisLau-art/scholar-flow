import pytest
from uuid import uuid4
from postgrest.exceptions import APIError

from .test_utils import make_user
import app.api.v1.editor as editor_api


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


def _require_precheck_visual_schema(db) -> None:
    checks = [
        ("manuscripts", "id,status,pre_check_status,assistant_editor_id,editor_id"),
        ("status_transition_logs", "id,manuscript_id,payload,created_at"),
    ]
    for table, cols in checks:
        try:
            db.table(table).select(cols).limit(1).execute()
        except APIError as e:
            pytest.skip(f"数据库缺少 Feature 044 所需 schema（{table}/{cols}）：{getattr(e, 'message', str(e))}")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_process_list_filters_by_q_and_multi_status(
    client,
    supabase_admin_client,
    set_admin_emails,
):
    editor = make_user(email="editor_process_filters@example.com")
    set_admin_emails([editor.email])
    _require_precheck_visual_schema(supabase_admin_client)

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
    _require_precheck_visual_schema(supabase_admin_client)

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


@pytest.mark.integration
@pytest.mark.asyncio
async def test_process_and_detail_include_precheck_visual_fields(
    client,
    supabase_admin_client,
    set_admin_emails,
):
    editor = make_user(email="editor_precheck_visuals@example.com")
    set_admin_emails([editor.email])
    _require_precheck_visual_schema(supabase_admin_client)

    journal_id = str(uuid4())
    manuscript_id = str(uuid4())
    author_id = str(uuid4())
    ae_id = str(uuid4())

    supabase_admin_client.table("journals").insert(
        {"id": journal_id, "title": "Journal C", "slug": f"journal-c-{journal_id[:8]}"}
    ).execute()
    supabase_admin_client.table("user_profiles").insert(
        {
            "id": ae_id,
            "email": "ae.precheck@example.com",
            "full_name": "AE Precheck",
            "roles": ["assistant_editor"],
        }
    ).execute()
    supabase_admin_client.table("manuscripts").insert(
        {
            "id": manuscript_id,
            "author_id": author_id,
            "title": "Precheck Visualized Manuscript",
            "abstract": "a",
            "status": "pre_check",
            "pre_check_status": "technical",
            "assistant_editor_id": ae_id,
            "version": 1,
            "journal_id": journal_id,
        }
    ).execute()
    supabase_admin_client.table("status_transition_logs").insert(
        {
            "manuscript_id": manuscript_id,
            "from_status": "pre_check",
            "to_status": "pre_check",
            "comment": "assigned to ae",
            "changed_by": None,
            "payload": {
                "action": "precheck_assign_ae",
                "pre_check_from": "intake",
                "pre_check_to": "technical",
                "assistant_editor_after": ae_id,
            },
        }
    ).execute()

    try:
        process_res = await client.get(
            f"/api/v1/editor/manuscripts/process?manuscript_id={manuscript_id}",
            headers={"Authorization": f"Bearer {editor.token}"},
        )
        assert process_res.status_code == 200, process_res.text
        process_body = process_res.json()
        rows = process_body.get("data") or []
        assert rows, "expected one process row"
        row = rows[0]
        assert row.get("pre_check_status") == "technical"
        assert row.get("current_role") == "assistant_editor"
        assert (row.get("current_assignee") or {}).get("id") == ae_id
        assert row.get("assigned_at") is not None

        detail_res = await client.get(
            f"/api/v1/editor/manuscripts/{manuscript_id}",
            headers={"Authorization": f"Bearer {editor.token}"},
        )
        assert detail_res.status_code == 200, detail_res.text
        detail = (detail_res.json().get("data") or {})
        role_queue = detail.get("role_queue") or {}
        assert role_queue.get("current_role") == "assistant_editor"
        assert (role_queue.get("current_assignee") or {}).get("id") == ae_id
        timeline = detail.get("precheck_timeline") or []
        assert any((e.get("payload") or {}).get("action") == "precheck_assign_ae" for e in timeline)
    finally:
        try:
            supabase_admin_client.table("status_transition_logs").delete().eq("manuscript_id", manuscript_id).execute()
        except Exception:
            pass
        try:
            supabase_admin_client.table("user_profiles").delete().eq("id", ae_id).execute()
        except Exception:
            pass
        _cleanup(supabase_admin_client, [manuscript_id], journal_id)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_process_overdue_only_query_param_is_forwarded(client, set_admin_emails, monkeypatch: pytest.MonkeyPatch):
    editor = make_user(email="editor_process_overdue@example.com")
    set_admin_emails([editor.email])

    captured = {}

    def _stub_list(
        self,
        *,
        filters,
        viewer_user_id=None,
        viewer_roles=None,
        scoped_journal_ids=None,
        scope_enforcement_enabled=None,
    ):
        captured["overdue_only"] = filters.overdue_only
        return [
            {
                "id": str(uuid4()),
                "title": "Overdue Manuscript",
                "status": "under_review",
                "is_overdue": True,
                "overdue_tasks_count": 2,
            }
        ]

    monkeypatch.setattr(editor_api.EditorService, "list_manuscripts_process", _stub_list)

    res = await client.get(
        "/api/v1/editor/manuscripts/process?overdue_only=true",
        headers={"Authorization": f"Bearer {editor.token}"},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body.get("success") is True
    assert captured.get("overdue_only") is True
    row = (body.get("data") or [])[0]
    assert row.get("is_overdue") is True
    assert row.get("overdue_tasks_count") == 2
