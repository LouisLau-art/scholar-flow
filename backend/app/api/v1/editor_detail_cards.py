from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.api.v1 import editor_detail_runtime as runtime
from app.models.internal_task import InternalTaskStatus
from app.models.manuscript import ManuscriptStatus, normalize_status

async def get_editor_manuscript_cards_context_impl(
    id: str,
    current_user: dict,
    profile: dict,
):
    """
    详情页统计卡片上下文（延迟加载）：
    - Task SLA Summary
    - Pre-check Role Queue
    """
    runtime._require_action_or_403(action="manuscript:view_detail", roles=profile.get("roles") or [])

    ms = runtime._load_manuscript_or_404(id)
    runtime._authorize_manuscript_detail_access(
        manuscript_id=id,
        manuscript=ms,
        current_user=current_user,
        profile=profile,
    )

    task_summary = {
        "open_tasks_count": 0,
        "overdue_tasks_count": 0,
        "is_overdue": False,
        "nearest_due_at": None,
    }
    try:
        t_resp = (
            runtime.supabase_admin.table("internal_tasks")
            .select("id,status,due_at")
            .eq("manuscript_id", id)
            .execute()
        )
        t_rows = getattr(t_resp, "data", None) or []
        open_rows = [r for r in t_rows if str(r.get("status") or "").lower() != InternalTaskStatus.DONE.value]
        overdue_count = 0
        nearest_due: str | None = None
        now = datetime.now(timezone.utc)
        for row in open_rows:
            due_raw = str(row.get("due_at") or "")
            if not due_raw:
                continue
            try:
                due_at = datetime.fromisoformat(due_raw.replace("Z", "+00:00")).astimezone(timezone.utc)
            except Exception:
                continue
            if due_at < now:
                overdue_count += 1
            if not nearest_due:
                nearest_due = due_at.isoformat()
            else:
                try:
                    prev = datetime.fromisoformat(nearest_due.replace("Z", "+00:00")).astimezone(timezone.utc)
                    if due_at < prev:
                        nearest_due = due_at.isoformat()
                except Exception:
                    nearest_due = due_at.isoformat()
        task_summary = {
            "open_tasks_count": len(open_rows),
            "overdue_tasks_count": overdue_count,
            "is_overdue": overdue_count > 0,
            "nearest_due_at": nearest_due,
        }
    except Exception as e:
        if not runtime._is_missing_table_error(str(e)):
            print(f"[CardsContext] task summary failed (ignored): {e}")

    tl_rows: list[dict[str, Any]] = []
    try:
        tl_resp = (
            runtime.supabase_admin.table("status_transition_logs")
            .select("id,created_at,comment,payload")
            .eq("manuscript_id", id)
            .order("created_at", desc=False)
            .limit(300)
            .execute()
        )
        tl_rows = getattr(tl_resp, "data", None) or []
    except Exception as e:
        print(f"[CardsContext] precheck timeline failed (ignored): {e}")

    aid = str(ms.get("assistant_editor_id") or "").strip()
    assistant_profile: dict[str, Any] = {}
    if aid:
        try:
            p = (
                runtime.supabase_admin.table("user_profiles")
                .select("id,full_name,email")
                .eq("id", aid)
                .single()
                .execute()
            )
            assistant_profile = getattr(p, "data", None) or {}
        except Exception:
            assistant_profile = {}

    role_map = {
        "intake": "managing_editor",
        "technical": "assistant_editor",
        "academic": "editor_in_chief",
    }
    pre_stage = str(ms.get("pre_check_status") or "intake").strip().lower() or "intake"
    current_status = normalize_status(str(ms.get("status") or "")) or str(ms.get("status") or "").strip().lower()
    in_precheck = current_status == ManuscriptStatus.PRE_CHECK.value
    current_role = role_map.get(pre_stage, "managing_editor") if in_precheck else "completed"
    current_assignee = None
    current_assignee_label = None
    if in_precheck and pre_stage == "technical" and aid:
        current_assignee = {
            "id": aid,
            "full_name": assistant_profile.get("full_name"),
            "email": assistant_profile.get("email"),
        }
    elif in_precheck and pre_stage == "academic":
        current_assignee_label = "Journal EIC Queue"
    elif in_precheck and pre_stage == "intake":
        current_assignee_label = "Managing Editor Queue"
    elif not in_precheck:
        current_assignee_label = "Pre-check completed"

    assigned_at = None
    technical_completed_at = None
    academic_completed_at = None
    for row in tl_rows:
        payload = row.get("payload") if isinstance(row.get("payload"), dict) else {}
        action = str(payload.get("action") or "")
        if not action.startswith("precheck_"):
            continue
        created_at = str(row.get("created_at") or "")
        if action in {"precheck_assign_ae", "precheck_reassign_ae"}:
            assigned_at = created_at or assigned_at
        if action in {"precheck_technical_pass", "precheck_technical_revision", "precheck_technical_to_under_review"}:
            technical_completed_at = created_at or technical_completed_at
        if action in {"precheck_academic_to_review", "precheck_academic_to_decision"}:
            academic_completed_at = created_at or academic_completed_at

    role_queue = {
        "current_role": current_role,
        "current_assignee": current_assignee,
        "current_assignee_label": current_assignee_label,
        "assigned_at": assigned_at,
        "technical_completed_at": technical_completed_at,
        "academic_completed_at": academic_completed_at,
    }

    return {
        "success": True,
        "data": {
            "task_summary": task_summary,
            "role_queue": role_queue,
        },
    }
