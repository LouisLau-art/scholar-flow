from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class ValidationRunStatus(str, Enum):
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    BLOCKED = "blocked"


class ValidationPhase(str, Enum):
    READINESS = "readiness"
    REGRESSION = "regression"
    ROLLBACK = "rollback"


class ValidationCheckStatus(str, Enum):
    PASSED = "passed"
    FAILED = "failed"
    BLOCKED = "blocked"
    SKIPPED = "skipped"


class RollbackStatus(str, Enum):
    NOT_REQUIRED = "not_required"
    PENDING = "pending"
    DONE = "done"


class ReleaseDecision(str, Enum):
    GO = "go"
    NO_GO = "no-go"


class CreateRunRequest(BaseModel):
    feature_key: str = Field(..., min_length=1, max_length=128)
    environment: str = Field(..., min_length=1, max_length=64)
    manuscript_id: UUID | None = None
    triggered_by: str | None = Field(default=None, max_length=128)
    note: str | None = Field(default=None, max_length=2000)


class ValidationRun(BaseModel):
    id: UUID
    feature_key: str
    environment: str
    manuscript_id: UUID | None = None
    triggered_by: str | None = None
    status: ValidationRunStatus
    blocking_count: int = 0
    failed_count: int = 0
    skipped_count: int = 0
    started_at: datetime
    finished_at: datetime | None = None
    summary: str | None = None
    rollback_required: bool = False
    rollback_status: RollbackStatus = RollbackStatus.NOT_REQUIRED
    note: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class RunResponse(BaseModel):
    run: ValidationRun


class RunListResponse(BaseModel):
    data: list[ValidationRun] = Field(default_factory=list)


class ReadinessRequest(BaseModel):
    check_keys: list[str] = Field(default_factory=list)
    strict_blocking: bool = True


class RegressionRequest(BaseModel):
    scenario_keys: list[str] = Field(default_factory=list)
    require_zero_skip: bool = True


class FinalizeRequest(BaseModel):
    force_no_go: bool = False
    rollback_note: str | None = Field(default=None, max_length=2000)


class ValidationCheck(BaseModel):
    id: UUID | None = None
    run_id: UUID | None = None
    phase: ValidationPhase
    check_key: str = Field(..., min_length=1, max_length=200)
    title: str = Field(..., min_length=1, max_length=200)
    status: ValidationCheckStatus
    is_blocking: bool = True
    detail: str | None = None
    evidence: dict[str, Any] = Field(default_factory=dict)
    started_at: datetime | None = None
    finished_at: datetime | None = None
    created_at: datetime | None = None


class PhaseResult(BaseModel):
    status: ValidationRunStatus
    checks: list[ValidationCheck] = Field(default_factory=list)


class ReadinessResponse(BaseModel):
    run_id: UUID
    result: PhaseResult


class RegressionResponse(BaseModel):
    run_id: UUID
    result: PhaseResult


class RollbackPlan(BaseModel):
    required: bool
    status: RollbackStatus
    note: str | None = None
    steps: list[str] = Field(default_factory=list)
    updated_at: datetime | None = None


class ValidationReport(BaseModel):
    run: ValidationRun
    readiness_checks: list[ValidationCheck] = Field(default_factory=list)
    regression_checks: list[ValidationCheck] = Field(default_factory=list)
    rollback_plan: RollbackPlan
    release_decision: ReleaseDecision


class FinalizeResponse(BaseModel):
    run_id: UUID
    release_decision: ReleaseDecision
    report: ValidationReport
