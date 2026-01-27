from fastapi import APIRouter, UploadFile, File, BackgroundTasks, HTTPException, Body
from app.core.pdf_processor import extract_text_from_pdf
from app.core.ai_engine import parse_manuscript_metadata
from app.core.plagiarism_worker import plagiarism_check_worker
from app.services.editorial_service import process_quality_check
from app.services.publishing_service import publish_manuscript
from app.core.recommender import recommend_reviewers
from app.models.schemas import ManuscriptCreate
from app.lib.api_client import supabase
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
    data, _ = supabase.table("manuscripts").select("*, journals(*)").eq("id", str(id)).single().execute()
    return {"success": True, "data": data[1]}

@router.get("/manuscripts/journals/{slug}")
async def get_journal_detail(slug: str):
    journal = supabase.table("journals").select("*").eq("slug", slug).single().execute()[1]
    articles = supabase.table("manuscripts").select("*").eq("journal_id", journal['id']).eq("status", "published").execute()[1]
    return {"success": True, "journal": journal, "articles": articles}