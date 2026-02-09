from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable
from uuid import UUID

from fastapi import HTTPException

from app.core.config import get_admin_api_key
from app.lib.api_client import supabase_admin
from app.models.release_validation import (
    CreateRunRequest,
    FinalizeRequest,
    FinalizeResponse,
    PhaseResult,
    ReadinessRequest,
    ReadinessResponse,
    RegressionRequest,
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
from app.services.production_workspace_service import ProductionWorkspaceService


POST_ACCEPTANCE_STATUSES = {
    "approved",
    "layout",
    "english_editing",
    "proofreading",
    "published",
}


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _utc_now_iso() -> str:
    return _utc_now().isoformat()


def _is_missing_table_error(error: Exception, table_name: str) -> bool:
    text = str(error).lower()
    return table_name.lower() in text and ("does not exist" in text or "schema cache" in text)


def _safe_error(error: Exception) -> str:
    return str(error).strip()[:500]


class ReleaseValidationService:
    """
    Feature 043: 云端发布验收编排服务。

    中文注释:
    - 统一管理 run/check 两层审计数据。
    - 提供 readiness / regression / finalize 的 go/no-go 判定。
    - 默认以“保守阻断”为策略，避免 skip/缺项误放行。
    """

    def __init__(self, client: Any | None = None) -> None:
        self.client = client or supabase_admin

    def _run_fields(self) -> str:
        return (
            "id,feature_key,environment,manuscript_id,triggered_by,status,"
            "blocking_count,failed_count,skipped_count,started_at,finished_at,summary,"
            "rollback_required,rollback_status,note,created_at,updated_at"
        )

    def _check_fields(self) -> str:
        return (
            "id,run_id,phase,check_key,title,status,is_blocking,detail,evidence,"
            "started_at,finished_at,created_at"
        )

    def _to_run(self, row: dict[str, Any]) -> ValidationRun:
        payload = dict(row or {})
        if not payload.get("manuscript_id"):
            payload["manuscript_id"] = None
        if not payload.get("triggered_by"):
            payload["triggered_by"] = None
        if not payload.get("note"):
            payload["note"] = None
        return ValidationRun(**payload)

    def _to_check(self, row: dict[str, Any]) -> ValidationCheck:
        payload = dict(row or {})
        if not payload.get("detail"):
            payload["detail"] = None
        payload["evidence"] = payload.get("evidence") or {}
        return ValidationCheck(**payload)

    def _get_run_or_404(self, run_id: UUID | str) -> ValidationRun:
        try:
            resp = (
                self.client.table("release_validation_runs")
                .select(self._run_fields())
                .eq("id", str(run_id))
                .single()
                .execute()
            )
            row = getattr(resp, "data", None) or None
        except Exception as e:
            if _is_missing_table_error(e, "release_validation_runs"):
                raise HTTPException(
                    status_code=500,
                    detail="DB not migrated: release_validation_runs table missing",
                ) from e
            raise HTTPException(status_code=404, detail="Validation run not found") from e

        if not row:
            raise HTTPException(status_code=404, detail="Validation run not found")
        return self._to_run(row)

    def _list_checks(self, run_id: UUID | str, *, phase: ValidationPhase | None = None) -> list[ValidationCheck]:
        try:
            query = (
                self.client.table("release_validation_checks")
                .select(self._check_fields())
                .eq("run_id", str(run_id))
            )
            if phase:
                query = query.eq("phase", phase.value)
            resp = query.order("created_at", desc=False).execute()
            rows = getattr(resp, "data", None) or []
        except Exception as e:
            if _is_missing_table_error(e, "release_validation_checks"):
                raise HTTPException(
                    status_code=500,
                    detail="DB not migrated: release_validation_checks table missing",
                ) from e
            raise
        return [self._to_check(r) for r in rows]

    def _replace_phase_checks(
        self,
        *,
        run_id: UUID | str,
        phase: ValidationPhase,
        checks: list[ValidationCheck],
    ) -> list[ValidationCheck]:
        try:
            (
                self.client.table("release_validation_checks")
                .delete()
                .eq("run_id", str(run_id))
                .eq("phase", phase.value)
                .execute()
            )

            payloads: list[dict[str, Any]] = []
            for check in checks:
                started_at = check.started_at or _utc_now()
                finished_at = check.finished_at or _utc_now()
                payloads.append(
                    {
                        "run_id": str(run_id),
                        "phase": phase.value,
                        "check_key": check.check_key,
                        "title": check.title,
                        "status": check.status.value,
                        "is_blocking": bool(check.is_blocking),
                        "detail": check.detail,
                        "evidence": check.evidence or {},
                        "started_at": started_at.isoformat(),
                        "finished_at": finished_at.isoformat(),
                    }
                )
            if payloads:
                self.client.table("release_validation_checks").insert(payloads).execute()
        except Exception as e:
            if _is_missing_table_error(e, "release_validation_checks"):
                raise HTTPException(
                    status_code=500,
                    detail="DB not migrated: release_validation_checks table missing",
                ) from e
            raise

        return self._list_checks(run_id, phase=phase)

    def _aggregate_counts(self, checks: list[ValidationCheck]) -> tuple[int, int, int]:
        blocking_count = sum(
            1
            for c in checks
            if c.is_blocking and c.status in {ValidationCheckStatus.FAILED, ValidationCheckStatus.BLOCKED}
        )
        failed_count = sum(1 for c in checks if c.status == ValidationCheckStatus.FAILED)
        skipped_count = sum(1 for c in checks if c.status == ValidationCheckStatus.SKIPPED)
        return blocking_count, failed_count, skipped_count

    def _classify_phase_status(self, checks: list[ValidationCheck]) -> ValidationRunStatus:
        if not checks:
            return ValidationRunStatus.BLOCKED
        if any(c.is_blocking and c.status == ValidationCheckStatus.BLOCKED for c in checks):
            return ValidationRunStatus.BLOCKED
        if any(c.is_blocking and c.status == ValidationCheckStatus.FAILED for c in checks):
            return ValidationRunStatus.FAILED
        if any(c.is_blocking and c.status == ValidationCheckStatus.SKIPPED for c in checks):
            return ValidationRunStatus.BLOCKED
        if any(c.status == ValidationCheckStatus.BLOCKED for c in checks):
            return ValidationRunStatus.BLOCKED
        if any(c.status == ValidationCheckStatus.FAILED for c in checks):
            return ValidationRunStatus.FAILED
        return ValidationRunStatus.PASSED

    def _classify_run_status(self, checks: list[ValidationCheck]) -> ValidationRunStatus:
        if not checks:
            return ValidationRunStatus.RUNNING
        if any(c.status == ValidationCheckStatus.BLOCKED for c in checks):
            return ValidationRunStatus.BLOCKED
        if any(c.status == ValidationCheckStatus.FAILED for c in checks):
            return ValidationRunStatus.FAILED
        if any(c.status == ValidationCheckStatus.SKIPPED for c in checks):
            return ValidationRunStatus.BLOCKED
        return ValidationRunStatus.PASSED

    def _update_run(
        self,
        *,
        run_id: UUID | str,
        status: ValidationRunStatus,
        summary: str | None = None,
        finished: bool = False,
        rollback_required: bool | None = None,
        rollback_status: RollbackStatus | None = None,
    ) -> ValidationRun:
        checks = self._list_checks(run_id)
        blocking_count, failed_count, skipped_count = self._aggregate_counts(checks)
        patch: dict[str, Any] = {
            "status": status.value,
            "blocking_count": blocking_count,
            "failed_count": failed_count,
            "skipped_count": skipped_count,
            "updated_at": _utc_now_iso(),
        }
        if summary is not None:
            patch["summary"] = summary
        if finished:
            patch["finished_at"] = _utc_now_iso()
        if rollback_required is not None:
            patch["rollback_required"] = bool(rollback_required)
        if rollback_status is not None:
            patch["rollback_status"] = rollback_status.value

        try:
            resp = (
                self.client.table("release_validation_runs")
                .update(patch)
                .eq("id", str(run_id))
                .execute()
            )
            rows = getattr(resp, "data", None) or []
        except Exception as e:
            if _is_missing_table_error(e, "release_validation_runs"):
                raise HTTPException(
                    status_code=500,
                    detail="DB not migrated: release_validation_runs table missing",
                ) from e
            raise

        if not rows:
            raise HTTPException(status_code=404, detail="Validation run not found")
        return self._to_run(rows[0])

    def create_run(self, request: CreateRunRequest) -> ValidationRun:
        try:
            running = (
                self.client.table("release_validation_runs")
                .select("id")
                .eq("environment", request.environment)
                .eq("status", ValidationRunStatus.RUNNING.value)
                .limit(1)
                .execute()
            )
            rows = getattr(running, "data", None) or []
            if rows:
                raise HTTPException(
                    status_code=409,
                    detail="Another validation run is already running in this environment",
                )
        except HTTPException:
            raise
        except Exception as e:
            if _is_missing_table_error(e, "release_validation_runs"):
                raise HTTPException(
                    status_code=500,
                    detail="DB not migrated: release_validation_runs table missing",
                ) from e
            raise

        payload = {
            "feature_key": request.feature_key,
            "environment": request.environment,
            "manuscript_id": str(request.manuscript_id) if request.manuscript_id else None,
            "triggered_by": request.triggered_by,
            "status": ValidationRunStatus.RUNNING.value,
            "blocking_count": 0,
            "failed_count": 0,
            "skipped_count": 0,
            "started_at": _utc_now_iso(),
            "rollback_required": False,
            "rollback_status": RollbackStatus.NOT_REQUIRED.value,
            "note": request.note,
        }
        try:
            inserted = self.client.table("release_validation_runs").insert(payload).execute()
            rows = getattr(inserted, "data", None) or []
            if not rows:
                raise RuntimeError("insert run failed")
            return self._to_run(rows[0])
        except Exception as e:
            text = str(e).lower()
            if "release_validation_runs" in text and "status" in text and "running" in text:
                raise HTTPException(
                    status_code=409,
                    detail="Another validation run is already running in this environment",
                ) from e
            if _is_missing_table_error(e, "release_validation_runs"):
                raise HTTPException(
                    status_code=500,
                    detail="DB not migrated: release_validation_runs table missing",
                ) from e
            raise

    def list_runs(self, *, environment: str | None = None, limit: int = 20) -> list[ValidationRun]:
        safe_limit = max(1, min(int(limit), 100))
        try:
            query = self.client.table("release_validation_runs").select(self._run_fields())
            if environment:
                query = query.eq("environment", environment)
            resp = query.order("started_at", desc=True).limit(safe_limit).execute()
            rows = getattr(resp, "data", None) or []
        except Exception as e:
            if _is_missing_table_error(e, "release_validation_runs"):
                raise HTTPException(
                    status_code=500,
                    detail="DB not migrated: release_validation_runs table missing",
                ) from e
            raise
        return [self._to_run(r) for r in rows]

    def _probe_table(self, table: str, columns: str = "id") -> tuple[ValidationCheckStatus, str, dict[str, Any]]:
        try:
            resp = self.client.table(table).select(columns).limit(1).execute()
            rows = getattr(resp, "data", None) or []
            return (
                ValidationCheckStatus.PASSED,
                f"{table} query ok",
                {"table": table, "rows": len(rows)},
            )
        except Exception as e:
            if _is_missing_table_error(e, table):
                return (
                    ValidationCheckStatus.BLOCKED,
                    f"{table} table missing",
                    {"table": table, "error": _safe_error(e)},
                )
            return (
                ValidationCheckStatus.FAILED,
                f"{table} query failed",
                {"table": table, "error": _safe_error(e)},
            )

    def _probe_bucket(self, bucket: str) -> tuple[ValidationCheckStatus, str, dict[str, Any]]:
        storage = getattr(self.client, "storage", None)
        if storage is None or not hasattr(storage, "get_bucket"):
            return (
                ValidationCheckStatus.BLOCKED,
                "Storage client not available",
                {"bucket": bucket},
            )
        try:
            storage.get_bucket(bucket)
            return ValidationCheckStatus.PASSED, f"{bucket} bucket available", {"bucket": bucket}
        except Exception as e:
            return (
                ValidationCheckStatus.BLOCKED,
                f"{bucket} bucket missing/unreachable",
                {"bucket": bucket, "error": _safe_error(e)},
            )

    def _probe_admin_key(self) -> tuple[ValidationCheckStatus, str, dict[str, Any]]:
        key = get_admin_api_key()
        if key:
            return ValidationCheckStatus.PASSED, "ADMIN_API_KEY configured", {"configured": True}
        return ValidationCheckStatus.BLOCKED, "ADMIN_API_KEY not configured", {"configured": False}

    def _probe_publish_gate(self, run: ValidationRun) -> tuple[ValidationCheckStatus, str, dict[str, Any]]:
        manuscript_id = run.manuscript_id
        if manuscript_id is None:
            return (
                ValidationCheckStatus.SKIPPED,
                "manuscript_id missing, publish gate probe skipped",
                {"manuscript_id": None},
            )

        workspace = ProductionWorkspaceService()
        workspace.client = self.client
        try:
            workspace.assert_publish_gate_ready(manuscript_id=str(manuscript_id))
            return (
                ValidationCheckStatus.PASSED,
                "publish gate ready",
                {"manuscript_id": str(manuscript_id)},
            )
        except HTTPException as e:
            status = ValidationCheckStatus.BLOCKED if e.status_code in {404, 500} else ValidationCheckStatus.FAILED
            return (
                status,
                f"publish gate probe failed: {e.detail}",
                {"manuscript_id": str(manuscript_id), "status_code": e.status_code},
            )
        except Exception as e:
            return (
                ValidationCheckStatus.BLOCKED,
                "publish gate probe errored",
                {"manuscript_id": str(manuscript_id), "error": _safe_error(e)},
            )

    def _probe_manuscript_status(self, run: ValidationRun) -> tuple[ValidationCheckStatus, str, dict[str, Any]]:
        manuscript_id = run.manuscript_id
        if manuscript_id is None:
            return (
                ValidationCheckStatus.SKIPPED,
                "manuscript_id missing, scenario skipped",
                {"manuscript_id": None},
            )
        try:
            resp = (
                self.client.table("manuscripts")
                .select("id,status,updated_at")
                .eq("id", str(manuscript_id))
                .single()
                .execute()
            )
            row = getattr(resp, "data", None) or None
            if not row:
                return (
                    ValidationCheckStatus.BLOCKED,
                    "manuscript not found",
                    {"manuscript_id": str(manuscript_id)},
                )
            status = str(row.get("status") or "").strip().lower()
            if status in POST_ACCEPTANCE_STATUSES:
                return (
                    ValidationCheckStatus.PASSED,
                    f"manuscript status={status}",
                    {"manuscript_id": str(manuscript_id), "status": status},
                )
            return (
                ValidationCheckStatus.FAILED,
                f"manuscript not in post-acceptance flow: {status or 'unknown'}",
                {"manuscript_id": str(manuscript_id), "status": status},
            )
        except Exception as e:
            return (
                ValidationCheckStatus.BLOCKED,
                "manuscript lookup failed",
                {"manuscript_id": str(manuscript_id), "error": _safe_error(e)},
            )

    def _probe_cycle_exists(self, run: ValidationRun) -> tuple[ValidationCheckStatus, str, dict[str, Any]]:
        manuscript_id = run.manuscript_id
        if manuscript_id is None:
            return (
                ValidationCheckStatus.SKIPPED,
                "manuscript_id missing, scenario skipped",
                {"manuscript_id": None},
            )
        try:
            resp = (
                self.client.table("production_cycles")
                .select("id,manuscript_id,cycle_no,status")
                .eq("manuscript_id", str(manuscript_id))
                .order("cycle_no", desc=True)
                .limit(1)
                .execute()
            )
            rows = getattr(resp, "data", None) or []
            if not rows:
                return (
                    ValidationCheckStatus.FAILED,
                    "no production cycle found",
                    {"manuscript_id": str(manuscript_id)},
                )
            row = rows[0]
            return (
                ValidationCheckStatus.PASSED,
                f"cycle found: {row.get('status')}",
                {
                    "manuscript_id": str(manuscript_id),
                    "cycle_id": row.get("id"),
                    "cycle_status": row.get("status"),
                },
            )
        except Exception as e:
            if _is_missing_table_error(e, "production_cycles"):
                return (
                    ValidationCheckStatus.BLOCKED,
                    "production_cycles table missing",
                    {"manuscript_id": str(manuscript_id), "error": _safe_error(e)},
                )
            return (
                ValidationCheckStatus.FAILED,
                "production cycle probe failed",
                {"manuscript_id": str(manuscript_id), "error": _safe_error(e)},
            )

    def _build_checks(
        self,
        *,
        phase: ValidationPhase,
        selected_keys: list[str],
        definitions: list[tuple[str, str, bool, Callable[[], tuple[ValidationCheckStatus, str, dict[str, Any]]]]],
    ) -> list[ValidationCheck]:
        checks: list[ValidationCheck] = []
        wanted = {k.strip() for k in selected_keys if k.strip()}
        for key, title, is_blocking, fn in definitions:
            if wanted and key not in wanted:
                continue
            status, detail, evidence = fn()
            checks.append(
                ValidationCheck(
                    phase=phase,
                    check_key=key,
                    title=title,
                    status=status,
                    is_blocking=is_blocking,
                    detail=detail,
                    evidence=evidence,
                )
            )
        return checks

    def execute_readiness(self, run_id: UUID | str, request: ReadinessRequest) -> ReadinessResponse:
        run = self._get_run_or_404(run_id)

        gate_blocking = bool(request.strict_blocking)
        readiness_definitions: list[
            tuple[str, str, bool, Callable[[], tuple[ValidationCheckStatus, str, dict[str, Any]]]]
        ] = [
            ("schema.production_cycles.exists", "Schema: production_cycles", True, lambda: self._probe_table("production_cycles")),
            (
                "schema.production_proofreading_responses.exists",
                "Schema: production_proofreading_responses",
                True,
                lambda: self._probe_table("production_proofreading_responses"),
            ),
            (
                "schema.production_correction_items.exists",
                "Schema: production_correction_items",
                True,
                lambda: self._probe_table("production_correction_items"),
            ),
            ("storage.production_proofs.bucket", "Storage: production-proofs bucket", True, lambda: self._probe_bucket("production-proofs")),
            ("permission.admin_key.configured", "Permission: ADMIN_API_KEY configured", True, self._probe_admin_key),
            ("gate.publish.ready", "Gate: publish readiness probe", gate_blocking, lambda: self._probe_publish_gate(run)),
        ]
        checks = self._build_checks(
            phase=ValidationPhase.READINESS,
            selected_keys=request.check_keys,
            definitions=readiness_definitions,
        )
        persisted = self._replace_phase_checks(run_id=run.id, phase=ValidationPhase.READINESS, checks=checks)
        phase_status = self._classify_phase_status(persisted)
        updated = self._update_run(
            run_id=run.id,
            status=self._classify_run_status(self._list_checks(run.id)),
            summary=f"Readiness {phase_status.value}: {len(persisted)} checks",
        )
        return ReadinessResponse(
            run_id=updated.id,
            result=PhaseResult(status=phase_status, checks=persisted),
        )

    def execute_regression(self, run_id: UUID | str, request: RegressionRequest) -> RegressionResponse:
        run = self._get_run_or_404(run_id)
        regression_definitions: list[
            tuple[str, str, bool, Callable[[], tuple[ValidationCheckStatus, str, dict[str, Any]]]]
        ] = [
            ("regression.manuscript.status", "Regression: manuscript in post-acceptance status", True, lambda: self._probe_manuscript_status(run)),
            ("regression.production_cycle.exists", "Regression: production cycle exists", True, lambda: self._probe_cycle_exists(run)),
            ("regression.publish_gate.ready", "Regression: publish gate readiness", True, lambda: self._probe_publish_gate(run)),
            ("regression.audit_log.table", "Regression: status_transition_logs reachable", False, lambda: self._probe_table("status_transition_logs")),
        ]
        checks = self._build_checks(
            phase=ValidationPhase.REGRESSION,
            selected_keys=request.scenario_keys,
            definitions=regression_definitions,
        )

        if request.require_zero_skip:
            skipped_blocking = [c for c in checks if c.is_blocking and c.status == ValidationCheckStatus.SKIPPED]
            if skipped_blocking:
                checks.append(
                    ValidationCheck(
                        phase=ValidationPhase.REGRESSION,
                        check_key="regression.zero_skip.enforced",
                        title="Regression gate: blocking scenarios skip=0",
                        status=ValidationCheckStatus.BLOCKED,
                        is_blocking=True,
                        detail="Blocking regression scenarios were skipped",
                        evidence={"skipped_keys": [c.check_key for c in skipped_blocking]},
                    )
                )

        persisted = self._replace_phase_checks(run_id=run.id, phase=ValidationPhase.REGRESSION, checks=checks)
        phase_status = self._classify_phase_status(persisted)
        updated = self._update_run(
            run_id=run.id,
            status=self._classify_run_status(self._list_checks(run.id)),
            summary=f"Regression {phase_status.value}: {len(persisted)} checks",
        )
        return RegressionResponse(
            run_id=updated.id,
            result=PhaseResult(status=phase_status, checks=persisted),
        )

    def _build_rollback_plan(self, run: ValidationRun, note: str | None = None) -> RollbackPlan:
        required = bool(run.rollback_required)
        if not required:
            return RollbackPlan(
                required=False,
                status=RollbackStatus.NOT_REQUIRED,
                note=note or "No rollback required.",
                steps=[],
                updated_at=run.updated_at or _utc_now(),
            )
        steps = [
            "冻结本次发布窗口并通知编辑团队暂停发布操作。",
            "回退到上一稳定后端镜像（Hugging Face Space）并确认健康检查通过。",
            "恢复上一版本前端环境变量/配置并触发 Vercel 回滚。",
            "重新执行关键验收链路（readiness + regression）确认恢复。",
            "在 release_validation_runs 记录回退完成时间与责任人。",
        ]
        return RollbackPlan(
            required=True,
            status=run.rollback_status,
            note=note or run.summary or "Rollback required before next release attempt.",
            steps=steps,
            updated_at=run.updated_at or _utc_now(),
        )

    def _derive_release_decision(
        self,
        *,
        readiness_checks: list[ValidationCheck],
        regression_checks: list[ValidationCheck],
        force_no_go: bool,
    ) -> ReleaseDecision:
        if force_no_go:
            return ReleaseDecision.NO_GO
        readiness_status = self._classify_phase_status(readiness_checks)
        regression_status = self._classify_phase_status(regression_checks)
        if readiness_status == ValidationRunStatus.PASSED and regression_status == ValidationRunStatus.PASSED:
            return ReleaseDecision.GO
        return ReleaseDecision.NO_GO

    def finalize(self, run_id: UUID | str, request: FinalizeRequest) -> FinalizeResponse:
        run = self._get_run_or_404(run_id)
        readiness_checks = self._list_checks(run.id, phase=ValidationPhase.READINESS)
        regression_checks = self._list_checks(run.id, phase=ValidationPhase.REGRESSION)

        release_decision = self._derive_release_decision(
            readiness_checks=readiness_checks,
            regression_checks=regression_checks,
            force_no_go=request.force_no_go,
        )
        rollback_required = release_decision == ReleaseDecision.NO_GO
        rollback_state = RollbackStatus.PENDING if rollback_required else RollbackStatus.NOT_REQUIRED

        rollback_marker = ValidationCheck(
            phase=ValidationPhase.ROLLBACK,
            check_key="rollback.plan.status",
            title="Rollback plan status",
            status=ValidationCheckStatus.BLOCKED if rollback_required else ValidationCheckStatus.PASSED,
            is_blocking=False,
            detail="Rollback required" if rollback_required else "Rollback not required",
            evidence={"required": rollback_required, "status": rollback_state.value},
        )
        self._replace_phase_checks(
            run_id=run.id,
            phase=ValidationPhase.ROLLBACK,
            checks=[rollback_marker],
        )

        if release_decision == ReleaseDecision.GO:
            final_status = ValidationRunStatus.PASSED
            summary = "Release decision GO: readiness/regression passed."
        else:
            has_blocked = any(c.status == ValidationCheckStatus.BLOCKED for c in (readiness_checks + regression_checks))
            has_skipped = any(c.status == ValidationCheckStatus.SKIPPED for c in (readiness_checks + regression_checks))
            final_status = ValidationRunStatus.BLOCKED if (has_blocked or has_skipped) else ValidationRunStatus.FAILED
            summary = "Release decision NO-GO: blocking/failure conditions detected."

        updated = self._update_run(
            run_id=run.id,
            status=final_status,
            summary=summary,
            finished=True,
            rollback_required=rollback_required,
            rollback_status=rollback_state,
        )
        report = ValidationReport(
            run=updated,
            readiness_checks=readiness_checks,
            regression_checks=regression_checks,
            rollback_plan=self._build_rollback_plan(updated, note=request.rollback_note),
            release_decision=release_decision,
        )
        return FinalizeResponse(
            run_id=updated.id,
            release_decision=release_decision,
            report=report,
        )

    def get_report(self, run_id: UUID | str) -> ValidationReport:
        run = self._get_run_or_404(run_id)
        readiness_checks = self._list_checks(run.id, phase=ValidationPhase.READINESS)
        regression_checks = self._list_checks(run.id, phase=ValidationPhase.REGRESSION)
        release_decision = (
            ReleaseDecision.GO
            if run.status == ValidationRunStatus.PASSED and not run.rollback_required
            else ReleaseDecision.NO_GO
        )
        return ValidationReport(
            run=run,
            readiness_checks=readiness_checks,
            regression_checks=regression_checks,
            rollback_plan=self._build_rollback_plan(run),
            release_decision=release_decision,
        )
