from fastapi import APIRouter, UploadFile, File, BackgroundTasks, HTTPException, Body, Depends
from app.core.pdf_processor import extract_text_from_pdf
from app.core.ai_engine import parse_manuscript_metadata
from app.core.plagiarism_worker import plagiarism_check_worker
from app.services.editorial_service import process_quality_check
from app.models.schemas import ManuscriptCreate
from app.lib.api_client import supabase, supabase_admin
from app.core.auth_utils import get_current_user
from app.core.mail import EmailService
from app.services.notification_service import NotificationService
from uuid import uuid4, UUID
import shutil
import os

router = APIRouter(tags=["Manuscripts"])

# === 1. 投稿 (User Story 1) ===
@router.post("/manuscripts/upload")
async def upload_manuscript(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    """稿件上传与 AI 解析"""
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="仅支持 PDF 格式文件")

    manuscript_id = uuid4()
    temp_path = f"temp_{file.filename}"
    try:
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        text = extract_text_from_pdf(temp_path)
        metadata = await parse_manuscript_metadata(text)
        background_tasks.add_task(plagiarism_check_worker, manuscript_id)
        return {"success": True, "id": manuscript_id, "data": metadata}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if os.path.exists(temp_path): os.remove(temp_path)

# === 2. 编辑质检 (User Story 2) ===
@router.post("/manuscripts/{manuscript_id}/quality-check")
async def submit_quality_check(
    manuscript_id: UUID,
    passed: bool = Body(..., embed=True),
    kpi_owner_id: UUID = Body(..., embed=True)
):
    result = await process_quality_check(manuscript_id, passed, kpi_owner_id)
    return {"success": True, "data": result}

# === 3. 搜索与列表 (Discovery) ===
@router.get("/manuscripts")
async def get_manuscripts():
    """获取所有稿件列表"""
    try:
        response = supabase.table("manuscripts").select("*").order("created_at", desc=True).execute()
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
            response = supabase.table("manuscripts").select("*, journals(title)").eq("status", "published").or_(f"title.ilike.%{q}%,abstract.ilike.%{q}%").execute()
        else:
            response = supabase.table("journals").select("*").ilike("title", f"%{q}%").execute()
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

@router.post("/manuscripts")
async def create_manuscript(
    manuscript: ManuscriptCreate,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user)
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
            "kpi_owner_id": None,
            # 中文注释: created_at/updated_at 由数据库默认值生成，避免传入 now() 字符串导致类型问题
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
                            "recipient_name": author_email.split("@")[0].replace(".", " ").title(),
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
        journal_response = supabase.table("journals").select("*").eq("slug", slug).single().execute()
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
