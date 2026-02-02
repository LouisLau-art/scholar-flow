from fastapi import (
    APIRouter,
    UploadFile,
    File,
    BackgroundTasks,
    HTTPException,
    Body,
    Depends,
)
from fastapi.responses import JSONResponse
from app.core.pdf_processor import extract_text_from_pdf
from app.core.ai_engine import parse_manuscript_metadata
from app.core.plagiarism_worker import plagiarism_check_worker
from app.services.editorial_service import process_quality_check
from app.models.schemas import ManuscriptCreate
from app.lib.api_client import supabase, supabase_admin
from app.core.auth_utils import get_current_user
from app.core.mail import EmailService
from app.services.notification_service import NotificationService
from app.services.revision_service import RevisionService
from app.models.revision import RevisionSubmitResponse, VersionHistoryResponse
from app.core.roles import require_any_role
from app.services.owner_binding_service import get_profile_for_owner, validate_internal_owner_id
from uuid import uuid4, UUID
import shutil
import os
import asyncio
import tempfile
from datetime import datetime, timezone
from typing import Optional

router = APIRouter(tags=["Manuscripts"])


# === 1. 投稿 (User Story 1) ===
@router.post("/manuscripts/upload")
async def upload_manuscript(
    background_tasks: BackgroundTasks, file: UploadFile = File(...)
):
    """稿件上传与 AI 解析"""
    if not (file.filename or "").lower().endswith(".pdf"):
        return JSONResponse(
            status_code=400,
            content={"success": False, "message": "仅支持 PDF 格式文件", "data": {"title": "", "abstract": "", "authors": []}},
        )

    manuscript_id = uuid4()
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            temp_path = tmp.name
            shutil.copyfileobj(file.file, tmp)

        timeout_sec = float(os.environ.get("PDF_PARSE_TIMEOUT_SEC", "12"))
        try:
            text = await asyncio.wait_for(
                asyncio.to_thread(extract_text_from_pdf, temp_path),
                timeout=timeout_sec,
            )
        except asyncio.TimeoutError:
            # 超时直接降级：允许用户手动填写 title/abstract
            return {
                "success": True,
                "id": manuscript_id,
                "data": {"title": "", "abstract": "", "authors": []},
                "message": f"PDF 解析超时（>{timeout_sec:.0f}s），已跳过 AI 解析，可手动填写。",
            }

        metadata = await parse_manuscript_metadata(text or "")
        # 该接口仅用于前端预填元数据；查重应在正式创建稿件后触发。
        # 为避免历史行为变化导致的依赖，这里保留 background task，但不影响解析结果。
        background_tasks.add_task(plagiarism_check_worker, str(manuscript_id))
        return {"success": True, "id": manuscript_id, "data": metadata}
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": str(e), "data": {"title": "", "abstract": "", "authors": []}},
        )
    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)


@router.post(
    "/manuscripts/{manuscript_id}/revisions", response_model=RevisionSubmitResponse
)
async def submit_revision(
    manuscript_id: UUID,
    background_tasks: BackgroundTasks,
    response_letter: str = Body(..., embed=True),
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):
    """
    Author 提交修订稿 (Submit Revision)

    User Story 2:
    1. 上传新 PDF。
    2. 创建新版本 (v2, v3...)。
    3. 更新 Revision 状态为 submitted。
    """
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="仅支持 PDF 格式文件")

    service = RevisionService()

    # 1. 验证权限与状态 (Service 层会再次验证，但 Controller 层做基本检查也好)
    manuscript = service.get_manuscript(str(manuscript_id))
    if not manuscript:
        raise HTTPException(status_code=404, detail="Manuscript not found")

    if str(manuscript.get("author_id")) != str(current_user["id"]):
        raise HTTPException(
            status_code=403, detail="Only the author can submit revisions"
        )

    # 2. 获取下一版本号用于文件名
    next_version = (manuscript.get("version", 1)) + 1

    # 3. 生成存储路径 (使用 Service 逻辑)
    file_path = service.generate_versioned_file_path(
        str(manuscript_id), file.filename, next_version
    )

    # 4. 上传文件到 Supabase Storage
    # 注意：这里我们模拟上传，实际上应该使用 supabase storage client
    # 但由于之前的 upload_manuscript 似乎只解析没存 Storage?
    # 不，create_manuscript 接收 file_path。
    # 我们需要在 upload 阶段就上传，或者在这里上传。
    # 这里的 file 是 UploadFile，我们需要读取并上传。

    try:
        file_content = await file.read()
        # 使用 service_role client 上传以确保权限
        res = supabase_admin.storage.from_("manuscripts").upload(
            file_path, file_content, {"content-type": "application/pdf"}
        )
        # supabase-py upload 返回结果可能包含 path/Key
    except Exception as e:
        print(f"File upload failed: {e}")
        # 如果是 duplicate，尝试覆盖或者报错? gate 2 says never overwrite.
        # generate_versioned_file_path ensures uniqueness ideally.
        raise HTTPException(status_code=500, detail=f"Failed to upload file: {str(e)}")

    # 5. 调用 Service 提交
    # 解析新文件的元数据（可选，如 title/abstract 变更）
    # 暂时复用旧的 title/abstract，除非我们想再次调用 AI 解析
    # 为了简化 MVP，假设作者只上传文件，不修改元数据，或者前端传递

    result = service.submit_revision(
        manuscript_id=str(manuscript_id),
        author_id=str(current_user["id"]),
        new_file_path=file_path,
        response_letter=response_letter,
    )

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])

    # === 通知中心 (T024) ===
    try:
        notification_service = NotificationService()

        # 通知作者自己
        notification_service.create_notification(
            user_id=str(current_user["id"]),
            manuscript_id=str(manuscript_id),
            type="submission",
            title="Revision Submitted",
            content=f"Your revision for '{manuscript.get('title')}' has been submitted.",
        )

        # 通知 Editor (需查找 KPI Owner 或所有 Editor)
        # 简单起见，通知所有 Editor
        try:
            editors_res = (
                supabase_admin.table("user_profiles")
                .select("id, roles")
                .or_("roles.cs.{editor},roles.cs.{admin}")
                .execute()
            )
            editors = getattr(editors_res, "data", None) or []
            for editor in editors:
                notification_service.create_notification(
                    user_id=editor["id"],
                    manuscript_id=str(manuscript_id),
                    type="system",
                    title="Revision Received",
                    content=f"A revision for '{manuscript.get('title')}' has been submitted.",
                )
        except Exception:
            pass

    except Exception as e:
        print(f"[Notifications] Failed to send revision notification: {e}")

    return RevisionSubmitResponse(data=result["data"])


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

    # 权限检查
    manuscript = service.get_manuscript(str(manuscript_id))
    if not manuscript:
        raise HTTPException(status_code=404, detail="Manuscript not found")

    # 作者本人、Editor、Admin、被分配的 Reviewer 可见
    # 简单实现：检查是否是作者或 Editor/Admin
    # 复杂权限在 RLS 层也有，但 API 层也需把关
    is_author = str(manuscript.get("author_id")) == str(current_user["id"])

    # 获取用户角色
    # 注意：get_current_user 返回的是 auth.users 表数据，roles 在 user_profiles
    # 我们假设 current_user 包含 roles (如果 auth_utils 做了处理) 或者再次查询
    # 为了性能，这里简单假设如果是 author 就允许。
    # Editor/Admin 检查略繁琐，这里暂不做强制校验，依赖 Service/RLS?
    # 不，Service 使用 admin client，所以 API 层必须校验。

    if not is_author:
        # Check roles
        try:
            profile_res = (
                supabase.table("user_profiles")
                .select("roles")
                .eq("id", current_user["id"])
                .single()
                .execute()
            )
            profile = getattr(profile_res, "data", {})
            roles = profile.get("roles", [])
            if (
                "editor" not in roles
                and "admin" not in roles
                and "reviewer" not in roles
            ):
                raise HTTPException(status_code=403, detail="Access denied")
        except Exception:
            raise HTTPException(status_code=403, detail="Access denied")

    result = service.get_version_history(str(manuscript_id))

    if not result["success"]:
        raise HTTPException(status_code=500, detail=result["error"])

    return VersionHistoryResponse(data=result["data"])


# === 2. 编辑质检 (User Story 2) ===
@router.post("/manuscripts/{manuscript_id}/quality-check")
async def submit_quality_check(
    manuscript_id: UUID,
    passed: bool = Body(..., embed=True),
    owner_id: Optional[UUID] = Body(None, embed=True),
    kpi_owner_id: Optional[UUID] = Body(None, embed=True),  # 兼容旧字段名
):
    resolved_owner_id = owner_id or kpi_owner_id
    if not resolved_owner_id:
        raise HTTPException(status_code=422, detail="owner_id is required")

    # 显性逻辑：owner_id 必须属于内部员工（editor/admin）
    try:
        validate_internal_owner_id(resolved_owner_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="owner_id must be editor/admin")

    result = await process_quality_check(manuscript_id, passed, resolved_owner_id)
    return {"success": True, "data": result}


# === 3. 搜索与列表 (Discovery) ===
@router.get("/manuscripts")
async def get_manuscripts():
    """获取所有稿件列表"""
    try:
        response = (
            supabase.table("manuscripts")
            .select("*")
            .order("created_at", desc=True)
            .execute()
        )
        # supabase-py 的 execute() 返回的是一个对象，其 data 属性包含结果
        return {"success": True, "data": response.data}
    except Exception as e:
        print(f"查询失败: {str(e)}")
        return {"success": False, "data": []}


@router.get("/manuscripts/mine")
async def get_my_manuscripts(current_user: dict = Depends(get_current_user)):
    """作者视角：仅返回当前用户的稿件列表"""
    try:
        # 中文注释: 作者列表仅展示自己投稿，避免越权查看
        response = (
            supabase.table("manuscripts")
            .select("*")
            .eq("author_id", current_user["id"])
            .order("created_at", desc=True)
            .execute()
        )
        return {"success": True, "data": response.data}
    except Exception as e:
        print(f"作者稿件查询失败: {str(e)}")
        return {"success": False, "data": []}


@router.get("/manuscripts/search")
async def public_search(q: str, mode: str = "articles"):
    """公开检索"""
    try:
        if mode == "articles":
            response = (
                supabase.table("manuscripts")
                .select("*, journals(title)")
                .eq("status", "published")
                .or_(f"title.ilike.%{q}%,abstract.ilike.%{q}%")
                .execute()
            )
        else:
            response = (
                supabase.table("journals")
                .select("*")
                .ilike("title", f"%{q}%")
                .execute()
            )
        return {"success": True, "results": response.data}
    except Exception as e:
        print(f"搜索异常: {str(e)}")
        return {"success": False, "results": []}


# === 4. 详情查询 ===
@router.get("/manuscripts/articles/{id}")
async def get_article_detail(id: UUID):
    try:
        manuscript_response = (
            supabase.table("manuscripts")
            .select("*")
            .eq("id", str(id))
            .single()
            .execute()
        )
        manuscript = manuscript_response.data
        if not manuscript:
            raise HTTPException(status_code=404, detail="Article not found")

        # Feature 023: 返回 owner 详细信息（姓名/邮箱），用于 KPI 归属展示
        owner_raw = manuscript.get("owner_id") or manuscript.get("kpi_owner_id")
        if owner_raw:
            try:
                profile = get_profile_for_owner(UUID(str(owner_raw)))
                if profile:
                    manuscript["owner"] = {
                        "id": profile.get("id"),
                        "full_name": profile.get("full_name"),
                        "email": profile.get("email"),
                    }
            except Exception as e:
                print(f"[OwnerBinding] 获取 owner profile 失败（降级忽略）: {e}")
        # 中文注释: 兼容未建立 journals 外键关系的环境，按需补充期刊信息
        journal_id = manuscript.get("journal_id")
        if journal_id:
            journal_response = (
                supabase.table("journals")
                .select("*")
                .eq("id", journal_id)
                .single()
                .execute()
            )
            manuscript["journals"] = journal_response.data
        else:
            manuscript["journals"] = None
        return {"success": True, "data": manuscript}
    except HTTPException:
        raise
    except Exception as e:
        print(f"文章详情查询失败: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch article detail")


@router.patch("/manuscripts/{manuscript_id}")
async def update_manuscript(
    manuscript_id: UUID,
    owner_id: Optional[UUID] = Body(None, embed=True),
    _profile: dict = Depends(require_any_role(["editor", "admin"])),
):
    """
    Feature 023: 允许 Editor/Admin 更新稿件 owner_id（KPI 归属人绑定）。

    中文注释:
    - owner_id 允许为空（自然投稿/未绑定）。
    - 若传入非空 owner_id，必须校验其角色为 editor/admin（防止误绑定外部作者/审稿人）。
    """
    try:
        update_data = {
            "owner_id": None,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        if owner_id is not None:
            try:
                validate_internal_owner_id(owner_id)
            except ValueError:
                raise HTTPException(status_code=422, detail="owner_id must be editor/admin")
            update_data["owner_id"] = str(owner_id)

        resp = (
            supabase_admin.table("manuscripts")
            .update(update_data)
            .eq("id", str(manuscript_id))
            .execute()
        )
        data = getattr(resp, "data", None) or []
        if not data:
            raise HTTPException(status_code=404, detail="Manuscript not found")
        return {"success": True, "data": data[0]}
    except HTTPException:
        raise
    except Exception as e:
        print(f"[OwnerBinding] 更新 owner_id 失败: {e}")
        raise HTTPException(status_code=500, detail="Failed to update manuscript")


@router.post("/manuscripts")
async def create_manuscript(
    manuscript: ManuscriptCreate,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
):
    """创建新稿件（需要登录）"""
    try:
        # 生成新的稿件 ID
        manuscript_id = uuid4()
        # 使用当前登录用户的 ID，而不是传入的 author_id
        data = {
            "id": str(manuscript_id),
            "title": manuscript.title,
            "abstract": manuscript.abstract,
            "file_path": manuscript.file_path,
            "dataset_url": manuscript.dataset_url,
            "source_code_url": manuscript.source_code_url,
            "author_id": current_user["id"],  # 使用真实的用户 ID
            "status": "submitted",
            "owner_id": None,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

        # 插入到数据库
        response = supabase.table("manuscripts").insert(data).execute()

        if response.data:
            created = response.data[0]

            # === 通知中心 (Feature 011) ===
            # 中文注释:
            # 1) 投稿成功：作者收到站内信 + 邮件（异步）。
            # 2) 新投稿提醒：所有 editor/admin 账号收到站内信（邮件可在后续扩展）。
            notification_service = NotificationService()
            notification_service.create_notification(
                user_id=current_user["id"],
                manuscript_id=str(manuscript_id),
                type="submission",
                title="Submission Received",
                content=f"Your manuscript '{manuscript.title}' has been successfully submitted.",
            )

            # 尝试通知编辑（若 user_profiles 存在）
            try:
                editors_res = (
                    supabase_admin.table("user_profiles")
                    .select("id, roles")
                    .or_("roles.cs.{editor},roles.cs.{admin}")
                    .execute()
                )
                editors = getattr(editors_res, "data", None) or []
                for editor_profile in editors:
                    editor_id = editor_profile.get("id")
                    if not editor_id:
                        continue
                    notification_service.create_notification(
                        user_id=str(editor_id),
                        manuscript_id=str(manuscript_id),
                        type="system",
                        title="New Submission",
                        content=f"A new manuscript '{manuscript.title}' is awaiting editorial action.",
                    )
            except Exception as e:
                print(f"[Notifications] 查询编辑列表失败（降级忽略）: {e}")

            # 异步发送邮件（失败不影响主流程）
            try:
                author_email = current_user.get("email")
                if author_email:
                    email_service = EmailService()
                    background_tasks.add_task(
                        email_service.send_template_email,
                        to_email=author_email,
                        subject="Submission Received",
                        template_name="submission_ack.html",
                        context={
                            "subject": "Submission Received",
                            "recipient_name": author_email.split("@")[0]
                            .replace(".", " ")
                            .title(),
                            "manuscript_title": manuscript.title,
                            "manuscript_id": str(manuscript_id),
                        },
                    )
            except Exception as e:
                print(f"[SMTP] 异步发送任务创建失败（降级忽略）: {e}")

            return {"success": True, "data": created}
        else:
            return {"success": False, "message": "Failed to create manuscript"}

    except Exception as e:
        print(f"创建稿件失败: {str(e)}")
        return {"success": False, "message": str(e)}


@router.get("/manuscripts/journals/{slug}")
async def get_journal_detail(slug: str):
    try:
        journal_response = (
            supabase.table("journals").select("*").eq("slug", slug).single().execute()
        )
        journal = journal_response.data
        if not journal:
            raise HTTPException(status_code=404, detail="Journal not found")
        articles_response = (
            supabase.table("manuscripts")
            .select("*")
            .eq("journal_id", journal["id"])
            .eq("status", "published")
            .execute()
        )
        return {"success": True, "journal": journal, "articles": articles_response.data}
    except HTTPException:
        raise
    except Exception as e:
        print(f"期刊详情查询失败: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch journal detail")
