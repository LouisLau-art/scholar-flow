from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import Mock

from app.services.editor_service import EditorService


class _QueryStub:
    def __init__(self, data):
        self._data = data

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

    def execute(self, *_args, **_kwargs):
        return SimpleNamespace(data=self._data)


class _ClientStub:
    def __init__(self, script: list[dict]):
        self._script = list(script)

    def table(self, table_name: str):
        if not self._script:
            raise AssertionError(f"unexpected table call: {table_name}")
        item = self._script.pop(0)
        assert item["table"] == table_name
        return _QueryStub(item["data"])


def _workspace_rows():
    return [
        {
            "id": "pre-1",
            "title": "Precheck Manuscript",
            "status": "pre_check",
            "pre_check_status": "technical",
            "assistant_editor_id": "ae-1",
            "owner_id": "owner-1",
            "journal_id": "journal-1",
            "created_at": "2026-02-24T00:00:00Z",
            "updated_at": "2026-02-24T01:00:00Z",
        },
        {
            "id": "review-1",
            "title": "Under Review Manuscript",
            "status": "under_review",
            "pre_check_status": None,
            "assistant_editor_id": "ae-1",
            "owner_id": "owner-1",
            "journal_id": "journal-1",
            "created_at": "2026-02-23T00:00:00Z",
            "updated_at": "2026-02-24T02:00:00Z",
        },
    ]


def test_managing_workspace_enriches_only_precheck_rows():
    svc = EditorService()
    svc.client = _ClientStub(
        [
            {"table": "manuscripts", "data": _workspace_rows()},
            {"table": "user_profiles", "data": []},
        ]
    )
    captured_ids: list[str] = []
    def _fake_enrich(rows):
        enriched = []
        for row in rows:
            captured_ids.append(str(row.get("id") or ""))
            enriched.append(
                {
                    **row,
                    "current_role": "assistant_editor",
                    "current_assignee": {"id": "ae-1"},
                }
            )
        return enriched

    svc._enrich_precheck_rows = Mock(side_effect=_fake_enrich)  # type: ignore[attr-defined]

    out = svc.get_managing_workspace(
        viewer_user_id="admin-user",
        viewer_roles=["admin"],
        page=1,
        page_size=20,
    )

    assert captured_ids == ["pre-1"]
    assert {row["id"] for row in out} == {"pre-1", "review-1"}


def test_ae_workspace_enriches_only_precheck_rows():
    svc = EditorService()
    svc.client = _ClientStub(
        [
            {"table": "manuscripts", "data": _workspace_rows()},
            {"table": "manuscripts", "data": []},  # legacy pending_decision query
            {"table": "user_profiles", "data": []},
        ]
    )
    captured_ids: list[str] = []
    def _fake_enrich(rows):
        enriched = []
        for row in rows:
            captured_ids.append(str(row.get("id") or ""))
            enriched.append(
                {
                    **row,
                    "current_role": "assistant_editor",
                    "current_assignee": {"id": "ae-1"},
                }
            )
        return enriched

    svc._enrich_precheck_rows = Mock(side_effect=_fake_enrich)  # type: ignore[attr-defined]

    out = svc.get_ae_workspace(ae_id="ae-1", page=1, page_size=20)

    assert captured_ids == ["pre-1"]
    assert {row["id"] for row in out} == {"pre-1", "review-1"}
