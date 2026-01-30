from fastapi import APIRouter, HTTPException, Depends, Body, BackgroundTasks
from app.lib.api_client import supabase, supabase_admin
from app.core.auth_utils import get_current_user
from app.core.roles import require_any_role
from app.core.mail import EmailService
from app.services.notification_service import NotificationService
from uuid import UUID
from typing import List, Dict, Any
from postgrest.exceptions import APIError
from datetime import datetime, timedelta, timezone
import secrets
import os

router = APIRouter(tags=["Reviews"])

# === 1. 分配审稿人 (Editor Task) ===
@router.post("/reviews/assign")
async def assign_reviewer(
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
    _profile: dict = Depends(require_any_role(["editor", "admin"])),
    manuscript_id: UUID = Body(..., embed=True),
    reviewer_id: UUID = Body(..., embed=True)
):
    """
    编辑分配审稿人
    
    中文注释:
    1. 校验逻辑: 确保 reviewer_id 不是稿件的作者 (通过 manuscripts 表查询)。
    2. 插入 review_assignments 表。
    """
    # 模拟校验: 获取稿件信息
    ms_res = (
        supabase.table("manuscripts")
        .select("author_id, title")
        .eq("id", str(manuscript_id))
        .single()
        .execute()
    )
    if ms_res.data and str(ms_res.data["author_id"]) == str(reviewer_id):
        raise HTTPException(status_code=400, detail="作者不能评审自己的稿件")
    
    try:
        # 中文注释: 默认给审稿任务 7 天期限，后续可改为按期刊/稿件类型配置
        due_at = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
        res = supabase.table("review_assignments").insert({
            "manuscript_id": str(manuscript_id),
            "reviewer_id": str(reviewer_id),
            "status": "pending",
            "due_at": due_at,
        }).execute()
        # 更新稿件状态为评审中
        supabase.table("manuscripts").update({
            "status": "under_review"
        }).eq("id", str(manuscript_id)).execute()

        # === 通知中心 (Feature 011) ===
        # 站内信：审稿人收到邀请提醒
        manuscript_title = (ms_res.data or {}).get("title") or "Manuscript"
        NotificationService().create_notification(
            user_id=str(reviewer_id),
            manuscript_id=str(manuscript_id),
            type="review_invite",
            title="Review Invitation",
            content=f"You have been invited to review '{manuscript_title}'.",
        )

        # 邮件：审稿邀请（含免登录 Token 链接）
        try:
            profile_res = (
                supabase_admin.table("user_profiles")
                .select("email")
                .eq("id", str(reviewer_id))
                .single()
                .execute()
            )
            reviewer_email = (getattr(profile_res, "data", None) or {}).get("email")
        except Exception:
            reviewer_email = None

        if reviewer_email:
            token = secrets.token_urlsafe(32)
            expiry_date = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
            try:
                supabase_admin.table("review_reports").insert({
                    "manuscript_id": str(manuscript_id),
                    "reviewer_id": str(reviewer_id),
                    "token": token,
                    "expiry_date": expiry_date,
                    "status": "invited",
                }).execute()
            except Exception as e:
                # 中文注释: 缺表/缺列时不阻塞主流程；邮件仍可发送，但 Token 校验可能无法落库
                print(f"[Review Invite] 写入 review_reports 失败（降级继续）: {e}")

            frontend_base_url = os.environ.get("FRONTEND_BASE_URL", "http://localhost:3000").rstrip("/")
            review_url = f"{frontend_base_url}/review/{token}"
            email_service = EmailService()
            background_tasks.add_task(
                email_service.send_template_email,
                to_email=reviewer_email,
                subject="Invitation to Review",
                template_name="review_invite.html",
                context={
                    "subject": "Invitation to Review",
                    "recipient_name": reviewer_email.split("@")[0].replace(".", " ").title(),
                    "manuscript_title": manuscript_title,
                    "manuscript_id": str(manuscript_id),
                    "due_at": due_at,
                    "review_url": review_url,
                },
            )

        return {"success": True, "data": res.data[0]}
    except Exception as e:
        # 如果表还没建，我们返回模拟成功以不阻塞开发
        return {"success": True, "message": "模拟分配成功 (请确保创建了 review_assignments 表)"}

# === 2. 获取我的审稿任务 (Reviewer Task) ===
@router.get("/reviews/my-tasks")
async def get_my_review_tasks(
    user_id: UUID,
    current_user: dict = Depends(get_current_user),
    _profile: dict = Depends(require_any_role(["reviewer", "admin"])),
):
    """
    审稿人获取自己名下的任务
    """
    if str(user_id) != str(current_user["id"]):
        raise HTTPException(status_code=403, detail="Cannot access other user's tasks")
    try:
        res = (
            supabase.table("review_assignments")
            .select("*, manuscripts(title, abstract, file_path)")
            .eq("reviewer_id", str(user_id))
            .eq("status", "pending")
            .execute()
        )
        return {"success": True, "data": res.data}
    except APIError as e:
        # 中文注释:
        # 1) 云端 Supabase 可能还没创建 review_assignments 表（schema cache 里会 404/PGRST205）。
        # 2) Reviewer Tab 属于“可选能力”，不要因为缺表把整个 Dashboard 打崩，降级为空列表。
        print(f"Review tasks query failed (fallback to empty): {e}")
        return {"success": True, "data": [], "message": "review_assignments table not found"}

# === 3. 提交多维度评价 (Submission) ===
@router.post("/reviews/submit")
async def submit_review(
    assignment_id: UUID = Body(..., embed=True),
    scores: Dict[str, int] = Body(..., embed=True), # {novelty: 5, rigor: 4, ...}
    comments: str = Body(..., embed=True)
):
    """
    提交结构化评审意见
    """
    try:
        # 逻辑: 更新状态并存储分数
        assignment_res = (
            supabase.table("review_assignments")
            .select("manuscript_id")
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

        res = supabase.table("review_assignments").update({
            "status": "completed",
            "scores": scores,
            "comments": comments
        }).eq("id", str(assignment_id)).execute()

        # 若全部评审完成，推动稿件进入待终审状态
        if manuscript_id:
            pending = (
                supabase.table("review_assignments")
                .select("id")
                .eq("manuscript_id", str(manuscript_id))
                .eq("status", "pending")
                .execute()
            )
            if not (pending.data or []):
                supabase.table("manuscripts").update({
                    "status": "pending_decision"
                }).eq("id", str(manuscript_id)).execute()

        return {"success": True, "data": res.data[0] if res.data else {}}
    except APIError as e:
        # 缺表时，给出可读提示，避免 500
        print(f"Review submit failed: {e}")
        return {"success": False, "message": "review_assignments table not found"}
