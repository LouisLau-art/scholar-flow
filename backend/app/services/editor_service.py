from __future__ import annotations

import csv
from io import StringIO
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from typing import Any, Iterable, Literal
from uuid import UUID

from fastapi import HTTPException

from app.core.journal_scope import (
    filter_rows_by_journal_scope,
    get_user_scope_journal_ids,
    is_scope_enforcement_enabled,
)
from app.core.role_matrix import normalize_roles
from app.lib.api_client import supabase_admin
from app.models.manuscript import ManuscriptStatus, PreCheckStatus, normalize_status
from app.services.editorial_service import EditorialService


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


class EditorService:
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
    ) -> list[dict[str, Any]]:
        """
        统一处理 Process/Intake 列表的角色可见范围。

        规则：
        - admin：不裁剪；
        - assistant_editor（且不具备 ME/EIC 全局角色）：仅看 `assistant_editor_id == 自己`；
        - managing_editor / editor_in_chief：
          若已配置 journal scopes，则按 scope 裁剪；
          若 scope 为空，返回空列表（fail-closed）；
        - 其余角色沿用现有灰度开关逻辑（filter_rows_by_journal_scope）。
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

        # 非 admin 的 ME/EIC：默认按已配置 scope 裁剪（即使灰度开关关闭也生效）。
        if has_global_process_scope:
            scoped_journal_ids = get_user_scope_journal_ids(
                user_id=str(viewer_user_id),
                roles=list(normalized_viewer_roles),
            )
            if scoped_journal_ids:
                out = [
                    row for row in out if str(row.get("journal_id") or "").strip() in scoped_journal_ids
                ]
            else:
                out = []

        # 其余角色继续走现有灰度策略，兼容旧环境。
        out = filter_rows_by_journal_scope(
            rows=out,
            user_id=str(viewer_user_id),
            roles=list(normalized_viewer_roles),
            journal_key="journal_id",
            allow_admin_bypass=True,
        )
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
        )
        return rows

    # --- Feature 038: Pre-check Role Workflow (ME -> AE -> EIC) ---

    def get_intake_queue(
        self,
        page: int = 1,
        page_size: int = 20,
        *,
        q: str | None = None,
        overdue_only: bool = False,
        viewer_user_id: str | None = None,
        viewer_roles: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """
        ME Intake Queue:
        - Active: status=pre_check & pre_check_status=intake
        - Passive placeholder: status=minor_revision 且来源于 precheck_intake_revision（等待作者 resubmit）
        """
        selects = [
            "id,title,created_at,updated_at,status,pre_check_status,assistant_editor_id,owner_id,author_id,journal_id,journals(title,slug)",
            "id,title,created_at,updated_at,status,pre_check_status,assistant_editor_id,owner_id,author_id,journal_id",
            "id,title,created_at,updated_at,status,pre_check_status,assistant_editor_id,owner_id,author_id",
        ]
        fetch_end = max(page * page_size - 1, page_size - 1)

        active_rows: list[dict[str, Any]] = []
        active_last_error: Exception | None = None
        for select_clause in selects:
            try:
                query = (
                    self.client.table("manuscripts")
                    .select(select_clause)
                    .eq("status", ManuscriptStatus.PRE_CHECK.value)
                    .or_(f"pre_check_status.eq.{PreCheckStatus.INTAKE.value},pre_check_status.is.null")
                    .order("updated_at", desc=True)
                    .order("created_at", desc=True)
                    .range(0, fetch_end)
                )
                resp = query.execute()
                active_rows = getattr(resp, "data", None) or []
                break
            except Exception as e:
                active_last_error = e
                lowered = str(e).lower()
                if "journals" in lowered or "schema cache" in lowered or "pgrst" in lowered:
                    continue
                raise
        if not active_rows and active_last_error:
            # 若因 schema 漂移导致多次降级仍失败，则抛出原始异常便于定位。
            # 这里仅在 rows 为空且确实经历过异常时触发。
            lowered = str(active_last_error).lower()
            if "schema cache" in lowered or "could not find" in lowered:
                raise active_last_error

        waiting_rows_candidates: list[dict[str, Any]] = []
        waiting_last_error: Exception | None = None
        for select_clause in selects:
            try:
                query = (
                    self.client.table("manuscripts")
                    .select(select_clause)
                    .eq("status", ManuscriptStatus.MINOR_REVISION.value)
                    .order("updated_at", desc=True)
                    .order("created_at", desc=True)
                    .range(0, fetch_end)
                )
                resp = query.execute()
                waiting_rows_candidates = getattr(resp, "data", None) or []
                break
            except Exception as e:
                waiting_last_error = e
                lowered = str(e).lower()
                if "journals" in lowered or "schema cache" in lowered or "pgrst" in lowered:
                    continue
                raise
        if not waiting_rows_candidates and waiting_last_error:
            lowered = str(waiting_last_error).lower()
            if "schema cache" in lowered or "could not find" in lowered:
                # 中文注释: “灰态占位”不可用时降级为仅返回 active intake，不阻断主流程。
                waiting_rows_candidates = []

        # Intake 列表不需要加载完整 pre-check 时间线，避免每次刷新多打一条审计日志聚合查询。
        active_out = [self._map_precheck_row(r) for r in active_rows]
        for row in active_out:
            row["intake_actionable"] = True
            row["waiting_resubmit"] = False
            row["waiting_resubmit_at"] = None
            row["waiting_resubmit_reason"] = None

        waiting_ids = [
            str(row.get("id") or "").strip()
            for row in waiting_rows_candidates
            if str(row.get("id") or "").strip()
        ]
        waiting_reason_map = self._load_latest_precheck_intake_revision_logs(waiting_ids)
        waiting_out: list[dict[str, Any]] = []
        for row in waiting_rows_candidates:
            mid = str(row.get("id") or "").strip()
            reason_meta = waiting_reason_map.get(mid)
            if not mid or not reason_meta:
                continue
            out_row = dict(row)
            out_row["pre_check_status"] = "awaiting_resubmit"
            out_row["current_role"] = "author"
            out_row["current_assignee"] = None
            out_row["intake_actionable"] = False
            out_row["waiting_resubmit"] = True
            out_row["waiting_resubmit_at"] = reason_meta.get("created_at")
            out_row["waiting_resubmit_reason"] = reason_meta.get("comment")
            waiting_out.append(out_row)

        out = [*active_out, *waiting_out]

        # 补齐 owner/author 展示字段（full_name/email/affiliation），用于 Intake 决策信息补全。
        profile_ids = sorted(
            {
                str(pid)
                for row in out
                for pid in (row.get("owner_id"), row.get("author_id"))
                if str(pid or "").strip()
            }
        )
        profile_map: dict[str, dict[str, Any]] = {}
        if profile_ids:
            try:
                prof = (
                    self.client.table("user_profiles")
                    .select("id,full_name,email,affiliation")
                    .in_("id", profile_ids)
                    .execute()
                )
                for p in (getattr(prof, "data", None) or []):
                    pid = str(p.get("id") or "")
                    if pid:
                        profile_map[pid] = p
            except Exception as e:
                print(f"[Intake] load owner/author profiles failed (ignored): {e}")

        for row in out:
            oid = str(row.get("owner_id") or "")
            aid = str(row.get("author_id") or "")
            row["owner"] = (
                {
                    "id": oid,
                    "full_name": (profile_map.get(oid) or {}).get("full_name"),
                    "email": (profile_map.get(oid) or {}).get("email"),
                }
                if oid
                else None
            )
            row["author"] = (
                {
                    "id": aid,
                    "full_name": (profile_map.get(aid) or {}).get("full_name"),
                    "email": (profile_map.get(aid) or {}).get("email"),
                    "affiliation": (profile_map.get(aid) or {}).get("affiliation"),
                }
                if aid
                else None
            )
            journal = row.get("journals")
            if isinstance(journal, list):
                row["journal"] = journal[0] if journal else None
            elif isinstance(journal, dict):
                row["journal"] = journal
            else:
                row["journal"] = None

        now = datetime.now(timezone.utc)
        for row in out:
            if bool(row.get("waiting_resubmit")):
                row["intake_elapsed_hours"] = None
                row["is_overdue"] = False
                row["intake_priority"] = "normal"
                continue
            created_raw = str(row.get("created_at") or "")
            created_at: datetime | None = None
            if created_raw:
                try:
                    created_at = datetime.fromisoformat(created_raw.replace("Z", "+00:00")).astimezone(timezone.utc)
                except Exception:
                    created_at = None
            if created_at is None:
                row["intake_elapsed_hours"] = None
                row["is_overdue"] = False
                row["intake_priority"] = "normal"
            else:
                elapsed_hours = max(0, int((now - created_at).total_seconds() // 3600))
                is_overdue = elapsed_hours >= 48
                row["intake_elapsed_hours"] = elapsed_hours
                row["is_overdue"] = is_overdue
                row["intake_priority"] = "high" if is_overdue else "normal"

        keyword = str(q or "").strip().lower()
        if keyword:
            out = [
                row
                for row in out
                if keyword in str(row.get("title") or "").lower()
                or keyword in str(row.get("id") or "").lower()
                or keyword in str(((row.get("owner") or {}).get("full_name") or "")).lower()
                or keyword in str(((row.get("author") or {}).get("full_name") or "")).lower()
                or keyword in str(((row.get("journal") or {}).get("title") or "")).lower()
                or keyword in str(row.get("waiting_resubmit_reason") or "").lower()
            ]

        if overdue_only:
            out = [row for row in out if bool(row.get("is_overdue"))]

        out = self._apply_process_visibility_scope(
            rows=out,
            viewer_user_id=viewer_user_id,
            viewer_roles=viewer_roles,
        )

        # 按 updated_at/created_at 全局排序后再分页，避免 active/passive 合并后顺序错乱。
        def _sort_key(item: dict[str, Any]) -> tuple[str, str]:
            updated = str(item.get("updated_at") or "")
            created = str(item.get("created_at") or "")
            return (updated, created)

        out.sort(key=_sort_key, reverse=True)
        start = max((page - 1) * page_size, 0)
        end = start + page_size
        return out[start:end]

    def assign_ae(
        self,
        manuscript_id: UUID,
        ae_id: UUID,
        current_user_id: UUID,
        *,
        owner_id: UUID | None = None,
        start_external_review: bool = False,
        bind_owner_if_empty: bool = False,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        """
        Assign/Reassign AE with state guard + audit trail.
        """
        manuscript_id_str = str(manuscript_id)
        ae_id_str = str(ae_id)
        actor = str(current_user_id)
        now = self._now()

        ms = self._get_manuscript(manuscript_id_str)
        status = normalize_status(str(ms.get("status") or ""))
        pre = self._normalize_precheck_status(ms.get("pre_check_status"))
        ae_before = str(ms.get("assistant_editor_id") or "")
        owner_before = str(ms.get("owner_id") or "")

        if status != ManuscriptStatus.PRE_CHECK.value:
            raise HTTPException(status_code=400, detail="AE assignment only allowed in pre_check")
        if pre not in {PreCheckStatus.INTAKE.value, PreCheckStatus.TECHNICAL.value}:
            raise HTTPException(status_code=409, detail=f"Invalid pre-check stage for assignment: {pre}")
        if pre == PreCheckStatus.TECHNICAL.value and ae_before == ae_id_str:
            # 幂等：同一 AE 重复分派
            out = dict(ms)
            out["pre_check_status"] = pre
            out["assistant_editor_id"] = ae_id_str
            out["updated_at"] = now
            return self._map_precheck_row(out)

        action = "precheck_reassign_ae" if pre == PreCheckStatus.TECHNICAL.value and ae_before else "precheck_assign_ae"
        data = {
            "assistant_editor_id": ae_id_str,
            "pre_check_status": PreCheckStatus.TECHNICAL.value,
            "updated_at": now,
        }
        owner_override = str(owner_id or "").strip()
        if owner_override:
            # 中文注释:
            # - ME 在 Intake Queue 可一次性分配 AE + Owner；
            # - Owner 必须是内部员工（admin/managing_editor/owner），避免外键/越权问题。
            try:
                from app.services.owner_binding_service import validate_internal_owner_id
                validate_internal_owner_id(UUID(owner_override))
            except ValueError as e:
                raise HTTPException(status_code=400, detail=str(e)) from e
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Invalid owner_id: {e}") from e
            data["owner_id"] = owner_override
        elif bind_owner_if_empty and not owner_before:
            # 中文注释:
            # - Intake 一键分配场景下，若 owner 为空可自动兜底绑定当前 ME；
            # - 避免稿件离开 Intake 后由于 owner 为空造成后续权限/协作信息缺失。
            data["owner_id"] = actor
        # 条件更新，避免并发覆盖
        q = (
            self.client.table("manuscripts")
            .update(data)
            .eq("id", manuscript_id_str)
            .eq("status", ManuscriptStatus.PRE_CHECK.value)
        )
        if pre == PreCheckStatus.INTAKE.value:
            q = q.or_("pre_check_status.eq.intake,pre_check_status.is.null")
        else:
            q = q.eq("pre_check_status", PreCheckStatus.TECHNICAL.value)
        resp = q.execute()
        rows = getattr(resp, "data", None) or []
        if not rows:
            latest = self._get_manuscript(manuscript_id_str)
            if (
                normalize_status(str(latest.get("status") or "")) == ManuscriptStatus.PRE_CHECK.value
                and self._normalize_precheck_status(latest.get("pre_check_status")) == PreCheckStatus.TECHNICAL.value
                and str(latest.get("assistant_editor_id") or "") == ae_id_str
            ):
                return self._map_precheck_row(latest)
            raise HTTPException(status_code=409, detail="Assignment conflict: manuscript state changed")

        updated = rows[0]
        owner_after = (data.get("owner_id") if data.get("owner_id") else (owner_before or None))
        self._safe_insert_transition_log(
            manuscript_id=manuscript_id_str,
            from_status=ManuscriptStatus.PRE_CHECK.value,
            to_status=ManuscriptStatus.PRE_CHECK.value,
            changed_by=actor,
            comment=f"assign ae: {ae_id_str}",
            payload={
                "action": action,
                "pre_check_from": pre,
                "pre_check_to": PreCheckStatus.TECHNICAL.value,
                "assistant_editor_before": ae_before or None,
                "assistant_editor_after": ae_id_str,
                "owner_before": owner_before or None,
                "owner_after": owner_after,
                "decision": None,
                "idempotency_key": idempotency_key,
            },
            created_at=now,
        )
        mapped = self._map_precheck_row(updated)

        if not start_external_review:
            return mapped

        # 中文注释:
        # - 入口页“通过并分配 AE”可选择一键进入 under_review；
        # - 该路径等价于 ME 完成技术审查后直接发起外审，避免稿件掉出 Intake 但仍停留 pre_check。
        moved = self.editorial.update_status(
            manuscript_id=manuscript_id_str,
            to_status=ManuscriptStatus.UNDER_REVIEW.value,
            changed_by=actor,
            comment="intake approve + assign AE + start external review",
            allow_skip=False,
            extra_updates={"pre_check_status": None},
            payload={
                "action": "precheck_assign_ae_start_review",
                "pre_check_from": PreCheckStatus.TECHNICAL.value,
                "pre_check_to": None,
                "assistant_editor_before": ae_before or None,
                "assistant_editor_after": ae_id_str,
                "owner_before": owner_before or None,
                "owner_after": owner_after,
                "decision": "pass",
                "source": "intake_assign_modal",
                "idempotency_key": idempotency_key,
            },
        )
        return moved

    def request_intake_revision(
        self,
        manuscript_id: UUID,
        current_user_id: UUID,
        *,
        comment: str,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        """
        ME 入口技术审查：退回作者修改（非学术拒稿）。

        中文注释:
        - 仅允许在 pre_check/intake 阶段执行；
        - 结果流转到 minor_revision，作者修回后再进入流程；
        - 幂等处理：若已在 minor_revision，重复提交直接返回当前稿件。
        """
        manuscript_id_str = str(manuscript_id)
        actor = str(current_user_id)
        comment_clean = (comment or "").strip()
        if not comment_clean:
            raise HTTPException(status_code=422, detail="comment is required")

        ms = self._get_manuscript(manuscript_id_str)
        status = normalize_status(str(ms.get("status") or ""))
        pre = self._normalize_precheck_status(ms.get("pre_check_status"))

        if status == ManuscriptStatus.MINOR_REVISION.value:
            return dict(ms)

        if status != ManuscriptStatus.PRE_CHECK.value:
            raise HTTPException(status_code=409, detail="Intake revision only allowed in pre_check")
        if pre != PreCheckStatus.INTAKE.value:
            raise HTTPException(status_code=409, detail=f"Intake revision only allowed in intake stage, current={pre}")

        updated = self.editorial.update_status(
            manuscript_id=manuscript_id_str,
            to_status=ManuscriptStatus.MINOR_REVISION.value,
            changed_by=actor,
            comment=comment_clean,
            allow_skip=False,
            payload={
                "action": "precheck_intake_revision",
                "pre_check_from": PreCheckStatus.INTAKE.value,
                "pre_check_to": None,
                "decision": "revision",
                "idempotency_key": idempotency_key,
            },
        )
        return updated

    def _derive_ae_workspace_bucket(self, *, status: str | None, pre_check_status: str | None) -> str:
        if status == ManuscriptStatus.PRE_CHECK.value and pre_check_status == PreCheckStatus.TECHNICAL.value:
            return "technical"
        if status == ManuscriptStatus.PRE_CHECK.value and pre_check_status == PreCheckStatus.ACADEMIC.value:
            return "academic_pending"
        if status == ManuscriptStatus.UNDER_REVIEW.value:
            return "under_review"
        if status in {
            ManuscriptStatus.RESUBMITTED.value,
            ManuscriptStatus.MINOR_REVISION.value,
            ManuscriptStatus.MAJOR_REVISION.value,
        }:
            return "revision_followup"
        if status == ManuscriptStatus.DECISION.value:
            return "decision"
        return "other"

    def get_ae_workspace(self, ae_id: UUID, page: int = 1, page_size: int = 20) -> list[dict[str, Any]]:
        """
        AE Workspace：返回 AE 在办稿件全集（仅本人分管）。

        设计约束：
        - pre_check 仅展示 technical 子阶段（由 ME 分配后待发起外审）；
        - under_review / major_revision / minor_revision / resubmitted / decision 也纳入 AE 待办；
        - 默认按 updated_at 倒序，确保最近更新稿件置顶。
        """
        status_scope = [
            ManuscriptStatus.PRE_CHECK.value,
            ManuscriptStatus.UNDER_REVIEW.value,
            ManuscriptStatus.MINOR_REVISION.value,
            ManuscriptStatus.MAJOR_REVISION.value,
            ManuscriptStatus.RESUBMITTED.value,
            ManuscriptStatus.DECISION.value,
        ]
        selects = [
            "id,title,created_at,updated_at,status,pre_check_status,assistant_editor_id,owner_id,journal_id,journals(title,slug)",
            "id,title,created_at,updated_at,status,pre_check_status,assistant_editor_id,owner_id,journal_id",
            "id,title,created_at,updated_at,status,pre_check_status,assistant_editor_id,owner_id",
            "id,title,created_at,updated_at,status,pre_check_status,assistant_editor_id",
        ]

        rows: list[dict[str, Any]] = []
        last_error: Exception | None = None
        for select_clause in selects:
            try:
                q = (
                    self.client.table("manuscripts")
                    .select(select_clause)
                    .in_("status", status_scope)
                    .eq("assistant_editor_id", str(ae_id))
                    .order("updated_at", desc=True)
                    .order("created_at", desc=True)
                    .range((page - 1) * page_size, page * page_size - 1)
                )
                resp = q.execute()
                rows = getattr(resp, "data", None) or []
                break
            except Exception as e:
                last_error = e
                lowered = str(e).lower()
                if "journals" in lowered or "schema cache" in lowered or "pgrst" in lowered:
                    continue
                raise
        if not rows and last_error:
            lowered = str(last_error).lower()
            if "schema cache" in lowered or "could not find" in lowered:
                raise last_error

        raw_enriched = self._enrich_precheck_rows(rows)
        out: list[dict[str, Any]] = []
        for row in raw_enriched:
            normalized_status = normalize_status(str(row.get("status") or ""))
            normalized_precheck = self._normalize_precheck_status(row.get("pre_check_status"))
            if normalized_status == ManuscriptStatus.PRE_CHECK.value and normalized_precheck not in {
                PreCheckStatus.TECHNICAL.value,
                PreCheckStatus.ACADEMIC.value,
            }:
                continue
            row["workspace_bucket"] = self._derive_ae_workspace_bucket(
                status=normalized_status,
                pre_check_status=normalized_precheck,
            )
            out.append(row)

        owner_ids = sorted({str(r.get("owner_id") or "") for r in out if str(r.get("owner_id") or "")})
        owner_map: dict[str, dict[str, Any]] = {}
        if owner_ids:
            try:
                prof = (
                    self.client.table("user_profiles")
                    .select("id,full_name,email")
                    .in_("id", owner_ids)
                    .execute()
                )
                for p in (getattr(prof, "data", None) or []):
                    pid = str(p.get("id") or "")
                    if pid:
                        owner_map[pid] = p
            except Exception as e:
                print(f"[AEWorkspace] load owner profiles failed (ignored): {e}")

        for row in out:
            oid = str(row.get("owner_id") or "")
            row["owner"] = (
                {
                    "id": oid,
                    "full_name": (owner_map.get(oid) or {}).get("full_name"),
                    "email": (owner_map.get(oid) or {}).get("email"),
                }
                if oid
                else None
            )
            journal = row.get("journals")
            if isinstance(journal, list):
                row["journal"] = journal[0] if journal else None
            elif isinstance(journal, dict):
                row["journal"] = journal
            else:
                row["journal"] = None

        return out

    def submit_technical_check(
        self,
        manuscript_id: UUID,
        ae_id: UUID,
        *,
        decision: str,
        comment: str | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        """
        AE technical check:
        - pass -> under_review（跳过 academic pre-check）
        - academic -> pre_check/academic（送 EIC 预审，可选）
        - revision -> minor_revision
        """
        manuscript_id_str = str(manuscript_id)
        ae_id_str = str(ae_id)
        normalized_decision = str(decision or "").strip().lower()
        if normalized_decision not in {"pass", "revision", "academic"}:
            raise HTTPException(status_code=422, detail="decision must be pass, academic or revision")
        comment_clean = (comment or "").strip() or None
        if normalized_decision == "revision" and not comment_clean:
            raise HTTPException(status_code=422, detail="comment is required for revision")

        ms = self._get_manuscript(manuscript_id_str)
        status = normalize_status(str(ms.get("status") or ""))
        pre = self._normalize_precheck_status(ms.get("pre_check_status"))
        owner_ae = str(ms.get("assistant_editor_id") or "")

        if status != ManuscriptStatus.PRE_CHECK.value:
            if normalized_decision == "revision" and status == ManuscriptStatus.MINOR_REVISION.value:
                return dict(ms)
            if normalized_decision == "pass" and status == ManuscriptStatus.UNDER_REVIEW.value:
                return dict(ms)
            if (
                normalized_decision == "academic"
                and status == ManuscriptStatus.PRE_CHECK.value
                and pre == PreCheckStatus.ACADEMIC.value
            ):
                return dict(ms)
            raise HTTPException(status_code=409, detail="Technical check conflict: manuscript state changed")

        if pre != PreCheckStatus.TECHNICAL.value:
            raise HTTPException(status_code=409, detail=f"Technical check only allowed in technical stage, current={pre}")

        if owner_ae != ae_id_str:
            raise HTTPException(status_code=403, detail="Only assigned assistant editor can submit technical check")

        if normalized_decision == "academic":
            now = self._now()
            data = {
                "pre_check_status": PreCheckStatus.ACADEMIC.value,
                "updated_at": now,
            }
            q = (
                self.client.table("manuscripts")
                .update(data)
                .eq("id", manuscript_id_str)
                .eq("status", ManuscriptStatus.PRE_CHECK.value)
                .eq("pre_check_status", PreCheckStatus.TECHNICAL.value)
                .eq("assistant_editor_id", ae_id_str)
            )
            resp = q.execute()
            rows = getattr(resp, "data", None) or []
            if not rows:
                latest = self._get_manuscript(manuscript_id_str)
                latest_status = normalize_status(str(latest.get("status") or ""))
                latest_pre = self._normalize_precheck_status(latest.get("pre_check_status"))
                latest_ae = str(latest.get("assistant_editor_id") or "")
                if (
                    latest_status == ManuscriptStatus.PRE_CHECK.value
                    and latest_pre == PreCheckStatus.ACADEMIC.value
                    and latest_ae == ae_id_str
                ):
                    return self._map_precheck_row(latest)
                raise HTTPException(status_code=409, detail="Technical check conflict: manuscript state changed")

            updated = rows[0]
            self._safe_insert_transition_log(
                manuscript_id=manuscript_id_str,
                from_status=ManuscriptStatus.PRE_CHECK.value,
                to_status=ManuscriptStatus.PRE_CHECK.value,
                changed_by=ae_id_str,
                comment=comment_clean or "technical check sent to academic queue",
                payload={
                    "action": "precheck_technical_to_academic",
                    "pre_check_from": PreCheckStatus.TECHNICAL.value,
                    "pre_check_to": PreCheckStatus.ACADEMIC.value,
                    "assistant_editor_before": owner_ae or None,
                    "assistant_editor_after": owner_ae or None,
                    "decision": "academic",
                    "idempotency_key": idempotency_key,
                },
                created_at=now,
            )
            return self._map_precheck_row(updated)

        if normalized_decision == "pass":
            updated = self.editorial.update_status(
                manuscript_id=manuscript_id_str,
                to_status=ManuscriptStatus.UNDER_REVIEW.value,
                changed_by=ae_id_str,
                comment=comment_clean or "technical check passed, moved to under_review",
                allow_skip=False,
                extra_updates={"pre_check_status": None},
                payload={
                    "action": "precheck_technical_to_under_review",
                    "pre_check_from": PreCheckStatus.TECHNICAL.value,
                    "pre_check_to": None,
                    "assistant_editor_before": owner_ae or None,
                    "assistant_editor_after": owner_ae or None,
                    "decision": "pass",
                    "idempotency_key": idempotency_key,
                },
            )
            return updated

        updated = self.editorial.update_status(
            manuscript_id=manuscript_id_str,
            to_status=ManuscriptStatus.MINOR_REVISION.value,
            changed_by=ae_id_str,
            comment=comment_clean,
            allow_skip=False,
            payload={
                "action": "precheck_technical_revision",
                "pre_check_from": PreCheckStatus.TECHNICAL.value,
                "pre_check_to": None,
                "assistant_editor_before": owner_ae or None,
                "assistant_editor_after": owner_ae or None,
                "decision": "revision",
                "idempotency_key": idempotency_key,
            },
        )
        return updated

    def get_academic_queue(
        self,
        *,
        viewer_user_id: UUID | str,
        viewer_roles: Iterable[str] | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> list[dict[str, Any]]:
        """
        EIC Academic Queue: Status=PRE_CHECK, PreCheckStatus=ACADEMIC
        """
        normalized_roles = set(normalize_roles(viewer_roles))
        q = (
            self.client.table("manuscripts")
            .select("*")
            .eq("status", ManuscriptStatus.PRE_CHECK.value)
            .eq("pre_check_status", PreCheckStatus.ACADEMIC.value)
            .order("updated_at", desc=True)
            .order("created_at", desc=True)
            .range((page - 1) * page_size, page * page_size - 1)
        )
        resp = q.execute()
        rows = getattr(resp, "data", None) or []
        out = self._enrich_precheck_rows(rows)

        if "admin" not in normalized_roles:
            scoped_journal_ids = get_user_scope_journal_ids(
                user_id=str(viewer_user_id),
                roles=normalized_roles,
            )
            has_global_scope_role = bool({"managing_editor", "editor_in_chief"} & normalized_roles)
            if scoped_journal_ids:
                out = [
                    row
                    for row in out
                    if str(row.get("journal_id") or "").strip() in scoped_journal_ids
                ]
            elif has_global_scope_role or is_scope_enforcement_enabled():
                return []

        return out

    def get_final_decision_queue(
        self,
        *,
        viewer_user_id: UUID | str,
        viewer_roles: Iterable[str] | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> list[dict[str, Any]]:
        """
        EIC Final Decision Queue:
        - 常规展示 status in decision / decision_done（终审阶段）
        - 额外展示“已有 first decision 草稿”的 under_review / resubmitted 稿件，
          便于 EIC 从 AE 草稿接手终审。
        """
        normalized_roles = set(normalize_roles(viewer_roles))
        decision_stage_statuses = {
            ManuscriptStatus.DECISION.value,
            ManuscriptStatus.DECISION_DONE.value,
        }
        q = (
            self.client.table("manuscripts")
            .select("id,title,status,updated_at,journal_id,journals(title,slug),assistant_editor_id,owner_id")
            .in_(
                "status",
                [
                    ManuscriptStatus.UNDER_REVIEW.value,
                    ManuscriptStatus.RESUBMITTED.value,
                    ManuscriptStatus.DECISION.value,
                    ManuscriptStatus.DECISION_DONE.value,
                ],
            )
            .order("updated_at", desc=True)
            .order("created_at", desc=True)
            .range((page - 1) * page_size, page * page_size - 1)
        )
        resp = q.execute()
        rows = getattr(resp, "data", None) or []

        if "admin" not in normalized_roles:
            scoped_journal_ids = get_user_scope_journal_ids(
                user_id=str(viewer_user_id),
                roles=normalized_roles,
            )
            has_global_scope_role = bool({"managing_editor", "editor_in_chief"} & normalized_roles)
            if scoped_journal_ids:
                rows = [
                    row
                    for row in rows
                    if str(row.get("journal_id") or "").strip() in scoped_journal_ids
                ]
            elif has_global_scope_role or is_scope_enforcement_enabled():
                return []

        manuscript_ids = [str(row.get("id") or "").strip() for row in rows if str(row.get("id") or "").strip()]
        latest_draft_map: dict[str, dict[str, Any]] = {}
        if manuscript_ids:
            try:
                draft_resp = (
                    self.client.table("decision_letters")
                    .select("id,manuscript_id,editor_id,decision,status,updated_at")
                    .eq("status", "draft")
                    .in_("manuscript_id", manuscript_ids)
                    .order("updated_at", desc=True)
                    .execute()
                )
                for row in (getattr(draft_resp, "data", None) or []):
                    mid = str(row.get("manuscript_id") or "").strip()
                    if mid and mid not in latest_draft_map:
                        latest_draft_map[mid] = row
            except Exception as e:
                print(f"[FinalDecisionQueue] load draft decision letters failed (ignored): {e}")

        for row in rows:
            draft = latest_draft_map.get(str(row.get("id") or "").strip())
            if draft:
                row["latest_first_decision_draft"] = {
                    "id": draft.get("id"),
                    "editor_id": draft.get("editor_id"),
                    "decision": draft.get("decision"),
                    "updated_at": draft.get("updated_at"),
                }
            else:
                row["latest_first_decision_draft"] = None

        filtered_rows: list[dict[str, Any]] = []
        for row in rows:
            status = normalize_status(str(row.get("status") or ""))
            has_draft = row.get("latest_first_decision_draft") is not None
            if status in decision_stage_statuses or has_draft:
                filtered_rows.append(row)
        return filtered_rows

    def submit_academic_check(
        self,
        manuscript_id: UUID,
        decision: str,
        comment: str | None = None,
        *,
        changed_by: UUID | str | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        """
        EIC academic check:
        - review -> under_review
        - decision_phase -> decision
        """
        manuscript_id_str = str(manuscript_id)
        actor = str(changed_by) if changed_by else None
        d = str(decision or "").strip().lower()
        if d not in {"review", "decision_phase"}:
            raise HTTPException(status_code=422, detail="decision must be review or decision_phase")
        to_status = ManuscriptStatus.UNDER_REVIEW.value if d == "review" else ManuscriptStatus.DECISION.value

        ms = self._get_manuscript(manuscript_id_str)
        status = normalize_status(str(ms.get("status") or ""))
        pre = self._normalize_precheck_status(ms.get("pre_check_status"))
        if status != ManuscriptStatus.PRE_CHECK.value:
            if status == to_status:
                return ms
            raise HTTPException(status_code=409, detail="Academic check conflict: manuscript state changed")
        if pre != PreCheckStatus.ACADEMIC.value:
            raise HTTPException(status_code=409, detail=f"Academic check only allowed in academic stage, current={pre}")

        payload_action = "precheck_academic_to_review" if d == "review" else "precheck_academic_to_decision"
        updated = self.editorial.update_status(
            manuscript_id=manuscript_id_str,
            to_status=to_status,
            changed_by=actor,
            comment=(comment or "").strip() or None,
            allow_skip=False,
            extra_updates={"pre_check_status": None},
            payload={
                "action": payload_action,
                "pre_check_from": PreCheckStatus.ACADEMIC.value,
                "pre_check_to": None,
                "assistant_editor_before": str(ms.get("assistant_editor_id") or "") or None,
                "assistant_editor_after": str(ms.get("assistant_editor_id") or "") or None,
                "decision": d,
                "idempotency_key": idempotency_key,
            },
        )
        return updated
