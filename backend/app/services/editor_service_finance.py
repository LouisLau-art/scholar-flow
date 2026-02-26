from __future__ import annotations

import csv
from dataclasses import replace
from datetime import datetime, timezone
from io import StringIO
from typing import TYPE_CHECKING, Any, Literal

from fastapi import HTTPException

if TYPE_CHECKING:
    from app.services.editor_service import FinanceListFilters


class EditorServiceFinanceMixin:
    """Editor 财务视图相关逻辑（Feature 046）。"""

    @staticmethod
    def _to_float(value: Any) -> float:
        try:
            return float(value)
        except Exception:
            return 0.0

    @staticmethod
    def _to_iso_datetime(value: Any, *, fallback: str | None = None) -> str:
        raw = str(value or "").strip()
        if raw:
            return raw
        return fallback or datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _parse_iso(value: str | None) -> datetime:
        raw = str(value or "").strip()
        if not raw:
            return datetime.fromtimestamp(0, tz=timezone.utc)
        try:
            return datetime.fromisoformat(raw.replace("Z", "+00:00")).astimezone(timezone.utc)
        except Exception:
            return datetime.fromtimestamp(0, tz=timezone.utc)

    @staticmethod
    def _effective_status(*, raw_status: str | None, amount: float) -> Literal["unpaid", "paid", "waived"]:
        status = str(raw_status or "").strip().lower()
        if amount <= 0 or status == "waived":
            return "waived"
        if status == "paid":
            return "paid"
        return "unpaid"

    def _load_finance_source_rows(
        self,
        *,
        filters: FinanceListFilters,
        export_mode: bool,
    ) -> tuple[list[dict[str, Any]], int]:
        select_clause = (
            "id,manuscript_id,amount,status,confirmed_at,invoice_number,created_at,"
            "manuscripts(id,title,author_id,updated_at,invoice_metadata)"
        )
        page = max(int(filters.page or 1), 1)
        page_size = max(min(int(filters.page_size or 20), 100), 1)
        offset = (page - 1) * page_size

        query = self.client.table("invoices").select(select_clause, count="exact")

        status = str(filters.status or "all").strip().lower()
        if status not in {"all", "unpaid", "paid", "waived"}:
            raise HTTPException(status_code=422, detail="Invalid status filter")
        if status == "paid":
            query = query.eq("status", "paid").gt("amount", 0)
        elif status == "waived":
            query = query.or_("status.eq.waived,amount.lte.0")
        elif status == "unpaid":
            query = query.gt("amount", 0).neq("status", "paid").neq("status", "waived")

        sort_by = str(filters.sort_by or "updated_at").strip().lower()
        sort_order = str(filters.sort_order or "desc").strip().lower()
        if sort_by not in {"updated_at", "amount", "status"}:
            raise HTTPException(status_code=422, detail="Invalid sort_by")
        if sort_order not in {"asc", "desc"}:
            raise HTTPException(status_code=422, detail="Invalid sort_order")
        desc = sort_order == "desc"
        if sort_by == "amount":
            query = query.order("amount", desc=desc).order("created_at", desc=True)
        elif sort_by == "status":
            query = query.order("status", desc=desc).order("created_at", desc=True)
        else:
            # 中文注释: updated_at 对 invoices 不稳定，统一退化为 created_at 排序以便走索引。
            query = query.order("created_at", desc=desc)

        if not export_mode:
            query = query.range(offset, offset + page_size - 1)
        resp = query.execute()
        return (getattr(resp, "data", None) or [], int(getattr(resp, "count", None) or 0))

    def _build_finance_rows(self, source_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        author_ids: set[str] = set()
        manuscripts: list[dict[str, Any]] = []
        for row in source_rows:
            ms = row.get("manuscripts")
            if isinstance(ms, list):
                ms = ms[0] if ms else {}
            if not isinstance(ms, dict):
                ms = {}
            manuscripts.append(ms)
            aid = str(ms.get("author_id") or "").strip()
            if aid:
                author_ids.add(aid)

        author_map: dict[str, dict[str, Any]] = {}
        if author_ids:
            try:
                resp = (
                    self.client.table("user_profiles")
                    .select("id,full_name,email")
                    .in_("id", sorted(author_ids))
                    .execute()
                )
                for row in (getattr(resp, "data", None) or []):
                    rid = str(row.get("id") or "").strip()
                    if rid:
                        author_map[rid] = row
            except Exception as e:
                print(f"[Finance] load author profiles failed (ignored): {e}")

        out: list[dict[str, Any]] = []
        for idx, row in enumerate(source_rows):
            ms = manuscripts[idx] if idx < len(manuscripts) else {}

            amount = self._to_float(row.get("amount"))
            raw_status = str(row.get("status") or "").strip().lower() or "unpaid"
            effective_status = self._effective_status(raw_status=raw_status, amount=amount)

            invoice_meta = ms.get("invoice_metadata") if isinstance(ms.get("invoice_metadata"), dict) else {}
            authors = str((invoice_meta or {}).get("authors") or "").strip()
            if not authors:
                author_id = str(ms.get("author_id") or "").strip()
                profile = author_map.get(author_id) or {}
                authors = str(profile.get("full_name") or "").strip() or "Author"

            confirmed_at = str(row.get("confirmed_at") or "").strip() or None
            updated_at = self._to_iso_datetime(
                confirmed_at or ms.get("updated_at") or row.get("created_at"),
                fallback=self._now(),
            )

            manuscript_title = str(ms.get("title") or "").strip() or "Untitled Manuscript"
            manuscript_id = str(row.get("manuscript_id") or "").strip()
            if not manuscript_id:
                # 中文注释: 缺失关键关联时跳过该行，避免污染财务列表。
                continue

            out.append(
                {
                    "invoice_id": str(row.get("id") or ""),
                    "manuscript_id": manuscript_id,
                    "invoice_number": str(row.get("invoice_number") or "").strip() or None,
                    "manuscript_title": manuscript_title,
                    "authors": authors,
                    "amount": amount,
                    "currency": "USD",
                    "raw_status": raw_status,
                    "effective_status": effective_status,
                    "confirmed_at": confirmed_at,
                    "updated_at": updated_at,
                    "payment_gate_blocked": bool(amount > 0 and effective_status not in {"paid", "waived"}),
                }
            )
        return out

    def _filter_and_sort_finance_rows(
        self,
        rows: list[dict[str, Any]],
        *,
        filters: FinanceListFilters,
    ) -> list[dict[str, Any]]:
        out = list(rows)

        status = str(filters.status or "all").strip().lower()
        if status not in {"all", "unpaid", "paid", "waived"}:
            raise HTTPException(status_code=422, detail="Invalid status filter")
        if status != "all":
            out = [r for r in out if str(r.get("effective_status") or "") == status]

        q = str(filters.q or "").strip().lower()
        if len(q) > 100:
            raise HTTPException(status_code=422, detail="q too long (max 100)")
        if q:
            out = [
                r
                for r in out
                if q in str(r.get("invoice_number") or "").lower() or q in str(r.get("manuscript_title") or "").lower()
            ]

        sort_by = str(filters.sort_by or "updated_at").strip().lower()
        sort_order = str(filters.sort_order or "desc").strip().lower()
        if sort_by not in {"updated_at", "amount", "status"}:
            raise HTTPException(status_code=422, detail="Invalid sort_by")
        if sort_order not in {"asc", "desc"}:
            raise HTTPException(status_code=422, detail="Invalid sort_order")
        reverse = sort_order == "desc"

        if sort_by == "amount":
            out.sort(key=lambda r: self._to_float(r.get("amount")), reverse=reverse)
        elif sort_by == "status":
            out.sort(key=lambda r: str(r.get("effective_status") or ""), reverse=reverse)
        else:
            out.sort(key=lambda r: self._parse_iso(str(r.get("updated_at") or "")).timestamp(), reverse=reverse)
        return out

    def _apply_finance_keyword_filter(
        self,
        rows: list[dict[str, Any]],
        *,
        keyword: str | None,
    ) -> list[dict[str, Any]]:
        q = str(keyword or "").strip().lower()
        if len(q) > 100:
            raise HTTPException(status_code=422, detail="q too long (max 100)")
        if not q:
            return rows
        return [
            row
            for row in rows
            if q in str(row.get("invoice_number") or "").lower()
            or q in str(row.get("manuscript_title") or "").lower()
        ]

    def list_finance_invoices(self, *, filters: FinanceListFilters) -> dict[str, Any]:
        page = max(int(filters.page or 1), 1)
        page_size = max(min(int(filters.page_size or 20), 100), 1)
        snapshot_at = self._now()
        keyword = str(filters.q or "").strip()
        if keyword:
            source_rows, _ = self._load_finance_source_rows(
                filters=replace(filters, q=None),
                export_mode=True,
            )
            rows = self._build_finance_rows(source_rows)
            filtered = self._apply_finance_keyword_filter(rows, keyword=keyword)
            total = len(filtered)
            start = (page - 1) * page_size
            end = start + page_size
            paged = filtered[start:end]
        else:
            source_rows, total = self._load_finance_source_rows(filters=filters, export_mode=False)
            paged = self._build_finance_rows(source_rows)

        return {
            "rows": paged,
            "meta": {
                "page": page,
                "page_size": page_size,
                "total": total,
                "status_filter": filters.status,
                "snapshot_at": snapshot_at,
                "empty": total == 0,
            },
        }

    def export_finance_invoices_csv(self, *, filters: FinanceListFilters) -> dict[str, Any]:
        snapshot_at = self._now()
        keyword = str(filters.q or "").strip()
        source_rows, _total = self._load_finance_source_rows(
            filters=replace(filters, q=None) if keyword else filters,
            export_mode=True,
        )
        filtered = self._apply_finance_keyword_filter(
            self._build_finance_rows(source_rows),
            keyword=keyword,
        )

        buf = StringIO()
        fieldnames = [
            "invoice_id",
            "manuscript_id",
            "invoice_number",
            "manuscript_title",
            "authors",
            "amount",
            "currency",
            "raw_status",
            "effective_status",
            "confirmed_at",
            "updated_at",
        ]
        writer = csv.DictWriter(buf, fieldnames=fieldnames)
        writer.writeheader()
        for row in filtered:
            writer.writerow({k: row.get(k) for k in fieldnames})

        return {
            "csv_text": buf.getvalue(),
            "snapshot_at": snapshot_at,
            "row_count": len(filtered),
            "empty": len(filtered) == 0,
        }
