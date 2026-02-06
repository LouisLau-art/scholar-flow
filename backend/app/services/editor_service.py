from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterable
from uuid import UUID

from fastapi import HTTPException

from app.lib.api_client import supabase_admin
from app.models.manuscript import ManuscriptStatus, PreCheckStatus, normalize_status


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

    def list_manuscripts_process(self, *, filters: ProcessListFilters) -> list[dict[str, Any]]:
        q = (
            self.client.table("manuscripts")
            .select(
                "id,title,created_at,updated_at,status,owner_id,editor_id,journal_id,journals(title,slug)"
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
        return getattr(resp, "data", None) or []

    def assign_ae(self, manuscript_id: UUID, ae_id: UUID, current_user_id: UUID) -> bool:
        """
        Assign AE: Update assistant_editor_id and move to TECHNICAL
        """
        data = {
            "assistant_editor_id": str(ae_id),
            "pre_check_status": PreCheckStatus.TECHNICAL.value,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        resp = self.client.table("manuscripts").update(data).eq("id", str(manuscript_id)).execute()
        
        # Log transition (Simplified for MVP)
        if getattr(resp, "data", None):
            print(f"[038] Manuscript {manuscript_id} assigned to AE {ae_id} by {current_user_id}")
            return True
        return False

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
        return getattr(resp, "data", None) or []

    def submit_technical_check(self, manuscript_id: UUID, ae_id: UUID) -> bool:
        """
        Move to ACADEMIC check
        """
        data = {
            "pre_check_status": PreCheckStatus.ACADEMIC.value,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        resp = (
            self.client.table("manuscripts")
            .update(data)
            .eq("id", str(manuscript_id))
            .eq("assistant_editor_id", str(ae_id))
            .execute()
        )
        return bool(getattr(resp, "data", None))

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
        return getattr(resp, "data", None) or []

    def submit_academic_check(self, manuscript_id: UUID, decision: str, comment: str | None = None) -> bool:
        """
        Academic Decision: route to Review or Decision phase
        """
        new_status = ManuscriptStatus.UNDER_REVIEW.value if decision == "review" else ManuscriptStatus.DECISION.value
        data = {
            "status": new_status,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        resp = self.client.table("manuscripts").update(data).eq("id", str(manuscript_id)).execute()
        return bool(getattr(resp, "data", None))

