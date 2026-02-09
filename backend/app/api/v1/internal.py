from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.core.scheduler import ChaseScheduler
from app.core.security import require_admin_key
from app.models.release_validation import (
    CreateRunRequest,
    FinalizeRequest,
    ReadinessRequest,
    RegressionRequest,
)
from app.services.release_validation_service import ReleaseValidationService

router = APIRouter(prefix="/internal", tags=["Internal"])


@router.post("/cron/chase-reviews")
async def chase_reviews(_admin: None = Depends(require_admin_key)):
    """
    触发自动催办逻辑（内部接口）
    """
    scheduler = ChaseScheduler()
    result = scheduler.run()
    return {"success": True, **result}


@router.get("/sentry/test-error")
async def sentry_test_error(_admin: None = Depends(require_admin_key)):
    """
    Sentry 联调用的“已知错误”端点（Feature 027）。

    中文注释:
    - 仅内部接口（需 ADMIN_API_KEY），避免公网被滥用。
    - 目的：验证 Sentry 能捕获后端异常 + 堆栈。
    """
    raise RuntimeError("Sentry test error (backend)")


@router.post("/release-validation/runs", status_code=201)
async def create_release_validation_run(
    payload: CreateRunRequest,
    _admin: None = Depends(require_admin_key),
):
    service = ReleaseValidationService()
    run = service.create_run(payload)
    return {"run": run}


@router.get("/release-validation/runs")
async def list_release_validation_runs(
    environment: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    _admin: None = Depends(require_admin_key),
):
    service = ReleaseValidationService()
    runs = service.list_runs(environment=environment, limit=limit)
    return {"data": runs}


@router.post("/release-validation/runs/{run_id}/readiness")
async def execute_release_readiness(
    run_id: UUID,
    payload: ReadinessRequest,
    _admin: None = Depends(require_admin_key),
):
    service = ReleaseValidationService()
    return service.execute_readiness(run_id, payload)


@router.post("/release-validation/runs/{run_id}/regression")
async def execute_release_regression(
    run_id: UUID,
    payload: RegressionRequest,
    _admin: None = Depends(require_admin_key),
):
    service = ReleaseValidationService()
    return service.execute_regression(run_id, payload)


@router.post("/release-validation/runs/{run_id}/finalize")
async def finalize_release_validation(
    run_id: UUID,
    payload: FinalizeRequest | None = None,
    _admin: None = Depends(require_admin_key),
):
    service = ReleaseValidationService()
    return service.finalize(run_id, payload or FinalizeRequest())


@router.get("/release-validation/runs/{run_id}/report")
async def get_release_validation_report(
    run_id: UUID,
    _admin: None = Depends(require_admin_key),
):
    service = ReleaseValidationService()
    return service.get_report(run_id)
