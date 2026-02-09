import pytest
from uuid import uuid4

from .test_utils import make_user


@pytest.mark.integration
@pytest.mark.asyncio
async def test_internal_comment_mentions_flow_with_dedup(
    client,
    set_admin_emails,
    monkeypatch: pytest.MonkeyPatch,
):
    editor = make_user(email="editor_internal_mentions@example.com")
    set_admin_emails([editor.email])

    manuscript_id = str(uuid4())
    mention_a = str(uuid4())

    class _StubCollabService:
        def __init__(self):
            self._rows: list[dict] = []

        def create_comment(self, *, manuscript_id: str, author_user_id: str, content: str, mention_user_ids):
            mention_ids = list(dict.fromkeys([str(v) for v in (mention_user_ids or [])]))
            row = {
                "id": str(uuid4()),
                "manuscript_id": manuscript_id,
                "content": content,
                "created_at": "2026-02-09T10:00:00Z",
                "user_id": author_user_id,
                "mention_user_ids": mention_ids,
                "user": {"full_name": "Editor", "email": "editor@example.com"},
            }
            self._rows.append(row)
            return row

        def list_comments(self, manuscript_id: str):
            return [row for row in self._rows if row.get("manuscript_id") == manuscript_id]

    stub = _StubCollabService()
    monkeypatch.setattr("app.api.v1.editor.InternalCollaborationService", lambda: stub)

    post_res = await client.post(
        f"/api/v1/editor/manuscripts/{manuscript_id}/comments",
        headers={"Authorization": f"Bearer {editor.token}"},
        json={"content": "@A please review", "mention_user_ids": [mention_a, mention_a]},
    )
    assert post_res.status_code == 200, post_res.text
    post_body = post_res.json()
    assert post_body.get("success") is True
    assert post_body["data"]["mention_user_ids"] == [mention_a]

    get_res = await client.get(
        f"/api/v1/editor/manuscripts/{manuscript_id}/comments",
        headers={"Authorization": f"Bearer {editor.token}"},
    )
    assert get_res.status_code == 200, get_res.text
    rows = get_res.json().get("data") or []
    assert len(rows) == 1
    assert rows[0].get("mention_user_ids") == [mention_a]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_internal_task_create_update_and_activity_flow(
    client,
    set_admin_emails,
    monkeypatch: pytest.MonkeyPatch,
):
    editor = make_user(email="editor_internal_tasks@example.com")
    set_admin_emails([editor.email])

    manuscript_id = str(uuid4())
    assignee_id = str(uuid4())

    class _StubTaskService:
        def __init__(self):
            self._task: dict | None = None
            self._activity: list[dict] = []

        def create_task(self, **kwargs):
            self._task = {
                "id": str(uuid4()),
                "manuscript_id": kwargs["manuscript_id"],
                "title": kwargs["title"],
                "description": kwargs.get("description"),
                "assignee_user_id": kwargs["assignee_user_id"],
                "status": "todo",
                "priority": "medium",
                "due_at": kwargs["due_at"].isoformat(),
                "is_overdue": False,
                "can_edit": True,
            }
            self._activity.append({"id": str(uuid4()), "action": "task_created"})
            return self._task

        def list_tasks(self, **kwargs):
            if not self._task:
                return []
            if kwargs.get("overdue_only") and not self._task.get("is_overdue"):
                return []
            return [self._task]

        def update_task(self, **kwargs):
            assert self._task is not None
            if kwargs.get("status") is not None:
                self._task["status"] = getattr(kwargs["status"], "value", kwargs["status"])
            self._activity.append({"id": str(uuid4()), "action": "status_changed"})
            return self._task

        def list_activity(self, **_kwargs):
            return self._activity

    stub = _StubTaskService()
    monkeypatch.setattr("app.api.v1.editor.InternalTaskService", lambda: stub)

    create_res = await client.post(
        f"/api/v1/editor/manuscripts/{manuscript_id}/tasks",
        headers={"Authorization": f"Bearer {editor.token}"},
        json={
            "title": "Follow up with reviewer",
            "assignee_user_id": assignee_id,
            "due_at": "2026-02-10T08:00:00Z",
        },
    )
    assert create_res.status_code == 200, create_res.text
    task_id = (create_res.json().get("data") or {}).get("id")
    assert task_id

    update_res = await client.patch(
        f"/api/v1/editor/manuscripts/{manuscript_id}/tasks/{task_id}",
        headers={"Authorization": f"Bearer {editor.token}"},
        json={"status": "done"},
    )
    assert update_res.status_code == 200, update_res.text
    assert (update_res.json().get("data") or {}).get("status") == "done"

    list_res = await client.get(
        f"/api/v1/editor/manuscripts/{manuscript_id}/tasks",
        headers={"Authorization": f"Bearer {editor.token}"},
    )
    assert list_res.status_code == 200
    rows = list_res.json().get("data") or []
    assert len(rows) == 1

    activity_res = await client.get(
        f"/api/v1/editor/manuscripts/{manuscript_id}/tasks/{task_id}/activity",
        headers={"Authorization": f"Bearer {editor.token}"},
    )
    assert activity_res.status_code == 200
    actions = [row.get("action") for row in (activity_res.json().get("data") or [])]
    assert "task_created" in actions
    assert "status_changed" in actions
