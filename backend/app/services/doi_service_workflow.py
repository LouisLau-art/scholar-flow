from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from uuid import UUID

from fastapi import HTTPException

from app.models.doi import (
    DOIRegistration,
    DOIRegistrationStatus,
    DOITask,
    DOITaskList,
    DOITaskStatus,
    DOITaskType,
)
from app.services.doi_service_common import (
    logger,
    looks_like_missing_schema,
    now_iso,
    truncate,
)


class DOIServiceWorkflowMixin:
    async def create_registration(self, article_id: UUID) -> DOIRegistration:
        manuscript_id = str(article_id)
        manuscript = self._load_manuscript(manuscript_id)
        if not manuscript:
            raise HTTPException(status_code=404, detail="Manuscript not found")

        current_status = str(manuscript.get("status") or "").strip().lower()
        if current_status != "published":
            raise HTTPException(status_code=400, detail="DOI registration requires manuscript status=published")

        existing = self._load_registration_row(article_id=manuscript_id)
        if existing:
            self._ensure_pending_task(registration_id=str(existing["id"]), priority=0)
            return self._to_registration_model(existing)

        published_raw = str(manuscript.get("published_at") or manuscript.get("created_at") or "")
        try:
            year = datetime.fromisoformat(published_raw.replace("Z", "+00:00")).year
        except Exception:
            year = datetime.now(timezone.utc).year

        sequence = self._next_sequence_for_year(year)
        doi = self.generate_doi(year, sequence)

        now = now_iso()
        try:
            insert_resp = (
                self.client.table("doi_registrations")
                .insert(
                    {
                        "article_id": manuscript_id,
                        "doi": doi,
                        "status": DOIRegistrationStatus.PENDING.value,
                        "attempts": 0,
                        "error_message": None,
                        "created_at": now,
                        "updated_at": now,
                    }
                )
                .execute()
            )
            rows = getattr(insert_resp, "data", None) or []
            if not rows:
                raise HTTPException(status_code=500, detail="Failed to create DOI registration")
            registration_row = rows[0]
        except HTTPException:
            raise
        except Exception as e:
            if "duplicate" in str(e).lower() or "unique" in str(e).lower():
                # 中文注释: 并发插入时走幂等回读。
                row = self._load_registration_row(article_id=manuscript_id)
                if row:
                    registration_row = row
                else:
                    raise HTTPException(status_code=500, detail="Failed to create DOI registration") from e
            elif looks_like_missing_schema(str(e)):
                raise HTTPException(
                    status_code=500,
                    detail="DB not migrated: doi_registrations table missing",
                ) from e
            else:
                raise

        task = self._ensure_pending_task(registration_id=str(registration_row["id"]), priority=0)
        self._log_audit(
            registration_id=str(registration_row["id"]),
            action="register_requested",
            request_payload={
                "article_id": manuscript_id,
                "queued_task_id": str(task.get("id") or ""),
            },
            response_status=202,
        )
        return self._to_registration_model(registration_row)

    async def get_registration(self, article_id: UUID) -> Optional[DOIRegistration]:
        row = self._load_registration_row(article_id=str(article_id))
        if not row:
            return None
        return self._to_registration_model(row)

    async def retry_registration(self, article_id: UUID) -> DOITask:
        registration = await self.get_registration(article_id)
        if not registration:
            raise HTTPException(status_code=404, detail="DOI registration not found")

        if registration.status == DOIRegistrationStatus.REGISTERED:
            raise HTTPException(status_code=400, detail="DOI already registered")

        updated = self._update_registration(
            str(registration.id),
            {
                "status": DOIRegistrationStatus.PENDING.value,
                "error_message": None,
            },
        )
        task_row = self._ensure_pending_task(registration_id=str(updated["id"]), priority=10)
        self._log_audit(
            registration_id=str(updated["id"]),
            action="manual_retry_requested",
            request_payload={"article_id": str(article_id), "task_id": str(task_row.get("id") or "")},
            response_status=202,
        )
        return self._to_task_model(task_row)

    async def list_tasks(
        self,
        *,
        status: str | None = None,
        limit: int = 20,
        offset: int = 0,
        failed_only: bool = False,
    ) -> DOITaskList:
        q = self.client.table("doi_tasks").select("*", count="exact")
        if failed_only:
            q = q.eq("status", DOITaskStatus.FAILED.value)
        elif status:
            q = q.eq("status", status)

        q = q.order("created_at", desc=True).range(offset, offset + limit - 1)
        resp = q.execute()

        rows = getattr(resp, "data", None) or []
        items = [self._to_task_model(r) for r in rows]
        total = int(getattr(resp, "count", None) or 0)
        if total == 0 and rows:
            total = len(rows)

        return DOITaskList(items=items, total=total, limit=limit, offset=offset)

    def _claim_next_task(self) -> Optional[dict[str, Any]]:
        now = now_iso()
        try:
            resp = (
                self.client.table("doi_tasks")
                .select("*")
                .eq("status", DOITaskStatus.PENDING.value)
                .lte("run_at", now)
                .order("priority", desc=True)
                .order("run_at", desc=False)
                .limit(1)
                .execute()
            )
            rows = getattr(resp, "data", None) or []
            if not rows:
                return None
            task = rows[0]

            locked = (
                self.client.table("doi_tasks")
                .update(
                    {
                        "status": DOITaskStatus.PROCESSING.value,
                        "locked_at": now,
                        "locked_by": self.worker_id,
                        "attempts": int(task.get("attempts") or 0) + 1,
                    }
                )
                .eq("id", task["id"])
                .eq("status", DOITaskStatus.PENDING.value)
                .execute()
            )
            locked_rows = getattr(locked, "data", None) or []
            if not locked_rows:
                return None
            return locked_rows[0]
        except Exception as e:
            if looks_like_missing_schema(str(e)):
                raise HTTPException(
                    status_code=500,
                    detail="DB not migrated: doi_tasks table missing",
                ) from e
            raise

    async def _handle_task_failure(self, task: dict[str, Any], error_message: str) -> None:
        attempts = int(task.get("attempts") or 1)
        max_attempts = int(task.get("max_attempts") or 4)

        if attempts >= max_attempts:
            self.client.table("doi_tasks").update(
                {
                    "status": DOITaskStatus.FAILED.value,
                    "last_error": truncate(error_message),
                    "locked_at": None,
                    "locked_by": None,
                }
            ).eq("id", task["id"]).execute()
            return

        delay_minutes = [1, 5, 30, 120][min(attempts - 1, 3)]
        run_at = (datetime.now(timezone.utc) + timedelta(minutes=delay_minutes)).isoformat()

        self.client.table("doi_tasks").update(
            {
                "status": DOITaskStatus.PENDING.value,
                "run_at": run_at,
                "last_error": truncate(error_message),
                "locked_at": None,
                "locked_by": None,
            }
        ).eq("id", task["id"]).execute()

    async def process_due_tasks(self, *, limit: int = 5) -> dict[str, Any]:
        processed: list[dict[str, Any]] = []

        for _ in range(max(1, min(limit, 50))):
            task = self._claim_next_task()
            if not task:
                break

            task_id = str(task.get("id") or "")
            try:
                task_type = str(task.get("task_type") or "")
                if task_type != DOITaskType.REGISTER.value:
                    raise RuntimeError(f"Unsupported DOI task_type: {task_type}")

                registration_id = str(task.get("registration_id") or "").strip()
                if not registration_id:
                    raise RuntimeError("Missing registration_id")

                await self.register_doi(UUID(registration_id))

                self.client.table("doi_tasks").update(
                    {
                        "status": DOITaskStatus.COMPLETED.value,
                        "completed_at": now_iso(),
                        "locked_at": None,
                        "locked_by": None,
                        "last_error": None,
                    }
                ).eq("id", task_id).execute()

                processed.append({"task_id": task_id, "status": "completed"})
            except Exception as e:
                await self._handle_task_failure(task, str(e))
                processed.append(
                    {
                        "task_id": task_id,
                        "status": "failed",
                        "error": truncate(str(e), 300),
                    }
                )

        return {
            "processed_count": len(processed),
            "items": processed,
        }

    async def register_doi(self, registration_id: UUID):
        """
        执行单条 DOI 注册任务（由 Worker/cron 调用）。
        """
        reg_id = str(registration_id)
        registration = self._load_registration_by_id(registration_id=reg_id)
        if not registration:
            raise HTTPException(status_code=404, detail="DOI registration not found")

        if str(registration.get("status") or "") == DOIRegistrationStatus.REGISTERED.value:
            return self._to_registration_model(registration)

        attempts = int(registration.get("attempts") or 0) + 1
        registration = self._update_registration(
            reg_id,
            {
                "status": DOIRegistrationStatus.SUBMITTING.value,
                "attempts": attempts,
                "error_message": None,
            },
        )

        manuscript_id = str(registration.get("article_id") or "").strip()
        manuscript = self._load_manuscript(manuscript_id)
        if not manuscript:
            err = "Manuscript not found for DOI registration"
            self._update_registration(
                reg_id,
                {
                    "status": DOIRegistrationStatus.FAILED.value,
                    "error_message": err,
                },
            )
            self._log_audit(
                registration_id=reg_id,
                action="register_failed",
                request_payload={"article_id": manuscript_id},
                response_status=404,
                error_details=err,
            )
            raise RuntimeError(err)

        if str(manuscript.get("status") or "").strip().lower() != "published":
            err = "Manuscript is not published"
            self._update_registration(
                reg_id,
                {
                    "status": DOIRegistrationStatus.FAILED.value,
                    "error_message": err,
                },
            )
            self._log_audit(
                registration_id=reg_id,
                action="register_failed",
                request_payload={"article_id": manuscript_id},
                response_status=400,
                error_details=err,
            )
            raise RuntimeError(err)

        if not self.config:
            err = "Crossref deposit configuration missing"
            self._update_registration(
                reg_id,
                {
                    "status": DOIRegistrationStatus.FAILED.value,
                    "error_message": err,
                },
            )
            self._log_audit(
                registration_id=reg_id,
                action="register_failed",
                request_payload={"article_id": manuscript_id},
                response_status=503,
                error_details=err,
            )
            raise RuntimeError(err)

        doi = str(registration.get("doi") or "").strip()
        if not doi:
            year = datetime.now(timezone.utc).year
            sequence = self._next_sequence_for_year(year)
            doi = self.generate_doi(year, sequence)
            registration = self._update_registration(reg_id, {"doi": doi})

        article_data = self._build_crossref_article_data(manuscript, doi)
        batch_id = self._create_batch_id(manuscript_id)
        xml_content = self.crossref.generate_xml(article_data, batch_id)

        try:
            response_body = await self.crossref.submit_deposit(
                xml_content,
                file_name=f"doi-{batch_id}.xml",
            )
        except Exception as e:
            err = truncate(str(e))
            self._update_registration(
                reg_id,
                {
                    "status": DOIRegistrationStatus.FAILED.value,
                    "error_message": err,
                },
            )
            self._log_audit(
                registration_id=reg_id,
                action="register_failed",
                request_payload={
                    "article_id": manuscript_id,
                    "doi": doi,
                    "batch_id": batch_id,
                },
                response_status=500,
                error_details=err,
            )
            raise

        crossref_batch_id = self._extract_crossref_batch_id(response_body) or batch_id
        now = now_iso()
        registered = self._update_registration(
            reg_id,
            {
                "status": DOIRegistrationStatus.REGISTERED.value,
                "doi": doi,
                "crossref_batch_id": crossref_batch_id,
                "registered_at": now,
                "error_message": None,
            },
        )

        # 中文注释: 回写 manuscripts.doi 为公开页/索引抓取提供一致来源；列缺失时降级忽略。
        try:
            self.client.table("manuscripts").update({"doi": doi}).eq("id", manuscript_id).execute()
        except Exception as e:
            if "doi" in str(e).lower() and looks_like_missing_schema(str(e)):
                logger.warning("[DOI] manuscripts.doi column missing (ignored): %s", e)
            else:
                logger.warning("[DOI] manuscripts.doi update failed (ignored): %s", e)

        self._log_audit(
            registration_id=reg_id,
            action="register_success",
            request_payload={
                "article_id": manuscript_id,
                "doi": doi,
                "batch_id": batch_id,
                "crossref_batch_id": crossref_batch_id,
            },
            response_status=200,
            response_body=truncate(response_body, 4000),
        )
        return self._to_registration_model(registered)
