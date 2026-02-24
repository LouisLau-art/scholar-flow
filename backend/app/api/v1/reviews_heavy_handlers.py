from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict
from urllib.parse import quote
from uuid import UUID

from fastapi import HTTPException, UploadFile
from postgrest.exceptions import APIError


async def assign_reviewer_impl(
    *,
    background_tasks,
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
    safe_insert_invite_policy_audit_fn,
    notification_service_cls,
    email_service_obj,
    create_magic_link_jwt_fn,
    is_foreign_key_user_error_fn,
    is_missing_relation_error_fn,
) -> dict[str, Any]:
    """编辑分配审稿人（搬运原逻辑）。"""
    requester_roles = set(normalize_roles_fn(parse_roles_fn(profile)))
    policy_service = review_policy_service_cls()
    reviewer_id_str = str(reviewer_id)
    manuscript_id_str = str(manuscript_id)

    ms_res = (
        supabase_client.table("manuscripts")
        .select("id, author_id, title, version, status, owner_id, file_path, journal_id, assistant_editor_id")
        .eq("id", manuscript_id_str)
        .single()
        .execute()
    )
    manuscript = ms_res.data or {}
    if not manuscript:
        raise HTTPException(status_code=404, detail="Manuscript not found")
    ensure_review_management_access_fn(
        manuscript=manuscript,
        user_id=str(current_user.get("id") or ""),
        roles=requester_roles,
    )

    if ms_res.data and str(ms_res.data["author_id"]) == str(reviewer_id):
        raise HTTPException(status_code=400, detail="作者不能评审自己的稿件")

    file_path = manuscript.get("file_path")
    if not file_path:
        raise HTTPException(
            status_code=400,
            detail="该稿件缺少 PDF（file_path 为空），无法分配审稿人。请先在投稿/修订流程上传 PDF。",
        )

    owner_raw = manuscript.get("owner_id")
    if not owner_raw:
        try:
            supabase_admin_client.table("manuscripts").update({"owner_id": str(current_user["id"])}).eq(
                "id", manuscript_id_str
            ).execute()
            owner_raw = str(current_user["id"])
        except Exception as e:
            print(f"[OwnerBinding] auto-bind owner_id failed: {e}")
            raise HTTPException(status_code=500, detail="Failed to bind Internal Owner")

    current_version = manuscript.get("version", 1) if manuscript else 1

    try:
        existing = (
            supabase_admin_client.table("review_assignments")
            .select("id, status, due_at, reviewer_id, round_number")
            .eq("manuscript_id", manuscript_id_str)
            .eq("reviewer_id", reviewer_id_str)
            .eq("round_number", current_version)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        if getattr(existing, "data", None):
            return {
                "success": True,
                "data": existing.data[0],
                "policy": policy_service.evaluate_candidates(manuscript=manuscript, reviewer_ids=[reviewer_id_str]).get(
                    reviewer_id_str
                )
                or {},
                "message": "Reviewer already assigned",
            }

        policy = policy_service.evaluate_candidates(manuscript=manuscript, reviewer_ids=[reviewer_id_str]).get(
            reviewer_id_str
        ) or {
            "can_assign": True,
            "allow_override": False,
            "cooldown_active": False,
            "conflict": False,
            "overdue_risk": False,
            "overdue_open_count": 0,
            "hits": [],
        }
        if policy.get("conflict"):
            raise HTTPException(status_code=400, detail="Invitation blocked: conflict of interest")
        override_role_set = {str(r).strip().lower() for r in policy_service.cooldown_override_roles() if str(r).strip()}
        can_override_cooldown = bool(requester_roles & override_role_set)
        if override_cooldown and not policy.get("cooldown_active"):
            override_cooldown = False
        if policy.get("cooldown_active"):
            cooldown_until = str(policy.get("cooldown_until") or "").strip()
            cooldown_suffix = f" until {cooldown_until}" if cooldown_until else ""
            if not can_override_cooldown:
                raise HTTPException(status_code=409, detail=f"Invitation blocked: cooldown active{cooldown_suffix}")
            if not override_cooldown:
                raise HTTPException(
                    status_code=409,
                    detail=f"Invitation blocked: cooldown active{cooldown_suffix}; override_cooldown=true required",
                )

        _min_days, _max_days, default_days = policy_service.due_window_days()
        due_at = (datetime.now(timezone.utc) + timedelta(days=default_days)).isoformat()
        invited_at = datetime.now(timezone.utc).isoformat()
        insert_payload = {
            "manuscript_id": manuscript_id_str,
            "reviewer_id": reviewer_id_str,
            "status": "pending",
            "due_at": due_at,
            "invited_at": invited_at,
            "round_number": current_version,
        }
        try:
            res = (
                supabase_admin_client.table("review_assignments")
                .insert(insert_payload)
                .execute()
            )
        except Exception as insert_err:
            if "invited_at" in str(insert_err).lower() and "column" in str(insert_err).lower():
                insert_payload.pop("invited_at", None)
                res = (
                    supabase_admin_client.table("review_assignments")
                    .insert(insert_payload)
                    .execute()
                )
            else:
                raise
        supabase_admin_client.table("manuscripts").update({"status": "under_review"}).eq(
            "id", manuscript_id_str
        ).execute()

        if policy.get("cooldown_active"):
            safe_insert_invite_policy_audit_fn(
                manuscript_id=manuscript_id_str,
                from_status=str(manuscript.get("status") or ""),
                to_status="under_review",
                changed_by=str(current_user.get("id") or ""),
                comment="reviewer_invite_cooldown_override",
                payload={
                    "action": "reviewer_invite_cooldown_override",
                    "reviewer_id": reviewer_id_str,
                    "manuscript_id": manuscript_id_str,
                    "override_applied": bool(override_cooldown),
                    "override_reason": str(override_reason or "").strip() or None,
                    "cooldown_days": policy_service.cooldown_days(),
                    "allowed_roles": sorted(override_role_set),
                    "policy_hits": policy.get("hits") or [],
                },
            )

        manuscript_title = manuscript.get("title") or "Manuscript"
        notification_service_cls().create_notification(
            user_id=reviewer_id_str,
            manuscript_id=manuscript_id_str,
            type="review_invite",
            title="Review Invitation",
            content=f"You have been invited to review '{manuscript_title}'.",
        )

        try:
            profile_res = (
                supabase_admin_client.table("user_profiles")
                .select("email,full_name")
                .eq("id", reviewer_id_str)
                .single()
                .execute()
            )
            reviewer_profile = getattr(profile_res, "data", None) or {}
            reviewer_email = reviewer_profile.get("email")
            reviewer_name = reviewer_profile.get("full_name") or "Reviewer"
        except Exception:
            reviewer_email = None
            reviewer_name = "Reviewer"

        journal_title = "ScholarFlow Journal"
        journal_id = str(manuscript.get("journal_id") or "").strip()
        if journal_id:
            try:
                jr = (
                    supabase_admin_client.table("journals")
                    .select("title")
                    .eq("id", journal_id)
                    .single()
                    .execute()
                )
                journal_title = str((getattr(jr, "data", None) or {}).get("title") or journal_title)
            except Exception:
                pass

        if reviewer_email:
            assignment_id = None
            try:
                assignment_id = (res.data or [])[0].get("id") if isinstance(res.data, list) else None
            except Exception:
                assignment_id = None
            if assignment_id:
                try:
                    expires_days = int((os.environ.get("MAGIC_LINK_EXPIRES_DAYS") or "14").strip())
                except ValueError:
                    expires_days = 14
                try:
                    assignment_uuid = UUID(str(assignment_id))
                except Exception:
                    assignment_uuid = None
                token = None
                if assignment_uuid:
                    try:
                        token = create_magic_link_jwt_fn(
                            reviewer_id=reviewer_id,
                            manuscript_id=manuscript_id,
                            assignment_id=assignment_uuid,
                            expires_in_days=expires_days,
                        )
                    except RuntimeError as e:
                        if "not configured" in str(e).lower():
                            print(f"[MagicLink] secret missing (ignored): {e}")
                            token = None
                        else:
                            raise
                    except Exception as e:
                        print(f"[MagicLink] token generation failed (ignored): {e}")
                        token = None
            else:
                token = None

            frontend_base_url = (os.environ.get("FRONTEND_BASE_URL") or "http://localhost:3000").rstrip("/")
            review_url = (
                f"{frontend_base_url}/review/invite?token={quote(str(token))}"
                if token
                else f"{frontend_base_url}/dashboard"
            )

            background_tasks.add_task(
                email_service_obj.send_email_background,
                to_email=reviewer_email,
                subject="Invitation to Review",
                template_name="invitation.html",
                context={
                    "review_url": review_url,
                    "reviewer_name": reviewer_name,
                    "manuscript_title": manuscript_title,
                    "manuscript_id": str(manuscript_id),
                    "journal_title": journal_title,
                    "due_at": due_at,
                    "due_date": str(due_at).split("T")[0],
                },
            )

        row = (getattr(res, "data", None) or [{}])[0]
        return {"success": True, "data": row, "policy": policy}
    except HTTPException:
        raise
    except APIError as e:
        if is_foreign_key_user_error_fn(e, constraint="review_assignments_reviewer_id_fkey"):
            raise HTTPException(
                status_code=400,
                detail=(
                    "该审稿人账号不存在于 Supabase Auth（可能是 mock user_profiles）。"
                    "请用「Invite New」创建真实账号，或运行 scripts/seed_mock_reviewers_auth.py 生成可指派 reviewer。"
                ),
            )
        if is_missing_relation_error_fn(e, relation="review_assignments"):
            raise HTTPException(
                status_code=500,
                detail="review_assignments 表不存在或 Schema cache 未更新（请先在云端 Supabase 创建/迁移该表）。",
            )
        raise HTTPException(status_code=500, detail=f"Failed to assign reviewer: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to assign reviewer: {e}")


async def establish_reviewer_workspace_session_impl(
    *,
    assignment_id: UUID,
    response,
    current_user: Dict[str, Any],
    supabase_admin_client: Any,
    create_magic_link_jwt_fn,
) -> dict[str, Any]:
    """登录态 Reviewer 会话桥接（搬运原逻辑）。"""
    reviewer_id = str(current_user.get("id") or "").strip()
    if not reviewer_id:
        raise HTTPException(status_code=401, detail="Unauthorized")

    try:
        a = (
            supabase_admin_client.table("review_assignments")
            .select("id, reviewer_id, manuscript_id, status")
            .eq("id", str(assignment_id))
            .single()
            .execute()
        )
        assignment = getattr(a, "data", None) or {}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load assignment: {e}")

    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")
    if str(assignment.get("reviewer_id") or "") != reviewer_id:
        raise HTTPException(status_code=403, detail="Not allowed to access this assignment")
    if str(assignment.get("status") or "").lower() == "cancelled":
        raise HTTPException(status_code=403, detail="Invitation revoked")

    try:
        status_raw = str(assignment.get("status") or "").strip().lower()
        if status_raw not in {"completed", "declined", "cancelled", "accepted"}:
            now_iso = datetime.now(timezone.utc).isoformat()
            try:
                supabase_admin_client.table("review_assignments").update(
                    {
                        "accepted_at": now_iso,
                        "opened_at": now_iso,
                    }
                ).eq("id", str(assignment_id)).execute()
            except Exception as e:
                lowered = str(e).lower()
                if "accepted_at" in lowered or "opened_at" in lowered or "column" in lowered:
                    try:
                        supabase_admin_client.table("review_assignments").update({"status": "accepted"}).eq(
                            "id", str(assignment_id)
                        ).execute()
                    except Exception:
                        pass
    except Exception:
        pass

    try:
        token = create_magic_link_jwt_fn(
            reviewer_id=UUID(str(assignment.get("reviewer_id"))),
            manuscript_id=UUID(str(assignment.get("manuscript_id"))),
            assignment_id=UUID(str(assignment.get("id"))),
            expires_in_days=14,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create reviewer session: {e}")

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
    """撤销审稿指派（搬运原逻辑）。"""
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

        delete_q = (
            supabase_admin_client.table("review_assignments")
            .delete()
            .eq("manuscript_id", manuscript_id)
            .eq("reviewer_id", reviewer_id)
        )
        if round_number is not None:
            delete_q = delete_q.eq("round_number", round_number)
        delete_q.execute()

        try:
            supabase_admin_client.table("review_reports").delete().eq(
                "manuscript_id", manuscript_id
            ).eq("reviewer_id", reviewer_id).in_(
                "status", ["invited", "pending"]
            ).execute()
        except Exception:
            pass

        remaining_res = (
            supabase_admin_client.table("review_assignments")
            .select("id")
            .eq("manuscript_id", manuscript_id)
            .execute()
        )
        remaining_count = len(remaining_res.data or [])

        if remaining_count == 0:
            supabase_admin_client.table("manuscripts").update({"status": "pre_check"}).eq(
                "id", manuscript_id
            ).execute()

        return {"success": True, "message": "Reviewer unassigned"}
    except Exception as e:
        print(f"Unassign failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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
    """获取稿件审稿指派（搬运原逻辑）。"""
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

        res = (
            supabase_admin_client.table("review_assignments")
            .select(
                "id, status, due_at, reviewer_id, round_number, created_at"
            )
            .eq("manuscript_id", str(manuscript_id))
            .order("created_at", desc=True)
            .execute()
        )
        assignments = res.data or []

        target_round: int | None = None
        if round_number is not None:
            target_round = int(round_number)
        else:
            ms_version: int | None = None
            try:
                ms = (
                    supabase_admin_client.table("manuscripts")
                    .select("version")
                    .eq("id", str(manuscript_id))
                    .single()
                    .execute()
                )
                ms_version = int((getattr(ms, "data", None) or {}).get("version") or 1)
            except Exception:
                ms_version = None

            if assignments:
                try:
                    max_round = max(int(a.get("round_number") or 1) for a in assignments)
                except Exception:
                    max_round = 1

                if ms_version is not None and any(
                    int(a.get("round_number") or 1) == int(ms_version) for a in assignments
                ):
                    target_round = int(ms_version)
                else:
                    target_round = int(max_round)
            else:
                target_round = ms_version

        if target_round is not None and assignments:
            assignments = [
                a
                for a in assignments
                if int(a.get("round_number") or 1) == int(target_round)
            ]

        reviewer_ids = list({a.get("reviewer_id") for a in assignments if a.get("reviewer_id")})
        profiles_by_id: Dict[str, Dict[str, Any]] = {}
        if reviewer_ids:
            try:
                profiles_res = (
                    supabase_admin_client.table("user_profiles")
                    .select("id, full_name, email")
                    .in_("id", reviewer_ids)
                    .execute()
                )
                for p in (profiles_res.data or []):
                    pid = p.get("id")
                    if pid:
                        profiles_by_id[str(pid)] = p
            except Exception as e:
                print(f"Fetch reviewer profiles failed (fallback to ids only): {e}")

        seen_keys = set()
        result = []
        for item in assignments:
            rid = str(item.get("reviewer_id") or "")
            rnd = item.get("round_number", 1)
            key = (rid, rnd)
            if not rid or key in seen_keys:
                continue
            seen_keys.add(key)
            profile_row = profiles_by_id.get(rid, {})
            result.append(
                {
                    "id": item["id"],
                    "status": item.get("status"),
                    "due_at": item.get("due_at"),
                    "round_number": rnd,
                    "reviewer_id": rid,
                    "reviewer_name": profile_row.get("full_name") or "Unknown",
                    "reviewer_email": profile_row.get("email") or "",
                }
            )
        return {"success": True, "data": result}
    except Exception as e:
        print(f"Fetch assignments failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to load reviewer assignments")


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
