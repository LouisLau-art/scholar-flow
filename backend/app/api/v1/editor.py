from fastapi import APIRouter, HTTPException, Body, Depends, BackgroundTasks, Query
from app.lib.api_client import supabase, supabase_admin
from app.core.auth_utils import get_current_user
from app.core.roles import require_any_role
from datetime import datetime
from app.core.mail import EmailService
from app.services.notification_service import NotificationService
from app.models.revision import RevisionCreate, RevisionRequestResponse
from app.services.revision_service import RevisionService

router = APIRouter(prefix="/editor", tags=["Editor Command Center"])


def _extract_supabase_data(response):
    """
    兼容 supabase-py / postgrest 在不同版本下的 execute() 返回值形态。
    - 新版: response.data
    - 旧/自定义 mock: (error, data)
    """
    if response is None:
        return None
    data = getattr(response, "data", None)
    if data is not None:
        return data
    if isinstance(response, tuple) and len(response) == 2:
        return response[1]
    return None


def _extract_supabase_error(response):
    """
    兼容不同版本的 supabase-py 错误字段。
    """
    if response is None:
        return None
    error = getattr(response, "error", None)
    if error:
        return error
    if isinstance(response, tuple) and len(response) == 2:
        return response[0]
    return None


def _is_missing_column_error(error_text: str) -> bool:
    if not error_text:
        return False
    lowered = error_text.lower()
    return (
        "column" in lowered
        or "published_at" in lowered
        or "reject_comment" in lowered
        or "doi" in lowered
    )


@router.get("/internal-staff")
async def list_internal_staff(
    search: str = Query("", description="按姓名/邮箱模糊检索（可选）"),
    _profile: dict = Depends(require_any_role(["editor", "admin"])),
):
    """
    Feature 023: 提供 Internal Owner 下拉框的数据源（仅 editor/admin）。
    """
    try:
        query = (
            supabase_admin.table("user_profiles")
            .select("id, email, full_name, roles")
            .or_("roles.cs.{editor},roles.cs.{admin}")
        )
        resp = query.execute()
        data = getattr(resp, "data", None) or []
        if search.strip():
            s = search.strip().lower()
            data = [
                row
                for row in data
                if s in (row.get("email") or "").lower() or s in (row.get("full_name") or "").lower()
            ]
        # 中文注释: 置顶有 full_name 的记录，便于下拉框展示
        data.sort(key=lambda x: (0 if (x.get("full_name") or "").strip() else 1, (x.get("full_name") or x.get("email") or "")))
        return {"success": True, "data": data}
    except Exception as e:
        print(f"[OwnerBinding] 获取内部员工列表失败: {e}")
        raise HTTPException(status_code=500, detail="Failed to load internal staff")


@router.get("/pipeline")
async def get_editor_pipeline(
    current_user: dict = Depends(get_current_user),
    _profile: dict = Depends(require_any_role(["editor", "admin"])),
):
    """
    获取全站稿件流转状态看板数据
    分栏：待质检、评审中、待录用、已发布
    """
    try:
        # 中文注释: 这里使用 service_role 读取，避免启用 RLS 的云端环境导致 editor 看板空数据。
        db = supabase_admin

        # 待质检 (submitted)
        pending_quality_resp = (
            db.table("manuscripts")
            .select("*")
            .eq("status", "submitted")
            .order("created_at", desc=True)
            .execute()
        )
        pending_quality = _extract_supabase_data(pending_quality_resp) or []

        # 评审中 (under_review)
        under_review_resp = (
            db.table("manuscripts")
            .select("*, review_assignments(count)")
            .eq("status", "under_review")
            .order("created_at", desc=True)
            .execute()
        )
        under_review_data = _extract_supabase_data(under_review_resp) or []
        # 中文注释: review_assignments(count) 会按“行数”计数，若历史/并发导致重复指派，会把同一 reviewer 计为 2。
        # 这里改为统计 distinct reviewer_id，保证 UI 中 review_count 与“人数”一致。
        under_review_ids = [str(m.get("id")) for m in under_review_data if m.get("id")]
        reviewers_by_ms: dict[str, set[str]] = {}
        if under_review_ids:
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

        # 待录用 (pending_decision)
        pending_decision_resp = (
            db.table("manuscripts")
            .select("*, review_assignments(count)")
            .eq("status", "pending_decision")
            .order("created_at", desc=True)
            .execute()
        )
        pending_decision_data = _extract_supabase_data(pending_decision_resp) or []
        pending_ids = [str(m.get("id")) for m in pending_decision_data if m.get("id")]
        reviewers_by_ms_pending: dict[str, set[str]] = {}
        if pending_ids:
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

        # 已录用 (approved) - 需要显示发文前的财务状态
        approved_resp = (
            db.table("manuscripts")
            .select("*, invoices(amount,status)")
            .eq("status", "approved")
            .order("updated_at", desc=True)
            .execute()
        )
        approved_data = _extract_supabase_data(approved_resp) or []
        approved = []
        for item in approved_data:
            invoices = item.get("invoices") or []
            inv = invoices[0] if isinstance(invoices, list) and invoices else {}
            item["invoice_amount"] = inv.get("amount")
            item["invoice_status"] = inv.get("status")
            if "invoices" in item:
                del item["invoices"]
            approved.append(item)

        # 已发布 (published)
        published_resp = (
            db.table("manuscripts")
            .select("*")
            .eq("status", "published")
            .order("created_at", desc=True)
            .execute()
        )
        published = _extract_supabase_data(published_resp) or []

        # 待处理修订稿 (resubmitted) - 类似待质检，需 Editor 处理
        resubmitted_resp = (
            db.table("manuscripts")
            .select("*")
            .eq("status", "resubmitted")
            .order("updated_at", desc=True)
            .execute()
        )
        resubmitted = _extract_supabase_data(resubmitted_resp) or []

        # 等待作者修改 (revision_requested) - 监控用
        revision_requested_resp = (
            db.table("manuscripts")
            .select("*")
            .eq("status", "revision_requested")
            .order("updated_at", desc=True)
            .execute()
        )
        revision_requested = _extract_supabase_data(revision_requested_resp) or []

        return {
            "success": True,
            "data": {
                "pending_quality": pending_quality,
                "resubmitted": resubmitted,  # New
                "under_review": under_review,
                "revision_requested": revision_requested,  # New
                "pending_decision": pending_decision,
                "approved": approved,
                "published": published,
            },
        }

    except Exception as e:
        print(f"Pipeline query failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch pipeline data")


@router.post("/revisions", response_model=RevisionRequestResponse)
async def request_revision(
    request: RevisionCreate,
    current_user: dict = Depends(get_current_user),
    _profile: dict = Depends(require_any_role(["editor", "admin"])),
    background_tasks: BackgroundTasks = None,
):
    """
    Editor 请求修订 (Request Revision)

    中文注释:
    1. 只能由 Editor 或 Admin 发起。
    2. 调用 RevisionService 处理核心逻辑（创建快照、更新状态）。
    3. 触发通知给作者。
    """
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

            # TODO (T024): 异步发送邮件
            # if background_tasks: ...

    except Exception as e:
        print(f"[Notifications] Failed to send revision notification: {e}")

    return RevisionRequestResponse(data=result["data"]["revision"])


@router.get("/available-reviewers")
async def get_available_reviewers(
    current_user: dict = Depends(get_current_user),
    _profile: dict = Depends(require_any_role(["editor", "admin"])),
):
    """
    获取可用的审稿人专家池
    """
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
            supabase.table("user_profiles")
            .select("id, email, roles")
            .contains("roles", ["reviewer"])
            .execute()
        )
        reviewers = _extract_supabase_data(reviewers_resp) or []

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
            if self_candidate and not any(
                r["id"] == self_candidate["id"] for r in formatted_reviewers
            ):
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


@router.post("/decision")
async def submit_final_decision(
    background_tasks: BackgroundTasks = None,
    current_user: dict = Depends(get_current_user),
    _profile: dict = Depends(require_any_role(["editor", "admin"])),
    manuscript_id: str = Body(..., embed=True),
    decision: str = Body(..., embed=True),
    comment: str = Body("", embed=True),
    apc_amount: float | None = Body(None, embed=True),
):
    """
    提交最终录用或退回决策
    decision: "accept" | "reject"
    """
    # 验证决策类型
    if decision not in ["accept", "reject"]:
        raise HTTPException(status_code=400, detail="Invalid decision type")

    try:
        # 更新稿件状态
        if decision == "accept":
            # 录用：仅进入“已录用/待发布”状态；发布必须通过 Financial Gate
            if apc_amount is None:
                raise HTTPException(status_code=400, detail="apc_amount is required for accept")
            if apc_amount < 0:
                raise HTTPException(status_code=400, detail="apc_amount must be >= 0")

            update_data = {"status": "approved"}
        else:
            # 退回：设置为需要修改，添加拒绝理由
            update_data = {"status": "revision_required", "reject_comment": comment}

        # 执行更新
        try:
            response = (
                supabase_admin.table("manuscripts")
                .update(update_data)
                .eq("id", manuscript_id)
                .execute()
            )
        except Exception as e:
            error_text = str(e)
            print(f"Decision update error: {error_text}")
            if _is_missing_column_error(error_text):
                response = (
                    supabase_admin.table("manuscripts")
                    .update({"status": update_data["status"]})
                    .eq("id", manuscript_id)
                    .execute()
                )
            else:
                raise

        error = _extract_supabase_error(response)
        if error and _is_missing_column_error(str(error)):
            response = (
                supabase_admin.table("manuscripts")
                .update({"status": update_data["status"]})
                .eq("id", manuscript_id)
                .execute()
            )
        elif error:
            raise HTTPException(status_code=500, detail="Failed to submit decision")

        data = _extract_supabase_data(response) or []
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
            try:
                supabase_admin.table("invoices").upsert(
                    invoice_payload, on_conflict="manuscript_id"
                ).execute()
            except Exception as e:
                print(f"[Financial] Failed to upsert invoice: {e}")
                raise HTTPException(status_code=500, detail="Failed to create invoice")

        # === 通知中心 (Feature 011) ===
        # 中文注释:
        # 1) 稿件决策变更属于核心状态变化：作者必须同时收到站内信 + 邮件（异步）。
        try:
            ms_res = (
                supabase_admin.table("manuscripts")
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
            decision_label = "Accepted" if decision == "accept" else "Revision Required"
            decision_title = (
                "Editorial Decision"
                if decision == "accept"
                else "Editorial Decision: Revision Required"
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
                    supabase_admin.table("user_profiles")
                    .select("email")
                    .eq("id", str(author_id))
                    .single()
                    .execute()
                )
                author_email = (getattr(author_profile, "data", None) or {}).get(
                    "email"
                )
            except Exception:
                author_email = None

            if author_email and background_tasks is not None:
                email_service = EmailService()
                background_tasks.add_task(
                    email_service.send_template_email,
                    to_email=author_email,
                    subject=decision_title,
                    template_name="decision.html",
                    context={
                        "subject": decision_title,
                        "recipient_name": author_email.split("@")[0]
                        .replace(".", " ")
                        .title(),
                        "manuscript_title": manuscript_title,
                        "manuscript_id": manuscript_id,
                        "decision_title": decision_title,
                        "decision_label": decision_label,
                        "comment": comment or "",
                    },
                )

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


@router.post("/publish")
async def publish_manuscript_dev(
    current_user: dict = Depends(get_current_user),
    _profile: dict = Depends(require_any_role(["editor", "admin"])),
    manuscript_id: str = Body(..., embed=True),
):
    """
    快捷发布：将稿件直接设置为 published。

    中文注释:
    1) 用于演示/测试，让公开搜索（published-only）能快速看到结果。
    2) 仍然需要 editor/admin 角色，避免普通作者误操作。
    """
    try:
        ms = {}
        try:
            ms_resp = (
                supabase_admin.table("manuscripts")
                .select("id,status")
                .eq("id", manuscript_id)
                .single()
                .execute()
            )
            ms = getattr(ms_resp, "data", None) or {}
        except Exception:
            ms = {}

        invoice = None
        try:
            inv_resp = (
                supabase_admin.table("invoices")
                .select("amount,status")
                .eq("manuscript_id", manuscript_id)
                .limit(1)
                .execute()
            )
            inv_data = getattr(inv_resp, "data", None) or []
            invoice = inv_data[0] if inv_data else None
        except Exception:
            invoice = None

        # CRITICAL: PAYMENT GATE CHECK
        if invoice is None:
            # 对已录用/待发布的稿件：必须存在 invoice 才允许发布，避免绕过 APC 流程
            if (ms.get("status") or "").lower() in {"approved", "pending_payment"}:
                raise HTTPException(status_code=403, detail="Payment Required: Invoice is unpaid.")
        else:
            try:
                amount = float(invoice.get("amount") or 0)
            except Exception:
                amount = 0
            status = (invoice.get("status") or "unpaid").lower()
            if amount > 0 and status != "paid":
                raise HTTPException(status_code=403, detail="Payment Required: Invoice is unpaid.")

        doi = f"10.1234/sf.{datetime.now().strftime('%Y%m%d%H%M%S')}"
        update_data = {
            "status": "published",
            "published_at": datetime.now().isoformat(),
            "doi": doi,
        }
        try:
            response = (
                supabase_admin.table("manuscripts")
                .update(update_data)
                .eq("id", manuscript_id)
                .execute()
            )
        except Exception as e:
            error_text = str(e)
            print(f"Publish update error: {error_text}")
            if _is_missing_column_error(error_text):
                response = (
                    supabase_admin.table("manuscripts")
                    .update({"status": update_data["status"]})
                    .eq("id", manuscript_id)
                    .execute()
                )
            else:
                raise

        error = _extract_supabase_error(response)
        if error and _is_missing_column_error(str(error)):
            response = (
                supabase_admin.table("manuscripts")
                .update({"status": update_data["status"]})
                .eq("id", manuscript_id)
                .execute()
            )
        elif error:
            raise HTTPException(status_code=500, detail="Failed to publish manuscript")

        data = _extract_supabase_data(response) or []
        if not data:
            raise HTTPException(status_code=404, detail="Manuscript not found")
        return {"success": True, "data": data[0]}
    except HTTPException:
        raise
    except Exception as e:
        print(f"Publish failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to publish manuscript")


# 测试端点 - 不需要身份验证
@router.get("/test/pipeline")
async def get_editor_pipeline_test():
    """
    测试端点：获取全站稿件流转状态看板数据（无需身份验证）
    """
    try:
        # Mock数据用于测试
        return {
            "success": True,
            "data": {
                "pending_quality": [
                    {"id": "1", "title": "Test Manuscript 1", "status": "submitted"}
                ],
                "under_review": [
                    {"id": "2", "title": "Test Manuscript 2", "status": "under_review"}
                ],
                "pending_decision": [
                    {
                        "id": "3",
                        "title": "Test Manuscript 3",
                        "status": "pending_decision",
                    }
                ],
                "published": [
                    {"id": "4", "title": "Test Manuscript 4", "status": "published"}
                ],
            },
        }

    except Exception as e:
        print(f"Pipeline query failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch pipeline data")


@router.get("/test/available-reviewers")
async def get_available_reviewers_test():
    """
    测试端点：获取可用的审稿人专家池（无需身份验证）
    """
    try:
        # Mock数据用于测试
        return {
            "success": True,
            "data": [
                {
                    "id": "1",
                    "name": "Dr. Jane Smith",
                    "email": "jane.smith@example.com",
                    "affiliation": "MIT",
                    "expertise": ["AI", "Machine Learning"],
                    "review_count": 15,
                },
                {
                    "id": "2",
                    "name": "Prof. John Doe",
                    "email": "john.doe@example.com",
                    "affiliation": "Stanford University",
                    "expertise": ["Computer Science", "Data Science"],
                    "review_count": 20,
                },
            ],
        }

    except Exception as e:
        print(f"Reviewers query failed: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to fetch available reviewers"
        )


@router.post("/test/decision")
async def submit_final_decision_test(
    manuscript_id: str = Body(..., embed=True),
    decision: str = Body(..., embed=True),
    comment: str = Body("", embed=True),
):
    """
    测试端点：提交最终录用或退回决策（无需身份验证）
    decision: "accept" | "reject"
    """
    # 验证决策类型
    if decision not in ["accept", "reject"]:
        raise HTTPException(status_code=400, detail="Invalid decision type")

    # Mock响应
    if decision == "accept":
        doi = f"10.1234/sf.{datetime.now().strftime('%Y%m%d%H%M%S')}"
        status = "published"
    else:
        status = "revision_required"

    return {
        "success": True,
        "message": "Decision submitted successfully",
        "data": {
            "manuscript_id": manuscript_id,
            "decision": decision,
            "status": status,
        },
    }
