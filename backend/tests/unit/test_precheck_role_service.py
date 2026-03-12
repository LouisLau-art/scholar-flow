from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.models.manuscript import ManuscriptStatus, PreCheckStatus
from app.services.editor_service import EditorService


class _QueryStub:
    def __init__(self, data):
        self._data = data

    def select(self, *_args, **_kwargs):
        return self

    def update(self, *_args, **_kwargs):
        return self

    def eq(self, *_args, **_kwargs):
        return self

    def or_(self, *_args, **_kwargs):
        return self

    def in_(self, *_args, **_kwargs):
        return self

    def order(self, *_args, **_kwargs):
        return self

    def range(self, *_args, **_kwargs):
        return self

    def single(self, *_args, **_kwargs):
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


class _StoreQueryStub:
    def __init__(self, store: dict[str, list[dict]]):
        self._store = store
        self._table = ""
        self._eq_filters: list[tuple[str, object]] = []
        self._in_filters: list[tuple[str, set[str]]] = []

    def bind(self, table_name: str):
        self._table = table_name
        self._eq_filters = []
        self._in_filters = []
        return self

    def select(self, *_args, **_kwargs):
        return self

    def eq(self, key: str, value: object):
        self._eq_filters.append((key, value))
        return self

    def in_(self, key: str, values):
        self._in_filters.append((key, {str(v) for v in values}))
        return self

    def single(self):
        return self

    def execute(self):
        rows = [dict(item) for item in self._store.get(self._table, [])]
        for key, value in self._eq_filters:
            rows = [row for row in rows if row.get(key) == value]
        for key, values in self._in_filters:
            rows = [row for row in rows if str(row.get(key)) in values]
        if any(row.get("id") == "__raise__" for row in rows):
            raise RuntimeError("forced failure")
        if self._table == "user_profiles" and any(key == "id" for key, _ in self._eq_filters):
            return SimpleNamespace(data=rows[0] if rows else None)
        return SimpleNamespace(data=rows)


class _StoreClientStub:
    def __init__(self, store: dict[str, list[dict]]):
        self._query = _StoreQueryStub(store)

    def table(self, table_name: str):
        return self._query.bind(table_name)


def _new_service() -> EditorService:
    svc = EditorService()
    # 中文注释：测试中禁用真实日志写入，避免依赖数据库
    svc._safe_insert_transition_log = Mock()  # type: ignore[attr-defined]
    return svc


def test_assign_ae_success_from_intake():
    svc = _new_service()
    manuscript_id = uuid4()
    ae_id = uuid4()
    operator = uuid4()

    svc._get_manuscript = Mock(  # type: ignore[method-assign]
        return_value={
            "id": str(manuscript_id),
            "status": ManuscriptStatus.PRE_CHECK.value,
            "pre_check_status": PreCheckStatus.INTAKE.value,
            "assistant_editor_id": None,
        }
    )
    svc.client = _ClientStub(
        [
            {
                "table": "manuscripts",
                "data": [
                    {
                        "id": str(manuscript_id),
                        "status": ManuscriptStatus.PRE_CHECK.value,
                        "pre_check_status": PreCheckStatus.TECHNICAL.value,
                        "assistant_editor_id": str(ae_id),
                    }
                ],
            }
        ]
    )

    out = svc.assign_ae(manuscript_id, ae_id, operator)
    assert out["pre_check_status"] == PreCheckStatus.TECHNICAL.value
    assert out["assistant_editor_id"] == str(ae_id)


def test_assign_ae_idempotent_when_same_ae_already_assigned():
    svc = _new_service()
    manuscript_id = uuid4()
    ae_id = uuid4()
    operator = uuid4()

    svc._get_manuscript = Mock(  # type: ignore[method-assign]
        return_value={
            "id": str(manuscript_id),
            "status": ManuscriptStatus.PRE_CHECK.value,
            "pre_check_status": PreCheckStatus.TECHNICAL.value,
            "assistant_editor_id": str(ae_id),
        }
    )
    svc.client = _ClientStub([])
    out = svc.assign_ae(manuscript_id, ae_id, operator)
    assert out["pre_check_status"] == PreCheckStatus.TECHNICAL.value
    assert out["assistant_editor_id"] == str(ae_id)


def test_assign_ae_allows_waiting_author_from_intake_and_switches_resume_stage_to_technical():
    svc = _new_service()
    manuscript_id = uuid4()
    ae_id = uuid4()
    operator = uuid4()

    svc._get_manuscript = Mock(  # type: ignore[method-assign]
        return_value={
            "id": str(manuscript_id),
            "status": ManuscriptStatus.REVISION_BEFORE_REVIEW.value,
            "pre_check_status": PreCheckStatus.INTAKE.value,
            "assistant_editor_id": None,
            "owner_id": None,
        }
    )

    client = Mock()
    for method in ("table", "update", "eq", "or_", "execute"):
        getattr(client, method).return_value = client
    client.execute.return_value = SimpleNamespace(
        data=[
            {
                "id": str(manuscript_id),
                "status": ManuscriptStatus.REVISION_BEFORE_REVIEW.value,
                "pre_check_status": PreCheckStatus.TECHNICAL.value,
                "assistant_editor_id": str(ae_id),
            }
        ]
    )
    svc.client = client

    out = svc.assign_ae(manuscript_id, ae_id, operator)

    assert out["status"] == ManuscriptStatus.REVISION_BEFORE_REVIEW.value
    assert out["pre_check_status"] == PreCheckStatus.TECHNICAL.value
    assert out["assistant_editor_id"] == str(ae_id)
    update_payload = client.update.call_args[0][0]
    assert update_payload["pre_check_status"] == PreCheckStatus.TECHNICAL.value
    assert update_payload["assistant_editor_id"] == str(ae_id)


def test_assign_ae_allows_waiting_author_reassignment_from_technical():
    svc = _new_service()
    manuscript_id = uuid4()
    old_ae_id = uuid4()
    new_ae_id = uuid4()
    operator = uuid4()

    svc._get_manuscript = Mock(  # type: ignore[method-assign]
        return_value={
            "id": str(manuscript_id),
            "status": ManuscriptStatus.REVISION_BEFORE_REVIEW.value,
            "pre_check_status": PreCheckStatus.TECHNICAL.value,
            "assistant_editor_id": str(old_ae_id),
            "owner_id": None,
        }
    )

    client = Mock()
    for method in ("table", "update", "eq", "or_", "execute"):
        getattr(client, method).return_value = client
    client.execute.return_value = SimpleNamespace(
        data=[
            {
                "id": str(manuscript_id),
                "status": ManuscriptStatus.REVISION_BEFORE_REVIEW.value,
                "pre_check_status": PreCheckStatus.TECHNICAL.value,
                "assistant_editor_id": str(new_ae_id),
            }
        ]
    )
    svc.client = client

    out = svc.assign_ae(manuscript_id, new_ae_id, operator)

    assert out["status"] == ManuscriptStatus.REVISION_BEFORE_REVIEW.value
    assert out["pre_check_status"] == PreCheckStatus.TECHNICAL.value
    assert out["assistant_editor_id"] == str(new_ae_id)
    log_kwargs = svc._safe_insert_transition_log.call_args.kwargs
    assert log_kwargs["from_status"] == ManuscriptStatus.REVISION_BEFORE_REVIEW.value
    assert log_kwargs["to_status"] == ManuscriptStatus.REVISION_BEFORE_REVIEW.value
    assert log_kwargs["payload"]["assistant_editor_before"] == str(old_ae_id)
    assert log_kwargs["payload"]["assistant_editor_after"] == str(new_ae_id)


def test_assign_ae_rejects_start_external_review_while_waiting_author():
    svc = _new_service()
    manuscript_id = uuid4()
    ae_id = uuid4()
    operator = uuid4()

    svc._get_manuscript = Mock(  # type: ignore[method-assign]
        return_value={
            "id": str(manuscript_id),
            "status": ManuscriptStatus.REVISION_BEFORE_REVIEW.value,
            "pre_check_status": PreCheckStatus.INTAKE.value,
            "assistant_editor_id": None,
            "owner_id": None,
        }
    )
    client = Mock()
    for method in ("table", "update", "eq", "or_", "execute"):
        getattr(client, method).return_value = client
    client.execute.return_value = SimpleNamespace(
        data=[
            {
                "id": str(manuscript_id),
                "status": ManuscriptStatus.REVISION_BEFORE_REVIEW.value,
                "pre_check_status": PreCheckStatus.TECHNICAL.value,
                "assistant_editor_id": str(ae_id),
            }
        ]
    )
    svc.client = client
    svc.editorial = Mock()

    with pytest.raises(HTTPException) as ei:
        svc.assign_ae(
            manuscript_id,
            ae_id,
            operator,
            start_external_review=True,
        )

    assert ei.value.status_code == 409
    assert "waiting author" in str(ei.value.detail).lower()


def test_assign_ae_raises_409_when_state_changed_concurrently():
    svc = _new_service()
    manuscript_id = uuid4()
    ae_id = uuid4()
    operator = uuid4()

    snapshots = [
        {
            "id": str(manuscript_id),
            "status": ManuscriptStatus.PRE_CHECK.value,
            "pre_check_status": PreCheckStatus.INTAKE.value,
            "assistant_editor_id": None,
        },
        {
            "id": str(manuscript_id),
            "status": ManuscriptStatus.UNDER_REVIEW.value,
            "pre_check_status": PreCheckStatus.ACADEMIC.value,
            "assistant_editor_id": str(ae_id),
        },
    ]
    svc._get_manuscript = Mock(side_effect=snapshots)  # type: ignore[method-assign]
    svc.client = _ClientStub([{"table": "manuscripts", "data": []}])

    with pytest.raises(HTTPException) as ei:
        svc.assign_ae(manuscript_id, ae_id, operator)
    assert ei.value.status_code == 409


def test_get_intake_queue_excludes_waiting_author_placeholders():
    svc = _new_service()
    svc.client = _ClientStub(
        [
            {
                "table": "manuscripts",
                "data": [
                    {
                        "id": "active-1",
                        "title": "Active Intake Manuscript",
                        "status": ManuscriptStatus.PRE_CHECK.value,
                        "pre_check_status": PreCheckStatus.INTAKE.value,
                        "assistant_editor_id": None,
                        "owner_id": None,
                        "author_id": None,
                        "created_at": "2026-03-12T08:00:00Z",
                        "updated_at": "2026-03-12T09:00:00Z",
                    }
                ],
            },
            {
                "table": "manuscripts",
                "data": [
                    {
                        "id": "wait-1",
                        "title": "Waiting Author Manuscript",
                        "status": ManuscriptStatus.REVISION_BEFORE_REVIEW.value,
                        "pre_check_status": PreCheckStatus.TECHNICAL.value,
                        "assistant_editor_id": "ae-1",
                        "owner_id": None,
                        "author_id": None,
                        "created_at": "2026-03-11T08:00:00Z",
                        "updated_at": "2026-03-12T10:00:00Z",
                    }
                ],
            },
            {
                "table": "user_profiles",
                "data": [],
            },
        ]
    )
    svc._load_latest_precheck_intake_revision_logs = Mock(  # type: ignore[attr-defined]
        return_value={
            "wait-1": {
                "created_at": "2026-03-12T10:00:00Z",
                "comment": "Need technical fixes before review",
            }
        }
    )
    svc._apply_process_visibility_scope = Mock(side_effect=lambda *, rows, **_kwargs: rows)  # type: ignore[attr-defined]

    out = svc.get_intake_queue(
        viewer_user_id="admin-user",
        viewer_roles=["admin"],
        page=1,
        page_size=20,
    )

    assert [row["id"] for row in out] == ["active-1"]
    assert out[0]["intake_actionable"] is True
    assert out[0]["waiting_resubmit"] is False


def test_submit_technical_check_revision_requires_comment():
    svc = _new_service()
    with pytest.raises(HTTPException) as ei:
        svc.submit_technical_check(uuid4(), uuid4(), decision="revision", comment=None)
    assert ei.value.status_code == 422


def test_submit_technical_check_forbidden_for_unassigned_ae():
    svc = _new_service()
    manuscript_id = uuid4()
    assigned_ae = uuid4()
    caller_ae = uuid4()
    svc._get_manuscript = Mock(  # type: ignore[method-assign]
        return_value={
            "id": str(manuscript_id),
            "status": ManuscriptStatus.PRE_CHECK.value,
            "pre_check_status": PreCheckStatus.TECHNICAL.value,
            "assistant_editor_id": str(assigned_ae),
        }
    )
    with pytest.raises(HTTPException) as ei:
        svc.submit_technical_check(manuscript_id, caller_ae, decision="pass")
    assert ei.value.status_code == 403


def test_submit_technical_check_pass_routes_to_under_review():
    svc = _new_service()
    manuscript_id = uuid4()
    ae_id = uuid4()
    svc._get_manuscript = Mock(  # type: ignore[method-assign]
        return_value={
            "id": str(manuscript_id),
            "status": ManuscriptStatus.PRE_CHECK.value,
            "pre_check_status": PreCheckStatus.TECHNICAL.value,
            "assistant_editor_id": str(ae_id),
        }
    )
    editorial_mock = Mock()
    editorial_mock.update_status.return_value = {
        "id": str(manuscript_id),
        "status": ManuscriptStatus.UNDER_REVIEW.value,
        "pre_check_status": None,
        "assistant_editor_id": str(ae_id),
    }
    svc.editorial = editorial_mock

    out = svc.submit_technical_check(manuscript_id, ae_id, decision="pass", comment="ok")
    assert out["status"] == ManuscriptStatus.UNDER_REVIEW.value
    kwargs = editorial_mock.update_status.call_args.kwargs
    assert kwargs["to_status"] == ManuscriptStatus.UNDER_REVIEW.value
    assert kwargs["extra_updates"] == {"pre_check_status": None}
    assert kwargs["payload"]["action"] == "precheck_technical_to_under_review"


def test_submit_technical_check_revision_routes_to_revision_before_review():
    svc = _new_service()
    manuscript_id = uuid4()
    ae_id = uuid4()
    svc._get_manuscript = Mock(  # type: ignore[method-assign]
        return_value={
            "id": str(manuscript_id),
            "status": ManuscriptStatus.PRE_CHECK.value,
            "pre_check_status": PreCheckStatus.TECHNICAL.value,
            "assistant_editor_id": str(ae_id),
        }
    )
    editorial_mock = Mock()
    editorial_mock.update_status.return_value = {
        "id": str(manuscript_id),
        "status": "revision_before_review",
        "pre_check_status": None,
        "assistant_editor_id": str(ae_id),
    }
    svc.editorial = editorial_mock

    out = svc.submit_technical_check(
        manuscript_id,
        ae_id,
        decision="revision",
        comment="formatting package is incomplete",
    )

    assert out["status"] == "revision_before_review"
    kwargs = editorial_mock.update_status.call_args.kwargs
    assert kwargs["to_status"] == "revision_before_review"
    assert kwargs["extra_updates"]["ae_sla_started_at"]
    assert kwargs["extra_updates"]["pre_check_status"] == PreCheckStatus.TECHNICAL.value
    assert kwargs["extra_updates"]["assistant_editor_id"] == str(ae_id)
    assert kwargs["payload"]["action"] == "precheck_technical_revision"


def test_assign_ae_sets_ae_sla_started_at_on_assignment():
    svc = _new_service()
    manuscript_id = uuid4()
    ae_id = uuid4()
    operator = uuid4()

    svc._get_manuscript = Mock(  # type: ignore[method-assign]
        return_value={
            "id": str(manuscript_id),
            "status": ManuscriptStatus.PRE_CHECK.value,
            "pre_check_status": PreCheckStatus.INTAKE.value,
            "assistant_editor_id": None,
            "owner_id": None,
        }
    )

    client = Mock()
    for method in ("table", "update", "eq", "or_", "execute"):
        getattr(client, method).return_value = client
    client.execute.return_value = SimpleNamespace(
        data=[
            {
                "id": str(manuscript_id),
                "status": ManuscriptStatus.PRE_CHECK.value,
                "pre_check_status": PreCheckStatus.TECHNICAL.value,
                "assistant_editor_id": str(ae_id),
            }
        ]
    )
    svc.client = client

    svc.assign_ae(manuscript_id, ae_id, operator)

    update_payload = client.update.call_args[0][0]
    assert update_payload["ae_sla_started_at"]


def test_submit_technical_check_academic_requires_academic_editor_id():
    svc = _new_service()
    manuscript_id = uuid4()
    ae_id = uuid4()
    svc._get_manuscript = Mock(  # type: ignore[method-assign]
        return_value={
            "id": str(manuscript_id),
            "status": ManuscriptStatus.PRE_CHECK.value,
            "pre_check_status": PreCheckStatus.TECHNICAL.value,
            "assistant_editor_id": str(ae_id),
            "journal_id": str(uuid4()),
        }
    )

    with pytest.raises(HTTPException) as ei:
        svc.submit_technical_check(manuscript_id, ae_id, decision="academic", comment="send to academic")

    assert ei.value.status_code == 422
    assert "academic_editor_id" in str(ei.value.detail)


def test_submit_technical_check_academic_routes_with_binding():
    svc = _new_service()
    manuscript_id = uuid4()
    ae_id = uuid4()
    academic_editor_id = uuid4()
    journal_id = uuid4()
    svc._get_manuscript = Mock(  # type: ignore[method-assign]
        return_value={
            "id": str(manuscript_id),
            "status": ManuscriptStatus.PRE_CHECK.value,
            "pre_check_status": PreCheckStatus.TECHNICAL.value,
            "assistant_editor_id": str(ae_id),
            "journal_id": str(journal_id),
            "academic_editor_id": None,
        }
    )
    svc._validate_academic_editor_assignment = Mock(return_value={"id": str(academic_editor_id)})  # type: ignore[attr-defined]
    svc.client = _ClientStub(
        [
            {
                "table": "manuscripts",
                "data": [
                    {
                        "id": str(manuscript_id),
                        "status": ManuscriptStatus.PRE_CHECK.value,
                        "pre_check_status": PreCheckStatus.ACADEMIC.value,
                        "assistant_editor_id": str(ae_id),
                        "academic_editor_id": str(academic_editor_id),
                        "academic_submitted_at": "2026-03-10T00:00:00Z",
                    }
                ],
            }
        ]
    )

    out = svc.submit_technical_check(
        manuscript_id,
        ae_id,
        decision="academic",
        comment="send to academic",
        academic_editor_id=academic_editor_id,
    )

    assert out["pre_check_status"] == PreCheckStatus.ACADEMIC.value
    assert out["academic_editor_id"] == str(academic_editor_id)


def test_list_academic_editor_candidates_rejects_pure_ae_on_unassigned_manuscript(monkeypatch):
    svc = _new_service()
    manuscript_id = uuid4()
    svc._get_manuscript = Mock(  # type: ignore[method-assign]
        return_value={
            "id": str(manuscript_id),
            "assistant_editor_id": str(uuid4()),
            "journal_id": str(uuid4()),
            "academic_editor_id": None,
        }
    )
    monkeypatch.setattr(
        "app.services.editor_service_precheck_workspace_views.ensure_manuscript_scope_access",
        lambda **_kwargs: "",
    )

    with pytest.raises(HTTPException) as ei:
        svc.list_academic_editor_candidates(
            manuscript_id=manuscript_id,
            viewer_user_id=str(uuid4()),
            viewer_roles=["assistant_editor"],
        )

    assert ei.value.status_code == 403


def test_list_academic_editor_candidates_does_not_fallback_to_global_profiles(monkeypatch):
    svc = _new_service()
    manuscript_id = str(uuid4())
    journal_id = str(uuid4())
    bound_id = str(uuid4())
    unrelated_id = str(uuid4())
    svc._get_manuscript = Mock(  # type: ignore[method-assign]
        return_value={
            "id": manuscript_id,
            "assistant_editor_id": str(uuid4()),
            "journal_id": journal_id,
            "academic_editor_id": bound_id,
        }
    )
    monkeypatch.setattr(
        "app.services.editor_service_precheck_workspace_views.ensure_manuscript_scope_access",
        lambda **_kwargs: journal_id,
    )
    svc.client = _StoreClientStub(
        {
            "journal_role_scopes": [],
            "user_profiles": [
                {
                    "id": bound_id,
                    "full_name": "Bound Academic",
                    "email": "bound@example.com",
                    "roles": ["academic_editor"],
                },
                {
                    "id": unrelated_id,
                    "full_name": "Global Academic",
                    "email": "global@example.com",
                    "roles": ["academic_editor"],
                },
            ]
        }
    )

    rows = svc.list_academic_editor_candidates(
        manuscript_id=manuscript_id,
        viewer_user_id=str(uuid4()),
        viewer_roles=["managing_editor"],
    )

    assert [row["id"] for row in rows] == [bound_id]


def test_validate_academic_editor_assignment_rejects_admin_only_target():
    svc = _new_service()
    academic_editor_id = str(uuid4())
    svc.client = _StoreClientStub(
        {
            "user_profiles": [
                {
                    "id": academic_editor_id,
                    "full_name": "Admin Only",
                    "email": "admin@example.com",
                    "roles": ["admin"],
                }
            ]
        }
    )

    with pytest.raises(HTTPException) as ei:
        svc._validate_academic_editor_assignment(
            academic_editor_id=academic_editor_id,
            manuscript_journal_id=str(uuid4()),
        )

    assert ei.value.status_code == 422


def test_validate_academic_editor_assignment_rejects_unscoped_target(monkeypatch):
    svc = _new_service()
    academic_editor_id = str(uuid4())
    journal_id = str(uuid4())
    svc.client = _StoreClientStub(
        {
            "user_profiles": [
                {
                    "id": academic_editor_id,
                    "full_name": "Academic Editor",
                    "email": "academic@example.com",
                    "roles": ["academic_editor"],
                }
            ]
        }
    )
    monkeypatch.setattr(
        "app.services.editor_service_precheck_workspace_decisions.get_user_scope_journal_ids",
        lambda **_kwargs: set(),
    )

    with pytest.raises(HTTPException) as ei:
        svc._validate_academic_editor_assignment(
            academic_editor_id=academic_editor_id,
            manuscript_journal_id=journal_id,
        )

    assert ei.value.status_code == 422


def test_revert_technical_check_routes_back_to_precheck_technical():
    svc = _new_service()
    manuscript_id = uuid4()
    ae_id = uuid4()
    svc._get_manuscript = Mock(  # type: ignore[method-assign]
        return_value={
            "id": str(manuscript_id),
            "status": ManuscriptStatus.UNDER_REVIEW.value,
            "pre_check_status": None,
            "assistant_editor_id": str(ae_id),
        }
    )
    svc.client = _ClientStub(
        [
            {
                "table": "status_transition_logs",
                "data": [
                    {
                        "id": "log-1",
                        "payload": {"action": "precheck_technical_to_under_review"},
                        "created_at": "2026-03-05T00:00:00Z",
                    }
                ],
            },
            {
                "table": "review_assignments",
                "data": [],
            },
            {
                "table": "manuscripts",
                "data": [
                    {
                        "id": str(manuscript_id),
                        "status": ManuscriptStatus.PRE_CHECK.value,
                        "pre_check_status": PreCheckStatus.TECHNICAL.value,
                        "assistant_editor_id": str(ae_id),
                    }
                ],
            },
        ]
    )

    out = svc.revert_technical_check(
        manuscript_id=manuscript_id,
        actor_id=ae_id,
        actor_roles=["assistant_editor"],
        reason="误触提交外审，回退到技术检查阶段",
        source="ae_workspace",
    )
    assert out["status"] == ManuscriptStatus.PRE_CHECK.value
    assert out["pre_check_status"] == PreCheckStatus.TECHNICAL.value
    kwargs = svc._safe_insert_transition_log.call_args.kwargs  # type: ignore[union-attr]
    assert kwargs["from_status"] == ManuscriptStatus.UNDER_REVIEW.value
    assert kwargs["to_status"] == ManuscriptStatus.PRE_CHECK.value
    assert kwargs["payload"]["action"] == "precheck_technical_revert_from_under_review"


def test_revert_technical_check_rejects_short_reason():
    svc = _new_service()
    with pytest.raises(HTTPException) as ei:
        svc.revert_technical_check(
            manuscript_id=uuid4(),
            actor_id=uuid4(),
            actor_roles=["assistant_editor"],
            reason="太短",
        )
    assert ei.value.status_code == 422


def test_revert_technical_check_rejects_non_owner_assistant_editor():
    svc = _new_service()
    manuscript_id = uuid4()
    assigned_ae = uuid4()
    caller_ae = uuid4()
    svc._get_manuscript = Mock(  # type: ignore[method-assign]
        return_value={
            "id": str(manuscript_id),
            "status": ManuscriptStatus.UNDER_REVIEW.value,
            "pre_check_status": None,
            "assistant_editor_id": str(assigned_ae),
        }
    )

    with pytest.raises(HTTPException) as ei:
        svc.revert_technical_check(
            manuscript_id=manuscript_id,
            actor_id=caller_ae,
            actor_roles=["assistant_editor"],
            reason="误触提交外审，需要回退到技术检查",
        )
    assert ei.value.status_code == 403


def test_revert_technical_check_rejects_when_latest_source_not_technical_submit():
    svc = _new_service()
    manuscript_id = uuid4()
    ae_id = uuid4()
    svc._get_manuscript = Mock(  # type: ignore[method-assign]
        return_value={
            "id": str(manuscript_id),
            "status": ManuscriptStatus.UNDER_REVIEW.value,
            "pre_check_status": None,
            "assistant_editor_id": str(ae_id),
        }
    )
    svc.client = _ClientStub(
        [
            {
                "table": "status_transition_logs",
                "data": [
                    {
                        "id": "log-2",
                        "payload": {"action": "precheck_academic_to_review"},
                        "created_at": "2026-03-05T00:00:00Z",
                    }
                ],
            }
        ]
    )

    with pytest.raises(HTTPException) as ei:
        svc.revert_technical_check(
            manuscript_id=manuscript_id,
            actor_id=ae_id,
            actor_roles=["assistant_editor"],
            reason="误触提交外审，需要撤回到技术检查",
        )
    assert ei.value.status_code == 409


def test_revert_technical_check_rejects_when_review_assignments_started():
    svc = _new_service()
    manuscript_id = uuid4()
    ae_id = uuid4()
    svc._get_manuscript = Mock(  # type: ignore[method-assign]
        return_value={
            "id": str(manuscript_id),
            "status": ManuscriptStatus.UNDER_REVIEW.value,
            "pre_check_status": None,
            "assistant_editor_id": str(ae_id),
        }
    )
    svc.client = _ClientStub(
        [
            {
                "table": "status_transition_logs",
                "data": [
                    {
                        "id": "log-3",
                        "payload": {"action": "precheck_technical_to_under_review"},
                        "created_at": "2026-03-05T00:00:00Z",
                    }
                ],
            },
            {
                "table": "review_assignments",
                "data": [
                    {
                        "id": "ra-1",
                        "status": "invited",
                        "accepted_at": None,
                        "submitted_at": None,
                        "declined_at": None,
                    }
                ],
            },
        ]
    )

    with pytest.raises(HTTPException) as ei:
        svc.revert_technical_check(
            manuscript_id=manuscript_id,
            actor_id=ae_id,
            actor_roles=["assistant_editor"],
            reason="误触提交外审，外审尚未开始时回退技术检查",
        )
    assert ei.value.status_code == 409


def test_request_intake_revision_requires_comment():
    svc = _new_service()
    with pytest.raises(HTTPException) as ei:
        svc.request_intake_revision(uuid4(), uuid4(), comment="   ")
    assert ei.value.status_code == 422


def test_request_intake_revision_success():
    svc = _new_service()
    manuscript_id = uuid4()
    current_user_id = uuid4()
    svc._get_manuscript = Mock(  # type: ignore[method-assign]
        return_value={
            "id": str(manuscript_id),
            "status": ManuscriptStatus.PRE_CHECK.value,
            "pre_check_status": PreCheckStatus.INTAKE.value,
        }
    )

    editorial_mock = Mock()
    editorial_mock.update_status.return_value = {
        "id": str(manuscript_id),
        "status": ManuscriptStatus.REVISION_BEFORE_REVIEW.value,
    }
    svc.editorial = editorial_mock

    out = svc.request_intake_revision(
        manuscript_id=manuscript_id,
        current_user_id=current_user_id,
        comment="请补充图表清晰度与伦理声明",
    )
    assert out["status"] == ManuscriptStatus.REVISION_BEFORE_REVIEW.value
    kwargs = editorial_mock.update_status.call_args.kwargs
    assert kwargs["to_status"] == ManuscriptStatus.REVISION_BEFORE_REVIEW.value
    assert kwargs["extra_updates"] == {
        "pre_check_status": PreCheckStatus.INTAKE.value,
        "assistant_editor_id": None,
        "ae_sla_started_at": None,
    }
    assert kwargs["payload"]["action"] == "precheck_intake_revision"


def test_request_intake_revision_rejects_non_intake_stage():
    svc = _new_service()
    manuscript_id = uuid4()
    current_user_id = uuid4()
    svc._get_manuscript = Mock(  # type: ignore[method-assign]
        return_value={
            "id": str(manuscript_id),
            "status": ManuscriptStatus.PRE_CHECK.value,
            "pre_check_status": PreCheckStatus.TECHNICAL.value,
        }
    )
    with pytest.raises(HTTPException) as ei:
        svc.request_intake_revision(
            manuscript_id=manuscript_id,
            current_user_id=current_user_id,
            comment="请先补充稿件结构",
        )
    assert ei.value.status_code == 409


def test_submit_academic_check_rejects_invalid_decision():
    svc = _new_service()
    with pytest.raises(HTTPException) as ei:
        svc.submit_academic_check(uuid4(), "invalid")
    assert ei.value.status_code == 422


def test_submit_academic_check_rejects_non_academic_stage():
    svc = _new_service()
    manuscript_id = uuid4()
    svc._get_manuscript = Mock(  # type: ignore[method-assign]
        return_value={
            "id": str(manuscript_id),
            "status": ManuscriptStatus.PRE_CHECK.value,
            "pre_check_status": PreCheckStatus.TECHNICAL.value,
            "assistant_editor_id": None,
        }
    )
    with pytest.raises(HTTPException) as ei:
        svc.submit_academic_check(manuscript_id, "review")
    assert ei.value.status_code == 409


def test_submit_academic_check_records_recommendation_without_transition():
    svc = _new_service()
    manuscript_id = uuid4()
    changed_by = uuid4()
    svc._get_manuscript = Mock(  # type: ignore[method-assign]
        return_value={
            "id": str(manuscript_id),
            "status": ManuscriptStatus.PRE_CHECK.value,
            "pre_check_status": PreCheckStatus.ACADEMIC.value,
            "assistant_editor_id": None,
            "academic_editor_id": str(changed_by),
        }
    )
    client = Mock()
    for method in ("table", "update", "eq", "execute"):
        getattr(client, method).return_value = client
    client.execute.return_value = SimpleNamespace(
        data=[
            {
                "id": str(manuscript_id),
                "status": ManuscriptStatus.PRE_CHECK.value,
                "pre_check_status": PreCheckStatus.ACADEMIC.value,
                "assistant_editor_id": None,
                "academic_editor_id": str(changed_by),
                "academic_completed_at": "2026-03-12T08:00:00Z",
            }
        ]
    )
    svc.client = client
    svc.editorial = Mock()

    out = svc.submit_academic_check(
        manuscript_id,
        "review",
        comment="looks ready for external review",
        changed_by=changed_by,
        actor_roles=["editor_in_chief"],
    )
    assert out["status"] == ManuscriptStatus.PRE_CHECK.value
    assert out["pre_check_status"] == PreCheckStatus.ACADEMIC.value
    svc.editorial.update_status.assert_not_called()

    update_payload = client.update.call_args[0][0]
    assert update_payload["academic_completed_at"]
    assert update_payload["updated_at"]

    log_kwargs = svc._safe_insert_transition_log.call_args.kwargs
    assert log_kwargs["from_status"] == ManuscriptStatus.PRE_CHECK.value
    assert log_kwargs["to_status"] == ManuscriptStatus.PRE_CHECK.value
    assert log_kwargs["payload"]["action"] == "precheck_academic_recommendation_submitted"
    assert log_kwargs["payload"]["decision"] == "review"
    assert log_kwargs["payload"]["recommended_next_status"] == ManuscriptStatus.UNDER_REVIEW.value


def test_submit_academic_check_rejects_unbound_academic_editor():
    svc = _new_service()
    manuscript_id = uuid4()
    caller = str(uuid4())
    svc._get_manuscript = Mock(  # type: ignore[method-assign]
        return_value={
            "id": str(manuscript_id),
            "status": ManuscriptStatus.PRE_CHECK.value,
            "pre_check_status": PreCheckStatus.ACADEMIC.value,
            "academic_editor_id": str(uuid4()),
        }
    )

    with pytest.raises(HTTPException) as ei:
        svc.submit_academic_check(
            manuscript_id,
            "review",
            changed_by=caller,
            actor_roles=["academic_editor"],
        )

    assert ei.value.status_code == 403


def test_submit_academic_check_rejects_unbound_editor_in_chief():
    svc = _new_service()
    manuscript_id = uuid4()
    caller = str(uuid4())
    svc._get_manuscript = Mock(  # type: ignore[method-assign]
        return_value={
            "id": str(manuscript_id),
            "status": ManuscriptStatus.PRE_CHECK.value,
            "pre_check_status": PreCheckStatus.ACADEMIC.value,
            "academic_editor_id": str(uuid4()),
        }
    )

    with pytest.raises(HTTPException) as ei:
        svc.submit_academic_check(
            manuscript_id,
            "review",
            changed_by=caller,
            actor_roles=["editor_in_chief"],
        )

    assert ei.value.status_code == 403
