from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import HTTPException
from postgrest.exceptions import APIError


def _load_manuscript_for_assignment(
    *,
    supabase_client: Any,
    manuscript_id: str,
) -> dict[str, Any]:
    result = (
        supabase_client.table("manuscripts")
        .select("id, author_id, title, version, status, owner_id, file_path, journal_id, assistant_editor_id")
        .eq("id", manuscript_id)
        .single()
        .execute()
    )
    manuscript = getattr(result, "data", None) or {}
    if not manuscript:
        raise HTTPException(status_code=404, detail="Manuscript not found")
    return manuscript


def _validate_manuscript_for_assignment(
    *,
    manuscript: dict[str, Any],
    reviewer_id: str,
) -> None:
    if str(manuscript.get("author_id") or "") == reviewer_id:
        raise HTTPException(status_code=400, detail="作者不能评审自己的稿件")
    if not manuscript.get("file_path"):
        raise HTTPException(
            status_code=400,
            detail="该稿件缺少 PDF（file_path 为空），无法分配审稿人。请先在投稿/修订流程上传 PDF。",
        )


def _auto_bind_owner_if_missing(
    *,
    manuscript: dict[str, Any],
    manuscript_id: str,
    current_user_id: str,
    supabase_admin_client: Any,
) -> None:
    if manuscript.get("owner_id"):
        return
    try:
        (
            supabase_admin_client.table("manuscripts")
            .update({"owner_id": current_user_id})
            .eq("id", manuscript_id)
            .execute()
        )
        manuscript["owner_id"] = current_user_id
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Failed to bind Internal Owner") from exc


def _load_existing_assignment(
    *,
    supabase_admin_client: Any,
    manuscript_id: str,
    reviewer_id: str,
    round_number: int,
) -> dict[str, Any] | None:
    existing = (
        supabase_admin_client.table("review_assignments")
        .select("id, status, due_at, reviewer_id, round_number")
        .eq("manuscript_id", manuscript_id)
        .eq("reviewer_id", reviewer_id)
        .eq("round_number", round_number)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    rows = getattr(existing, "data", None) or []
    return rows[0] if rows else None


def _resolve_invite_policy(
    *,
    policy_service: Any,
    manuscript: dict[str, Any],
    reviewer_id: str,
) -> dict[str, Any]:
    policy = policy_service.evaluate_candidates(manuscript=manuscript, reviewer_ids=[reviewer_id]).get(reviewer_id)
    return policy or {
        "can_assign": True,
        "allow_override": False,
        "cooldown_active": False,
        "conflict": False,
        "overdue_risk": False,
        "overdue_open_count": 0,
        "hits": [],
    }


def _validate_cooldown_policy(
    *,
    policy: dict[str, Any],
    policy_service: Any,
    requester_roles: set[str],
    override_cooldown: bool,
) -> tuple[set[str], bool]:
    if policy.get("conflict"):
        raise HTTPException(status_code=400, detail="Invitation blocked: conflict of interest")

    override_role_set = {str(role).strip().lower() for role in policy_service.cooldown_override_roles() if str(role).strip()}
    can_override_cooldown = bool(requester_roles & override_role_set)
    override_requested = bool(override_cooldown and policy.get("cooldown_active"))
    if not policy.get("cooldown_active"):
        return override_role_set, False

    cooldown_until = str(policy.get("cooldown_until") or "").strip()
    cooldown_suffix = f" until {cooldown_until}" if cooldown_until else ""
    if not can_override_cooldown:
        raise HTTPException(status_code=409, detail=f"Invitation blocked: cooldown active{cooldown_suffix}")
    if not override_requested:
        raise HTTPException(
            status_code=409,
            detail=f"Invitation blocked: cooldown active{cooldown_suffix}; override_cooldown=true required",
        )
    return override_role_set, True


def _insert_review_assignment(
    *,
    supabase_admin_client: Any,
    manuscript_id: str,
    reviewer_id: str,
    round_number: int,
    due_at: str,
) -> Any:
    payload = {
        "manuscript_id": manuscript_id,
        "reviewer_id": reviewer_id,
        "status": "selected",
        "due_at": due_at,
        "round_number": round_number,
    }
    return supabase_admin_client.table("review_assignments").insert(payload).execute()


async def assign_reviewer_impl(
    *,
    current_user: dict[str, Any],
    profile: dict[str, Any],
    manuscript_id: UUID,
    reviewer_id: UUID,
    override_cooldown: bool,
    override_reason: str | None,
    supabase_client: Any,
    supabase_admin_client: Any,
    normalize_roles_fn,
    parse_roles_fn,
    review_policy_service_cls,
    ensure_review_management_access_fn,
    is_foreign_key_user_error_fn,
    is_missing_relation_error_fn,
) -> dict[str, Any]:
    """编辑分配审稿人（拆分后入口，行为保持一致）。"""
    requester_roles = set(normalize_roles_fn(parse_roles_fn(profile)))
    policy_service = review_policy_service_cls()
    reviewer_id_str = str(reviewer_id)
    manuscript_id_str = str(manuscript_id)
    current_user_id = str(current_user.get("id") or "")

    manuscript = _load_manuscript_for_assignment(supabase_client=supabase_client, manuscript_id=manuscript_id_str)
    ensure_review_management_access_fn(
        manuscript=manuscript,
        user_id=current_user_id,
        roles=requester_roles,
    )
    _validate_manuscript_for_assignment(manuscript=manuscript, reviewer_id=reviewer_id_str)
    _auto_bind_owner_if_missing(
        manuscript=manuscript,
        manuscript_id=manuscript_id_str,
        current_user_id=current_user_id,
        supabase_admin_client=supabase_admin_client,
    )
    current_version = manuscript.get("version", 1) if manuscript else 1

    try:
        existing = _load_existing_assignment(
            supabase_admin_client=supabase_admin_client,
            manuscript_id=manuscript_id_str,
            reviewer_id=reviewer_id_str,
            round_number=current_version,
        )
        policy = _resolve_invite_policy(
            policy_service=policy_service,
            manuscript=manuscript,
            reviewer_id=reviewer_id_str,
        )
        if existing:
            return {
                "success": True,
                "data": existing,
                "policy": policy,
                "message": "Reviewer already assigned",
            }

        override_role_set, override_applied = _validate_cooldown_policy(
            policy=policy,
            policy_service=policy_service,
            requester_roles=requester_roles,
            override_cooldown=override_cooldown,
        )
        _ = (override_role_set, override_applied)

        _min_days, _max_days, default_days = policy_service.due_window_days()
        due_at = (datetime.now(timezone.utc) + timedelta(days=default_days)).isoformat()
        insert_resp = _insert_review_assignment(
            supabase_admin_client=supabase_admin_client,
            manuscript_id=manuscript_id_str,
            reviewer_id=reviewer_id_str,
            round_number=current_version,
            due_at=due_at,
        )

        row = (getattr(insert_resp, "data", None) or [{}])[0]
        return {
            "success": True,
            "data": row,
            "policy": policy,
            "message": "Reviewer added to selection list",
            "next_step": "send_invitation_email",
        }
    except HTTPException:
        raise
    except APIError as exc:
        if is_foreign_key_user_error_fn(exc, constraint="review_assignments_reviewer_id_fkey"):
            raise HTTPException(
                status_code=400,
                detail=(
                    "该审稿人账号不存在于 Supabase Auth（可能是 mock user_profiles）。"
                    "请用「Invite New」创建真实账号，或运行 scripts/seed_mock_reviewers_auth.py 生成可指派 reviewer。"
                ),
            ) from exc
        if is_missing_relation_error_fn(exc, relation="review_assignments"):
            raise HTTPException(
                status_code=500,
                detail="review_assignments 表不存在或 Schema cache 未更新（请先在云端 Supabase 创建/迁移该表）。",
            ) from exc
        raise HTTPException(status_code=500, detail=f"Failed to assign reviewer: {exc}") from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to assign reviewer: {exc}") from exc
