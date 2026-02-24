from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from fastapi import HTTPException, UploadFile


async def get_reviewer_workspace_data_impl(
    *,
    assignment_id: UUID,
    magic_token: str | None,
    require_magic_link_scope_fn,
    reviewer_workspace_service_cls,
) -> dict[str, Any]:
    payload = await require_magic_link_scope_fn(
        assignment_id=assignment_id,
        magic_token=magic_token,
    )
    try:
        data = reviewer_workspace_service_cls().get_workspace_data(
            assignment_id=assignment_id,
            reviewer_id=payload.reviewer_id,
        )
    except PermissionError:
        raise HTTPException(status_code=403, detail="Forbidden")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load workspace: {e}")
    return {"success": True, "data": data.model_dump()}


async def get_reviewer_invite_data_impl(
    *,
    assignment_id: UUID,
    magic_token: str | None,
    require_magic_link_scope_fn,
    reviewer_invite_service_cls,
) -> dict[str, Any]:
    payload = await require_magic_link_scope_fn(
        assignment_id=assignment_id,
        magic_token=magic_token,
    )
    try:
        data = reviewer_invite_service_cls().get_invite_view(
            assignment_id=assignment_id,
            reviewer_id=payload.reviewer_id,
        )
    except PermissionError:
        raise HTTPException(status_code=403, detail="Forbidden")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load invite view: {e}")
    return {"success": True, "data": data.model_dump()}


async def accept_reviewer_invitation_impl(
    *,
    assignment_id: UUID,
    body,
    magic_token: str | None,
    require_magic_link_scope_fn,
    reviewer_invite_service_cls,
) -> dict[str, Any]:
    token_payload = await require_magic_link_scope_fn(
        assignment_id=assignment_id,
        magic_token=magic_token,
    )
    try:
        data = reviewer_invite_service_cls().accept_invitation(
            assignment_id=assignment_id,
            reviewer_id=token_payload.reviewer_id,
            payload=body,
        )
        return {"success": True, "data": data}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except PermissionError:
        raise HTTPException(status_code=403, detail="Forbidden")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to accept invitation: {e}")


async def decline_reviewer_invitation_impl(
    *,
    assignment_id: UUID,
    body,
    magic_token: str | None,
    require_magic_link_scope_fn,
    reviewer_invite_service_cls,
) -> dict[str, Any]:
    token_payload = await require_magic_link_scope_fn(
        assignment_id=assignment_id,
        magic_token=magic_token,
    )
    try:
        data = reviewer_invite_service_cls().decline_invitation(
            assignment_id=assignment_id,
            reviewer_id=token_payload.reviewer_id,
            payload=body,
        )
        return {"success": True, "data": data}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except PermissionError:
        raise HTTPException(status_code=403, detail="Forbidden")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to decline invitation: {e}")


async def upload_reviewer_workspace_attachment_impl(
    *,
    assignment_id: UUID,
    file: UploadFile,
    magic_token: str | None,
    require_magic_link_scope_fn,
    reviewer_workspace_service_cls,
    get_signed_url_for_review_attachments_bucket_fn,
) -> dict[str, Any]:
    payload = await require_magic_link_scope_fn(
        assignment_id=assignment_id,
        magic_token=magic_token,
    )
    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="Attachment cannot be empty")
    try:
        path = reviewer_workspace_service_cls().upload_attachment(
            assignment_id=assignment_id,
            reviewer_id=payload.reviewer_id,
            filename=file.filename or "attachment",
            content=raw,
            content_type=file.content_type,
        )
        signed_url = get_signed_url_for_review_attachments_bucket_fn(path, expires_in=60 * 5)
    except PermissionError:
        raise HTTPException(status_code=403, detail="Forbidden")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload attachment: {e}")
    return {"success": True, "data": {"path": path, "url": signed_url}}


async def submit_reviewer_workspace_review_impl(
    *,
    assignment_id: UUID,
    body,
    magic_token: str | None,
    require_magic_link_scope_fn,
    reviewer_workspace_service_cls,
) -> dict[str, Any]:
    payload = await require_magic_link_scope_fn(
        assignment_id=assignment_id,
        magic_token=magic_token,
    )
    try:
        result = reviewer_workspace_service_cls().submit_review(
            assignment_id=assignment_id,
            reviewer_id=payload.reviewer_id,
            payload=body,
        )
    except PermissionError:
        raise HTTPException(status_code=403, detail="Forbidden")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to submit review: {e}")
    return {
        "success": True,
        "data": {"status": result.get("status", "completed"), "redirect_to": "/review/thank-you"},
    }


async def get_review_assignment_via_magic_link_impl(
    *,
    assignment_id: UUID,
    magic_token: str | None,
    require_magic_link_scope_fn,
    supabase_admin_client: Any,
) -> dict[str, Any]:
    payload = await require_magic_link_scope_fn(
        assignment_id=assignment_id,
        magic_token=magic_token,
    )

    ms_resp = (
        supabase_admin_client.table("manuscripts")
        .select("id,title,abstract,file_path,status")
        .eq("id", str(payload.manuscript_id))
        .single()
        .execute()
    )
    ms = getattr(ms_resp, "data", None) or {}

    latest_revision = None
    try:
        rev_resp = (
            supabase_admin_client.table("revisions")
            .select("id, round_number, decision_type, editor_comment, response_letter, status, submitted_at, created_at")
            .eq("manuscript_id", str(payload.manuscript_id))
            .order("round_number", desc=True)
            .limit(1)
            .execute()
        )
        revs = getattr(rev_resp, "data", None) or []
        latest_revision = revs[0] if revs else None
    except Exception:
        latest_revision = None

    review_report = None
    try:
        rr = (
            supabase_admin_client.table("review_reports")
            .select("id, manuscript_id, reviewer_id, status, score, comments_for_author, confidential_comments_to_editor, attachment_path")
            .eq("manuscript_id", str(payload.manuscript_id))
            .eq("reviewer_id", str(payload.reviewer_id))
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        rows = getattr(rr, "data", None) or []
        review_report = rows[0] if rows else None
    except Exception:
        review_report = None

    return {
        "success": True,
        "data": {
            "assignment_id": str(payload.assignment_id),
            "reviewer_id": str(payload.reviewer_id),
            "manuscript": ms,
            "review_report": review_report,
            "latest_revision": latest_revision,
        },
    }


async def get_review_assignment_pdf_signed_via_magic_link_impl(
    *,
    assignment_id: UUID,
    magic_token: str | None,
    require_magic_link_scope_fn,
    supabase_admin_client: Any,
    get_signed_url_for_manuscripts_bucket_fn,
) -> dict[str, Any]:
    payload = await require_magic_link_scope_fn(
        assignment_id=assignment_id,
        magic_token=magic_token,
    )

    ms_resp = (
        supabase_admin_client.table("manuscripts")
        .select("id,file_path")
        .eq("id", str(payload.manuscript_id))
        .single()
        .execute()
    )
    ms = getattr(ms_resp, "data", None) or {}
    file_path = ms.get("file_path")
    if not file_path:
        raise HTTPException(status_code=404, detail="Manuscript PDF not found")

    signed_url = get_signed_url_for_manuscripts_bucket_fn(str(file_path))
    return {"success": True, "data": {"signed_url": signed_url}}


async def get_review_attachment_signed_via_magic_link_impl(
    *,
    assignment_id: UUID,
    magic_token: str | None,
    require_magic_link_scope_fn,
    supabase_admin_client: Any,
    get_signed_url_for_review_attachments_bucket_fn,
) -> dict[str, Any]:
    payload = await require_magic_link_scope_fn(
        assignment_id=assignment_id,
        magic_token=magic_token,
    )

    try:
        rr = (
            supabase_admin_client.table("review_reports")
            .select("id, attachment_path")
            .eq("manuscript_id", str(payload.manuscript_id))
            .eq("reviewer_id", str(payload.reviewer_id))
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        rows = getattr(rr, "data", None) or []
        row = rows[0] if rows else None
    except Exception:
        row = None

    attachment_path = (row or {}).get("attachment_path") if row else None
    if not attachment_path:
        return {"success": True, "data": {"signed_url": None}}

    signed_url = get_signed_url_for_review_attachments_bucket_fn(str(attachment_path))
    return {"success": True, "data": {"signed_url": signed_url}}


async def get_review_pdf_signed_by_token_impl(
    *,
    token: str,
    supabase_admin_client: Any,
    get_signed_url_for_manuscripts_bucket_fn,
) -> dict[str, Any]:
    try:
        rr_resp = (
            supabase_admin_client.table("review_reports")
            .select("id, manuscript_id, reviewer_id, status, expiry_date")
            .eq("token", token)
            .single()
            .execute()
        )
        rr = getattr(rr_resp, "data", None) or {}
        if not rr:
            raise HTTPException(status_code=404, detail="Review token not found")

        expiry = rr.get("expiry_date")
        try:
            expiry_dt = (
                datetime.fromisoformat(expiry.replace("Z", "+00:00"))
                if isinstance(expiry, str)
                else expiry
            )
        except Exception:
            expiry_dt = None
        if expiry_dt and expiry_dt < datetime.now(timezone.utc):
            raise HTTPException(status_code=410, detail="Review token expired")

        ms_resp = (
            supabase_admin_client.table("manuscripts")
            .select("id,file_path")
            .eq("id", rr["manuscript_id"])
            .single()
            .execute()
        )
        ms = getattr(ms_resp, "data", None) or {}
        file_path = ms.get("file_path")
        if not file_path:
            raise HTTPException(status_code=404, detail="Manuscript PDF not found")

        signed_url = get_signed_url_for_manuscripts_bucket_fn(str(file_path))
        return {"success": True, "data": {"signed_url": signed_url}}
    except HTTPException:
        raise
    except Exception as e:
        print(f"Get review pdf signed url by token failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate PDF preview URL")


async def get_review_feedback_for_manuscript_impl(
    *,
    manuscript_id: UUID,
    current_user: dict[str, Any],
    supabase_admin_client: Any,
    is_admin_email_fn,
) -> dict[str, Any]:
    try:
        ms_resp = (
            supabase_admin_client.table("manuscripts")
            .select("id, author_id")
            .eq("id", str(manuscript_id))
            .single()
            .execute()
        )
        ms = getattr(ms_resp, "data", None) or {}
        if not ms:
            raise HTTPException(status_code=404, detail="Manuscript not found")

        is_author = str(ms.get("author_id")) == str(current_user.get("id"))
        is_editor = is_admin_email_fn(current_user.get("email"))
        if not (is_author or is_editor):
            raise HTTPException(status_code=403, detail="Forbidden")

        rr_resp = (
            supabase_admin_client.table("review_reports")
            .select("id, manuscript_id, reviewer_id, status, comments_for_author, content, score, confidential_comments_to_editor, attachment_path")
            .eq("manuscript_id", str(manuscript_id))
            .order("created_at", desc=True)
            .execute()
        )
        rows = getattr(rr_resp, "data", None) or []

        if is_author:
            sanitized = []
            for r in rows:
                public_text = r.get("comments_for_author") or r.get("content")
                r2 = {
                    "id": r.get("id"),
                    "manuscript_id": r.get("manuscript_id"),
                    "reviewer_id": r.get("reviewer_id"),
                    "status": r.get("status"),
                    "content": public_text,
                    "comments_for_author": public_text,
                    "score": r.get("score"),
                }
                sanitized.append(r2)
            return {"success": True, "data": sanitized}

        for r in rows:
            if not r.get("comments_for_author") and r.get("content"):
                r["comments_for_author"] = r.get("content")
        return {"success": True, "data": rows}
    except HTTPException:
        raise
    except Exception as e:
        print(f"Fetch review feedback failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch review feedback")


async def get_review_attachment_signed_by_token_impl(
    *,
    token: str,
    supabase_admin_client: Any,
    get_signed_url_for_review_attachments_bucket_fn,
) -> dict[str, Any]:
    try:
        rr_resp = (
            supabase_admin_client.table("review_reports")
            .select("id, attachment_path, expiry_date")
            .eq("token", token)
            .single()
            .execute()
        )
        rr = getattr(rr_resp, "data", None) or {}
        if not rr:
            raise HTTPException(status_code=404, detail="Review token not found")

        expiry = rr.get("expiry_date")
        try:
            expiry_dt = (
                datetime.fromisoformat(expiry.replace("Z", "+00:00"))
                if isinstance(expiry, str)
                else expiry
            )
        except Exception:
            expiry_dt = None
        if expiry_dt and expiry_dt < datetime.now(timezone.utc):
            raise HTTPException(status_code=410, detail="Review token expired")

        path = rr.get("attachment_path")
        if not path:
            raise HTTPException(status_code=404, detail="No attachment")

        signed_url = get_signed_url_for_review_attachments_bucket_fn(str(path))
        return {"success": True, "data": {"signed_url": signed_url}}
    except HTTPException:
        raise
    except Exception as e:
        print(f"Get review attachment signed url by token failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate attachment URL")


async def get_review_attachment_signed_impl(
    *,
    review_report_id: UUID,
    current_user: dict[str, Any],
    profile: dict[str, Any],
    supabase_admin_client: Any,
    get_signed_url_for_review_attachments_bucket_fn,
) -> dict[str, Any]:
    try:
        rr_resp = (
            supabase_admin_client.table("review_reports")
            .select("id, reviewer_id, attachment_path")
            .eq("id", str(review_report_id))
            .single()
            .execute()
        )
        rr = getattr(rr_resp, "data", None) or {}
        if not rr:
            raise HTTPException(status_code=404, detail="Review report not found")

        roles = set(profile.get("roles") or [])
        is_editor = bool(roles.intersection({"managing_editor", "admin"}))
        if not is_editor and str(rr.get("reviewer_id") or "") != str(current_user.get("id") or ""):
            raise HTTPException(status_code=403, detail="Forbidden")

        path = rr.get("attachment_path")
        if not path:
            raise HTTPException(status_code=404, detail="No attachment")

        signed_url = get_signed_url_for_review_attachments_bucket_fn(str(path))
        return {"success": True, "data": {"signed_url": signed_url}}
    except HTTPException:
        raise
    except Exception as e:
        print(f"Get review attachment signed url failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate attachment URL")
