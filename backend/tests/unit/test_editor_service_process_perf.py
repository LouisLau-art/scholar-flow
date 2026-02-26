from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import Mock

from app.services.editor_service import EditorService, ProcessListFilters


class _UserProfilesQuery:
    def __init__(self, rows: list[dict]) -> None:
        self._rows = rows
        self.requested_ids: list[str] = []

    def select(self, *_args, **_kwargs):
        return self

    def in_(self, column: str, values: list[str]):
        assert column == "id"
        self.requested_ids = [str(v) for v in values]
        return self

    def execute(self):
        requested = set(self.requested_ids)
        matched = [row for row in self._rows if str(row.get("id") or "") in requested]
        return SimpleNamespace(data=matched)


class _ClientStub:
    def __init__(self, profile_rows: list[dict]) -> None:
        self.user_profiles = _UserProfilesQuery(profile_rows)
        self.user_profiles_calls = 0

    def table(self, name: str):
        if name != "user_profiles":
            raise AssertionError(f"unexpected table call: {name}")
        self.user_profiles_calls += 1
        return self.user_profiles


def test_list_manuscripts_process_applies_scope_before_overdue_snapshot():
    svc = EditorService()
    svc.client = _ClientStub(
        [
            {"id": "ae-self", "full_name": "Assistant Self", "email": "ae-self@example.com"},
            {"id": "ae-other", "full_name": "Assistant Other", "email": "ae-other@example.com"},
        ]
    )
    svc._list_process_rows_with_fallback = Mock(  # type: ignore[attr-defined]
        return_value=[
            {
                "id": "m-visible",
                "status": "under_review",
                "assistant_editor_id": "ae-self",
                "owner_id": None,
                "editor_id": None,
                "journal_id": "j-1",
            },
            {
                "id": "m-hidden",
                "status": "under_review",
                "assistant_editor_id": "ae-other",
                "owner_id": None,
                "editor_id": None,
                "journal_id": "j-1",
            },
        ]
    )
    captured_overdue_input: list[list[str]] = []

    def _capture_overdue(rows: list[dict]):
        captured_overdue_input.append([str(r.get("id") or "") for r in rows])
        return rows

    svc._attach_overdue_snapshot = Mock(side_effect=_capture_overdue)  # type: ignore[attr-defined]

    out = svc.list_manuscripts_process(
        filters=ProcessListFilters(),
        viewer_user_id="ae-self",
        viewer_roles=["assistant_editor"],
        scope_enforcement_enabled=False,
    )

    assert [row["id"] for row in out] == ["m-visible"]
    assert captured_overdue_input == [["m-visible"]]
    assert svc.client.user_profiles_calls == 1
    assert svc.client.user_profiles.requested_ids == ["ae-self"]


def test_list_manuscripts_process_reuses_profile_map_for_precheck_assignee():
    svc = EditorService()
    svc.client = _ClientStub(
        [
            {"id": "owner-1", "full_name": "Owner One", "email": "owner-1@example.com"},
            {"id": "editor-1", "full_name": "Editor One", "email": "editor-1@example.com"},
            {"id": "ae-1", "full_name": "Assistant One", "email": "ae-1@example.com"},
        ]
    )
    svc._list_process_rows_with_fallback = Mock(  # type: ignore[attr-defined]
        return_value=[
            {
                "id": "m-precheck",
                "status": "pre_check",
                "pre_check_status": "technical",
                "assistant_editor_id": "ae-1",
                "owner_id": "owner-1",
                "editor_id": "editor-1",
                "journal_id": "j-1",
            }
        ]
    )

    def _fake_enrich(rows: list[dict], **kwargs):
        assert kwargs.get("include_timeline") is True
        assert kwargs.get("include_assignee_profiles") is False
        return [
            {
                **rows[0],
                "pre_check_status": "technical",
                "current_role": "assistant_editor",
                "current_assignee": {"id": "ae-1"},
                "assigned_at": None,
                "technical_completed_at": None,
                "academic_completed_at": None,
            }
        ]

    svc._enrich_precheck_rows = Mock(side_effect=_fake_enrich)  # type: ignore[attr-defined]
    svc._attach_overdue_snapshot = Mock(side_effect=lambda rows: rows)  # type: ignore[attr-defined]

    out = svc.list_manuscripts_process(
        filters=ProcessListFilters(),
        viewer_user_id="admin-user",
        viewer_roles=["admin"],
    )

    assert len(out) == 1
    row = out[0]
    assert row["owner"]["full_name"] == "Owner One"
    assert row["editor"]["full_name"] == "Editor One"
    assert row["current_assignee"]["full_name"] == "Assistant One"
    assert row["current_assignee"]["email"] == "ae-1@example.com"
    assert row["assigned_at"] is None
    assert row["technical_completed_at"] is None
    assert row["academic_completed_at"] is None
    assert svc.client.user_profiles_calls == 1
    assert svc.client.user_profiles.requested_ids == ["ae-1", "editor-1", "owner-1"]
