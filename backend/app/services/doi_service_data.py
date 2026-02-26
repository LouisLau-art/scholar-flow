from __future__ import annotations

import os
import re
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import HTTPException

from app.models.doi import (
    DOIRegistration,
    DOIRegistrationStatus,
    DOITask,
    DOITaskStatus,
    DOITaskType,
)
from app.services.doi_service_common import (
    logger,
    looks_like_missing_schema,
    looks_like_single_no_rows,
    now_iso,
)


class DOIServiceDataMixin:
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
            if looks_like_single_no_rows(str(e)):
                return None
            if looks_like_missing_schema(str(e)):
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
            if looks_like_single_no_rows(str(e)):
                return None
            if looks_like_missing_schema(str(e)):
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
                if looks_like_single_no_rows(str(e)):
                    return None
                last_err = e
                continue

        if last_err and looks_like_missing_schema(str(last_err)):
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
            "created_at": now_iso(),
        }

        try:
            self.client.table("doi_audit_log").insert(row).execute()
        except Exception as e:
            if looks_like_missing_schema(str(e)):
                logger.warning("[DOI] audit log table missing (ignored): %s", e)
                return
            logger.warning("[DOI] audit insert failed (ignored): %s", e)

    def _update_registration(self, registration_id: str, updates: dict[str, Any]) -> dict[str, Any]:
        payload = dict(updates)
        payload.setdefault("updated_at", now_iso())
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

            now = now_iso()
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
            if looks_like_missing_schema(str(e)):
                raise HTTPException(
                    status_code=500,
                    detail="DB not migrated: doi_tasks table missing",
                ) from e
            raise
