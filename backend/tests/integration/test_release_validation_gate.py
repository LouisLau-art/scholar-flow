from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from app.models.release_validation import (
    FinalizeResponse,
    PhaseResult,
    ReadinessResponse,
    RegressionResponse,
    ReleaseDecision,
    RollbackPlan,
    RollbackStatus,
    ValidationCheck,
    ValidationCheckStatus,
    ValidationPhase,
    ValidationReport,
    ValidationRun,
    ValidationRunStatus,
)


class _FakeGateService:
    def __init__(self) -> None:
        self.run_id = uuid4()
        now = datetime.now(timezone.utc)
        self.run = ValidationRun(
            id=self.run_id,
            feature_key='001-editor-performance-refactor',
            environment='staging',
            manuscript_id=None,
            triggered_by='tester',
            status=ValidationRunStatus.RUNNING,
            blocking_count=0,
            failed_count=0,
            skipped_count=0,
            started_at=now,
            finished_at=None,
            summary=None,
            rollback_required=False,
            rollback_status=RollbackStatus.NOT_REQUIRED,
            note=None,
            created_at=now,
            updated_at=now,
        )

    def create_run(self, _payload):
        return self.run

    def execute_readiness(self, run_id, _payload):
        now = datetime.now(timezone.utc)
        return ReadinessResponse(
            run_id=run_id,
            result=PhaseResult(
                status=ValidationRunStatus.PASSED,
                checks=[
                    ValidationCheck(
                        id=uuid4(),
                        run_id=run_id,
                        phase=ValidationPhase.READINESS,
                        check_key='readiness.editor-api',
                        title='readiness.editor-api',
                        status=ValidationCheckStatus.PASSED,
                        is_blocking=True,
                        detail='ok',
                        evidence={},
                        started_at=now,
                        finished_at=now,
                        created_at=now,
                    )
                ],
            ),
        )

    def execute_regression(self, run_id, _payload):
        now = datetime.now(timezone.utc)
        return RegressionResponse(
            run_id=run_id,
            result=PhaseResult(
                status=ValidationRunStatus.PASSED,
                checks=[
                    ValidationCheck(
                        id=uuid4(),
                        run_id=run_id,
                        phase=ValidationPhase.REGRESSION,
                        check_key='regression.editor-workspace',
                        title='regression.editor-workspace',
                        status=ValidationCheckStatus.PASSED,
                        is_blocking=True,
                        detail='ok',
                        evidence={},
                        started_at=now,
                        finished_at=now,
                        created_at=now,
                    )
                ],
            ),
        )

    def finalize(self, run_id, _payload):
        now = datetime.now(timezone.utc)
        report = ValidationReport(
            run=self.run.model_copy(
                update={
                    'id': run_id,
                    'status': ValidationRunStatus.PASSED,
                    'rollback_required': False,
                    'rollback_status': RollbackStatus.NOT_REQUIRED,
                    'finished_at': now,
                    'summary': 'gate passed',
                }
            ),
            readiness_checks=[],
            regression_checks=[],
            rollback_plan=RollbackPlan(
                required=False,
                status=RollbackStatus.NOT_REQUIRED,
                note='not required',
                steps=[],
                updated_at=now,
            ),
            release_decision=ReleaseDecision.GO,
        )
        return FinalizeResponse(run_id=run_id, release_decision=ReleaseDecision.GO, report=report)

    def get_report(self, run_id):
        now = datetime.now(timezone.utc)
        return ValidationReport(
            run=self.run.model_copy(
                update={
                    'id': run_id,
                    'status': ValidationRunStatus.PASSED,
                    'rollback_required': False,
                    'rollback_status': RollbackStatus.NOT_REQUIRED,
                    'finished_at': now,
                    'summary': 'gate passed',
                }
            ),
            readiness_checks=[],
            regression_checks=[],
            rollback_plan=RollbackPlan(
                required=False,
                status=RollbackStatus.NOT_REQUIRED,
                note='not required',
                steps=[],
                updated_at=now,
            ),
            release_decision=ReleaseDecision.GO,
        )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_release_validation_gate_smoke(client, monkeypatch: pytest.MonkeyPatch):
    from app.api.v1 import internal as internal_api

    monkeypatch.setenv('ADMIN_API_KEY', 'test-admin')
    fake = _FakeGateService()
    monkeypatch.setattr(internal_api, 'ReleaseValidationService', lambda: fake)

    create_resp = await client.post(
        '/api/v1/internal/release-validation/runs',
        headers={'X-Admin-Key': 'test-admin'},
        json={'feature_key': '001-editor-performance-refactor', 'environment': 'staging'},
    )
    assert create_resp.status_code == 201, create_resp.text
    run_id = create_resp.json()['run']['id']

    readiness_resp = await client.post(
        f'/api/v1/internal/release-validation/runs/{run_id}/readiness',
        headers={'X-Admin-Key': 'test-admin'},
        json={'strict_blocking': True},
    )
    assert readiness_resp.status_code == 200, readiness_resp.text
    assert readiness_resp.json()['result']['status'] == 'passed'

    regression_resp = await client.post(
        f'/api/v1/internal/release-validation/runs/{run_id}/regression',
        headers={'X-Admin-Key': 'test-admin'},
        json={'require_zero_skip': True},
    )
    assert regression_resp.status_code == 200, regression_resp.text
    assert regression_resp.json()['result']['status'] == 'passed'

    finalize_resp = await client.post(
        f'/api/v1/internal/release-validation/runs/{run_id}/finalize',
        headers={'X-Admin-Key': 'test-admin'},
        json={'force_no_go': False},
    )
    assert finalize_resp.status_code == 200, finalize_resp.text
    assert finalize_resp.json()['release_decision'] == 'go'

    report_resp = await client.get(
        f'/api/v1/internal/release-validation/runs/{run_id}/report',
        headers={'X-Admin-Key': 'test-admin'},
    )
    assert report_resp.status_code == 200, report_resp.text
    assert report_resp.json()['release_decision'] == 'go'
