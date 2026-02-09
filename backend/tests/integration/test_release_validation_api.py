from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

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


def _run_payload(run_id: UUID) -> ValidationRun:
    now = datetime.now(timezone.utc)
    return ValidationRun(
        id=run_id,
        feature_key="042-production-pipeline",
        environment="staging",
        manuscript_id=None,
        triggered_by="tester",
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


def _check_payload(*, phase: ValidationPhase, key: str, status: ValidationCheckStatus, blocking: bool = True) -> ValidationCheck:
    now = datetime.now(timezone.utc)
    return ValidationCheck(
        id=uuid4(),
        run_id=uuid4(),
        phase=phase,
        check_key=key,
        title=key,
        status=status,
        is_blocking=blocking,
        detail="mock",
        evidence={},
        started_at=now,
        finished_at=now,
        created_at=now,
    )


class _FakeReleaseValidationService:
    def __init__(self) -> None:
        self.run_id = uuid4()
        self.run = _run_payload(self.run_id)
        self.readiness_status = ValidationRunStatus.PASSED
        self.regression_status = ValidationRunStatus.PASSED
        self.final_decision = ReleaseDecision.GO

    def create_run(self, _payload):
        self.run = _run_payload(self.run_id)
        return self.run

    def list_runs(self, *, environment: str | None = None, limit: int = 20):  # noqa: ARG002
        if environment and environment != self.run.environment:
            return []
        return [self.run][:limit]

    def execute_readiness(self, run_id: UUID, _payload):
        status_map = {
            ValidationRunStatus.PASSED: ValidationCheckStatus.PASSED,
            ValidationRunStatus.FAILED: ValidationCheckStatus.FAILED,
            ValidationRunStatus.BLOCKED: ValidationCheckStatus.BLOCKED,
        }
        return ReadinessResponse(
            run_id=run_id,
            result=PhaseResult(
                status=self.readiness_status,
                checks=[
                    _check_payload(
                        phase=ValidationPhase.READINESS,
                        key="readiness.mock",
                        status=status_map[self.readiness_status],
                    )
                ],
            ),
        )

    def execute_regression(self, run_id: UUID, _payload):
        checks = [
            _check_payload(
                phase=ValidationPhase.REGRESSION,
                key="regression.mock",
                status=ValidationCheckStatus.PASSED,
            )
        ]
        if self.regression_status == ValidationRunStatus.FAILED:
            checks[0] = _check_payload(
                phase=ValidationPhase.REGRESSION,
                key="regression.mock",
                status=ValidationCheckStatus.FAILED,
            )
        if self.regression_status == ValidationRunStatus.BLOCKED:
            checks = [
                _check_payload(
                    phase=ValidationPhase.REGRESSION,
                    key="regression.zero_skip.enforced",
                    status=ValidationCheckStatus.BLOCKED,
                )
            ]
        return RegressionResponse(run_id=run_id, result=PhaseResult(status=self.regression_status, checks=checks))

    def finalize(self, run_id: UUID, _payload):
        rollback_required = self.final_decision == ReleaseDecision.NO_GO
        run = self.run.model_copy(
            update={
                "id": run_id,
                "status": ValidationRunStatus.PASSED if not rollback_required else ValidationRunStatus.BLOCKED,
                "rollback_required": rollback_required,
                "rollback_status": RollbackStatus.PENDING if rollback_required else RollbackStatus.NOT_REQUIRED,
                "finished_at": datetime.now(timezone.utc),
                "summary": "mock finalize",
            }
        )
        report = ValidationReport(
            run=run,
            readiness_checks=[],
            regression_checks=[],
            rollback_plan=RollbackPlan(
                required=rollback_required,
                status=run.rollback_status,
                note="mock",
                steps=["step-1"] if rollback_required else [],
                updated_at=datetime.now(timezone.utc),
            ),
            release_decision=self.final_decision,
        )
        return FinalizeResponse(run_id=run_id, release_decision=self.final_decision, report=report)

    def get_report(self, run_id: UUID):
        rollback_required = self.final_decision == ReleaseDecision.NO_GO
        run = self.run.model_copy(
            update={
                "id": run_id,
                "status": ValidationRunStatus.PASSED if not rollback_required else ValidationRunStatus.BLOCKED,
                "rollback_required": rollback_required,
                "rollback_status": RollbackStatus.PENDING if rollback_required else RollbackStatus.NOT_REQUIRED,
            }
        )
        return ValidationReport(
            run=run,
            readiness_checks=[],
            regression_checks=[],
            rollback_plan=RollbackPlan(
                required=rollback_required,
                status=run.rollback_status,
                note="mock",
                steps=["step-1"] if rollback_required else [],
                updated_at=datetime.now(timezone.utc),
            ),
            release_decision=self.final_decision,
        )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_release_validation_requires_admin_key(client, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("ADMIN_API_KEY", "test-admin")
    resp = await client.post(
        "/api/v1/internal/release-validation/runs",
        json={"feature_key": "042-production-pipeline", "environment": "staging"},
    )
    assert resp.status_code == 401


@pytest.mark.integration
@pytest.mark.asyncio
async def test_create_and_list_release_validation_runs(client, monkeypatch: pytest.MonkeyPatch):
    from app.api.v1 import internal as internal_api

    monkeypatch.setenv("ADMIN_API_KEY", "test-admin")
    fake = _FakeReleaseValidationService()
    monkeypatch.setattr(internal_api, "ReleaseValidationService", lambda: fake)

    create_resp = await client.post(
        "/api/v1/internal/release-validation/runs",
        headers={"X-Admin-Key": "test-admin"},
        json={"feature_key": "042-production-pipeline", "environment": "staging"},
    )
    assert create_resp.status_code == 201, create_resp.text
    assert create_resp.json()["run"]["id"] == str(fake.run_id)

    list_resp = await client.get(
        "/api/v1/internal/release-validation/runs?environment=staging&limit=20",
        headers={"X-Admin-Key": "test-admin"},
    )
    assert list_resp.status_code == 200, list_resp.text
    assert len(list_resp.json()["data"]) == 1


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("status", "expected"),
    [
        (ValidationRunStatus.PASSED, "passed"),
        (ValidationRunStatus.FAILED, "failed"),
        (ValidationRunStatus.BLOCKED, "blocked"),
    ],
)
async def test_readiness_endpoint_returns_status(client, monkeypatch: pytest.MonkeyPatch, status, expected: str):
    from app.api.v1 import internal as internal_api

    monkeypatch.setenv("ADMIN_API_KEY", "test-admin")
    fake = _FakeReleaseValidationService()
    fake.readiness_status = status
    monkeypatch.setattr(internal_api, "ReleaseValidationService", lambda: fake)

    resp = await client.post(
        f"/api/v1/internal/release-validation/runs/{fake.run_id}/readiness",
        headers={"X-Admin-Key": "test-admin"},
        json={"strict_blocking": True},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["result"]["status"] == expected


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("status", "expected"),
    [
        (ValidationRunStatus.PASSED, "passed"),
        (ValidationRunStatus.FAILED, "failed"),
        (ValidationRunStatus.BLOCKED, "blocked"),
    ],
)
async def test_regression_endpoint_returns_status(client, monkeypatch: pytest.MonkeyPatch, status, expected: str):
    from app.api.v1 import internal as internal_api

    monkeypatch.setenv("ADMIN_API_KEY", "test-admin")
    fake = _FakeReleaseValidationService()
    fake.regression_status = status
    monkeypatch.setattr(internal_api, "ReleaseValidationService", lambda: fake)

    resp = await client.post(
        f"/api/v1/internal/release-validation/runs/{fake.run_id}/regression",
        headers={"X-Admin-Key": "test-admin"},
        json={"require_zero_skip": True},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["result"]["status"] == expected
    if expected == "blocked":
        assert any(item["check_key"] == "regression.zero_skip.enforced" for item in body["result"]["checks"])


@pytest.mark.integration
@pytest.mark.asyncio
async def test_finalize_and_report_no_go(client, monkeypatch: pytest.MonkeyPatch):
    from app.api.v1 import internal as internal_api

    monkeypatch.setenv("ADMIN_API_KEY", "test-admin")
    fake = _FakeReleaseValidationService()
    fake.final_decision = ReleaseDecision.NO_GO
    monkeypatch.setattr(internal_api, "ReleaseValidationService", lambda: fake)

    finalize_resp = await client.post(
        f"/api/v1/internal/release-validation/runs/{fake.run_id}/finalize",
        headers={"X-Admin-Key": "test-admin"},
        json={"force_no_go": True},
    )
    assert finalize_resp.status_code == 200, finalize_resp.text
    finalize_body = finalize_resp.json()
    assert finalize_body["release_decision"] == "no-go"
    assert finalize_body["report"]["rollback_plan"]["required"] is True

    report_resp = await client.get(
        f"/api/v1/internal/release-validation/runs/{fake.run_id}/report",
        headers={"X-Admin-Key": "test-admin"},
    )
    assert report_resp.status_code == 200, report_resp.text
    report_body = report_resp.json()
    assert report_body["release_decision"] == "no-go"
    assert report_body["rollback_plan"]["status"] == "pending"
