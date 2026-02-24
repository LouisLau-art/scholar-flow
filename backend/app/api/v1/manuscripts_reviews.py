from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from app.core.auth_utils import get_current_user
from app.core.roles import get_current_profile
from app.lib.api_client import supabase_admin


router = APIRouter(tags=["Manuscripts"])


@router.get("/manuscripts/{manuscript_id}/reviews")
async def get_manuscript_reviews(
    manuscript_id: UUID,
    current_user: dict = Depends(get_current_user),
    profile: dict = Depends(get_current_profile),
):
    """
    获取某稿件的审稿反馈（用于 Editor 决策页展示 Review Summary）。

    中文注释:
    - Author 只能看到公开字段（comments_for_author/content/score）
    - Internal（admin / managing_editor / editor_in_chief / assistant_editor / production_editor）可读取内部视图
    - assistant_editor 仅可读取自己被分配稿件
    - production_editor 仅可读取自己分配到的活跃 production cycle 稿件
    """
    user_id = str(current_user.get("id"))
    roles = {str(role).strip().lower() for role in ((profile or {}).get("roles") or []) if str(role).strip()}

    ms_resp = (
        supabase_admin.table("manuscripts")
        .select("id, author_id, assistant_editor_id, owner_id")
        .eq("id", str(manuscript_id))
        .single()
        .execute()
    )
    ms = getattr(ms_resp, "data", None) or {}
    if not ms:
        raise HTTPException(status_code=404, detail="Manuscript not found")

    is_author = str(ms.get("author_id") or "") == user_id
    is_internal = bool(
        roles.intersection(
            {
                "admin",
                "managing_editor",
                "editor_in_chief",
                "assistant_editor",
                "production_editor",
                "owner",
            }
        )
    )
    if not (is_author or is_internal):
        raise HTTPException(status_code=403, detail="Forbidden")

    def _is_assigned_production_editor() -> bool:
        active_statuses = [
            "draft",
            "awaiting_author",
            "author_corrections_submitted",
            "author_confirmed",
            "in_layout_revision",
            "approved_for_publish",
        ]
        try:
            layout_bound = (
                supabase_admin.table("production_cycles")
                .select("id")
                .eq("manuscript_id", str(manuscript_id))
                .eq("layout_editor_id", user_id)
                .in_("status", active_statuses)
                .limit(1)
                .execute()
            )
            if getattr(layout_bound, "data", None):
                return True
        except Exception:
            return False

        try:
            collab_bound = (
                supabase_admin.table("production_cycles")
                .select("id")
                .eq("manuscript_id", str(manuscript_id))
                .contains("collaborator_editor_ids", [user_id])
                .in_("status", active_statuses)
                .limit(1)
                .execute()
            )
            return bool(getattr(collab_bound, "data", None))
        except Exception:
            # 老环境可能缺少 collaborator_editor_ids，降级为仅 layout_editor_id 校验
            return False

    # 中文注释:
    # - admin / managing_editor / editor_in_chief 为全局内部可见；
    # - assistant_editor 仅看分配稿件；
    # - production_editor 仅看分配到活跃 production cycle 的稿件；
    # - owner 仅看 owner_id 归属稿件。
    has_privileged_internal_role = bool(roles.intersection({"admin", "managing_editor", "editor_in_chief"}))
    if not is_author and not has_privileged_internal_role:
        internal_allowed = False

        if "assistant_editor" in roles:
            assigned_ae_id = str(ms.get("assistant_editor_id") or "").strip()
            if assigned_ae_id and assigned_ae_id == user_id:
                internal_allowed = True

        if (not internal_allowed) and ("production_editor" in roles):
            if _is_assigned_production_editor():
                internal_allowed = True

        if (not internal_allowed) and ("owner" in roles):
            owner_id = str(ms.get("owner_id") or "").strip()
            if owner_id and owner_id == user_id:
                internal_allowed = True

        if not internal_allowed:
            raise HTTPException(status_code=403, detail="Forbidden")

    rr_resp = (
        supabase_admin.table("review_reports")
        .select(
            "id, manuscript_id, reviewer_id, status, comments_for_author, content, score, confidential_comments_to_editor, attachment_path, created_at"
        )
        .eq("manuscript_id", str(manuscript_id))
        .order("created_at", desc=True)
        .execute()
    )
    rows: list[dict] = getattr(rr_resp, "data", None) or []

    reviewer_ids = sorted({str(r.get("reviewer_id")) for r in rows if r.get("reviewer_id")})
    profile_by_id: dict[str, dict] = {}
    if reviewer_ids:
        try:
            pr = (
                supabase_admin.table("user_profiles")
                .select("id, full_name, email")
                .in_("id", reviewer_ids)
                .execute()
            )
            for p in (getattr(pr, "data", None) or []):
                if p.get("id"):
                    profile_by_id[str(p["id"])] = p
        except Exception:
            profile_by_id = {}

    for r in rows:
        rid = str(r.get("reviewer_id") or "")
        p = profile_by_id.get(rid) or {}
        r["reviewer_name"] = p.get("full_name")
        r["reviewer_email"] = p.get("email")
        if not r.get("comments_for_author") and r.get("content"):
            r["comments_for_author"] = r.get("content")

    # 中文注释:
    # - 历史上可能出现“重复邀请/重复指派”导致同一 reviewer 多条 review_reports（其中部分未提交）。
    # - Editor 决策页应优先展示“已完成/有内容”的那条，避免出现 Score N/A 的误导。
    def _parse_dt(value: object) -> datetime | None:
        if isinstance(value, datetime):
            return value
        if not isinstance(value, str):
            return None
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except Exception:
            return None

    def _row_rank(r: dict) -> tuple[int, int, int, datetime]:
        status = str(r.get("status") or "").strip().lower()
        is_completed = 1 if status in {"completed", "done", "submitted"} else 0
        has_score = 1 if r.get("score") is not None else 0
        public_text = str(r.get("comments_for_author") or r.get("content") or "").strip()
        has_public = 1 if public_text else 0
        dt = _parse_dt(r.get("created_at")) or datetime.min.replace(tzinfo=timezone.utc)
        return (is_completed, has_score, has_public, dt)

    best_by_reviewer: dict[str, dict] = {}
    others: list[dict] = []
    for r in rows:
        rid = str(r.get("reviewer_id") or "").strip()
        if not rid:
            others.append(r)
            continue
        prev = best_by_reviewer.get(rid)
        if prev is None or _row_rank(r) > _row_rank(prev):
            best_by_reviewer[rid] = r

    deduped = list(best_by_reviewer.values())
    deduped.sort(key=lambda r: _parse_dt(r.get("created_at")) or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
    rows = deduped + others

    if is_author:
        sanitized = []
        for r in rows:
            public_text = r.get("comments_for_author") or r.get("content")
            sanitized.append(
                {
                    "id": r.get("id"),
                    "manuscript_id": r.get("manuscript_id"),
                    "reviewer_id": r.get("reviewer_id"),
                    "reviewer_name": r.get("reviewer_name"),
                    "reviewer_email": r.get("reviewer_email"),
                    "status": r.get("status"),
                    # 兼容：旧页面读取 content
                    "content": public_text,
                    "comments_for_author": public_text,
                    "score": r.get("score"),
                    "created_at": r.get("created_at"),
                }
            )
        return {"success": True, "data": sanitized}

    return {"success": True, "data": rows}
