from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import Mock

from app.services.editor_service import EditorService


class _QueryStub:
    def __init__(self, data):
        self._data = data
        self._in_filters: list[tuple[str, set[str]]] = []

    def select(self, *_args, **_kwargs):
        return self

    def in_(self, *_args, **_kwargs):
        if len(_args) >= 2:
            key = str(_args[0])
            values = {str(v) for v in (_args[1] or [])}
            self._in_filters.append((key, values))
        return self

    def eq(self, *_args, **_kwargs):
        return self

    def order(self, *_args, **_kwargs):
        return self

    def range(self, *_args, **_kwargs):
        return self

    def execute(self, *_args, **_kwargs):
        rows = [dict(item) for item in self._data]
        for key, values in self._in_filters:
            rows = [row for row in rows if str(row.get(key)) in values]
        return SimpleNamespace(data=rows)


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
    def _fake_enrich(rows, **_kwargs):
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
    def _fake_enrich(rows, **_kwargs):
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


def test_managing_workspace_includes_waiting_author_precheck_rows():
    svc = EditorService()
    svc.client = _ClientStub(
        [
            {
                "table": "manuscripts",
                "data": [
                    *_workspace_rows(),
                    {
                        "id": "wait-1",
                        "title": "Waiting Author Manuscript",
                        "status": "revision_before_review",
                        "pre_check_status": "technical",
                        "assistant_editor_id": "ae-2",
                        "owner_id": "owner-1",
                        "journal_id": "journal-1",
                        "created_at": "2026-02-22T00:00:00Z",
                        "updated_at": "2026-02-24T03:00:00Z",
                    },
                ],
            },
            {
                "table": "user_profiles",
                "data": [
                    {
                        "id": "ae-2",
                        "full_name": "AE Waiting",
                        "email": "ae-waiting@example.com",
                    }
                ],
            },
        ]
    )
    svc._enrich_precheck_rows = Mock(side_effect=lambda rows, **_kwargs: rows)  # type: ignore[attr-defined]

    out = svc.get_managing_workspace(
        viewer_user_id="admin-user",
        viewer_roles=["admin"],
        page=1,
        page_size=20,
    )

    waiting = next((row for row in out if row["id"] == "wait-1"), None)
    assert waiting is not None
    assert waiting["status"] == "revision_before_review"
    assert waiting["pre_check_status"] == "technical"
    assert waiting["workspace_bucket"] == "awaiting_author"
    assert waiting["assistant_editor"]["id"] == "ae-2"
