import pytest
from fastapi import HTTPException
from datetime import datetime, timedelta, timezone

from app.services.editor_service import ProcessListFilters, apply_process_filters
from app.services.editor_service import EditorService


class FakeQuery:
    def __init__(self) -> None:
        self.calls: list[tuple] = []

    def eq(self, column: str, value: str):
        self.calls.append(("eq", column, value))
        return self

    def in_(self, column: str, values: list[str]):
        self.calls.append(("in_", column, values))
        return self

    def ilike(self, column: str, pattern: str):
        self.calls.append(("ilike", column, pattern))
        return self


def test_apply_process_filters_noop_when_empty():
    q = FakeQuery()
    apply_process_filters(q, ProcessListFilters())
    assert q.calls == []


def test_apply_process_filters_applies_ids_and_statuses_and_search_title():
    q = FakeQuery()
    apply_process_filters(
        q,
        ProcessListFilters(
            manuscript_id="m1",
            journal_id="j1",
            editor_id="e1",
            owner_id="o1",
            statuses=["under_review", "pending_quality", "under_review"],
            q="energy",
        ),
    )
    assert ("eq", "id", "m1") in q.calls
    assert ("eq", "journal_id", "j1") in q.calls
    assert ("eq", "editor_id", "e1") in q.calls
    assert ("eq", "owner_id", "o1") in q.calls

    # pending_quality -> pre_check（legacy normalize）
    assert ("in_", "status", ["under_review", "pre_check"]) in q.calls
    assert ("ilike", "title", "%energy%") in q.calls


def test_apply_process_filters_search_uuid_uses_eq_id():
    q = FakeQuery()
    apply_process_filters(q, ProcessListFilters(q="11111111-1111-1111-1111-111111111111"))
    assert q.calls == [("eq", "id", "11111111-1111-1111-1111-111111111111")]


def test_apply_process_filters_invalid_status_raises_422():
    q = FakeQuery()
    with pytest.raises(HTTPException) as ei:
        apply_process_filters(q, ProcessListFilters(statuses=["not-a-status"]))
    assert ei.value.status_code == 422


def test_apply_process_filters_q_too_long_raises_422():
    q = FakeQuery()
    with pytest.raises(HTTPException) as ei:
        apply_process_filters(q, ProcessListFilters(q="x" * 101))
    assert ei.value.status_code == 422


class _FakeTaskQuery:
    def __init__(self, rows: list[dict]) -> None:
        self._rows = rows

    def select(self, *_args, **_kwargs):
        return self

    def in_(self, *_args, **_kwargs):
        return self

    def neq(self, *_args, **_kwargs):
        return self

    def execute(self):
        from types import SimpleNamespace

        return SimpleNamespace(data=self._rows)


class _FakeClient:
    def __init__(self, task_rows: list[dict]) -> None:
        self._task_rows = task_rows

    def table(self, name: str):
        if name == "internal_tasks":
            return _FakeTaskQuery(self._task_rows)
        raise AssertionError(f"unexpected table: {name}")


def test_attach_overdue_snapshot_marks_overdue_and_counts():
    now = datetime.now(timezone.utc)
    overdue_due = (now - timedelta(hours=2)).isoformat()
    future_due = (now + timedelta(hours=2)).isoformat()
    rows = [{"id": "m1"}, {"id": "m2"}]
    task_rows = [
        {"manuscript_id": "m1", "status": "todo", "due_at": overdue_due},
        {"manuscript_id": "m1", "status": "in_progress", "due_at": future_due},
        {"manuscript_id": "m2", "status": "todo", "due_at": future_due},
    ]

    svc = EditorService()
    svc.client = _FakeClient(task_rows)
    out = svc._attach_overdue_snapshot(rows)
    by_id = {row["id"]: row for row in out}

    assert by_id["m1"]["is_overdue"] is True
    assert by_id["m1"]["overdue_tasks_count"] == 1
    assert by_id["m2"]["is_overdue"] is False
    assert by_id["m2"]["overdue_tasks_count"] == 0
