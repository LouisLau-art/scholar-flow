from fastapi import APIRouter, HTTPException, Depends, Body, BackgroundTasks, UploadFile, File, Form
from app.lib.api_client import supabase, supabase_admin
from app.core.auth_utils import get_current_user
from app.core.roles import require_any_role
from app.core.mail import EmailService
from app.services.notification_service import NotificationService
from uuid import UUID
from typing import Dict, Optional
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
    reviewer_id: UUID = Body(..., embed=True),
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
        .select("author_id, title, version")
        .eq("id", str(manuscript_id))
        .single()
        .execute()
    )
    if ms_res.data and str(ms_res.data["author_id"]) == str(reviewer_id):
        raise HTTPException(status_code=400, detail="作者不能评审自己的稿件")

    current_version = ms_res.data.get("version", 1) if ms_res.data else 1

    try:
        # 中文注释: 默认给审稿任务 7 天期限，后续可改为按期刊/稿件类型配置
        due_at = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
        res = (
            supabase.table("review_assignments")
            .insert(
                {
                    "manuscript_id": str(manuscript_id),
                    "reviewer_id": str(reviewer_id),
                    "status": "pending",
                    "due_at": due_at,
                    "round_number": current_version,
                }
            )
            .execute()
        )
        # 更新稿件状态为评审中
        supabase.table("manuscripts").update({"status": "under_review"}).eq(
            "id", str(manuscript_id)
        ).execute()

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
                supabase_admin.table("review_reports").insert(
                    {
                        "manuscript_id": str(manuscript_id),
                        "reviewer_id": str(reviewer_id),
                        "token": token,
                        "expiry_date": expiry_date,
                        "status": "invited",
                    }
                ).execute()
            except Exception as e:
                # 中文注释: 缺表/缺列时不阻塞主流程；邮件仍可发送，但 Token 校验可能无法落库
                print(f"[Review Invite] 写入 review_reports 失败（降级继续）: {e}")

            frontend_base_url = os.environ.get(
                "FRONTEND_BASE_URL", "http://localhost:3000"
            ).rstrip("/")
            review_url = f"{frontend_base_url}/review/{token}"
            email_service = EmailService()
            background_tasks.add_task(
                email_service.send_template_email,
                to_email=reviewer_email,
                subject="Invitation to Review",
                template_name="review_invite.html",
                context={
                    "subject": "Invitation to Review",
                    "recipient_name": reviewer_email.split("@")[0]
                    .replace(".", " ")
                    .title(),
                    "manuscript_title": manuscript_title,
                    "manuscript_id": str(manuscript_id),
                    "due_at": due_at,
                    "review_url": review_url,
                },
            )

        return {"success": True, "data": res.data[0]}
    except Exception:
        # 如果表还没建，我们返回模拟成功以不阻塞开发
        return {
            "success": True,
            "message": "模拟分配成功 (请确保创建了 review_assignments 表)",
        }


@router.delete("/reviews/assign/{assignment_id}")
async def unassign_reviewer(
    assignment_id: UUID,
    current_user: dict = Depends(get_current_user),
    _profile: dict = Depends(require_any_role(["editor", "admin"])),
):
    """
    撤销审稿指派
    """
    try:
        # 1. 获取 manuscript_id 以便后续状态检查
        assign_res = (
            supabase.table("review_assignments")
            .select("manuscript_id, reviewer_id")
            .eq("id", str(assignment_id))
            .single()
            .execute()
        )
        if not assign_res.data:
            raise HTTPException(status_code=404, detail="Assignment not found")

        manuscript_id = assign_res.data["manuscript_id"]
        reviewer_id = assign_res.data["reviewer_id"]

        # 2. 删除指派
        supabase.table("review_assignments").delete().eq(
            "id", str(assignment_id)
        ).execute()

        # 3. 尝试删除关联的 review_reports (如果状态是 invited/pending)
        try:
            supabase_admin.table("review_reports").delete().eq(
                "manuscript_id", manuscript_id
            ).eq("reviewer_id", reviewer_id).in_(
                "status", ["invited", "pending"]
            ).execute()
        except Exception:
            pass

        # 4. 检查是否还有其他审稿人
        remaining_res = (
            supabase.table("review_assignments")
            .select("id")
            .eq("manuscript_id", manuscript_id)
            .execute()
        )
        remaining_count = len(remaining_res.data or [])

        # 5. 如果没有审稿人了，回滚稿件状态为 submitted
        if remaining_count == 0:
            supabase.table("manuscripts").update({"status": "submitted"}).eq(
                "id", manuscript_id
            ).execute()

        return {"success": True, "message": "Reviewer unassigned"}
    except Exception as e:
        print(f"Unassign failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/reviews/assignments/{manuscript_id}")
async def get_manuscript_assignments(
    manuscript_id: UUID,
    current_user: dict = Depends(get_current_user),
    _profile: dict = Depends(require_any_role(["editor", "admin"])),
):
    """
    获取某篇稿件的审稿指派列表
    """
    try:
        # 关联查询 user_profiles 获取审稿人名字
        res = (
            # 使用 service_role 读取，避免 RLS/权限导致编辑端看不到已指派数据
            supabase_admin.table("review_assignments")
            .select(
                "id, status, due_at, reviewer_id, round_number, user_profiles:reviewer_id(full_name, email)"
            )
            .eq("manuscript_id", str(manuscript_id))
            .execute()
        )
        data = res.data or []
        # Flatten structure
        result = []
        for item in data:
            profile = item.get("user_profiles") or {}
            result.append(
                {
                    "id": item["id"],  # assignment_id
                    "status": item["status"],
                    "due_at": item["due_at"],
                    "round_number": item.get("round_number", 1),
                    "reviewer_id": item["reviewer_id"],
                    "reviewer_name": profile.get("full_name") or "Unknown",
                    "reviewer_email": profile.get("email") or "",
                }
            )
        return {"success": True, "data": result}
    except Exception as e:
        print(f"Fetch assignments failed: {e}")
        return {"success": True, "data": []}


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
        return {
            "success": True,
            "data": [],
            "message": "review_assignments table not found",
        }


# === 3. 提交多维度评价 (Submission) ===
@router.post("/reviews/submit")
async def submit_review(
    assignment_id: UUID = Body(..., embed=True),
    scores: Dict[str, int] = Body(..., embed=True),  # {novelty: 5, rigor: 4, ...}
    comments: str = Body(..., embed=True),
    confidential_comments_to_editor: str | None = Body(None, embed=True),
    attachment_path: str | None = Body(None, embed=True),
):
    """
    提交结构化评审意见
    """
    try:
        # 逻辑: 更新状态并存储分数
        assignment_res = (
            supabase.table("review_assignments")
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
            supabase.table("review_assignments")
            .update({"status": "completed", "scores": scores, "comments": comments})
            .eq("id", str(assignment_id))
            .execute()
        )

        # === Feature 022: Reviewer Privacy（双通道评论落库到 review_reports） ===
        # 中文注释:
        # - review_assignments 用于任务状态机；review_reports 用于对外展示（按角色过滤机密字段）。
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
                "content": comments,
                "score": overall_score,
                "confidential_comments_to_editor": confidential_comments_to_editor,
                "attachment_path": attachment_path,
            }
            try:
                existing = (
                    supabase_admin.table("review_reports")
                    .select("id")
                    .eq("manuscript_id", str(manuscript_id))
                    .eq("reviewer_id", str(reviewer_id))
                    .limit(1)
                    .execute()
                )
                existing_rows = getattr(existing, "data", None) or []
                if existing_rows:
                    supabase_admin.table("review_reports").update(rr_payload).eq(
                        "id", existing_rows[0]["id"]
                    ).execute()
                else:
                    supabase_admin.table("review_reports").insert(
                        {
                            **rr_payload,
                            "token": None,
                            "expiry_date": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
                        }
                    ).execute()
            except Exception as e:
                # 中文注释: 不因 review_reports 失败阻塞 review_assignments 主流程
                print(f"[Reviews] upsert review_reports failed (ignored): {e}")

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
                supabase.table("manuscripts").update({"status": "pending_decision"}).eq(
                    "id", str(manuscript_id)
                ).execute()

        return {"success": True, "data": res.data[0] if res.data else {}}
    except APIError as e:
        # 缺表时，给出可读提示，避免 500
        print(f"Review submit failed: {e}")
        return {"success": False, "message": "review_assignments table not found"}


def _is_admin_email(email: Optional[str]) -> bool:
    if not email:
        return False
    admins = [e.strip().lower() for e in (os.environ.get("ADMIN_EMAILS") or "").split(",") if e.strip()]
    return email.strip().lower() in set(admins)


@router.get("/reviews/token/{token}")
async def get_review_by_token(token: str):
    """
    免登录审稿入口：通过 token 获取审稿任务与稿件信息

    中文注释:
    - 这是 Reviewer 无需登录的落地页能力；必须严格校验 token 有效性与过期时间。
    """
    try:
        rr_resp = (
            supabase_admin.table("review_reports")
            .select("id, manuscript_id, reviewer_id, status, expiry_date")
            .eq("token", token)
            .single()
            .execute()
        )
        rr = getattr(rr_resp, "data", None) or {}
        if not rr:
            raise HTTPException(status_code=404, detail="Review token not found")

        expiry = rr.get("expiry_date")
        # expiry_date 可能是字符串
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
            supabase_admin.table("manuscripts")
            .select("id,title,abstract,file_path,status")
            .eq("id", rr["manuscript_id"])
            .single()
            .execute()
        )
        ms = getattr(ms_resp, "data", None) or {}

        return {"success": True, "data": {"review_report": rr, "manuscript": ms}}
    except HTTPException:
        raise
    except Exception as e:
        print(f"Get review by token failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch review task")


@router.post("/reviews/token/{token}/submit")
async def submit_review_by_token(
    token: str,
    content: str = Form(...),
    score: int = Form(...),
    confidential_comments_to_editor: str | None = Form(None),
    attachment: UploadFile | None = File(None),
):
    """
    免登录审稿提交：支持双通道评论 + 机密附件
    """
    if not content or content.strip() == "":
        raise HTTPException(status_code=400, detail="content is required")
    if score < 1 or score > 5:
        raise HTTPException(status_code=400, detail="score must be 1..5")

    try:
        rr_resp = (
            supabase_admin.table("review_reports")
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
            # 中文注释: 机密附件仅供编辑查看；存储路径不暴露给作者
            safe_name = (attachment.filename or "attachment").replace("/", "_")
            attachment_path = f"review_attachments/{rr['id']}/{safe_name}"
            try:
                supabase_admin.storage.from_("manuscripts").upload(
                    attachment_path,
                    file_bytes,
                    {"content-type": attachment.content_type or "application/octet-stream"},
                )
            except Exception as e:
                print(f"[Review Attachment] upload failed: {e}")
                raise HTTPException(status_code=500, detail="Failed to upload attachment")

        update_payload = {
            "content": content,
            "score": score,
            "status": "completed",
            "confidential_comments_to_editor": confidential_comments_to_editor,
            "attachment_path": attachment_path,
        }
        supabase_admin.table("review_reports").update(update_payload).eq("id", rr["id"]).execute()

        return {"success": True, "data": {"review_report_id": rr["id"]}}
    except HTTPException:
        raise
    except Exception as e:
        print(f"Submit review by token failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to submit review")


@router.get("/reviews/feedback/{manuscript_id}")
async def get_review_feedback_for_manuscript(
    manuscript_id: UUID,
    current_user: dict = Depends(get_current_user),
):
    """
    获取某稿件的审稿反馈（按身份过滤机密字段）

    中文注释:
    - Author 只能看到公开字段（content/score）
    - Editor/Admin 可以看到机密字段（confidential_comments_to_editor/attachment_path）
    """
    try:
        ms_resp = (
            supabase_admin.table("manuscripts")
            .select("id, author_id")
            .eq("id", str(manuscript_id))
            .single()
            .execute()
        )
        ms = getattr(ms_resp, "data", None) or {}
        if not ms:
            raise HTTPException(status_code=404, detail="Manuscript not found")

        is_author = str(ms.get("author_id")) == str(current_user.get("id"))
        is_editor = _is_admin_email(current_user.get("email"))
        if not (is_author or is_editor):
            raise HTTPException(status_code=403, detail="Forbidden")

        rr_resp = (
            supabase_admin.table("review_reports")
            .select("id, manuscript_id, reviewer_id, status, content, score, confidential_comments_to_editor, attachment_path")
            .eq("manuscript_id", str(manuscript_id))
            .order("created_at", desc=True)
            .execute()
        )
        rows = getattr(rr_resp, "data", None) or []

        if is_author:
            sanitized = []
            for r in rows:
                r2 = {
                    "id": r.get("id"),
                    "manuscript_id": r.get("manuscript_id"),
                    "reviewer_id": r.get("reviewer_id"),
                    "status": r.get("status"),
                    "content": r.get("content"),
                    "score": r.get("score"),
                }
                sanitized.append(r2)
            return {"success": True, "data": sanitized}

        return {"success": True, "data": rows}
    except HTTPException:
        raise
    except Exception as e:
        print(f"Fetch review feedback failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch review feedback")
