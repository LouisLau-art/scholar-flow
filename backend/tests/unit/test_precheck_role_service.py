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


def test_submit_technical_check_pass_to_academic():
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
                    }
                ],
            }
        ]
    )
    out = svc.submit_technical_check(manuscript_id, ae_id, decision="pass", comment="ok")
    assert out["pre_check_status"] == PreCheckStatus.ACADEMIC.value


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


def test_submit_academic_check_routes_to_under_review():
    svc = _new_service()
    manuscript_id = uuid4()
    changed_by = uuid4()
    svc._get_manuscript = Mock(  # type: ignore[method-assign]
        return_value={
            "id": str(manuscript_id),
            "status": ManuscriptStatus.PRE_CHECK.value,
            "pre_check_status": PreCheckStatus.ACADEMIC.value,
            "assistant_editor_id": None,
        }
    )
    editorial_mock = Mock()
    editorial_mock.update_status.return_value = {
        "id": str(manuscript_id),
        "status": ManuscriptStatus.UNDER_REVIEW.value,
    }
    svc.editorial = editorial_mock

    out = svc.submit_academic_check(manuscript_id, "review", changed_by=changed_by)
    assert out["status"] == ManuscriptStatus.UNDER_REVIEW.value
    kwargs = editorial_mock.update_status.call_args.kwargs
    assert kwargs["to_status"] == ManuscriptStatus.UNDER_REVIEW.value
    assert kwargs["payload"]["action"] == "precheck_academic_to_review"
