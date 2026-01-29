from fastapi import APIRouter, UploadFile, File, BackgroundTasks, HTTPException, Body, Depends
from app.core.pdf_processor import extract_text_from_pdf
from app.core.ai_engine import parse_manuscript_metadata
from app.core.plagiarism_worker import plagiarism_check_worker
from app.services.editorial_service import process_quality_check
from app.services.publishing_service import publish_manuscript
from app.core.recommender import recommend_reviewers
from app.models.schemas import ManuscriptCreate
from app.lib.api_client import supabase
from app.core.auth_utils import get_current_user
from uuid import uuid4, UUID
from typing import Dict, Any, List
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
            "created_at": "now()",
            "updated_at": "now()"
        }

        # 插入到数据库
        response = supabase.table("manuscripts").insert(data).execute()

        if response.data:
            return {"success": True, "data": response.data[0]}
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
