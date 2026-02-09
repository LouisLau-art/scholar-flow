from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.models.release_validation import (
    CreateRunRequest,
    FinalizeRequest,
    ReadinessRequest,
    RegressionRequest,
    ValidationCheck,
    ValidationCheckStatus,
    ValidationPhase,
    ValidationRunStatus,
)
from app.services.release_validation_service import ReleaseValidationService


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class _FakeTable:
    def __init__(self, client: "_FakeClient", name: str):
        self._client = client
        self._name = name
        self._mode = "select"
        self._filters: list[tuple[str, str]] = []
        self._limit: int | None = None
        self._order: tuple[str, bool] | None = None
        self._single = False
        self._payload = None

    def select(self, *_args, **_kwargs):
        self._mode = "select"
        return self

    def eq(self, key: str, value):
        self._filters.append((key, str(value)))
        return self

    def order(self, key: str, *, desc: bool = False):
        self._order = (key, desc)
        return self

    def limit(self, n: int):
        self._limit = int(n)
        return self

    def single(self):
        self._single = True
        return self

    def insert(self, payload):
        self._mode = "insert"
        self._payload = payload
        return self

    def update(self, payload):
        self._mode = "update"
        self._payload = payload
        return self

    def delete(self):
        self._mode = "delete"
        return self

    def _rows(self) -> list[dict]:
        if self._name in self._client.missing_tables:
            raise RuntimeError(f"relation '{self._name}' does not exist")
        return self._client.tables.setdefault(self._name, [])

    def _matched_rows(self, rows: list[dict]) -> list[dict]:
        data = [r for r in rows if all(str(r.get(k)) == v for k, v in self._filters)]
        if self._order:
            key, desc = self._order
            data = sorted(data, key=lambda x: x.get(key), reverse=desc)
        if self._limit is not None:
            data = data[: self._limit]
        return data

    def execute(self):
        rows = self._rows()

        if self._mode == "select":
            data = [deepcopy(r) for r in self._matched_rows(rows)]
            if self._single:
                if not data:
                    raise RuntimeError("not found")
                return SimpleNamespace(data=data[0])
            return SimpleNamespace(data=data)

        if self._mode == "insert":
            payloads = self._payload if isinstance(self._payload, list) else [self._payload]
            inserted = []
            for item in payloads:
                row = deepcopy(item)
                row.setdefault("id", str(uuid4()))
                row.setdefault("created_at", _iso_now())
                if self._name == "release_validation_runs":
                    row.setdefault("updated_at", _iso_now())
                    row.setdefault("started_at", _iso_now())
                rows.append(row)
                inserted.append(deepcopy(row))
            return SimpleNamespace(data=inserted)

        if self._mode == "update":
            updated = []
            for row in rows:
                if all(str(row.get(k)) == v for k, v in self._filters):
                    row.update(deepcopy(self._payload))
                    updated.append(deepcopy(row))
            return SimpleNamespace(data=updated)

        if self._mode == "delete":
            kept = []
            deleted = []
            for row in rows:
                if all(str(row.get(k)) == v for k, v in self._filters):
                    deleted.append(deepcopy(row))
                    continue
                kept.append(row)
            self._client.tables[self._name] = kept
            return SimpleNamespace(data=deleted)

        raise RuntimeError(f"unsupported mode: {self._mode}")


class _FakeStorage:
    def __init__(self, buckets: set[str] | None = None):
        self._buckets = buckets or set()

    def get_bucket(self, bucket: str):
        if bucket not in self._buckets:
            raise RuntimeError("bucket not found")
        return {"id": bucket}


class _FakeClient:
    def __init__(self, *, tables: dict[str, list[dict]] | None = None, missing_tables: set[str] | None = None):
        self.tables = tables or {}
        self.missing_tables = missing_tables or set()
        self.storage = _FakeStorage({"production-proofs"})

    def table(self, name: str):
        return _FakeTable(self, name)


def _svc(client: _FakeClient | None = None) -> ReleaseValidationService:
    return ReleaseValidationService(client=client or _FakeClient())


def _check(*, phase: ValidationPhase, key: str, status: ValidationCheckStatus, is_blocking: bool = True) -> ValidationCheck:
    return ValidationCheck(
        phase=phase,
        check_key=key,
        title=key,
        status=status,
        is_blocking=is_blocking,
        detail="test",
        evidence={},
    )


def test_create_run_and_list_runs():
    svc = _svc()
    run = svc.create_run(CreateRunRequest(feature_key="042-production-pipeline", environment="staging"))

    assert run.environment == "staging"
    assert run.status == ValidationRunStatus.RUNNING

    runs = svc.list_runs(environment="staging", limit=10)
    assert len(runs) == 1
    assert runs[0].id == run.id


def test_create_run_rejects_duplicate_running_environment():
    svc = _svc()
    svc.create_run(CreateRunRequest(feature_key="042-production-pipeline", environment="staging"))

    with pytest.raises(HTTPException) as exc:
        svc.create_run(CreateRunRequest(feature_key="042-production-pipeline", environment="staging"))
    assert exc.value.status_code == 409


def test_readiness_returns_blocked_when_blocking_checks_fail(monkeypatch: pytest.MonkeyPatch):
    svc = _svc()
    run = svc.create_run(CreateRunRequest(feature_key="042-production-pipeline", environment="staging"))

    def _probe_table(table: str, columns: str = "id"):  # noqa: ARG001
        if table == "production_cycles":
            return ValidationCheckStatus.BLOCKED, "missing", {"table": table}
        return ValidationCheckStatus.PASSED, "ok", {"table": table}

    monkeypatch.setattr(svc, "_probe_table", _probe_table)
    monkeypatch.setattr(svc, "_probe_bucket", lambda bucket: (ValidationCheckStatus.PASSED, "ok", {"bucket": bucket}))
    monkeypatch.setattr(svc, "_probe_admin_key", lambda: (ValidationCheckStatus.PASSED, "ok", {"configured": True}))
    monkeypatch.setattr(
        svc,
        "_probe_publish_gate",
        lambda _run: (ValidationCheckStatus.PASSED, "ok", {"gate": "publish"}),
    )

    result = svc.execute_readiness(run.id, ReadinessRequest(strict_blocking=True))

    assert result.result.status == ValidationRunStatus.BLOCKED
    report = svc.get_report(run.id)
    assert report.run.status == ValidationRunStatus.BLOCKED
    assert report.run.blocking_count >= 1


def test_regression_zero_skip_gate_blocks_release():
    svc = _svc()
    run = svc.create_run(CreateRunRequest(feature_key="042-production-pipeline", environment="staging"))

    result = svc.execute_regression(run.id, RegressionRequest(require_zero_skip=True))

    assert result.result.status == ValidationRunStatus.BLOCKED
    assert any(c.check_key == "regression.zero_skip.enforced" for c in result.result.checks)
    report = svc.get_report(run.id)
    assert report.run.status == ValidationRunStatus.BLOCKED


def test_finalize_sets_go_and_no_go_correctly():
    svc = _svc()

    run_go = svc.create_run(CreateRunRequest(feature_key="042-production-pipeline", environment="staging"))
    svc._replace_phase_checks(  # noqa: SLF001
        run_id=run_go.id,
        phase=ValidationPhase.READINESS,
        checks=[_check(phase=ValidationPhase.READINESS, key="readiness.ok", status=ValidationCheckStatus.PASSED)],
    )
    svc._replace_phase_checks(  # noqa: SLF001
        run_id=run_go.id,
        phase=ValidationPhase.REGRESSION,
        checks=[_check(phase=ValidationPhase.REGRESSION, key="regression.ok", status=ValidationCheckStatus.PASSED)],
    )
    finalize_go = svc.finalize(run_go.id, FinalizeRequest())
    assert finalize_go.release_decision.value == "go"
    assert finalize_go.report.run.rollback_required is False
    assert finalize_go.report.run.status == ValidationRunStatus.PASSED

    run_fail = svc.create_run(CreateRunRequest(feature_key="042-production-pipeline", environment="prod-like"))
    svc._replace_phase_checks(  # noqa: SLF001
        run_id=run_fail.id,
        phase=ValidationPhase.READINESS,
        checks=[_check(phase=ValidationPhase.READINESS, key="readiness.ok", status=ValidationCheckStatus.PASSED)],
    )
    svc._replace_phase_checks(  # noqa: SLF001
        run_id=run_fail.id,
        phase=ValidationPhase.REGRESSION,
        checks=[_check(phase=ValidationPhase.REGRESSION, key="regression.fail", status=ValidationCheckStatus.FAILED)],
    )
    finalize_fail = svc.finalize(run_fail.id, FinalizeRequest())
    assert finalize_fail.release_decision.value == "no-go"
    assert finalize_fail.report.run.rollback_required is True
    assert finalize_fail.report.run.rollback_status.value == "pending"
