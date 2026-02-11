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
