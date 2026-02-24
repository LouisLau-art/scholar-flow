from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict
from uuid import UUID

from fastapi import HTTPException, UploadFile
from postgrest.exceptions import APIError

async def submit_review_via_magic_link_impl(
    *,
    assignment_id: UUID,
    payload,
    comments_for_author: str | None,
    content: str | None,
    score: int,
    confidential_comments_to_editor: str | None,
    attachment: UploadFile | None,
    supabase_admin_client: Any,
    ensure_review_attachments_bucket_exists_fn,
) -> dict[str, Any]:
    """Magic link 提交评审（搬运原逻辑）。"""
    public_comments = (comments_for_author or content or "").strip()
    if not public_comments:
        raise HTTPException(status_code=400, detail="comments_for_author is required")
    if score < 1 or score > 5:
        raise HTTPException(status_code=400, detail="score must be 1..5")

    attachment_path = None
    if attachment is not None:
        file_bytes = await attachment.read()
        safe_name = (attachment.filename or "attachment").replace("/", "_")
        attachment_path = f"review_reports/{payload.assignment_id}/{safe_name}"
        try:
            ensure_review_attachments_bucket_exists_fn()
            supabase_admin_client.storage.from_("review-attachments").upload(
                attachment_path,
                file_bytes,
                {"content-type": attachment.content_type or "application/octet-stream"},
            )
        except Exception as e:
            print(f"[Review Attachment] upload failed: {e}")
            raise HTTPException(status_code=500, detail="Failed to upload attachment")

    rr_payload = {
        "manuscript_id": str(payload.manuscript_id),
        "reviewer_id": str(payload.reviewer_id),
        "status": "completed",
        "comments_for_author": public_comments,
        "content": public_comments,  # 兼容旧字段
        "score": score,
        "confidential_comments_to_editor": confidential_comments_to_editor,
        "attachment_path": attachment_path,
    }
    try:
        existing = (
            supabase_admin_client.table("review_reports")
            .select("id")
            .eq("manuscript_id", str(payload.manuscript_id))
            .eq("reviewer_id", str(payload.reviewer_id))
            .limit(1)
            .execute()
        )
        rows = getattr(existing, "data", None) or []
        if rows:
            supabase_admin_client.table("review_reports").update(rr_payload).eq("id", rows[0]["id"]).execute()
        else:
            supabase_admin_client.table("review_reports").insert(
                {
                    **rr_payload,
                    "token": None,
                    "expiry_date": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
                }
            ).execute()
    except Exception as e:
        print(f"[Reviews] upsert review_reports failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to submit review")

    try:
        supabase_admin_client.table("review_assignments").update(
            {
                "status": "completed",
                "comments": public_comments,
                "scores": {"overall": score},
            }
        ).eq("id", str(assignment_id)).execute()
    except Exception as e:
        print(f"[Reviews] update assignment failed (ignored): {e}")

    try:
        pending = (
            supabase_admin_client.table("review_assignments")
            .select("id")
            .eq("manuscript_id", str(payload.manuscript_id))
            .eq("status", "pending")
            .execute()
        )
        if not (getattr(pending, "data", None) or []):
            supabase_admin_client.table("manuscripts").update({"status": "decision"}).eq(
                "id", str(payload.manuscript_id)
            ).in_("status", ["under_review", "resubmitted", "decision"]).execute()
            try:
                supabase_admin_client.table("manuscripts").update({"status": "decision"}).eq(
                    "id", str(payload.manuscript_id)
                ).eq("status", "pending_decision").execute()
            except Exception:
                pass
    except Exception:
        pass

    return {"success": True, "data": {"assignment_id": str(assignment_id)}}


async def submit_review_impl(
    *,
    assignment_id: UUID,
    scores: Dict[str, int],
    comments_for_author: str | None,
    comments: str | None,
    confidential_comments_to_editor: str | None,
    attachment_path: str | None,
    supabase_client: Any,
    supabase_admin_client: Any,
) -> dict[str, Any]:
    """登录态提交评审（搬运原逻辑）。"""
    public_comments = (comments_for_author or comments or "").strip()
    if not public_comments:
        raise HTTPException(status_code=400, detail="comments_for_author is required")

    try:
        assignment_res = (
            supabase_client.table("review_assignments")
            .select("manuscript_id, reviewer_id")
            .eq("id", str(assignment_id))
            .single()
            .execute()
        )
        manuscript_id = None
        assignment_data = getattr(assignment_res, "data", None)
        if isinstance(assignment_data, list):
            assignment_data = assignment_data[0] if assignment_data else None
        if assignment_data:
            manuscript_id = assignment_data.get("manuscript_id")
            reviewer_id = assignment_data.get("reviewer_id")
        else:
            reviewer_id = None

        res = (
            supabase_client.table("review_assignments")
            .update({"status": "completed", "scores": scores, "comments": public_comments})
            .eq("id", str(assignment_id))
            .execute()
        )

        if manuscript_id and reviewer_id:
            overall_score = None
            try:
                vals = list((scores or {}).values())
                overall_score = round(sum(vals) / max(len(vals), 1)) if vals else None
            except Exception:
                overall_score = None

            rr_payload = {
                "manuscript_id": str(manuscript_id),
                "reviewer_id": str(reviewer_id),
                "status": "completed",
                "comments_for_author": public_comments,
                "content": public_comments,
                "score": overall_score,
                "confidential_comments_to_editor": confidential_comments_to_editor,
                "attachment_path": attachment_path,
            }
            try:
                existing = (
                    supabase_admin_client.table("review_reports")
                    .select("id")
                    .eq("manuscript_id", str(manuscript_id))
                    .eq("reviewer_id", str(reviewer_id))
                    .limit(1)
                    .execute()
                )
                existing_rows = getattr(existing, "data", None) or []
                if existing_rows:
                    supabase_admin_client.table("review_reports").update(rr_payload).eq(
                        "id", existing_rows[0]["id"]
                    ).execute()
                else:
                    supabase_admin_client.table("review_reports").insert(
                        {
                            **rr_payload,
                            "token": None,
                            "expiry_date": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
                        }
                    ).execute()
            except Exception as e:
                print(f"[Reviews] upsert review_reports failed (ignored): {e}")

        if manuscript_id:
            try:
                pending = (
                    supabase_admin_client.table("review_assignments")
                    .select("id")
                    .eq("manuscript_id", str(manuscript_id))
                    .eq("status", "pending")
                    .execute()
                )
                pending_rows = getattr(pending, "data", None) or []
            except Exception:
                pending = (
                    supabase_client.table("review_assignments")
                    .select("id")
                    .eq("manuscript_id", str(manuscript_id))
                    .eq("status", "pending")
                    .execute()
                )
                pending_rows = getattr(pending, "data", None) or []

            if not pending_rows:
                try:
                    supabase_admin_client.table("manuscripts").update({"status": "decision"}).eq(
                        "id", str(manuscript_id)
                    ).execute()
                except Exception:
                    supabase_client.table("manuscripts").update({"status": "decision"}).eq(
                        "id", str(manuscript_id)
                    ).execute()

        return {"success": True, "data": res.data[0] if res.data else {}}
    except APIError as e:
        print(f"Review submit failed: {e}")
        return {"success": False, "message": "review_assignments table not found"}


async def submit_review_by_token_impl(
    *,
    token: str,
    comments_for_author: str | None,
    content: str | None,
    score: int,
    confidential_comments_to_editor: str | None,
    attachment: UploadFile | None,
    supabase_admin_client: Any,
    ensure_review_attachments_bucket_exists_fn,
) -> dict[str, Any]:
    """免登录 token 提交评审（搬运原逻辑）。"""
    public_comments = (comments_for_author or content or "").strip()
    if not public_comments:
        raise HTTPException(status_code=400, detail="comments_for_author is required")
    if score < 1 or score > 5:
        raise HTTPException(status_code=400, detail="score must be 1..5")

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

        attachment_path = None
        if attachment is not None:
            file_bytes = await attachment.read()
            safe_name = (attachment.filename or "attachment").replace("/", "_")
            attachment_path = f"review_reports/{rr['id']}/{safe_name}"
            try:
                ensure_review_attachments_bucket_exists_fn()
                supabase_admin_client.storage.from_("review-attachments").upload(
                    attachment_path,
                    file_bytes,
                    {"content-type": attachment.content_type or "application/octet-stream"},
                )
            except Exception as e:
                print(f"[Review Attachment] upload failed: {e}")
                raise HTTPException(status_code=500, detail="Failed to upload attachment")

        update_payload = {
            "comments_for_author": public_comments,
            "content": public_comments,
            "score": score,
            "status": "completed",
            "confidential_comments_to_editor": confidential_comments_to_editor,
            "attachment_path": attachment_path,
        }
        supabase_admin_client.table("review_reports").update(update_payload).eq("id", rr["id"]).execute()

        try:
            ms_version = 1
            try:
                ms_v = (
                    supabase_admin_client.table("manuscripts")
                    .select("version")
                    .eq("id", rr["manuscript_id"])
                    .single()
                    .execute()
                )
                ms_version = int((getattr(ms_v, "data", None) or {}).get("version") or 1)
            except Exception:
                ms_version = 1

            assignment_rows = []
            try:
                a = (
                    supabase_admin_client.table("review_assignments")
                    .select("id")
                    .eq("manuscript_id", str(rr["manuscript_id"]))
                    .eq("reviewer_id", str(rr["reviewer_id"]))
                    .eq("round_number", ms_version)
                    .order("created_at", desc=True)
                    .limit(1)
                    .execute()
                )
                assignment_rows = getattr(a, "data", None) or []
            except Exception:
                assignment_rows = []

            if not assignment_rows:
                try:
                    a2 = (
                        supabase_admin_client.table("review_assignments")
                        .select("id")
                        .eq("manuscript_id", str(rr["manuscript_id"]))
                        .eq("reviewer_id", str(rr["reviewer_id"]))
                        .order("created_at", desc=True)
                        .limit(1)
                        .execute()
                    )
                    assignment_rows = getattr(a2, "data", None) or []
                except Exception:
                    assignment_rows = []

            if assignment_rows:
                supabase_admin_client.table("review_assignments").update(
                    {
                        "status": "completed",
                        "comments": public_comments,
                        "scores": {"overall": score},
                    }
                ).eq("id", assignment_rows[0]["id"]).execute()

            pending = (
                supabase_admin_client.table("review_assignments")
                .select("id")
                .eq("manuscript_id", str(rr["manuscript_id"]))
                .eq("status", "pending")
                .execute()
            )
            if not (getattr(pending, "data", None) or []):
                supabase_admin_client.table("manuscripts").update({"status": "decision"}).eq(
                    "id", str(rr["manuscript_id"])
                ).execute()
        except Exception as e:
            print(f"[Reviews] token submit sync to assignments/manuscripts failed (ignored): {e}")

        return {"success": True, "data": {"review_report_id": rr["id"]}}
    except HTTPException:
        raise
    except Exception as e:
        print(f"Submit review by token failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to submit review")


async def get_review_by_token_impl(
    *,
    token: str,
    supabase_admin_client: Any,
) -> dict[str, Any]:
    """免登录 token 获取审稿任务（搬运原逻辑）。"""
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
            .select("id,title,abstract,file_path,status")
            .eq("id", rr["manuscript_id"])
            .single()
            .execute()
        )
        ms = getattr(ms_resp, "data", None) or {}

        latest_revision = None
        try:
            rev_resp = (
                supabase_admin_client.table("revisions")
                .select("id, round_number, decision_type, editor_comment, response_letter, status, submitted_at, created_at")
                .eq("manuscript_id", rr["manuscript_id"])
                .order("round_number", desc=True)
                .limit(1)
                .execute()
            )
            revs = getattr(rev_resp, "data", None) or []
            latest_revision = revs[0] if revs else None
        except Exception:
            latest_revision = None

        return {"success": True, "data": {"review_report": rr, "manuscript": ms, "latest_revision": latest_revision}}
    except HTTPException:
        raise
    except Exception as e:
        print(f"Get review by token failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch review task")
