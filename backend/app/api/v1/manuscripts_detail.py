from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from app.core.auth_utils import get_current_user
from app.core.roles import get_current_profile
from app.models.revision import VersionHistoryResponse
from app.services.revision_service import RevisionService

router = APIRouter(tags=["Manuscripts"])


def _m():
    from app.api.v1 import manuscripts as manuscripts_api

    return manuscripts_api


@router.get(
    "/manuscripts/{manuscript_id}/versions", response_model=VersionHistoryResponse
)
async def get_manuscript_versions(
    manuscript_id: UUID,
    current_user: dict = Depends(get_current_user),
):
    """
    获取稿件版本历史
    """
    service = RevisionService()

    manuscript = service.get_manuscript(str(manuscript_id))
    if not manuscript:
        raise HTTPException(status_code=404, detail="Manuscript not found")

    is_author = str(manuscript.get("author_id")) == str(current_user["id"])

    if not is_author:
        try:
            profile_res = (
                _m()
                .supabase.table("user_profiles")
                .select("roles")
                .eq("id", current_user["id"])
                .single()
                .execute()
            )
            profile = getattr(profile_res, "data", {}) or {}
            roles = set(profile.get("roles", []) or [])
        except Exception:
            raise HTTPException(status_code=403, detail="Access denied")

        if roles.intersection({"managing_editor", "admin"}):
            pass
        elif "reviewer" in roles:
            try:
                ra = (
                    _m()
                    .supabase_admin.table("review_assignments")
                    .select("id")
                    .eq("manuscript_id", str(manuscript_id))
                    .eq("reviewer_id", str(current_user["id"]))
                    .limit(1)
                    .execute()
                )
                if not getattr(ra, "data", None):
                    raise HTTPException(status_code=403, detail="Access denied")
            except HTTPException:
                raise
            except Exception:
                raise HTTPException(status_code=403, detail="Access denied")
        else:
            raise HTTPException(status_code=403, detail="Access denied")

    result = service.get_version_history(str(manuscript_id))

    if not result["success"]:
        raise HTTPException(status_code=500, detail=result["error"])

    return VersionHistoryResponse(data=result["data"])


@router.get("/manuscripts/by-id/{manuscript_id}")
async def get_manuscript_detail(
    manuscript_id: UUID,
    current_user: dict = Depends(get_current_user),
    profile: dict = Depends(get_current_profile),
):
    """
    登录态稿件详情（非公开文章页）。
    """
    user_id = str(current_user["id"])
    roles = set((profile or {}).get("roles") or [])

    try:
        ms_resp = (
            _m()
            .supabase_admin.table("manuscripts")
            .select("*")
            .eq("id", str(manuscript_id))
            .single()
            .execute()
        )
        ms = getattr(ms_resp, "data", None) or {}
    except Exception as e:
        if _m()._is_postgrest_single_no_rows_error(str(e)):
            raise HTTPException(status_code=404, detail="Manuscript not found")
        raise
    if not ms:
        raise HTTPException(status_code=404, detail="Manuscript not found")

    allowed = False
    if roles.intersection({"admin", "managing_editor"}):
        allowed = True
    elif str(ms.get("author_id") or "") == user_id:
        allowed = True
    else:
        try:
            ra = (
                _m()
                .supabase_admin.table("review_assignments")
                .select("id")
                .eq("manuscript_id", str(manuscript_id))
                .eq("reviewer_id", user_id)
                .limit(1)
                .execute()
            )
            if getattr(ra, "data", None):
                allowed = True
        except Exception:
            allowed = False

    if not allowed:
        raise HTTPException(status_code=403, detail="Forbidden")
    manuscript_id_str = str(manuscript_id)
    visited_statuses: set[str] = {"submitted"}
    current_status = _m()._normalize_private_progress_status(ms.get("status"))
    if current_status:
        visited_statuses.add(current_status)

    latest_feedback_comment: str | None = None
    latest_feedback_at: str | None = None
    latest_feedback_source: str | None = None
    latest_author_response_letter: str | None = None
    latest_author_response_at: str | None = None
    latest_author_response_round: int | None = None

    try:
        revision_resp = (
            _m()
            .supabase_admin.table("revisions")
            .select("editor_comment,created_at,updated_at")
            .eq("manuscript_id", manuscript_id_str)
            .order("created_at", desc=True)
            .limit(20)
            .execute()
        )
        revision_rows = getattr(revision_resp, "data", None) or []
        for row in revision_rows:
            comment = str(row.get("editor_comment") or "").strip()
            if not comment:
                continue
            latest_feedback_comment = comment
            latest_feedback_at = str(row.get("created_at") or row.get("updated_at") or "")
            latest_feedback_source = "revision_request"
            break
    except Exception as e:
        print(f"[ById] revisions feedback fallback failed (ignored): {e}")

    revision_selects = [
        "response_letter,submitted_at,updated_at,round",
        "response_letter,updated_at",
    ]
    for select_clause in revision_selects:
        try:
            response_resp = (
                _m()
                .supabase_admin.table("revisions")
                .select(select_clause)
                .eq("manuscript_id", manuscript_id_str)
                .order("updated_at", desc=True)
                .limit(30)
                .execute()
            )
            response_rows = getattr(response_resp, "data", None) or []
            for row in response_rows:
                response_letter = str(row.get("response_letter") or "").strip()
                if not response_letter:
                    continue
                latest_author_response_letter = response_letter
                latest_author_response_at = str(row.get("submitted_at") or row.get("updated_at") or "")
                raw_round = row.get("round")
                try:
                    latest_author_response_round = int(raw_round) if raw_round is not None else None
                except Exception:
                    latest_author_response_round = None
                break
            break
        except Exception as e:
            lowered = str(e).lower()
            if "schema cache" in lowered or "column" in lowered or "pgrst" in lowered:
                continue
            print(f"[ById] latest author response fallback failed (ignored): {e}")
            break

    try:
        logs_resp = (
            _m()
            .supabase_admin.table("status_transition_logs")
            .select("from_status,to_status,comment,created_at,payload")
            .eq("manuscript_id", manuscript_id_str)
            .order("created_at", desc=True)
            .limit(120)
            .execute()
        )
        log_rows = getattr(logs_resp, "data", None) or []
        for row in log_rows:
            from_status = _m()._normalize_private_progress_status(row.get("from_status"))
            to_status = _m()._normalize_private_progress_status(row.get("to_status"))
            if from_status:
                visited_statuses.add(from_status)
            if to_status:
                visited_statuses.add(to_status)

            if latest_feedback_comment:
                continue

            comment = str(row.get("comment") or "").strip()
            if not comment:
                continue
            payload = row.get("payload") if isinstance(row.get("payload"), dict) else {}
            action = str(payload.get("action") or "").strip().lower()
            is_revision_feedback = (
                to_status == "revision_requested"
                or action in {"precheck_intake_revision", "precheck_technical_revision"}
            )
            if is_revision_feedback:
                latest_feedback_comment = comment
                latest_feedback_at = str(row.get("created_at") or "")
                latest_feedback_source = "status_transition"
    except Exception as e:
        if not _m()._is_missing_table_error(str(e), "status_transition_logs"):
            print(f"[ById] transition logs fallback failed (ignored): {e}")

    enriched = dict(ms)
    enriched["workflow_visited_statuses"] = _m()._order_private_progress_statuses(visited_statuses)
    enriched["author_latest_feedback_comment"] = latest_feedback_comment
    enriched["author_latest_feedback_at"] = latest_feedback_at
    enriched["author_latest_feedback_source"] = latest_feedback_source
    enriched["author_latest_response_letter"] = latest_author_response_letter
    enriched["author_latest_response_at"] = latest_author_response_at
    enriched["author_latest_response_round"] = latest_author_response_round
    return {"success": True, "data": enriched}
