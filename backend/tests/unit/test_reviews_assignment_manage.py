from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.api.v1.reviews_handlers_assignment_manage import get_manuscript_assignments_impl


class _QueryStub:
    def __init__(self, rows):
        self.rows = rows
        self.filters: list[tuple[str, object]] = []
        self.select_clause: str | None = None

    def select(self, clause: str):
        self.select_clause = clause
        return self

    def eq(self, key: str, value: object):
        self.filters.append((key, value))
        return self

    def in_(self, *_args, **_kwargs):
        return self

    def order(self, *_args, **_kwargs):
        return self

    def single(self):
        return self

    def execute(self):
        data = self.rows
        if isinstance(data, list):
            return SimpleNamespace(data=list(data))
        return SimpleNamespace(data=dict(data))


class _SupabaseStub:
    def __init__(self):
        self._manuscript_row = {"id": "m-1", "journal_id": "j-1", "assistant_editor_id": "ae-1"}
        self._version_row = {"version": 2}
        self._assignment_rows = [
            {
                "id": "a-1",
                "status": "completed",
                "due_at": None,
                "reviewer_id": "r-1",
                "round_number": 1,
                "created_at": "2026-03-01T00:00:00Z",
            },
            {
                "id": "a-2",
                "status": "completed",
                "due_at": None,
                "reviewer_id": "r-2",
                "round_number": 1,
                "created_at": "2026-03-02T00:00:00Z",
            },
        ]
        self._profiles = [
            {"id": "r-1", "full_name": "Reviewer One", "email": "one@example.com"},
            {"id": "r-2", "full_name": "Reviewer Two", "email": "two@example.com"},
        ]

    def table(self, name: str):
        if name == "manuscripts":
            return _ManuscriptsTableStub(self)
        if name == "review_assignments":
            return _QueryStub(self._assignment_rows)
        if name == "user_profiles":
            return _QueryStub(self._profiles)
        raise AssertionError(f"unexpected table: {name}")


class _ManuscriptsTableStub:
    def __init__(self, owner: _SupabaseStub):
        self.owner = owner
        self._select_clause: str | None = None

    def select(self, clause: str):
        self._select_clause = clause
        return self

    def eq(self, *_args, **_kwargs):
        return self

    def single(self):
        return self

    def execute(self):
        if self._select_clause == "version":
            return SimpleNamespace(data=dict(self.owner._version_row))
        return SimpleNamespace(data=dict(self.owner._manuscript_row))


@pytest.mark.asyncio
async def test_get_manuscript_assignments_marks_previous_round_reuse_scope() -> None:
    stub = _SupabaseStub()

    out = await get_manuscript_assignments_impl(
        manuscript_id=uuid4(),
        round_number=None,
        current_user={"id": "ae-1"},
        profile={"roles": ["assistant_editor"]},
        supabase_admin_client=stub,
        ensure_review_management_access_fn=lambda **_kwargs: None,
        normalize_roles_fn=lambda roles: roles,
        parse_roles_fn=lambda profile: profile.get("roles", []),
    )

    assert out["success"] is True
    assert out["meta"]["manuscript_version"] == 2
    assert out["meta"]["target_round"] == 1
    assert out["meta"]["selection_scope"] == "previous_round_reuse"
    assert [item["reviewer_id"] for item in out["data"]] == ["r-1", "r-2"]
