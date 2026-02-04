from fastapi import APIRouter, HTTPException, Depends, Body, BackgroundTasks, UploadFile, File, Form
from app.lib.api_client import supabase, supabase_admin
from app.core.auth_utils import get_current_user
from app.core.roles import require_any_role
from app.services.notification_service import NotificationService
from uuid import UUID
from typing import Any, Dict, Optional
from postgrest.exceptions import APIError
from datetime import datetime, timedelta, timezone
import os

router = APIRouter(tags=["Reviews"])

def _get_signed_url_for_manuscripts_bucket(file_path: str, *, expires_in: int = 60 * 10) -> str:
    """
    生成 manuscripts bucket 的 signed URL（优先使用 service_role）。

    中文注释:
    - 免登录 token 页面与 iframe 无法携带 Authorization header，因此需要后端返回可访问的 signed URL。
    - 为避免受 Storage RLS 影响，这里优先用 supabase_admin（service_role）签名。
    """
    last_err: Exception | None = None
    for client in (supabase_admin, supabase):
        try:
            signed = client.storage.from_("manuscripts").create_signed_url(file_path, expires_in)
            url = (signed or {}).get("signedUrl") or (signed or {}).get("signedURL")
            if url:
                return str(url)
        except Exception as e:
            last_err = e
            continue
    raise HTTPException(status_code=500, detail=f"Failed to create signed url: {last_err}")


def _get_signed_url_for_review_attachments_bucket(file_path: str, *, expires_in: int = 60 * 10) -> str:
    """
    生成 review-attachments bucket 的 signed URL（优先使用 service_role）。

    中文注释:
    - review-attachments 是私有桶：Author 不可见；Reviewer/Editor 通过后端鉴权拿 signed URL 下载。
    """
    last_err: Exception | None = None
    for client in (supabase_admin, supabase):
        try:
            signed = client.storage.from_("review-attachments").create_signed_url(file_path, expires_in)
            url = (signed or {}).get("signedUrl") or (signed or {}).get("signedURL")
            if url:
                return str(url)
        except Exception as e:
            last_err = e
            continue
    raise HTTPException(status_code=500, detail=f"Failed to create signed url: {last_err}")


def _ensure_review_attachments_bucket_exists() -> None:
    """
    确保 review-attachments 桶存在（用于开发/演示环境的一键可用）。

    中文注释:
    - 正式环境建议通过 migration / Dashboard 创建 bucket。
    - 但为了减少“缺桶导致 500”的踩坑，这里做一次性兜底创建。
    """
    storage = getattr(supabase_admin, "storage", None)
    # 单元测试里会用 FakeStorage 替换；若不支持 bucket 管理方法则直接跳过
    if storage is None or not hasattr(storage, "get_bucket") or not hasattr(storage, "create_bucket"):
        return

    try:
        storage.get_bucket("review-attachments")
        return
    except Exception:
        pass
    try:
        storage.create_bucket("review-attachments", options={"public": False})
    except Exception as e:
        text = str(e).lower()
        if "already" in text or "exists" in text or "duplicate" in text:
            return
        raise

def _is_missing_relation_error(err: Exception, *, relation: str) -> bool:
    """
    判断 Supabase/PostgREST 返回的“表不存在/Schema cache 未更新”等错误。

    中文注释:
    - 早期开发阶段可能还没建表；但不要对所有异常都“模拟成功”，否则会掩盖外键/权限等真实问题。
    """
    if not isinstance(err, APIError):
        return False
    text = str(err).lower()
    # 常见信号：
    # - Postgres: 42P01 (undefined_table)
    # - PostgREST: PGRST205 / "schema cache"
    # - 直接报 "relation ... does not exist"
    return (
        "42p01" in text
        or "pgrst205" in text
        or "schema cache" in text
        or f'"{relation.lower()}"' in text
        and "does not exist" in text
    )


def _is_foreign_key_user_error(err: Exception, *, constraint: str) -> bool:
    if not isinstance(err, APIError):
        return False
    text = str(err).lower()
    return ("23503" in text or "foreign key" in text) and constraint.lower() in text


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
        .select("author_id, title, version, status, owner_id, file_path")
        .eq("id", str(manuscript_id))
        .single()
        .execute()
    )
    if ms_res.data and str(ms_res.data["author_id"]) == str(reviewer_id):
        raise HTTPException(status_code=400, detail="作者不能评审自己的稿件")

    # 体验/数据兜底：没有 PDF 的稿件不允许分配审稿人，否则 reviewer 侧无法预览全文
    file_path = (ms_res.data or {}).get("file_path")
    if not file_path:
        raise HTTPException(
            status_code=400,
            detail="该稿件缺少 PDF（file_path 为空），无法分配审稿人。请先在投稿/修订流程上传 PDF。",
        )

    # Feature 023: 初审阶段必须绑定 Internal Owner（KPI 归属人）
    # 中文注释: 分配审稿人会把稿件推进到 under_review，因此这里强制要求 owner_id 已设置。
    owner_raw = (ms_res.data or {}).get("owner_id")
    if not owner_raw:
        # 体验优化：若 Editor 尚未手动绑定，则默认绑定为当前 Editor（仍满足“初审阶段完成绑定”的业务要求）
        try:
            supabase_admin.table("manuscripts").update({"owner_id": str(current_user["id"])}).eq(
                "id", str(manuscript_id)
            ).execute()
            owner_raw = str(current_user["id"])
        except Exception as e:
            print(f"[OwnerBinding] auto-bind owner_id failed: {e}")
            raise HTTPException(status_code=500, detail="Failed to bind Internal Owner")

    current_version = ms_res.data.get("version", 1) if ms_res.data else 1

    try:
        # 幂等保护：避免同一审稿人被重复指派（UI 可能因“已指派列表”加载失败而重复提交）
        existing = (
            supabase_admin.table("review_assignments")
            .select("id, status, due_at, reviewer_id, round_number")
            .eq("manuscript_id", str(manuscript_id))
            .eq("reviewer_id", str(reviewer_id))
            .eq("round_number", current_version)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        if getattr(existing, "data", None):
            # 中文注释: 返回现有 assignment，前端可直接刷新展示。
            return {
                "success": True,
                "data": existing.data[0],
                "message": "Reviewer already assigned",
            }

        # 中文注释: 默认给审稿任务 7 天期限，后续可改为按期刊/稿件类型配置
        due_at = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
        res = (
            # 中文注释: 使用 service_role 写入，避免云端 RLS/权限导致“写入成功但读取不到”的不一致体验
            supabase_admin.table("review_assignments")
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
        supabase_admin.table("manuscripts").update({"status": "under_review"}).eq(
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
            # Feature 025: Use signed tokens
            from app.core.mail import email_service
            token = email_service.create_token(reviewer_email, salt="review-invite")
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
            
            background_tasks.add_task(
                email_service.send_email_background,
                to_email=reviewer_email,
                subject="Invitation to Review",
                template_name="reviewer_invite.html",
                context={
                    "link": review_url,
                    "manuscript_title": manuscript_title,
                },
            )

        return {"success": True, "data": res.data[0]}
    except APIError as e:
        # 中文注释:
        # - reviewer_id 外键指向 auth.users(id)，如果前端列表里混入了“仅 user_profiles 的 mock reviewer”，这里会触发 23503。
        if _is_foreign_key_user_error(e, constraint="review_assignments_reviewer_id_fkey"):
            raise HTTPException(
                status_code=400,
                detail=(
                    "该审稿人账号不存在于 Supabase Auth（可能是 mock user_profiles）。"
                    "请用「Invite New」创建真实账号，或运行 scripts/seed_mock_reviewers_auth.py 生成可指派 reviewer。"
                ),
            )
        if _is_missing_relation_error(e, relation="review_assignments"):
            raise HTTPException(
                status_code=500,
                detail="review_assignments 表不存在或 Schema cache 未更新（请先在云端 Supabase 创建/迁移该表）。",
            )
        raise HTTPException(status_code=500, detail=f"Failed to assign reviewer: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to assign reviewer: {e}")


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
            supabase_admin.table("review_assignments")
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

        # 2. 删除指派
        # 中文注释: 同一 reviewer 可能被重复指派（历史数据/并发），这里按 reviewer+round 做幂等清理。
        delete_q = (
            supabase_admin.table("review_assignments")
            .delete()
            .eq("manuscript_id", manuscript_id)
            .eq("reviewer_id", reviewer_id)
        )
        if round_number is not None:
            delete_q = delete_q.eq("round_number", round_number)
        delete_q.execute()

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
            supabase_admin.table("review_assignments")
            .select("id")
            .eq("manuscript_id", manuscript_id)
            .execute()
        )
        remaining_count = len(remaining_res.data or [])

        # 5. 如果没有审稿人了，回滚稿件状态为 submitted
        if remaining_count == 0:
            supabase_admin.table("manuscripts").update({"status": "submitted"}).eq(
                "id", manuscript_id
            ).execute()

        return {"success": True, "message": "Reviewer unassigned"}
    except Exception as e:
        print(f"Unassign failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/reviews/assignments/{manuscript_id}")
async def get_manuscript_assignments(
    manuscript_id: UUID,
    round_number: int | None = None,
    current_user: dict = Depends(get_current_user),
    _profile: dict = Depends(require_any_role(["editor", "admin"])),
):
    """
    获取某篇稿件的审稿指派列表
    """
    try:
        res = (
            # 使用 service_role 读取，避免 RLS/权限导致编辑端看不到已指派数据
            supabase_admin.table("review_assignments")
            .select(
                "id, status, due_at, reviewer_id, round_number, created_at"
            )
            .eq("manuscript_id", str(manuscript_id))
            .order("created_at", desc=True)
            .execute()
        )
        assignments = res.data or []

        # 中文注释:
        # - UI 里的“Manage/Assign Reviewer”应默认聚焦在“当前轮次”。
        # - 但如果当前轮次尚未创建任何指派（例如 resubmitted 但尚未二审分配），则回退到已有的最新轮次，
        #   这样 Editor 至少能看到上一轮的 reviewer 与完成状态。
        target_round: int | None = None
        if round_number is not None:
            target_round = int(round_number)
        else:
            ms_version: int | None = None
            try:
                ms = (
                    supabase_admin.table("manuscripts")
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

        # 中文注释:
        # - review_assignments.reviewer_id 外键指向 auth.users(id)，并不指向 public.user_profiles(id)
        # - 因此不能用 PostgREST embed 语法直接 join user_profiles（会报错/返回空）
        # - 这里用两次查询做“应用层 join”，保证 UI 能拿到 reviewer_id 并正确预选
        reviewer_ids = list({a.get("reviewer_id") for a in assignments if a.get("reviewer_id")})
        profiles_by_id: Dict[str, Dict[str, Any]] = {}
        if reviewer_ids:
            try:
                profiles_res = (
                    supabase_admin.table("user_profiles")
                    .select("id, full_name, email")
                    .in_("id", reviewer_ids)
                    .execute()
                )
                for p in (profiles_res.data or []):
                    pid = p.get("id")
                    if pid:
                        profiles_by_id[str(pid)] = p
            except Exception as e:
                # 不阻塞主流程：仍返回 assignments，只是名称/邮箱为空
                print(f"Fetch reviewer profiles failed (fallback to ids only): {e}")

        # 去重：同一个 reviewer 在同一 round 被重复指派时，只返回最新一条（避免 UI 显示 2 个“同一人”）
        seen_keys = set()
        result = []
        for item in assignments:
            rid = str(item.get("reviewer_id") or "")
            rnd = item.get("round_number", 1)
            key = (rid, rnd)
            if not rid or key in seen_keys:
                continue
            seen_keys.add(key)
            profile = profiles_by_id.get(rid, {})
            result.append(
                {
                    "id": item["id"],  # assignment_id
                    "status": item.get("status"),
                    "due_at": item.get("due_at"),
                    "round_number": rnd,
                    "reviewer_id": rid,
                    "reviewer_name": profile.get("full_name") or "Unknown",
                    "reviewer_email": profile.get("email") or "",
                }
            )
        return {"success": True, "data": result}
    except Exception as e:
        print(f"Fetch assignments failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to load reviewer assignments")


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
    # Feature 022 completion: comments_for_author 必填；兼容旧字段 comments
    comments_for_author: str | None = Body(None, embed=True),
    comments: str | None = Body(None, embed=True),
    confidential_comments_to_editor: str | None = Body(None, embed=True),
    attachment_path: str | None = Body(None, embed=True),
):
    """
    提交结构化评审意见
    """
    public_comments = (comments_for_author or comments or "").strip()
    if not public_comments:
        raise HTTPException(status_code=400, detail="comments_for_author is required")

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
            .update({"status": "completed", "scores": scores, "comments": public_comments})
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
                # 新字段（Author 可见）
                "comments_for_author": public_comments,
                # 兼容旧字段：历史页面仍可能读取 content
                "content": public_comments,
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
            try:
                pending = (
                    supabase_admin.table("review_assignments")
                    .select("id")
                    .eq("manuscript_id", str(manuscript_id))
                    .eq("status", "pending")
                    .execute()
                )
                pending_rows = getattr(pending, "data", None) or []
            except Exception:
                pending = (
                    supabase.table("review_assignments")
                    .select("id")
                    .eq("manuscript_id", str(manuscript_id))
                    .eq("status", "pending")
                    .execute()
                )
                pending_rows = getattr(pending, "data", None) or []

            if not pending_rows:
                try:
                    supabase_admin.table("manuscripts").update({"status": "pending_decision"}).eq(
                        "id", str(manuscript_id)
                    ).execute()
                except Exception:
                    supabase.table("manuscripts").update({"status": "pending_decision"}).eq(
                        "id", str(manuscript_id)
                    ).execute()

        return {"success": True, "data": res.data[0] if res.data else {}}
    except APIError as e:
        # 缺表时，给出可读提示，避免 500
        print(f"Review submit failed: {e}")
        return {"success": False, "message": "review_assignments table not found"}


@router.post("/reviews/assignments/{assignment_id}/attachment")
async def upload_review_attachment(
    assignment_id: UUID,
    current_user: dict = Depends(get_current_user),
    profile: dict = Depends(require_any_role(["reviewer", "admin"])),
    attachment: UploadFile = File(...),
):
    """
    Reviewer 上传机密附件（Annotated PDF）

    中文注释:
    - 文件存储在 review-attachments 私有桶
    - 仅 reviewer 本人（或 admin）可上传
    - 返回 attachment_path，前端在提交 review 时写入 review_reports.attachment_path
    """
    if attachment is None:
        raise HTTPException(status_code=400, detail="attachment is required")

    safe_name = (attachment.filename or "attachment").replace("/", "_")
    is_pdf = (attachment.content_type == "application/pdf") or safe_name.lower().endswith(".pdf")
    if not is_pdf:
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    try:
        assignment_res = (
            supabase_admin.table("review_assignments")
            .select("id, reviewer_id")
            .eq("id", str(assignment_id))
            .single()
            .execute()
        )
        assignment = getattr(assignment_res, "data", None) or {}
        if not assignment:
            raise HTTPException(status_code=404, detail="Assignment not found")

        is_admin = "admin" in (profile.get("roles") or [])
        if not is_admin and str(assignment.get("reviewer_id") or "") != str(current_user.get("id") or ""):
            raise HTTPException(status_code=403, detail="Forbidden")

        file_bytes = await attachment.read()
        path = f"review_assignments/{assignment_id}/{safe_name}"
        try:
            _ensure_review_attachments_bucket_exists()
            supabase_admin.storage.from_("review-attachments").upload(
                path,
                file_bytes,
                {"content-type": attachment.content_type or "application/pdf"},
            )
        except Exception as e:
            print(f"[Review Attachment] upload failed: {e}")
            raise HTTPException(status_code=500, detail="Failed to upload attachment")

        return {"success": True, "data": {"attachment_path": path}}
    except HTTPException:
        raise
    except Exception as e:
        print(f"Upload review attachment failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to upload attachment")


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

        # 最新修订信息（用于二审/复审时给 reviewer 展示作者 response letter）
        latest_revision = None
        try:
            rev_resp = (
                supabase_admin.table("revisions")
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


@router.get("/reviews/token/{token}/pdf-signed")
async def get_review_pdf_signed_by_token(token: str):
    """
    免登录审稿：返回该 token 对应稿件 PDF 的 signed URL。

    中文注释:
    - 前端 iframe 无法携带 Authorization header，因此必须由后端生成 signed URL。
    - token 本身是访问凭证，必须严格校验有效性与过期时间。
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
            .select("id,file_path")
            .eq("id", rr["manuscript_id"])
            .single()
            .execute()
        )
        ms = getattr(ms_resp, "data", None) or {}
        file_path = ms.get("file_path")
        if not file_path:
            raise HTTPException(status_code=404, detail="Manuscript PDF not found")

        signed_url = _get_signed_url_for_manuscripts_bucket(str(file_path))
        return {"success": True, "data": {"signed_url": signed_url}}
    except HTTPException:
        raise
    except Exception as e:
        print(f"Get review pdf signed url by token failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate PDF preview URL")


@router.post("/reviews/token/{token}/submit")
async def submit_review_by_token(
    token: str,
    # Feature 022 completion: comments_for_author 必填；兼容旧字段 content
    comments_for_author: str | None = Form(None),
    content: str | None = Form(None),
    score: int = Form(...),
    confidential_comments_to_editor: str | None = Form(None),
    attachment: UploadFile | None = File(None),
):
    """
    免登录审稿提交：支持双通道评论 + 机密附件
    """
    public_comments = (comments_for_author or content or "").strip()
    if not public_comments:
        raise HTTPException(status_code=400, detail="comments_for_author is required")
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
            attachment_path = f"review_reports/{rr['id']}/{safe_name}"
            try:
                _ensure_review_attachments_bucket_exists()
                supabase_admin.storage.from_("review-attachments").upload(
                    attachment_path,
                    file_bytes,
                    {"content-type": attachment.content_type or "application/octet-stream"},
                )
            except Exception as e:
                print(f"[Review Attachment] upload failed: {e}")
                raise HTTPException(status_code=500, detail="Failed to upload attachment")

        update_payload = {
            # 新字段（Author 可见）
            "comments_for_author": public_comments,
            # 兼容旧字段
            "content": public_comments,
            "score": score,
            "status": "completed",
            "confidential_comments_to_editor": confidential_comments_to_editor,
            "attachment_path": attachment_path,
        }
        supabase_admin.table("review_reports").update(update_payload).eq("id", rr["id"]).execute()

        # === 同步到 review_assignments / manuscripts（修复 Editor 状态不同步）===
        # 中文注释:
        # - Editor Pipeline 依赖 review_assignments 的 pending/completed 统计。
        # - 免登录 token 提交如果只更新 review_reports，会导致 Editor 侧看不到变化。
        try:
            ms_version = 1
            try:
                ms_v = (
                    supabase_admin.table("manuscripts")
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
                    supabase_admin.table("review_assignments")
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
                # 兼容旧数据：round_number 可能为空
                try:
                    a2 = (
                        supabase_admin.table("review_assignments")
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
                supabase_admin.table("review_assignments").update(
                    {
                        "status": "completed",
                        "comments": public_comments,
                        "scores": {"overall": score},
                    }
                ).eq("id", assignment_rows[0]["id"]).execute()

            pending = (
                supabase_admin.table("review_assignments")
                .select("id")
                .eq("manuscript_id", str(rr["manuscript_id"]))
                .eq("status", "pending")
                .execute()
            )
            if not (getattr(pending, "data", None) or []):
                supabase_admin.table("manuscripts").update({"status": "pending_decision"}).eq(
                    "id", str(rr["manuscript_id"])
                ).execute()
        except Exception as e:
            # 中文注释: 不因同步失败阻塞免登录提交主流程，但要打日志便于排查。
            print(f"[Reviews] token submit sync to assignments/manuscripts failed (ignored): {e}")

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
                    # 兼容：旧页面读取 content
                    "content": public_text,
                    "comments_for_author": public_text,
                    "score": r.get("score"),
                }
                sanitized.append(r2)
            return {"success": True, "data": sanitized}

        # Editor/Admin：返回机密字段，但保证 comments_for_author 有值，避免老数据为空
        for r in rows:
            if not r.get("comments_for_author") and r.get("content"):
                r["comments_for_author"] = r.get("content")
        return {"success": True, "data": rows}
    except HTTPException:
        raise
    except Exception as e:
        print(f"Fetch review feedback failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch review feedback")


@router.get("/reviews/token/{token}/attachment-signed")
async def get_review_attachment_signed_by_token(token: str):
    """
    免登录审稿：返回该 token 对应 review attachment 的 signed URL（如果存在）。
    """
    try:
        rr_resp = (
            supabase_admin.table("review_reports")
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

        signed_url = _get_signed_url_for_review_attachments_bucket(str(path))
        return {"success": True, "data": {"signed_url": signed_url}}
    except HTTPException:
        raise
    except Exception as e:
        print(f"Get review attachment signed url by token failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate attachment URL")


@router.get("/reviews/reports/{review_report_id}/attachment-signed")
async def get_review_attachment_signed(
    review_report_id: UUID,
    current_user: dict = Depends(get_current_user),
    profile: dict = Depends(require_any_role(["reviewer", "editor", "admin"])),
):
    """
    登录态：Reviewer/Editor/Admin 下载机密附件（Author 禁止）。
    """
    try:
        rr_resp = (
            supabase_admin.table("review_reports")
            .select("id, reviewer_id, attachment_path")
            .eq("id", str(review_report_id))
            .single()
            .execute()
        )
        rr = getattr(rr_resp, "data", None) or {}
        if not rr:
            raise HTTPException(status_code=404, detail="Review report not found")

        roles = set(profile.get("roles") or [])
        is_editor = bool(roles.intersection({"editor", "admin"}))
        if not is_editor and str(rr.get("reviewer_id") or "") != str(current_user.get("id") or ""):
            raise HTTPException(status_code=403, detail="Forbidden")

        path = rr.get("attachment_path")
        if not path:
            raise HTTPException(status_code=404, detail="No attachment")

        signed_url = _get_signed_url_for_review_attachments_bucket(str(path))
        return {"success": True, "data": {"signed_url": signed_url}}
    except HTTPException:
        raise
    except Exception as e:
        print(f"Get review attachment signed url failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate attachment URL")
