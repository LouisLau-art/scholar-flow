from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

from fastapi import BackgroundTasks, HTTPException

from app.core.role_matrix import can_perform_action
from app.models.manuscript import ManuscriptStatus, normalize_status
from app.services.notification_service import NotificationService
from app.services.revision_service import RevisionService


async def get_editor_pipeline_impl(
    *,
    supabase_admin_client: Any,
    extract_data_fn,
    per_stage_limit: int | None = None,
) -> dict[str, Any]:
    """
    获取全站稿件流转状态看板数据。

    中文注释:
    - 仅搬运原有逻辑到独立模块，避免 editor.py 继续膨胀。
    - 业务行为保持不变。
    """
    try:
        # 中文注释: 这里使用 service_role 读取，避免启用 RLS 的云端环境导致 editor 看板空数据。
        db = supabase_admin_client
        default_limit_raw = str(os.getenv("EDITOR_PIPELINE_STAGE_LIMIT", "80") or "80").strip()
        try:
            default_limit = int(default_limit_raw)
        except Exception:
            default_limit = 80
        stage_limit = max(10, min(int(per_stage_limit or default_limit), 300))

        def _with_limit(query):
            if hasattr(query, "limit"):
                return query.limit(stage_limit)
            return query

        # Pre-check（旧：submitted/pending_quality）
        pending_quality_resp = _with_limit(
            db.table("manuscripts")
            .select("*")
            .eq("status", "pre_check")
            .order("created_at", desc=True)
        ).execute()
        pending_quality = extract_data_fn(pending_quality_resp) or []

        # 评审中 (under_review)
        under_review_resp = _with_limit(
            db.table("manuscripts")
            .select("*, review_assignments(count)")
            .eq("status", "under_review")
            .order("created_at", desc=True)
        ).execute()
        under_review_data = extract_data_fn(under_review_resp) or []
        # 中文注释: review_assignments(count) 会按“行数”计数，若历史/并发导致重复指派，会把同一 reviewer 计为 2。
        # 这里改为统计 distinct reviewer_id，保证 UI 中 review_count 与“人数”一致。
        under_review_ids = [str(m.get("id")) for m in under_review_data if m.get("id")]
        reviewers_by_ms: dict[str, set[str]] = {}
        if under_review_ids and hasattr(db.table("review_assignments"), "in_"):
            try:
                ras = (
                    db.table("review_assignments")
                    .select("manuscript_id, reviewer_id")
                    .in_("manuscript_id", under_review_ids)
                    .execute()
                )
                for row in (getattr(ras, "data", None) or []):
                    mid = str(row.get("manuscript_id") or "")
                    rid = str(row.get("reviewer_id") or "")
                    if not mid or not rid:
                        continue
                    reviewers_by_ms.setdefault(mid, set()).add(rid)
            except Exception as e:
                print(f"Pipeline reviewer count fallback to row count: {e}")
        under_review = []
        for item in under_review_data:
            mid = str(item.get("id") or "")
            distinct_count = len(reviewers_by_ms.get(mid, set())) if reviewers_by_ms else 0
            if distinct_count == 0 and "review_assignments" in item:
                # 兜底：若 distinct 查询失败，仍用后端原始 count
                ra = item["review_assignments"]
                if isinstance(ra, list) and ra and isinstance(ra[0], dict) and "count" in ra[0]:
                    distinct_count = ra[0].get("count", 0)
                elif isinstance(ra, list):
                    distinct_count = len(ra)

            item["review_count"] = distinct_count
            if "review_assignments" in item:
                del item["review_assignments"]
            under_review.append(item)

        # 待决策（decision，旧：pending_decision）
        pending_decision_resp = _with_limit(
            db.table("manuscripts")
            .select("*, review_assignments(count)")
            .eq("status", "decision")
            .order("created_at", desc=True)
        ).execute()
        pending_decision_data = extract_data_fn(pending_decision_resp) or []
        pending_ids = [str(m.get("id")) for m in pending_decision_data if m.get("id")]
        reviewers_by_ms_pending: dict[str, set[str]] = {}
        if pending_ids and hasattr(db.table("review_assignments"), "in_"):
            try:
                ras = (
                    db.table("review_assignments")
                    .select("manuscript_id, reviewer_id")
                    .in_("manuscript_id", pending_ids)
                    .execute()
                )
                for row in (getattr(ras, "data", None) or []):
                    mid = str(row.get("manuscript_id") or "")
                    rid = str(row.get("reviewer_id") or "")
                    if not mid or not rid:
                        continue
                    reviewers_by_ms_pending.setdefault(mid, set()).add(rid)
            except Exception as e:
                print(f"Pipeline reviewer count fallback to row count (pending_decision): {e}")
        pending_decision = []
        for item in pending_decision_data:
            mid = str(item.get("id") or "")
            distinct_count = len(reviewers_by_ms_pending.get(mid, set())) if reviewers_by_ms_pending else 0
            if distinct_count == 0 and "review_assignments" in item:
                ra = item["review_assignments"]
                if isinstance(ra, list) and ra and isinstance(ra[0], dict) and "count" in ra[0]:
                    distinct_count = ra[0].get("count", 0)
                elif isinstance(ra, list):
                    distinct_count = len(ra)

            item["review_count"] = distinct_count
            if "review_assignments" in item:
                del item["review_assignments"]
            pending_decision.append(item)

        # Post-acceptance（approved/layout/english_editing/proofreading）- 需要显示发文前的财务状态
        approved_query = (
            db.table("manuscripts")
            .select("*, invoices(id,amount,status)")
            .order("updated_at", desc=True)
        )
        if hasattr(approved_query, "in_"):
            approved_query = approved_query.in_("status", ["approved", "layout", "english_editing", "proofreading"])
        else:
            # 单元测试 stub client 可能不实现 in_；此时仅返回 approved，避免抛错阻断看板。
            approved_query = approved_query.eq("status", "approved")
        approved_resp = _with_limit(approved_query).execute()
        approved_data = extract_data_fn(approved_resp) or []
        approved = []
        for item in approved_data:
            invoices = item.get("invoices")
            # PostgREST 1:1 关联可能返回 dict（而不是 list）
            if isinstance(invoices, dict):
                inv = invoices
            elif isinstance(invoices, list):
                inv = invoices[0] if invoices else {}
            else:
                inv = {}
            item["invoice_amount"] = inv.get("amount")
            item["invoice_status"] = inv.get("status")
            item["invoice_id"] = inv.get("id")
            if "invoices" in item:
                del item["invoices"]
            approved.append(item)

        # 已发布 (published)
        published_resp = _with_limit(
            db.table("manuscripts")
            .select("*")
            .eq("status", "published")
            .order("created_at", desc=True)
        ).execute()
        published = extract_data_fn(published_resp) or []

        # 待处理修订稿 (resubmitted) - 类似待质检，需 Editor 处理
        resubmitted_resp = _with_limit(
            db.table("manuscripts")
            .select("*")
            .eq("status", "resubmitted")
            .order("updated_at", desc=True)
        ).execute()
        resubmitted = extract_data_fn(resubmitted_resp) or []

        # 等待作者修订（major/minor revision，旧：revision_requested）- 监控用
        revision_requested = []
        try:
            rr_query = (
                db.table("manuscripts")
                .select("*")
                .order("updated_at", desc=True)
            )
            if hasattr(rr_query, "in_"):
                rr_query = rr_query.in_("status", ["major_revision", "minor_revision"])
                revision_requested = extract_data_fn(_with_limit(rr_query).execute()) or []
            else:
                # fallback: 两次 eq 合并（不阻断）
                maj = extract_data_fn(
                    _with_limit(
                        db.table("manuscripts").select("*").eq("status", "major_revision").order("updated_at", desc=True)
                    ).execute()
                ) or []
                minor = extract_data_fn(
                    _with_limit(
                        db.table("manuscripts").select("*").eq("status", "minor_revision").order("updated_at", desc=True)
                    ).execute()
                ) or []
                revision_requested = (maj or []) + (minor or [])
        except Exception as e:
            print(f"Pipeline revision_requested fallback empty: {e}")

        # 已拒稿 (rejected) - 终态归档
        rejected_resp = _with_limit(
            db.table("manuscripts")
            .select("*")
            .eq("status", "rejected")
            .order("updated_at", desc=True)
        ).execute()
        rejected = extract_data_fn(rejected_resp) or []

        return {
            "success": True,
            "data": {
                "pending_quality": pending_quality,
                "resubmitted": resubmitted,
                "under_review": under_review,
                "revision_requested": revision_requested,
                "pending_decision": pending_decision,
                "approved": approved,
                "published": published,
                "rejected": rejected,
            },
        }

    except Exception as e:
        print(f"Pipeline query failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch pipeline data")


async def request_revision_impl(
    *,
    request,
    profile: dict[str, Any],
    background_tasks: BackgroundTasks | None,
    supabase_admin_client: Any,
) -> Any:
    """Editor 请求修订（搬运原逻辑）。"""
    # MVP 业务规则:
    # - 上一轮如果是“小修”，Editor 不允许升级成“大修”；如确需升级，必须由 Admin 执行。
    try:
        roles = set((profile or {}).get("roles") or [])
        if request.decision_type == "major" and "admin" not in roles:
            latest = (
                supabase_admin_client.table("revisions")
                .select("decision_type, round_number")
                .eq("manuscript_id", str(request.manuscript_id))
                .order("round_number", desc=True)
                .limit(1)
                .execute()
            )
            latest_rows = getattr(latest, "data", None) or []
            if latest_rows:
                last_type = str(latest_rows[0].get("decision_type") or "").strip().lower()
                if last_type == "minor":
                    raise HTTPException(
                        status_code=403,
                        detail="该稿件上一轮为小修，编辑无权升级为大修；如确需大修请用 Admin 账号操作。",
                    )
    except HTTPException:
        raise
    except Exception as e:
        print(f"[Revision] major-after-minor guard failed (ignored): {e}")

    service = RevisionService()
    result = service.create_revision_request(
        manuscript_id=str(request.manuscript_id),
        decision_type=request.decision_type,
        editor_comment=request.comment,
    )

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])

    # === 通知中心 (Feature 011 / T024) ===
    try:
        manuscript = service.get_manuscript(str(request.manuscript_id))
        if manuscript:
            author_id = manuscript.get("author_id")
            title = manuscript.get("title", "Manuscript")

            notification_service = NotificationService()
            notification_service.create_notification(
                user_id=str(author_id),
                manuscript_id=str(request.manuscript_id),
                type="decision",
                title="Revision Requested",
                content=f"Editor has requested a {request.decision_type} revision for '{title}'.",
            )

            # Feature 025: Send Email
            if background_tasks:
                try:
                    prof = supabase_admin_client.table("user_profiles").select("email, full_name").eq("id", str(author_id)).single().execute()
                    pdata = getattr(prof, "data", None) or {}
                    author_email = pdata.get("email")
                    recipient_name = pdata.get("full_name") or "Author"

                    if author_email:
                        from app.core.mail import email_service

                        background_tasks.add_task(
                            email_service.send_email_background,
                            to_email=author_email,
                            subject="Revision Requested",
                            template_name="status_update.html",
                            context={
                                "recipient_name": recipient_name,
                                "manuscript_title": title,
                                "decision_label": f"{request.decision_type.capitalize()} Revision Requested",
                                "comment": request.comment or "Please check the portal for details.",
                            },
                        )
                except Exception as e:
                    print(f"[Email] Failed to send revision email: {e}")

    except Exception as e:
        print(f"[Notifications] Failed to send revision notification: {e}")

    return result


async def get_available_reviewers_impl(
    *,
    current_user: dict[str, Any],
    supabase_client: Any,
    extract_data_fn,
) -> dict[str, Any]:
    """获取可用的审稿人专家池（搬运原逻辑）。"""
    try:
        user_id = current_user.get("id")
        email = current_user.get("email")
        self_candidate = None
        if user_id and email:
            name_part = email.split("@")[0].replace(".", " ").title()
            self_candidate = {
                "id": str(user_id),
                "name": f"{name_part} (You)",
                "email": email,
                "affiliation": "Your Account",
                "expertise": ["AI", "Systems"],
                "review_count": 0,
            }

        reviewers_resp = (
            supabase_client.table("user_profiles")
            .select("id, email, roles")
            .contains("roles", ["reviewer"])
            .execute()
        )
        reviewers = extract_data_fn(reviewers_resp) or []

        formatted_reviewers = []
        for reviewer in reviewers:
            email = reviewer.get("email") or "reviewer@example.com"
            name_part = email.split("@")[0].replace(".", " ").title()
            formatted_reviewers.append(
                {
                    "id": reviewer["id"],
                    "name": name_part or "Reviewer",
                    "email": email,
                    "affiliation": "Independent Researcher",
                    "expertise": ["AI", "Systems"],
                    "review_count": 0,
                }
            )

        if formatted_reviewers:
            if self_candidate and not any(r["id"] == self_candidate["id"] for r in formatted_reviewers):
                formatted_reviewers.insert(0, self_candidate)
            return {"success": True, "data": formatted_reviewers}

        # fallback: demo reviewers for empty dataset
        if self_candidate:
            return {
                "success": True,
                "data": [
                    self_candidate,
                    {
                        "id": "88888888-8888-8888-8888-888888888888",
                        "name": "Dr. Demo Reviewer",
                        "email": "reviewer1@example.com",
                        "affiliation": "Demo Lab",
                        "expertise": ["AI", "NLP"],
                        "review_count": 12,
                    },
                    {
                        "id": "77777777-7777-7777-7777-777777777777",
                        "name": "Prof. Sample Expert",
                        "email": "reviewer2@example.com",
                        "affiliation": "Sample University",
                        "expertise": ["Machine Learning", "Computer Vision"],
                        "review_count": 8,
                    },
                    {
                        "id": "66666666-6666-6666-6666-666666666666",
                        "name": "Dr. Placeholder",
                        "email": "reviewer3@example.com",
                        "affiliation": "Research Institute",
                        "expertise": ["Security", "Blockchain"],
                        "review_count": 5,
                    },
                ],
            }
        return {
            "success": True,
            "data": [
                {
                    "id": "88888888-8888-8888-8888-888888888888",
                    "name": "Dr. Demo Reviewer",
                    "email": "reviewer1@example.com",
                    "affiliation": "Demo Lab",
                    "expertise": ["AI", "NLP"],
                    "review_count": 12,
                },
                {
                    "id": "77777777-7777-7777-7777-777777777777",
                    "name": "Prof. Sample Expert",
                    "email": "reviewer2@example.com",
                    "affiliation": "Sample University",
                    "expertise": ["Machine Learning", "Computer Vision"],
                    "review_count": 8,
                },
                {
                    "id": "66666666-6666-6666-6666-666666666666",
                    "name": "Dr. Placeholder",
                    "email": "reviewer3@example.com",
                    "affiliation": "Research Institute",
                    "expertise": ["Security", "Blockchain"],
                    "review_count": 5,
                },
            ],
        }

    except Exception as e:
        print(f"Reviewers query failed: {e}")
        if self_candidate:
            return {"success": True, "data": [self_candidate]}
        return {"success": True, "data": []}


async def search_reviewer_library_impl(
    *,
    query: str,
    page: int,
    page_size: int,
    manuscript_id: str | None,
    profile: dict[str, Any],
    supabase_admin_client: Any,
    reviewer_service_cls,
    review_policy_service_cls,
    normalize_roles_fn,
) -> dict[str, Any]:
    """Reviewer Library 搜索（搬运原逻辑并保留依赖注入）。"""
    try:
        reviewer_service = reviewer_service_cls()
        rows: list[dict[str, Any]]
        pagination: dict[str, Any]
        if hasattr(reviewer_service, "search_page"):
            page_result = reviewer_service.search_page(query=query, page=page, page_size=page_size)
            rows = list(page_result.get("items") or [])
            pagination = {
                "page": int(page_result.get("page") or page),
                "page_size": int(page_result.get("page_size") or page_size),
                "returned": len(rows),
                "has_more": bool(page_result.get("has_more")),
            }
        else:
            # 兼容旧测试 stub（仅实现 search(query, limit)）。
            rows = reviewer_service.search(query=query, limit=page_size)
            pagination = {
                "page": int(page),
                "page_size": int(page_size),
                "returned": len(rows),
                "has_more": len(rows) >= int(page_size),
            }
        meta: dict[str, Any] = {}
        normalized_roles = set(normalize_roles_fn(profile.get("roles") or []))
        if "assistant_editor" in normalized_roles and "managing_editor" not in normalized_roles and not manuscript_id:
            raise HTTPException(status_code=422, detail="manuscript_id is required for assistant editor reviewer search")

        if manuscript_id:
            ms_resp = (
                supabase_admin_client.table("manuscripts")
                .select("id,author_id,journal_id,status,assistant_editor_id")
                .eq("id", manuscript_id)
                .single()
                .execute()
            )
            manuscript = getattr(ms_resp, "data", None) or {}
            if not manuscript:
                raise HTTPException(status_code=404, detail="Manuscript not found")

            if "admin" not in normalized_roles:
                # 纯 AE 仅允许访问自己分管稿件的候选池（ME/Admin 保持现有可见范围）。
                if "assistant_editor" in normalized_roles and "managing_editor" not in normalized_roles:
                    assigned_ae = str(manuscript.get("assistant_editor_id") or "").strip()
                    if assigned_ae != str(profile.get("id") or "").strip():
                        raise HTTPException(status_code=403, detail="Forbidden: manuscript not assigned to current assistant editor")
                elif "managing_editor" not in normalized_roles:
                    raise HTTPException(status_code=403, detail="Insufficient role")

            policy_service = review_policy_service_cls()
            reviewer_ids = [str(r.get("id") or "").strip() for r in rows if str(r.get("id") or "").strip()]
            policy_map = policy_service.evaluate_candidates(manuscript=manuscript, reviewer_ids=reviewer_ids)
            for row in rows:
                rid = str(row.get("id") or "").strip()
                row["invite_policy"] = policy_map.get(rid) or {
                    "can_assign": True,
                    "allow_override": False,
                    "cooldown_active": False,
                    "conflict": False,
                    "overdue_risk": False,
                    "overdue_open_count": 0,
                    "hits": [],
                }
            meta = {
                "cooldown_days": policy_service.cooldown_days(),
                "override_roles": policy_service.cooldown_override_roles(),
            }
        return {"success": True, "data": rows, "policy": meta, "pagination": pagination}
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ReviewerLibrary] search failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to search reviewer library")


async def submit_final_decision_impl(
    *,
    background_tasks: BackgroundTasks | None,
    current_user: dict[str, Any],
    profile: dict[str, Any],
    manuscript_id: str,
    decision: str,
    comment: str,
    apc_amount: float | None,
    supabase_admin_client: Any,
    extract_error_fn,
    extract_data_fn,
    is_missing_column_error_fn,
    require_action_or_403_fn,
    ensure_manuscript_scope_access_fn,
) -> dict[str, Any]:
    """提交最终决策（搬运原逻辑）。"""
    # 验证决策类型
    if decision not in ["accept", "reject"]:
        raise HTTPException(status_code=400, detail="Invalid decision type")
    if decision == "accept":
        if apc_amount is None:
            raise HTTPException(status_code=400, detail="apc_amount is required for accept")
        if apc_amount < 0:
            raise HTTPException(status_code=400, detail="apc_amount must be >= 0")

    roles = profile.get("roles") if isinstance(profile, dict) else ["admin"]
    require_action_or_403_fn(action="decision:submit_final", roles=roles or ["admin"])

    ensure_manuscript_scope_access_fn(
        manuscript_id=manuscript_id,
        user_id=str(current_user.get("id") or ""),
        roles=roles or ["admin"],
        allow_admin_bypass=True,
    )

    try:
        try:
            manuscript_row = (
                supabase_admin_client.table("manuscripts")
                .select("status")
                .eq("id", manuscript_id)
                .single()
                .execute()
            )
        except Exception as e:
            raise HTTPException(status_code=404, detail="Manuscript not found") from e
        manuscript = getattr(manuscript_row, "data", None) or {}
        current_status = normalize_status(str(manuscript.get("status") or ""))
        if not current_status:
            raise HTTPException(status_code=404, detail="Manuscript not found")
        allowed_statuses = {
            ManuscriptStatus.DECISION.value,
            ManuscriptStatus.DECISION_DONE.value,
        }
        # 中文注释:
        # - Accept 后（approved）仍允许再次“accept”以便调整 APC / 触发 invoice upsert（幂等）。
        # - Reject 不允许在 approved 后执行，避免破坏已进入 Production 的稿件。
        if decision == "accept":
            allowed_statuses.add("approved")
        if current_status not in allowed_statuses:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Decision is only allowed in {ManuscriptStatus.DECISION.value}/"
                    f"{ManuscriptStatus.DECISION_DONE.value}. Current: {current_status}"
                ),
            )

        # 更新稿件状态
        if decision == "accept":
            # 录用：仅进入“已录用/待发布”状态；发布必须通过 Financial Gate
            update_data = {"status": "approved"}
        else:
            # 拒稿：进入 rejected 终态（修回请走 /editor/revisions）
            update_data = {"status": "rejected", "reject_comment": comment}

        # 执行更新
        try:
            response = (
                supabase_admin_client.table("manuscripts")
                .update(update_data)
                .eq("id", manuscript_id)
                .execute()
            )
        except Exception as e:
            error_text = str(e)
            print(f"Decision update error: {error_text}")
            if is_missing_column_error_fn(error_text):
                response = (
                    supabase_admin_client.table("manuscripts")
                    .update({"status": update_data["status"]})
                    .eq("id", manuscript_id)
                    .execute()
                )
            else:
                raise

        error = extract_error_fn(response)
        if error and is_missing_column_error_fn(str(error)):
            response = (
                supabase_admin_client.table("manuscripts")
                .update({"status": update_data["status"]})
                .eq("id", manuscript_id)
                .execute()
            )
        elif error:
            raise HTTPException(status_code=500, detail="Failed to submit decision")

        data = extract_data_fn(response) or []
        if len(data) == 0:
            raise HTTPException(status_code=404, detail="Manuscript not found")

        # === Feature 022: APC 确认（录用时创建/更新 Invoice） ===
        if decision == "accept":
            invoice_status = "paid" if apc_amount == 0 else "unpaid"
            invoice_payload = {
                "manuscript_id": manuscript_id,
                "amount": apc_amount,
                "status": invoice_status,
                "confirmed_at": datetime.now().isoformat() if invoice_status == "paid" else None,
            }
            invoice_id: str | None = None
            try:
                inv_upsert = supabase_admin_client.table("invoices").upsert(
                    invoice_payload, on_conflict="manuscript_id"
                ).execute()
                inv_rows = getattr(inv_upsert, "data", None) or []
                if inv_rows:
                    invoice_id = (inv_rows[0] or {}).get("id")
            except Exception as e:
                print(f"[Financial] Failed to upsert invoice: {e}")
                raise HTTPException(status_code=500, detail="Failed to create invoice")

            # === Feature 026: 自动生成并持久化 Invoice PDF（后台任务） ===
            if background_tasks is not None:
                try:
                    if not invoice_id:
                        inv_q = (
                            supabase_admin_client.table("invoices")
                            .select("id")
                            .eq("manuscript_id", manuscript_id)
                            .limit(1)
                            .execute()
                        )
                        inv_q_rows = getattr(inv_q, "data", None) or []
                        invoice_id = (inv_q_rows[0] or {}).get("id") if inv_q_rows else None

                    if invoice_id:
                        from uuid import UUID

                        from app.services.invoice_pdf_service import (
                            generate_and_store_invoice_pdf_safe,
                        )

                        background_tasks.add_task(
                            generate_and_store_invoice_pdf_safe,
                            invoice_id=UUID(str(invoice_id)),
                        )
                except Exception as e:
                    print(f"[InvoicePDF] enqueue failed (ignored): {e}")

        # === MVP: 决策后取消未完成的审稿任务（避免 Reviewer 继续看到该稿件）===
        try:
            supabase_admin_client.table("review_assignments").update({"status": "cancelled"}).eq(
                "manuscript_id", manuscript_id
            ).eq("status", "pending").execute()
        except Exception as e:
            print(f"[Decision] cancel pending review_assignments failed (ignored): {e}")

        # === 通知中心 (Feature 011) ===
        try:
            ms_res = (
                supabase_admin_client.table("manuscripts")
                .select("author_id, title")
                .eq("id", manuscript_id)
                .single()
                .execute()
            )
            ms = getattr(ms_res, "data", None) or {}
            author_id = ms.get("author_id")
            manuscript_title = ms.get("title") or "Manuscript"
        except Exception:
            author_id = None
            manuscript_title = "Manuscript"

        if author_id:
            decision_label = "Accepted" if decision == "accept" else "Rejected"
            decision_title = (
                "Editorial Decision"
                if decision == "accept"
                else "Editorial Decision: Rejected"
            )

            NotificationService().create_notification(
                user_id=str(author_id),
                manuscript_id=manuscript_id,
                type="decision",
                title=decision_title,
                content=f"Decision for '{manuscript_title}': {decision_label}.",
            )

            try:
                author_profile = (
                    supabase_admin_client.table("user_profiles")
                    .select("email")
                    .eq("id", str(author_id))
                    .single()
                    .execute()
                )
                author_email = (getattr(author_profile, "data", None) or {}).get("email")
            except Exception:
                author_email = None

            if author_email and background_tasks is not None:
                from app.core.mail import email_service

                # 1. Decision Email
                background_tasks.add_task(
                    email_service.send_email_background,
                    to_email=author_email,
                    subject=decision_title,
                    template_name="status_update.html",
                    context={
                        "recipient_name": author_email.split("@")[0].replace(".", " ").title(),
                        "manuscript_title": manuscript_title,
                        "decision_label": decision_label,
                        "comment": comment or "",
                    },
                )

                # 2. Invoice Email (Feature 025)
                if decision == "accept" and apc_amount and apc_amount > 0:
                    frontend_base_url = os.environ.get("FRONTEND_BASE_URL", "http://localhost:3000").rstrip("/")
                    invoice_link = f"{frontend_base_url}/dashboard"

                    background_tasks.add_task(
                        email_service.send_email_background,
                        to_email=author_email,
                        subject="Invoice Generated",
                        template_name="invoice.html",
                        context={
                            "recipient_name": author_email.split("@")[0].replace(".", " ").title(),
                            "manuscript_title": manuscript_title,
                            "amount": f"{apc_amount:,.2f}",
                            "link": invoice_link,
                        },
                    )

        # GAP-P1-05 / US3: legacy final decision 审计对齐（before/after/reason/source）
        try:
            now_log = datetime.now(timezone.utc).isoformat()
            supabase_admin_client.table("status_transition_logs").insert(
                {
                    "manuscript_id": manuscript_id,
                    "from_status": current_status,
                    "to_status": str(update_data.get("status") or current_status),
                    "comment": f"legacy final decision: {decision}",
                    "changed_by": str(current_user.get("id") or ""),
                    "created_at": now_log,
                    "payload": {
                        "action": "final_decision_legacy",
                        "decision_stage": "final",
                        "source": "legacy_editor_decision_endpoint",
                        "reason": "editor_submit_final_decision",
                        "decision": decision,
                        "before": {
                            "status": current_status,
                            "apc_amount": None,
                        },
                        "after": {
                            "status": str(update_data.get("status") or current_status),
                            "apc_amount": apc_amount if decision == "accept" else None,
                        },
                    },
                }
            ).execute()
        except Exception:
            pass

        return {
            "success": True,
            "message": "Decision submitted successfully",
            "data": {
                "manuscript_id": manuscript_id,
                "decision": decision,
                "status": update_data["status"],
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"Decision submission failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to submit decision")


async def publish_manuscript_dev_impl(
    *,
    background_tasks: BackgroundTasks | None,
    current_user: dict[str, Any],
    manuscript_id: str,
    supabase_admin_client: Any,
    publish_manuscript_fn,
) -> dict[str, Any]:
    """发布稿件（搬运原逻辑）。"""
    try:
        # Feature 024：保留“直接发布”入口（MVP 提速），发布本身仍强制 Payment/Production Gate。
        # Feature 031 的线性阶段推进（layout/english_editing/proofreading）通过 /production/advance 完成。
        try:
            before = (
                supabase_admin_client.table("manuscripts")
                .select("status")
                .eq("id", manuscript_id)
                .single()
                .execute()
            )
            from_status = str((getattr(before, "data", None) or {}).get("status") or "")
        except Exception:
            from_status = ""
        published = publish_manuscript_fn(manuscript_id=manuscript_id)

        # Feature 031：尽力写入审计日志（不阻断主流程）
        try:
            now = datetime.now(timezone.utc).isoformat()
            supabase_admin_client.table("status_transition_logs").insert(
                {
                    "manuscript_id": manuscript_id,
                    "from_status": from_status,
                    "to_status": "published",
                    "comment": "publish",
                    "changed_by": str(current_user.get("id")),
                    "created_at": now,
                }
            ).execute()
        except Exception:
            pass

        # Feature 024: 发布通知（站内信 + 邮件，失败不影响主流程）
        try:
            ms_res = (
                supabase_admin_client.table("manuscripts")
                .select("author_id, title")
                .eq("id", manuscript_id)
                .single()
                .execute()
            )
            ms = getattr(ms_res, "data", None) or {}
            author_id = ms.get("author_id")
            title = ms.get("title") or "Manuscript"

            if author_id:
                NotificationService().create_notification(
                    user_id=str(author_id),
                    manuscript_id=manuscript_id,
                    type="system",
                    title="Article Published",
                    content=f"Your article '{title}' has been published.",
                    action_url=f"/articles/{manuscript_id}",
                )

                if background_tasks is not None:
                    try:
                        prof = (
                            supabase_admin_client.table("user_profiles")
                            .select("email, full_name")
                            .eq("id", str(author_id))
                            .single()
                            .execute()
                        )
                        pdata = getattr(prof, "data", None) or {}
                        author_email = pdata.get("email")
                        author_name = pdata.get("full_name") or (author_email.split("@")[0] if author_email else "Author")
                    except Exception:
                        author_email = None
                        author_name = "Author"

                    if author_email:
                        from app.core.mail import email_service

                        background_tasks.add_task(
                            email_service.send_email_background,
                            to_email=author_email,
                            subject="Your article has been published",
                            template_name="published.html",
                            context={
                                "recipient_name": author_name,
                                "manuscript_title": title,
                                "doi": published.get("doi"),
                            },
                        )
        except Exception as e:
            print(f"[Publish] notify author failed (ignored): {e}")

        return {"success": True, "data": published}
    except HTTPException:
        raise
    except Exception as e:
        print(f"Publish failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to publish manuscript")
