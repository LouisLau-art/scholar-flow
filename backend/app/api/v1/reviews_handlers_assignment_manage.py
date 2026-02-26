from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import HTTPException


def _pick_target_round(
    *,
    round_number: int | None,
    assignments: list[dict[str, Any]],
    manuscript_version: int | None,
) -> int | None:
    if round_number is not None:
        return int(round_number)
    if not assignments:
        return manuscript_version

    try:
        max_round = max(int(item.get("round_number") or 1) for item in assignments)
    except Exception:
        max_round = 1

    if manuscript_version is not None and any(
        int(item.get("round_number") or 1) == int(manuscript_version) for item in assignments
    ):
        return int(manuscript_version)
    return int(max_round)


def _enrich_assignment_rows(
    *,
    assignments: list[dict[str, Any]],
    profiles_by_id: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    seen_keys: set[tuple[str, Any]] = set()
    result: list[dict[str, Any]] = []
    for item in assignments:
        reviewer_id = str(item.get("reviewer_id") or "")
        round_no = item.get("round_number", 1)
        key = (reviewer_id, round_no)
        if not reviewer_id or key in seen_keys:
            continue
        seen_keys.add(key)
        profile_row = profiles_by_id.get(reviewer_id, {})
        result.append(
            {
                "id": item["id"],
                "status": item.get("status"),
                "due_at": item.get("due_at"),
                "round_number": round_no,
                "reviewer_id": reviewer_id,
                "reviewer_name": profile_row.get("full_name") or "Unknown",
                "reviewer_email": profile_row.get("email") or "",
            }
        )
    return result


async def unassign_reviewer_impl(
    *,
    assignment_id: UUID,
    current_user: dict[str, Any],
    profile: dict[str, Any],
    supabase_admin_client: Any,
    ensure_review_management_access_fn,
    normalize_roles_fn,
    parse_roles_fn,
) -> dict[str, Any]:
    """撤销审稿指派（拆分后入口，行为保持一致）。"""
    try:
        assign_res = (
            supabase_admin_client.table("review_assignments")
            .select("manuscript_id, reviewer_id, round_number")
            .eq("id", str(assignment_id))
            .single()
            .execute()
        )
        if not assign_res.data:
            raise HTTPException(status_code=404, detail="Assignment not found")

        manuscript_id = assign_res.data["manuscript_id"]
        reviewer_id = assign_res.data["reviewer_id"]
        round_number = assign_res.data.get("round_number")

        manuscript_res = (
            supabase_admin_client.table("manuscripts")
            .select("id,journal_id,assistant_editor_id")
            .eq("id", str(manuscript_id))
            .single()
            .execute()
        )
        manuscript = getattr(manuscript_res, "data", None) or {}
        ensure_review_management_access_fn(
            manuscript=manuscript,
            user_id=str(current_user.get("id") or ""),
            roles=set(normalize_roles_fn(parse_roles_fn(profile))),
        )

        delete_query = (
            supabase_admin_client.table("review_assignments")
            .delete()
            .eq("manuscript_id", manuscript_id)
            .eq("reviewer_id", reviewer_id)
        )
        if round_number is not None:
            delete_query = delete_query.eq("round_number", round_number)
        delete_query.execute()

        try:
            (
                supabase_admin_client.table("review_reports")
                .delete()
                .eq("manuscript_id", manuscript_id)
                .eq("reviewer_id", reviewer_id)
                .in_("status", ["invited", "pending"])
                .execute()
            )
        except Exception:
            pass

        remaining_res = (
            supabase_admin_client.table("review_assignments")
            .select("id")
            .eq("manuscript_id", manuscript_id)
            .execute()
        )
        if len(remaining_res.data or []) == 0:
            (
                supabase_admin_client.table("manuscripts")
                .update({"status": "pre_check"})
                .eq("id", manuscript_id)
                .execute()
            )

        return {"success": True, "message": "Reviewer unassigned"}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


async def get_manuscript_assignments_impl(
    *,
    manuscript_id: UUID,
    round_number: int | None,
    current_user: dict[str, Any],
    profile: dict[str, Any],
    supabase_admin_client: Any,
    ensure_review_management_access_fn,
    normalize_roles_fn,
    parse_roles_fn,
) -> dict[str, Any]:
    """获取稿件审稿指派（拆分后入口，行为保持一致）。"""
    try:
        manuscript_res = (
            supabase_admin_client.table("manuscripts")
            .select("id,journal_id,assistant_editor_id")
            .eq("id", str(manuscript_id))
            .single()
            .execute()
        )
        manuscript = getattr(manuscript_res, "data", None) or {}
        if not manuscript:
            raise HTTPException(status_code=404, detail="Manuscript not found")
        ensure_review_management_access_fn(
            manuscript=manuscript,
            user_id=str(current_user.get("id") or ""),
            roles=set(normalize_roles_fn(parse_roles_fn(profile))),
        )

        assignment_res = (
            supabase_admin_client.table("review_assignments")
            .select("id, status, due_at, reviewer_id, round_number, created_at")
            .eq("manuscript_id", str(manuscript_id))
            .order("created_at", desc=True)
            .execute()
        )
        assignments = assignment_res.data or []

        manuscript_version: int | None = None
        if round_number is None:
            try:
                ms_version_res = (
                    supabase_admin_client.table("manuscripts")
                    .select("version")
                    .eq("id", str(manuscript_id))
                    .single()
                    .execute()
                )
                manuscript_version = int((getattr(ms_version_res, "data", None) or {}).get("version") or 1)
            except Exception:
                manuscript_version = None

        target_round = _pick_target_round(
            round_number=round_number,
            assignments=assignments,
            manuscript_version=manuscript_version,
        )
        if target_round is not None and assignments:
            assignments = [item for item in assignments if int(item.get("round_number") or 1) == int(target_round)]

        reviewer_ids = list({item.get("reviewer_id") for item in assignments if item.get("reviewer_id")})
        profiles_by_id: dict[str, dict[str, Any]] = {}
        if reviewer_ids:
            try:
                profiles_res = (
                    supabase_admin_client.table("user_profiles")
                    .select("id, full_name, email")
                    .in_("id", reviewer_ids)
                    .execute()
                )
                for row in (profiles_res.data or []):
                    profile_id = row.get("id")
                    if profile_id:
                        profiles_by_id[str(profile_id)] = row
            except Exception:
                pass

        return {
            "success": True,
            "data": _enrich_assignment_rows(assignments=assignments, profiles_by_id=profiles_by_id),
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Failed to load reviewer assignments") from exc
