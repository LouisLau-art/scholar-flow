from __future__ import annotations

import csv
from io import StringIO
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from typing import Any, Iterable, Literal
from uuid import UUID

from fastapi import HTTPException

from app.core.journal_scope import (
    get_user_scope_journal_ids,
    is_scope_enforcement_enabled,
)
from app.core.role_matrix import normalize_roles
from app.lib.api_client import supabase_admin
from app.models.manuscript import ManuscriptStatus, PreCheckStatus, normalize_status
from app.services.editorial_service import EditorialService
from app.services.editor_service_precheck import EditorServicePrecheckMixin


@dataclass(frozen=True)
class ProcessListFilters:
    """
    032: Process List 高级筛选参数（URL 驱动）。

    中文注释：
    - 这里做成“纯数据对象”，便于单测覆盖 query builder 的行为；
    - API 层负责把 Query 参数解析为此对象，再交给 service。
    """

    q: str | None = None
    statuses: list[str] | None = None
    journal_id: str | None = None
    editor_id: str | None = None
    owner_id: str | None = None
    manuscript_id: str | None = None
    overdue_only: bool = False


@dataclass(frozen=True)
class FinanceListFilters:
    """
    Finance 列表筛选参数。
    """

    status: Literal["all", "unpaid", "paid", "waived"] = "all"
    q: str | None = None
    page: int = 1
    page_size: int = 20
    sort_by: Literal["updated_at", "amount", "status"] = "updated_at"
    sort_order: Literal["asc", "desc"] = "desc"


def _is_uuid(value: str) -> bool:
    try:
        UUID(str(value))
        return True
    except Exception:
        return False


def _normalize_statuses(values: Iterable[str] | None) -> list[str] | None:
    if not values:
        return None
    normalized: list[str] = []
    for raw in values:
        n = normalize_status(raw)
        if n is None:
            raise HTTPException(status_code=422, detail=f"Invalid status: {raw}")
        normalized.append(n)
    # 去重但保持顺序
    out: list[str] = []
    seen: set[str] = set()
    for s in normalized:
        if s in seen:
            continue
        seen.add(s)
        out.append(s)
    return out or None


def _is_schema_drift_error(error_text: str) -> bool:
    """
    判断是否为“云端 schema 与代码不一致”导致的查询失败。

    中文注释:
    - 典型场景：列缺失、关系缺失、PostgREST schema cache 未刷新。
    - 这些错误应触发 fallback，而不是直接让 Process API 返回 500。
    """
    lowered = (error_text or "").lower()
    return (
        ("does not exist" in lowered and ("column" in lowered or "table" in lowered or "relation" in lowered))
        or "could not find the relationship" in lowered
        or ("schema cache" in lowered and "pgrst" in lowered)
        or "pgrst204" in lowered
    )


def apply_process_filters(query: Any, filters: ProcessListFilters) -> Any:
    """
    对 Supabase PostgREST Query 应用动态筛选（可单测）。

    支持：
    - status: 多选
    - journal/editor/owner: 精确匹配
    - manuscript_id: 精确匹配
    - q: 标题模糊搜索 + UUID 精确匹配
    """

    if filters.manuscript_id:
        query = query.eq("id", filters.manuscript_id)
    if filters.journal_id:
        query = query.eq("journal_id", filters.journal_id)
    if filters.owner_id:
        query = query.eq("owner_id", filters.owner_id)
    if filters.editor_id:
        query = query.eq("editor_id", filters.editor_id)

    statuses = _normalize_statuses(filters.statuses)
    if statuses:
        query = query.in_("status", statuses)

    q = (filters.q or "").strip()
    if q:
        if len(q) > 100:
            raise HTTPException(status_code=422, detail="q too long (max 100)")
        if _is_uuid(q):
            query = query.eq("id", q)
        else:
            # 中文注释：PostgREST 对 uuid 列做 ilike 兼容性不稳定；MVP 仅对 title 做模糊搜索。
            query = query.ilike("title", f"%{q}%")

    return query


class EditorService(EditorServicePrecheckMixin):
    """
    032: Process List 数据查询服务

    中文注释：
    - 读取使用 service_role（supabase_admin），兼容云端 RLS。
    - 仅做“读模型拼装”，不包含状态机写入逻辑（写入归 EditorialService）。
    """

    def __init__(self) -> None:
        self.client = supabase_admin
        self.editorial = EditorialService()

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def _apply_process_visibility_scope(
        self,
        *,
        rows: list[dict[str, Any]],
        viewer_user_id: str | None,
        viewer_roles: list[str] | None,
        scoped_journal_ids: set[str] | None = None,
        scope_enforcement_enabled: bool | None = None,
    ) -> list[dict[str, Any]]:
        """
        统一处理 Process/Intake 列表的角色可见范围。

        规则：
        - admin：不裁剪；
        - assistant_editor（且不具备 ME/EIC 全局角色）：仅看 `assistant_editor_id == 自己`；
        - scope enforcement 开启时（或角色为 ME/EIC），按 journal scopes 裁剪；
        - 若 scope 为空，返回空列表（fail-closed）；
        - enforcement 关闭时，保留现有可见行。
        """
        if not viewer_user_id or viewer_roles is None:
            return rows

        normalized_viewer_roles = normalize_roles(viewer_roles)
        if "admin" in normalized_viewer_roles:
            return rows

        has_global_process_scope = bool({"managing_editor", "editor_in_chief"} & normalized_viewer_roles)
        is_pure_assistant_editor = (
            "assistant_editor" in normalized_viewer_roles and not has_global_process_scope
        )

        out = rows
        if is_pure_assistant_editor:
            out = [
                row for row in out if str(row.get("assistant_editor_id") or "") == str(viewer_user_id)
            ]

        enforcement_enabled = bool(scope_enforcement_enabled or has_global_process_scope)
        if scope_enforcement_enabled is None:
            enforcement_enabled = bool(has_global_process_scope or is_scope_enforcement_enabled())

        if not enforcement_enabled:
            return out

        allowed_ids = scoped_journal_ids
        if allowed_ids is None:
            allowed_ids = get_user_scope_journal_ids(
                user_id=str(viewer_user_id),
                roles=list(normalized_viewer_roles),
            )
        if not allowed_ids:
            return []

        out = [
            row for row in out if str(row.get("journal_id") or "").strip() in allowed_ids
        ]
        return out

    def _build_process_query(self, *, filters: ProcessListFilters, select_clause: str):
        q = (
            self.client.table("manuscripts")
            .select(select_clause)
            .order("updated_at", desc=True)
            .order("created_at", desc=True)
        )
        return apply_process_filters(q, filters)

    def _list_process_rows_with_fallback(self, *, filters: ProcessListFilters) -> list[dict[str, Any]]:
        """
        兼容云端 schema 漂移的 Process 列表查询。

        中文注释:
        - 优先使用完整字段（含 pre_check_status / journals 关联）；
        - 若遇到缺列/缺关系，自动逐级降级 select；
        - 若筛选字段本身缺失（journal_id/editor_id/owner_id），自动移除该筛选并继续；
        - 保证返回结构稳定，不让前端因缺 key 崩溃。
        """
        select_variants = [
            "id,title,created_at,updated_at,status,pre_check_status,assistant_editor_id,owner_id,editor_id,journal_id,journals(title,slug)",
            "id,title,created_at,updated_at,status,assistant_editor_id,owner_id,editor_id,journal_id,journals(title,slug)",
            "id,title,created_at,updated_at,status,owner_id,editor_id,journal_id,journals(title,slug)",
            "id,title,created_at,updated_at,status,owner_id,editor_id,journal_id",
            "id,title,created_at,updated_at,status,journal_id",
            "id,title,created_at,updated_at,status",
        ]

        current_filters = filters
        dropped_filter_keys: set[str] = set()
        last_error: Exception | None = None
        idx = 0

        while idx < len(select_variants):
            select_clause = select_variants[idx]
            try:
                resp = self._build_process_query(filters=current_filters, select_clause=select_clause).execute()
                rows: list[dict[str, Any]] = getattr(resp, "data", None) or []
                for row in rows:
                    row.setdefault("pre_check_status", None)
                    row.setdefault("assistant_editor_id", None)
                    row.setdefault("owner_id", None)
                    row.setdefault("editor_id", None)
                    row.setdefault("journal_id", None)
                    row.setdefault("journals", None)
                return rows
            except HTTPException:
                raise
            except Exception as e:
                last_error = e
                lowered = str(e).lower()

                # 兼容：筛选字段缺失时自动去掉该筛选，避免整个列表 500
                if (
                    "manuscripts.journal_id" in lowered
                    and "does not exist" in lowered
                    and current_filters.journal_id
                    and "journal_id" not in dropped_filter_keys
                ):
                    current_filters = replace(current_filters, journal_id=None)
                    dropped_filter_keys.add("journal_id")
                    idx = 0
                    print("[Process] fallback: drop journal_id filter due to missing column")
                    continue

                if (
                    "manuscripts.editor_id" in lowered
                    and "does not exist" in lowered
                    and current_filters.editor_id
                    and "editor_id" not in dropped_filter_keys
                ):
                    current_filters = replace(current_filters, editor_id=None)
                    dropped_filter_keys.add("editor_id")
                    idx = 0
                    print("[Process] fallback: drop editor_id filter due to missing column")
                    continue

                if (
                    "manuscripts.owner_id" in lowered
                    and "does not exist" in lowered
                    and current_filters.owner_id
                    and "owner_id" not in dropped_filter_keys
                ):
                    current_filters = replace(current_filters, owner_id=None)
                    dropped_filter_keys.add("owner_id")
                    idx = 0
                    print("[Process] fallback: drop owner_id filter due to missing column")
                    continue

                if _is_schema_drift_error(lowered):
                    print(f"[Process] schema fallback level {idx + 1} failed: {e}")
                    idx += 1
                    continue

                raise

        if last_error:
            raise last_error
        return []

    def _safe_insert_transition_log(
        self,
        *,
        manuscript_id: str,
        from_status: str,
        to_status: str,
        changed_by: str | None,
        comment: str | None = None,
        payload: dict[str, Any] | None = None,
        created_at: str | None = None,
    ) -> None:
        """
        写入审计日志（失败降级，不阻断主流程）。

        中文注释：
        - 沿用项目“fail-open”策略：日志异常不影响业务主流程；
        - 尝试包含 payload；若列不存在或外键限制失败，则自动降级重试。
        """
        row: dict[str, Any] = {
            "manuscript_id": manuscript_id,
            "from_status": from_status,
            "to_status": to_status,
            "comment": comment,
            "changed_by": changed_by,
            "created_at": created_at or self._now(),
        }
        if payload is not None:
            row["payload"] = payload

        candidates: list[dict[str, Any]] = [dict(row)]
        # payload 可能未迁移
        if "payload" in row:
            fallback = dict(row)
            fallback.pop("payload", None)
            candidates.append(fallback)
        # changed_by 外键兼容
        if changed_by:
            degraded = dict(row)
            degraded["changed_by"] = None
            if payload is not None and isinstance(payload, dict):
                degraded["payload"] = {**payload, "changed_by_raw": changed_by}
            candidates.append(degraded)
            degraded_no_payload = dict(degraded)
            degraded_no_payload.pop("payload", None)
            candidates.append(degraded_no_payload)

        for cand in candidates:
            try:
                self.client.table("status_transition_logs").insert(cand).execute()
                return
            except Exception:
                continue

    def _map_precheck_row(self, row: dict[str, Any]) -> dict[str, Any]:
        """
        统一队列输出字段，便于前端列表/详情复用。
        """
        out = dict(row)
        pre = str(row.get("pre_check_status") or PreCheckStatus.INTAKE.value)
        pre = pre if pre in {PreCheckStatus.INTAKE.value, PreCheckStatus.TECHNICAL.value, PreCheckStatus.ACADEMIC.value} else PreCheckStatus.INTAKE.value
        current_role = (
            "managing_editor"
            if pre == PreCheckStatus.INTAKE.value
            else "assistant_editor"
            if pre == PreCheckStatus.TECHNICAL.value
            else "editor_in_chief"
        )
        out["pre_check_status"] = pre
        out["current_role"] = current_role

        ae_id = str(row.get("assistant_editor_id") or "")
        if ae_id:
            out["current_assignee"] = {"id": ae_id}
        else:
            out["current_assignee"] = None
        return out

    def _load_latest_precheck_intake_revision_logs(
        self,
        manuscript_ids: list[str],
    ) -> dict[str, dict[str, str]]:
        """
        读取“ME 技术退回”最近一条日志（用于 Intake 队列灰态占位展示）。

        中文注释:
        - 仅识别 payload.action == precheck_intake_revision；
        - 返回每篇稿件最近一条（created_at desc）；
        - 若审计表缺失/未迁移，降级为空，不影响主流程。
        """
        if not manuscript_ids:
            return {}

        try:
            resp = (
                self.client.table("status_transition_logs")
                .select("manuscript_id,created_at,comment,payload")
                .in_("manuscript_id", manuscript_ids)
                .order("created_at", desc=True)
                .execute()
            )
            rows = getattr(resp, "data", None) or []
        except Exception:
            return {}

        out: dict[str, dict[str, str]] = {}
        for row in rows:
            mid = str(row.get("manuscript_id") or "").strip()
            if not mid or mid in out:
                continue
            payload = row.get("payload") if isinstance(row.get("payload"), dict) else {}
            action = str(payload.get("action") or "").strip()
            if action != "precheck_intake_revision":
                continue
            out[mid] = {
                "created_at": str(row.get("created_at") or "").strip(),
                "comment": str(row.get("comment") or "").strip(),
            }
        return out

    def _load_precheck_timeline_index(self, manuscript_ids: list[str]) -> dict[str, dict[str, str]]:
        """
        从审计日志汇总 assigned_at / technical_completed_at / academic_completed_at。
        """
        if not manuscript_ids:
            return {}
        index: dict[str, dict[str, str]] = {}
        try:
            resp = (
                self.client.table("status_transition_logs")
                .select("manuscript_id,created_at,payload")
                .in_("manuscript_id", manuscript_ids)
                .order("created_at", desc=False)
                .execute()
            )
            rows = getattr(resp, "data", None) or []
        except Exception:
            rows = []

        for row in rows:
            manuscript_id = str(row.get("manuscript_id") or "")
            if not manuscript_id:
                continue
            payload = row.get("payload") if isinstance(row.get("payload"), dict) else {}
            action = str(payload.get("action") or "")
            created_at = str(row.get("created_at") or "")
            if not created_at:
                continue

            bucket = index.setdefault(manuscript_id, {})
            if action in {"precheck_assign_ae", "precheck_reassign_ae"}:
                bucket["assigned_at"] = created_at
            if action in {"precheck_technical_pass", "precheck_technical_revision", "precheck_technical_to_under_review"}:
                bucket["technical_completed_at"] = created_at
            if action in {"precheck_academic_to_review", "precheck_academic_to_decision"}:
                bucket["academic_completed_at"] = created_at
        return index

    def _enrich_precheck_rows(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        out = [self._map_precheck_row(r) for r in rows]
        ids = [str(r.get("id") or "") for r in out if r.get("id")]
        timeline_index = self._load_precheck_timeline_index(ids)
        assignee_ids = sorted(
            {
                str(r.get("assistant_editor_id") or "")
                for r in out
                if str(r.get("assistant_editor_id") or "")
            }
        )
        assignee_map: dict[str, dict[str, Any]] = {}
        if assignee_ids:
            try:
                resp = (
                    self.client.table("user_profiles")
                    .select("id,full_name,email")
                    .in_("id", assignee_ids)
                    .execute()
                )
                for row in (getattr(resp, "data", None) or []):
                    rid = str(row.get("id") or "")
                    if rid:
                        assignee_map[rid] = row
            except Exception:
                assignee_map = {}

        for row in out:
            manuscript_id = str(row.get("id") or "")
            stamp = timeline_index.get(manuscript_id, {})
            row["assigned_at"] = stamp.get("assigned_at")
            row["technical_completed_at"] = stamp.get("technical_completed_at")
            row["academic_completed_at"] = stamp.get("academic_completed_at")
            ae_id = str(row.get("assistant_editor_id") or "")
            if ae_id:
                prof = assignee_map.get(ae_id) or {}
                row["current_assignee"] = {
                    "id": ae_id,
                    "full_name": prof.get("full_name"),
                    "email": prof.get("email"),
                }
            else:
                row["current_assignee"] = None
        return out

    def _get_manuscript(self, manuscript_id: str) -> dict[str, Any]:
        try:
            resp = (
                self.client.table("manuscripts")
                .select("id,status,pre_check_status,assistant_editor_id,updated_at")
                .eq("id", manuscript_id)
                .single()
                .execute()
            )
        except Exception as e:
            raise HTTPException(status_code=404, detail="Manuscript not found") from e
        row = getattr(resp, "data", None) or None
        if not row:
            raise HTTPException(status_code=404, detail="Manuscript not found")
        return row

    def _normalize_precheck_status(self, value: str | None) -> str:
        raw = str(value or "").strip().lower()
        if raw in {PreCheckStatus.INTAKE.value, PreCheckStatus.TECHNICAL.value, PreCheckStatus.ACADEMIC.value}:
            return raw
        return PreCheckStatus.INTAKE.value

    def _attach_overdue_snapshot(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Feature 045:
        在 Process 列表行上补充任务逾期快照（读时聚合，不做冗余存储）。
        """
        if not rows:
            return rows

        manuscript_ids = [str(r.get("id") or "") for r in rows if r.get("id")]
        if not manuscript_ids:
            return rows

        overdue_count: dict[str, int] = {mid: 0 for mid in manuscript_ids}
        nearest_due: dict[str, str] = {}
        now = datetime.now(timezone.utc)

        try:
            resp = (
                self.client.table("internal_tasks")
                .select("manuscript_id,status,due_at")
                .in_("manuscript_id", manuscript_ids)
                .neq("status", "done")
                .execute()
            )
            task_rows = getattr(resp, "data", None) or []
        except Exception as e:
            # 中文注释: 云端未迁移 internal_tasks 时，Process 列表不应 500。
            # 统一按“无逾期数据”降级，并保留日志便于排障。
            print(f"[Process] load internal_tasks failed (ignored): {e}")
            task_rows = []

        for task in task_rows:
            manuscript_id = str(task.get("manuscript_id") or "")
            due_raw = str(task.get("due_at") or "")
            if not manuscript_id or not due_raw:
                continue
            try:
                due_at = datetime.fromisoformat(due_raw.replace("Z", "+00:00")).astimezone(timezone.utc)
            except Exception:
                continue
            if due_at < now:
                overdue_count[manuscript_id] = overdue_count.get(manuscript_id, 0) + 1

            nearest = nearest_due.get(manuscript_id)
            if nearest:
                try:
                    nearest_dt = datetime.fromisoformat(str(nearest).replace("Z", "+00:00")).astimezone(timezone.utc)
                except Exception:
                    nearest_dt = None
            else:
                nearest_dt = None
            if nearest_dt is None or due_at < nearest_dt:
                nearest_due[manuscript_id] = due_at.isoformat()

        for row in rows:
            mid = str(row.get("id") or "")
            count = int(overdue_count.get(mid, 0))
            row["is_overdue"] = count > 0
            row["overdue_tasks_count"] = count
            row["nearest_due_at"] = nearest_due.get(mid)
        return rows

    # --- Feature 046: Finance Invoices Sync ---

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

    def _load_finance_source_rows(self) -> list[dict[str, Any]]:
        select_clause = (
            "id,manuscript_id,amount,status,confirmed_at,invoice_number,created_at,"
            "manuscripts(id,title,author_id,updated_at,invoice_metadata)"
        )
        query = (
            self.client.table("invoices")
            .select(select_clause)
            .order("created_at", desc=True)
            .range(0, 4999)
        )
        try:
            if hasattr(query, "is_"):
                resp = query.is_("deleted_at", "null").execute()
            else:
                resp = query.execute()
        except Exception as e:
            # 中文注释: 云端可能未同步 deleted_at 字段，降级为不过滤 deleted_at。
            lowered = str(e).lower()
            if "deleted_at" in lowered and ("column" in lowered or "schema cache" in lowered):
                resp = (
                    self.client.table("invoices")
                    .select(select_clause)
                    .order("created_at", desc=True)
                    .range(0, 4999)
                    .execute()
                )
            else:
                raise
        return getattr(resp, "data", None) or []

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

    def list_finance_invoices(self, *, filters: FinanceListFilters) -> dict[str, Any]:
        page = max(int(filters.page or 1), 1)
        page_size = max(min(int(filters.page_size or 20), 100), 1)
        snapshot_at = self._now()

        source_rows = self._load_finance_source_rows()
        mapped_rows = self._build_finance_rows(source_rows)
        filtered = self._filter_and_sort_finance_rows(mapped_rows, filters=filters)

        total = len(filtered)
        start = (page - 1) * page_size
        end = start + page_size
        paged = filtered[start:end]

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
        source_rows = self._load_finance_source_rows()
        mapped_rows = self._build_finance_rows(source_rows)
        filtered = self._filter_and_sort_finance_rows(mapped_rows, filters=filters)

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

    def list_manuscripts_process(
        self,
        *,
        filters: ProcessListFilters,
        viewer_user_id: str | None = None,
        viewer_roles: list[str] | None = None,
        scoped_journal_ids: set[str] | None = None,
        scope_enforcement_enabled: bool | None = None,
    ) -> list[dict[str, Any]]:
        rows = self._list_process_rows_with_fallback(filters=filters)

        profile_ids: set[str] = set()
        for r in rows:
            if r.get("owner_id"):
                profile_ids.add(str(r["owner_id"]))
            if r.get("editor_id"):
                profile_ids.add(str(r["editor_id"]))

        profiles_map: dict[str, dict[str, Any]] = {}
        if profile_ids:
            try:
                prof = (
                    self.client.table("user_profiles")
                    .select("id,email,full_name,roles")
                    .in_("id", sorted(profile_ids))
                    .execute()
                )
                for p in (getattr(prof, "data", None) or []):
                    pid = str(p.get("id") or "")
                    if pid:
                        profiles_map[pid] = p
            except Exception as e:
                print(f"[Process] load user_profiles failed (ignored): {e}")

        for r in rows:
            oid = str(r.get("owner_id") or "")
            eid = str(r.get("editor_id") or "")
            r["owner"] = (
                {
                    "id": oid,
                    "full_name": (profiles_map.get(oid) or {}).get("full_name"),
                    "email": (profiles_map.get(oid) or {}).get("email"),
                }
                if oid
                else None
            )
            r["editor"] = (
                {
                    "id": eid,
                    "full_name": (profiles_map.get(eid) or {}).get("full_name"),
                    "email": (profiles_map.get(eid) or {}).get("email"),
                }
                if eid
                else None
            )

        precheck_rows = [
            r for r in rows if normalize_status(str(r.get("status") or "")) == ManuscriptStatus.PRE_CHECK.value
        ]
        precheck_enriched = self._enrich_precheck_rows(precheck_rows)
        by_id = {str(r.get("id") or ""): r for r in precheck_enriched}
        for row in rows:
            rid = str(row.get("id") or "")
            if rid and rid in by_id:
                enriched = by_id[rid]
                row["pre_check_status"] = enriched.get("pre_check_status")
                row["current_role"] = enriched.get("current_role")
                row["current_assignee"] = enriched.get("current_assignee")
                row["assigned_at"] = enriched.get("assigned_at")
                row["technical_completed_at"] = enriched.get("technical_completed_at")
                row["academic_completed_at"] = enriched.get("academic_completed_at")

        rows = self._attach_overdue_snapshot(rows)
        if filters.overdue_only:
            rows = [row for row in rows if bool(row.get("is_overdue"))]

        rows = self._apply_process_visibility_scope(
            rows=rows,
            viewer_user_id=viewer_user_id,
            viewer_roles=viewer_roles,
            scoped_journal_ids=scoped_journal_ids,
            scope_enforcement_enabled=scope_enforcement_enabled,
        )
        return rows

    # --- Feature 038: Pre-check Role Workflow (ME -> AE -> EIC) ---
