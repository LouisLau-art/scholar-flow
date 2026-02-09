from __future__ import annotations

import os
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from uuid import UUID

from fastapi import HTTPException

from app.core.config import CrossrefConfig
from app.lib.api_client import supabase_admin
from app.models.doi import (
    DOIRegistration,
    DOIRegistrationStatus,
    DOITask,
    DOITaskList,
    DOITaskStatus,
    DOITaskType,
)
from app.services.crossref_client import CrossrefClient


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _truncate(value: str, max_len: int = 2000) -> str:
    text = str(value or "").strip()
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."


def _looks_like_single_no_rows(error_text: str) -> bool:
    lowered = (error_text or "").lower()
    return (
        "pgrst116" in lowered
        or "cannot coerce the result to a single json object" in lowered
        or "0 rows" in lowered
    )


def _looks_like_missing_schema(error_text: str) -> bool:
    lowered = (error_text or "").lower()
    return (
        "pgrst205" in lowered
        or "schema cache" in lowered
        or "does not exist" in lowered
        or "relation" in lowered
        or "undefinedtable" in lowered
    )


class DOIService:
    """
    DOI/Crossref 服务（GAP-P2-01）。

    中文注释:
    - 使用数据库队列（doi_tasks）实现“异步可重试”。
    - 落库 `doi_registrations` + `doi_audit_log`，保证可追踪。
    """

    def __init__(
        self,
        config: Optional[CrossrefConfig] = None,
        *,
        client: Any | None = None,
        crossref_client: CrossrefClient | None = None,
    ):
        self.config = config
        self.client = client or supabase_admin
        self.crossref = crossref_client or CrossrefClient(config)
        self.worker_id = f"doi-service-{int(datetime.now(timezone.utc).timestamp())}"

    def generate_doi(self, year: int, sequence: int) -> str:
        """
        Generate DOI string: prefix/sf.{year}.{sequence}
        e.g. 10.12345/sf.2026.00001
        """
        prefix = self.config.doi_prefix if self.config else "10.12345"
        return f"{prefix}/sf.{year}.{sequence:05d}"

    def _to_registration_model(self, row: dict[str, Any]) -> DOIRegistration:
        return DOIRegistration(**row)

    def _to_task_model(self, row: dict[str, Any]) -> DOITask:
        return DOITask(**row)

    def _load_registration_row(self, *, article_id: str) -> Optional[dict[str, Any]]:
        try:
            resp = (
                self.client.table("doi_registrations")
                .select("*")
                .eq("article_id", article_id)
                .single()
                .execute()
            )
            return getattr(resp, "data", None) or None
        except Exception as e:
            if _looks_like_single_no_rows(str(e)):
                return None
            if _looks_like_missing_schema(str(e)):
                raise HTTPException(
                    status_code=500,
                    detail="DB not migrated: doi_registrations table missing",
                ) from e
            raise

    def _load_registration_by_id(self, *, registration_id: str) -> Optional[dict[str, Any]]:
        try:
            resp = (
                self.client.table("doi_registrations")
                .select("*")
                .eq("id", registration_id)
                .single()
                .execute()
            )
            return getattr(resp, "data", None) or None
        except Exception as e:
            if _looks_like_single_no_rows(str(e)):
                return None
            if _looks_like_missing_schema(str(e)):
                raise HTTPException(
                    status_code=500,
                    detail="DB not migrated: doi_registrations table missing",
                ) from e
            raise

    def _load_manuscript(self, manuscript_id: str) -> Optional[dict[str, Any]]:
        # 中文注释: 云端 schema 可能存在列漂移（doi/published_at 缺失），这里分层降级查询。
        select_candidates = [
            "id,title,abstract,status,published_at,created_at,doi,journal_id,author_id,authors",
            "id,title,abstract,status,published_at,created_at,doi,journal_id,author_id",
            "id,title,abstract,status,created_at,journal_id,author_id",
        ]

        last_err: Exception | None = None
        for fields in select_candidates:
            try:
                resp = (
                    self.client.table("manuscripts")
                    .select(fields)
                    .eq("id", manuscript_id)
                    .single()
                    .execute()
                )
                return getattr(resp, "data", None) or None
            except Exception as e:
                if _looks_like_single_no_rows(str(e)):
                    return None
                last_err = e
                continue

        if last_err and _looks_like_missing_schema(str(last_err)):
            raise HTTPException(
                status_code=500,
                detail="DB not migrated: manuscripts schema incompatible",
            ) from last_err
        if last_err:
            raise last_err
        return None

    def _load_author_names(self, manuscript: dict[str, Any]) -> list[str]:
        names: list[str] = []

        raw_authors = manuscript.get("authors")
        if isinstance(raw_authors, list):
            for item in raw_authors:
                if isinstance(item, str) and item.strip():
                    names.append(item.strip())
                elif isinstance(item, dict):
                    full_name = str(item.get("full_name") or "").strip()
                    first_name = str(item.get("first_name") or item.get("firstName") or "").strip()
                    last_name = str(item.get("last_name") or item.get("lastName") or "").strip()
                    composed = " ".join([p for p in [first_name, last_name] if p]).strip()
                    if full_name:
                        names.append(full_name)
                    elif composed:
                        names.append(composed)

        if names:
            deduped: list[str] = []
            seen: set[str] = set()
            for n in names:
                key = n.lower().strip()
                if key and key not in seen:
                    seen.add(key)
                    deduped.append(n)
            if deduped:
                return deduped

        author_id = str(manuscript.get("author_id") or "").strip()
        if author_id:
            try:
                profile_resp = (
                    self.client.table("user_profiles")
                    .select("full_name")
                    .eq("id", author_id)
                    .single()
                    .execute()
                )
                profile = getattr(profile_resp, "data", None) or {}
                full_name = str(profile.get("full_name") or "").strip()
                if full_name:
                    return [full_name]
            except Exception:
                pass

        return ["Author"]

    def _load_journal_meta(self, journal_id: str | None) -> dict[str, Any]:
        if not journal_id:
            return {}
        try:
            resp = (
                self.client.table("journals")
                .select("id,title,issn")
                .eq("id", str(journal_id))
                .single()
                .execute()
            )
            return getattr(resp, "data", None) or {}
        except Exception:
            return {}

    def _build_public_article_url(self, article_id: str) -> str:
        origin = (os.environ.get("FRONTEND_ORIGIN") or "").strip().rstrip("/")
        if origin:
            return f"{origin}/articles/{article_id}"
        return f"/articles/{article_id}"

    def _build_crossref_article_data(self, manuscript: dict[str, Any], doi: str) -> dict[str, Any]:
        article_id = str(manuscript.get("id") or "")
        authors = self._load_author_names(manuscript)
        journal_meta = self._load_journal_meta(str(manuscript.get("journal_id") or "") or None)
        journal_title = str(journal_meta.get("title") or (self.config.journal_title if self.config else "ScholarFlow Journal"))

        publication_date = str(manuscript.get("published_at") or manuscript.get("created_at") or "")
        if publication_date.endswith("+00:00"):
            publication_date = publication_date.replace("+00:00", "Z")

        author_payload = [{"full_name": a} for a in authors]

        return {
            "id": article_id,
            "title": str(manuscript.get("title") or "Untitled"),
            "abstract": str(manuscript.get("abstract") or ""),
            "authors": author_payload,
            "publication_date": publication_date,
            "journal_title": journal_title,
            "doi": doi,
            "url": self._build_public_article_url(article_id),
        }

    def _create_batch_id(self, article_id: str) -> str:
        ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        short_id = "".join(ch for ch in article_id if ch.isalnum())[:8] or "article"
        return f"sf-{ts}-{short_id}"

    def _extract_crossref_batch_id(self, response_body: str) -> str | None:
        text = str(response_body or "")
        patterns = [
            r"(?i)batch[_\s-]*id\s*[:=]\s*([A-Za-z0-9._-]+)",
            r"(?i)<batch_id>([^<]+)</batch_id>",
            r"(?i)<doi_batch_id>([^<]+)</doi_batch_id>",
        ]
        for pat in patterns:
            matched = re.search(pat, text)
            if matched:
                return matched.group(1).strip()
        return None

    def _next_sequence_for_year(self, year: int) -> int:
        start = f"{year}-01-01T00:00:00+00:00"
        end = f"{year + 1}-01-01T00:00:00+00:00"
        try:
            resp = (
                self.client.table("doi_registrations")
                .select("id", count="exact")
                .gte("created_at", start)
                .lt("created_at", end)
                .limit(1)
                .execute()
            )
            count = getattr(resp, "count", None)
            if isinstance(count, int):
                return count + 1
            data = getattr(resp, "data", None) or []
            return len(data) + 1
        except Exception:
            # 中文注释: 计数失败时兜底时间戳，保证不会阻塞注册流程。
            return int(datetime.now(timezone.utc).timestamp()) % 100000

    def _log_audit(
        self,
        *,
        registration_id: str,
        action: str,
        request_payload: dict[str, Any] | None = None,
        response_status: int | None = None,
        response_body: str | None = None,
        error_details: str | None = None,
    ) -> None:
        row: dict[str, Any] = {
            "registration_id": registration_id,
            "action": action,
            "request_payload": request_payload or {},
            "response_status": response_status,
            "response_body": response_body,
            "error_details": error_details,
            "created_at": _now_iso(),
        }

        try:
            self.client.table("doi_audit_log").insert(row).execute()
        except Exception as e:
            if _looks_like_missing_schema(str(e)):
                print(f"[DOI] audit log table missing (ignored): {e}")
                return
            print(f"[DOI] audit insert failed (ignored): {e}")

    def _update_registration(self, registration_id: str, updates: dict[str, Any]) -> dict[str, Any]:
        payload = dict(updates)
        payload.setdefault("updated_at", _now_iso())
        resp = (
            self.client.table("doi_registrations")
            .update(payload)
            .eq("id", registration_id)
            .execute()
        )
        rows = getattr(resp, "data", None) or []
        if not rows:
            raise HTTPException(status_code=404, detail="DOI registration not found")
        return rows[0]

    def _ensure_pending_task(self, *, registration_id: str, priority: int = 0) -> dict[str, Any]:
        try:
            existing_resp = (
                self.client.table("doi_tasks")
                .select("*")
                .eq("registration_id", registration_id)
                .eq("task_type", DOITaskType.REGISTER.value)
                .in_(
                    "status",
                    [DOITaskStatus.PENDING.value, DOITaskStatus.PROCESSING.value],
                )
                .order("created_at", desc=True)
                .limit(1)
                .execute()
            )
            existing_rows = getattr(existing_resp, "data", None) or []
            if existing_rows:
                return existing_rows[0]

            now = _now_iso()
            insert_resp = (
                self.client.table("doi_tasks")
                .insert(
                    {
                        "registration_id": registration_id,
                        "task_type": DOITaskType.REGISTER.value,
                        "status": DOITaskStatus.PENDING.value,
                        "priority": int(priority),
                        "run_at": now,
                        "attempts": 0,
                        "max_attempts": 4,
                        "created_at": now,
                    }
                )
                .execute()
            )
            rows = getattr(insert_resp, "data", None) or []
            if not rows:
                raise HTTPException(status_code=500, detail="Failed to create DOI task")
            return rows[0]
        except HTTPException:
            raise
        except Exception as e:
            if _looks_like_missing_schema(str(e)):
                raise HTTPException(
                    status_code=500,
                    detail="DB not migrated: doi_tasks table missing",
                ) from e
            raise

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

        now = _now_iso()
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
            elif _looks_like_missing_schema(str(e)):
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
        now = _now_iso()
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
            if _looks_like_missing_schema(str(e)):
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
                    "last_error": _truncate(error_message),
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
                "last_error": _truncate(error_message),
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
                        "completed_at": _now_iso(),
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
                        "error": _truncate(str(e), 300),
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
            err = _truncate(str(e))
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
        now = _now_iso()
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
            if "doi" in str(e).lower() and _looks_like_missing_schema(str(e)):
                print(f"[DOI] manuscripts.doi column missing (ignored): {e}")
            else:
                print(f"[DOI] manuscripts.doi update failed (ignored): {e}")

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
            response_body=_truncate(response_body, 4000),
        )
        return self._to_registration_model(registered)
