from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.models.internal_task import InternalTaskStatus
from app.services.internal_task_service import InternalTaskService


class _FakeTaskUpdateQuery:
    def __init__(self, row: dict) -> None:
        self.row = row
        self.patch: dict = {}

    def update(self, patch: dict):
        self.patch = patch
        return self

    def eq(self, *_args):
        return self

    def execute(self):
        updated = dict(self.row)
        updated.update(self.patch)
        return SimpleNamespace(data=[updated])


class _FakeDB:
    def __init__(self, row: dict) -> None:
        self.row = row

    def table(self, name: str):
        if name == "internal_tasks":
            return _FakeTaskUpdateQuery(self.row)
        raise AssertionError(f"unexpected table: {name}")


class _FakeTaskListQuery:
    def __init__(self, rows: list[dict]) -> None:
        self.rows = rows
        self.limit_n = None

    def select(self, *_args):
        return self

    def eq(self, *_args):
        return self

    def order(self, *_args, **_kwargs):
        return self

    def limit(self, n: int):
        self.limit_n = n
        return self

    def execute(self):
        rows = list(self.rows)
        if isinstance(self.limit_n, int):
            rows = rows[: self.limit_n]
        return SimpleNamespace(data=rows)


class _FakeTaskActivityListQuery:
    def __init__(self, rows: list[dict]) -> None:
        self.rows = rows
        self.task_ids: set[str] | None = None
        self.limit_n = None

    def select(self, *_args):
        return self

    def eq(self, *_args):
        return self

    def in_(self, _col: str, values: list[str]):
        self.task_ids = set(str(v) for v in values)
        return self

    def order(self, *_args, **_kwargs):
        return self

    def limit(self, n: int):
        self.limit_n = n
        return self

    def execute(self):
        rows = [row for row in self.rows if self.task_ids is None or str(row.get("task_id") or "") in self.task_ids]
        if isinstance(self.limit_n, int):
            rows = rows[: self.limit_n]
        return SimpleNamespace(data=rows)


class _FakeListDB:
    def __init__(self, *, tasks: list[dict], activities: list[dict]) -> None:
        self.tasks = tasks
        self.activities = activities

    def table(self, name: str):
        if name == "internal_tasks":
            return _FakeTaskListQuery(self.tasks)
        if name == "internal_task_activity_logs":
            return _FakeTaskActivityListQuery(self.activities)
        raise AssertionError(f"unexpected table: {name}")


def test_assignee_cannot_edit_metadata_fields(monkeypatch: pytest.MonkeyPatch):
    row = {
        "id": str(uuid4()),
        "manuscript_id": str(uuid4()),
        "status": "todo",
        "assignee_user_id": "11111111-1111-1111-1111-111111111111",
        "title": "Task A",
        "description": None,
        "priority": "medium",
        "due_at": "2026-02-12T10:00:00+00:00",
        "created_by": str(uuid4()),
    }
    svc = InternalTaskService(client=_FakeDB(row))
    monkeypatch.setattr(svc, "_load_task_or_404", lambda *_args, **_kwargs: row)

    with pytest.raises(HTTPException) as ei:
        svc.update_task(
            manuscript_id=row["manuscript_id"],
            task_id=row["id"],
            actor_user_id=row["assignee_user_id"],
            actor_roles=[],
            title="Try to overwrite title",
        )

    assert ei.value.status_code == 403


def test_status_transition_done_to_todo_is_rejected(monkeypatch: pytest.MonkeyPatch):
    row = {
        "id": str(uuid4()),
        "manuscript_id": str(uuid4()),
        "status": "done",
        "assignee_user_id": "11111111-1111-1111-1111-111111111111",
        "title": "Task A",
        "description": None,
        "priority": "medium",
        "due_at": "2026-02-12T10:00:00+00:00",
        "created_by": str(uuid4()),
    }
    svc = InternalTaskService(client=_FakeDB(row))
    monkeypatch.setattr(svc, "_load_task_or_404", lambda *_args, **_kwargs: row)

    with pytest.raises(HTTPException) as ei:
        svc.update_task(
            manuscript_id=row["manuscript_id"],
            task_id=row["id"],
            actor_user_id=row["assignee_user_id"],
            actor_roles=["managing_editor"],
            status=InternalTaskStatus.TODO,
        )

    assert ei.value.status_code == 409


def test_privileged_user_can_mark_task_done_and_activity_is_written(monkeypatch: pytest.MonkeyPatch):
    row = {
        "id": str(uuid4()),
        "manuscript_id": str(uuid4()),
        "status": "todo",
        "assignee_user_id": "11111111-1111-1111-1111-111111111111",
        "title": "Task A",
        "description": None,
        "priority": "medium",
        "due_at": "2026-02-12T10:00:00+00:00",
        "created_by": str(uuid4()),
        "created_at": "2026-02-09T00:00:00+00:00",
        "updated_at": "2026-02-09T00:00:00+00:00",
        "completed_at": None,
    }
    svc = InternalTaskService(client=_FakeDB(row))
    monkeypatch.setattr(svc, "_load_task_or_404", lambda *_args, **_kwargs: row)

    actions: list[str] = []
    monkeypatch.setattr(
        svc,
        "_insert_activity",
        lambda **kwargs: actions.append(str(kwargs.get("action") or "")),
    )
    monkeypatch.setattr(
        svc,
        "_enrich_tasks",
        lambda rows, **_kwargs: rows,
    )

    out = svc.update_task(
        manuscript_id=row["manuscript_id"],
        task_id=row["id"],
        actor_user_id=str(uuid4()),
        actor_roles=["managing_editor"],
        status=InternalTaskStatus.DONE,
    )

    assert out["status"] == "done"
    assert out["completed_at"] is not None
    assert "status_changed" in actions


def test_list_manuscript_activity_batches_and_enriches(monkeypatch: pytest.MonkeyPatch):
    tasks = [
        {"id": "task-1", "title": "Task One", "updated_at": "2026-02-12T00:00:00+00:00"},
        {"id": "task-2", "title": "Task Two", "updated_at": "2026-02-11T00:00:00+00:00"},
    ]
    activities = [
        {
            "id": "act-1",
            "task_id": "task-1",
            "manuscript_id": "ms-1",
            "action": "task_created",
            "actor_user_id": "u-1",
            "before_payload": None,
            "after_payload": {"status": "todo"},
            "created_at": "2026-02-12T01:00:00+00:00",
        },
        {
            "id": "act-2",
            "task_id": "task-2",
            "manuscript_id": "ms-1",
            "action": "status_changed",
            "actor_user_id": "u-2",
            "before_payload": {"status": "todo"},
            "after_payload": {"status": "done"},
            "created_at": "2026-02-12T02:00:00+00:00",
        },
        {
            "id": "act-3",
            "task_id": "task-x",
            "manuscript_id": "ms-1",
            "action": "task_created",
            "actor_user_id": "u-x",
            "created_at": "2026-02-12T03:00:00+00:00",
        },
    ]
    svc = InternalTaskService(client=_FakeListDB(tasks=tasks, activities=activities))
    monkeypatch.setattr(
        svc,
        "_load_profiles_map",
        lambda _ids: {
            "u-1": {"id": "u-1", "full_name": "User 1", "email": "u1@example.com"},
            "u-2": {"id": "u-2", "full_name": "User 2", "email": "u2@example.com"},
        },
    )

    rows = svc.list_manuscript_activity(manuscript_id="ms-1", task_limit=50, activity_limit=50)

    assert len(rows) == 2
    assert {row["task_id"] for row in rows} == {"task-1", "task-2"}
    assert rows[0]["task_title"] in {"Task One", "Task Two"}
    assert rows[0]["actor"]["email"] in {"u1@example.com", "u2@example.com"}
