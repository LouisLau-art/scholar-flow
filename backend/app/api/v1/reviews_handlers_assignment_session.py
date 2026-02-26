from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from fastapi import HTTPException


def _load_assignment(
    *,
    supabase_admin_client: Any,
    assignment_id: UUID,
) -> dict[str, Any]:
    try:
        resp = (
            supabase_admin_client.table("review_assignments")
            .select("id, reviewer_id, manuscript_id, status")
            .eq("id", str(assignment_id))
            .single()
            .execute()
        )
        return getattr(resp, "data", None) or {}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to load assignment: {exc}") from exc


def _assert_assignment_access(
    *,
    assignment: dict[str, Any],
    reviewer_id: str,
) -> None:
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")
    if str(assignment.get("reviewer_id") or "") != reviewer_id:
        raise HTTPException(status_code=403, detail="Not allowed to access this assignment")
    if str(assignment.get("status") or "").lower() == "cancelled":
        raise HTTPException(status_code=403, detail="Invitation revoked")


def _activate_assignment_if_needed(
    *,
    supabase_admin_client: Any,
    assignment_id: UUID,
    status_raw: str,
) -> None:
    if status_raw in {"completed", "declined", "cancelled", "accepted"}:
        return

    now_iso = datetime.now(timezone.utc).isoformat()
    update_candidates = [
        {
            "status": "accepted",
            "accepted_at": now_iso,
            "opened_at": now_iso,
        },
        {"status": "accepted"},
    ]

    last_error: Exception | None = None
    for payload in update_candidates:
        try:
            (
                supabase_admin_client.table("review_assignments")
                .update(payload)
                .eq("id", str(assignment_id))
                .execute()
            )
            last_error = None
            break
        except Exception as exc:
            last_error = exc

    if last_error is not None:
        raise HTTPException(
            status_code=500,
            detail="Failed to activate reviewer assignment session; please retry.",
        ) from last_error


def _create_session_token(
    *,
    assignment: dict[str, Any],
    create_magic_link_jwt_fn,
) -> str:
    try:
        return create_magic_link_jwt_fn(
            reviewer_id=UUID(str(assignment.get("reviewer_id"))),
            manuscript_id=UUID(str(assignment.get("manuscript_id"))),
            assignment_id=UUID(str(assignment.get("id"))),
            expires_in_days=14,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to create reviewer session: {exc}") from exc


async def establish_reviewer_workspace_session_impl(
    *,
    assignment_id: UUID,
    response,
    current_user: dict[str, Any],
    supabase_admin_client: Any,
    create_magic_link_jwt_fn,
) -> dict[str, Any]:
    """登录态 Reviewer 会话桥接（拆分后入口，行为保持一致）。"""
    reviewer_id = str(current_user.get("id") or "").strip()
    if not reviewer_id:
        raise HTTPException(status_code=401, detail="Unauthorized")

    assignment = _load_assignment(
        supabase_admin_client=supabase_admin_client,
        assignment_id=assignment_id,
    )
    _assert_assignment_access(assignment=assignment, reviewer_id=reviewer_id)
    _activate_assignment_if_needed(
        supabase_admin_client=supabase_admin_client,
        assignment_id=assignment_id,
        status_raw=str(assignment.get("status") or "").strip().lower(),
    )

    token = _create_session_token(
        assignment=assignment,
        create_magic_link_jwt_fn=create_magic_link_jwt_fn,
    )
    secure_cookie = (os.environ.get("GO_ENV") or "").strip().lower() in {"prod", "production"}
    response.set_cookie(
        key="sf_review_magic",
        value=token,
        httponly=True,
        samesite="lax",
        secure=secure_cookie,
        path="/",
        max_age=60 * 60 * 24 * 14,
    )
    return {
        "success": True,
        "data": {
            "assignment_id": str(assignment_id),
            "redirect_url": f"/reviewer/workspace/{assignment_id}",
        },
    }
