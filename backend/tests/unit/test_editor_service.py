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


class _FinalDecisionQuery:
    def __init__(self, rows: list[dict]) -> None:
        self._rows = rows

    def select(self, *_args, **_kwargs):
        return self

    def in_(self, *_args, **_kwargs):
        return self

    def eq(self, *_args, **_kwargs):
        return self

    def order(self, *_args, **_kwargs):
        return self

    def range(self, *_args, **_kwargs):
        return self

    def execute(self):
        from types import SimpleNamespace

        return SimpleNamespace(data=self._rows)


class _FinalDecisionClient:
    def __init__(self, manuscript_rows: list[dict], draft_rows: list[dict]) -> None:
        self._manuscript_rows = manuscript_rows
        self._draft_rows = draft_rows

    def table(self, name: str):
        if name == "manuscripts":
            return _FinalDecisionQuery(self._manuscript_rows)
        if name == "decision_letters":
            return _FinalDecisionQuery(self._draft_rows)
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


def test_final_decision_queue_excludes_under_review_even_with_first_decision_draft(
    monkeypatch: pytest.MonkeyPatch,
):
    svc = EditorService()
    svc.client = _FinalDecisionClient(
        manuscript_rows=[
            {
                "id": "ms-under-review",
                "title": "Under Review Manuscript",
                "status": "under_review",
                "updated_at": "2026-03-10T10:00:00Z",
                "journal_id": "j1",
                "journals": {"title": "Journal A", "slug": "journal-a"},
                "assistant_editor_id": "ae-1",
                "owner_id": "me-1",
            },
            {
                "id": "ms-decision-done",
                "title": "Decision Done Manuscript",
                "status": "decision_done",
                "updated_at": "2026-03-10T09:00:00Z",
                "journal_id": "j1",
                "journals": {"title": "Journal A", "slug": "journal-a"},
                "assistant_editor_id": "ae-1",
                "owner_id": "me-1",
            },
        ],
        draft_rows=[
            {
                "id": "draft-1",
                "manuscript_id": "ms-under-review",
                "editor_id": "ae-1",
                "decision": "minor_revision",
                "status": "draft",
                "updated_at": "2026-03-10T10:05:00Z",
            }
        ],
    )
    monkeypatch.setattr("app.services.editor_service_precheck_workspace_decisions.is_scope_enforcement_enabled", lambda: False)
    monkeypatch.setattr("app.services.editor_service_precheck_workspace_decisions.get_user_scope_journal_ids", lambda **_kwargs: [])

    rows = svc.get_final_decision_queue(
        viewer_user_id="admin-1",
        viewer_roles=["admin"],
    )

    ids = [row["id"] for row in rows]
    assert "ms-under-review" not in ids
    assert ids == ["ms-decision-done"]
