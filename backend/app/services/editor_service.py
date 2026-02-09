from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterable
from uuid import UUID

from fastapi import HTTPException

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
            if action in {"precheck_technical_pass", "precheck_technical_revision"}:
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

    def list_manuscripts_process(self, *, filters: ProcessListFilters) -> list[dict[str, Any]]:
        q = (
            self.client.table("manuscripts")
            .select(
                "id,title,created_at,updated_at,status,pre_check_status,assistant_editor_id,owner_id,editor_id,journal_id,journals(title,slug)"
            )
            .order("created_at", desc=True)
        )
        q = apply_process_filters(q, filters)
        resp = q.execute()
        rows: list[dict[str, Any]] = getattr(resp, "data", None) or []

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
        return rows

    # --- Feature 038: Pre-check Role Workflow (ME -> AE -> EIC) ---

    def get_intake_queue(self, page: int = 1, page_size: int = 20) -> list[dict[str, Any]]:
        """
        ME Intake Queue: Status=PRE_CHECK, PreCheckStatus=INTAKE
        """
        q = (
            self.client.table("manuscripts")
            .select("*")
            .eq("status", ManuscriptStatus.PRE_CHECK.value)
            .or_(f"pre_check_status.eq.{PreCheckStatus.INTAKE.value},pre_check_status.is.null")
            .order("created_at", desc=True)
            .range((page - 1) * page_size, page * page_size - 1)
        )
        resp = q.execute()
        rows = getattr(resp, "data", None) or []
        return self._enrich_precheck_rows(rows)

    def assign_ae(
        self,
        manuscript_id: UUID,
        ae_id: UUID,
        current_user_id: UUID,
        *,
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
                "decision": None,
                "idempotency_key": idempotency_key,
            },
            created_at=now,
        )
        return self._map_precheck_row(updated)

    def get_ae_workspace(self, ae_id: UUID, page: int = 1, page_size: int = 20) -> list[dict[str, Any]]:
        """
        AE Workspace: Status=PRE_CHECK, PreCheckStatus=TECHNICAL, assigned to ae_id
        """
        q = (
            self.client.table("manuscripts")
            .select("*")
            .eq("status", ManuscriptStatus.PRE_CHECK.value)
            .eq("pre_check_status", PreCheckStatus.TECHNICAL.value)
            .eq("assistant_editor_id", str(ae_id))
            .order("created_at", desc=True)
            .range((page - 1) * page_size, page * page_size - 1)
        )
        resp = q.execute()
        rows = getattr(resp, "data", None) or []
        return self._enrich_precheck_rows(rows)

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
        - pass -> pre_check/academic
        - revision -> minor_revision
        """
        manuscript_id_str = str(manuscript_id)
        ae_id_str = str(ae_id)
        now = self._now()
        normalized_decision = str(decision or "").strip().lower()
        if normalized_decision not in {"pass", "revision"}:
            raise HTTPException(status_code=422, detail="decision must be pass or revision")
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
            if normalized_decision == "pass" and pre == PreCheckStatus.ACADEMIC.value:
                return self._map_precheck_row(ms)
            raise HTTPException(status_code=409, detail="Technical check conflict: manuscript state changed")

        if pre != PreCheckStatus.TECHNICAL.value:
            if normalized_decision == "pass" and pre == PreCheckStatus.ACADEMIC.value:
                return self._map_precheck_row(ms)
            raise HTTPException(status_code=409, detail=f"Technical check only allowed in technical stage, current={pre}")

        if owner_ae != ae_id_str:
            raise HTTPException(status_code=403, detail="Only assigned assistant editor can submit technical check")

        if normalized_decision == "pass":
            data = {
                "pre_check_status": PreCheckStatus.ACADEMIC.value,
                "updated_at": now,
            }
            resp = (
                self.client.table("manuscripts")
                .update(data)
                .eq("id", manuscript_id_str)
                .eq("status", ManuscriptStatus.PRE_CHECK.value)
                .eq("pre_check_status", PreCheckStatus.TECHNICAL.value)
                .eq("assistant_editor_id", ae_id_str)
                .execute()
            )
            rows = getattr(resp, "data", None) or []
            if not rows:
                latest = self._get_manuscript(manuscript_id_str)
                if (
                    normalize_status(str(latest.get("status") or "")) == ManuscriptStatus.PRE_CHECK.value
                    and self._normalize_precheck_status(latest.get("pre_check_status")) == PreCheckStatus.ACADEMIC.value
                ):
                    return self._map_precheck_row(latest)
                raise HTTPException(status_code=409, detail="Technical pass conflict: manuscript state changed")

            updated = rows[0]
            self._safe_insert_transition_log(
                manuscript_id=manuscript_id_str,
                from_status=ManuscriptStatus.PRE_CHECK.value,
                to_status=ManuscriptStatus.PRE_CHECK.value,
                changed_by=ae_id_str,
                comment=comment_clean or "technical check passed",
                payload={
                    "action": "precheck_technical_pass",
                    "pre_check_from": PreCheckStatus.TECHNICAL.value,
                    "pre_check_to": PreCheckStatus.ACADEMIC.value,
                    "assistant_editor_before": owner_ae or None,
                    "assistant_editor_after": owner_ae or None,
                    "decision": "pass",
                    "idempotency_key": idempotency_key,
                },
                created_at=now,
            )
            return self._map_precheck_row(updated)

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

    def get_academic_queue(self, page: int = 1, page_size: int = 20) -> list[dict[str, Any]]:
        """
        EIC Academic Queue: Status=PRE_CHECK, PreCheckStatus=ACADEMIC
        """
        q = (
            self.client.table("manuscripts")
            .select("*")
            .eq("status", ManuscriptStatus.PRE_CHECK.value)
            .eq("pre_check_status", PreCheckStatus.ACADEMIC.value)
            .order("created_at", desc=True)
            .range((page - 1) * page_size, page * page_size - 1)
        )
        resp = q.execute()
        rows = getattr(resp, "data", None) or []
        return self._enrich_precheck_rows(rows)

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
