from fastapi import APIRouter, UploadFile, File, BackgroundTasks, HTTPException, Body
from app.core.pdf_processor import extract_text_from_pdf
from app.core.ai_engine import parse_manuscript_metadata
from app.core.plagiarism_worker import plagiarism_check_worker
from app.services.editorial_service import process_quality_check
from app.services.publishing_service import publish_manuscript
from app.core.recommender import recommend_reviewers
from uuid import uuid4, UUID
from typing import Dict, Any, List
import shutil
import os

router = APIRouter(prefix="/manuscripts", tags=["Manuscripts"])

# === 1. 投稿 (User Story 1) ===
@router.post("/upload")
async def upload_manuscript(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    """
    稿件上传与 AI 自动解析入口
    """
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="仅支持 PDF 格式文件")

    manuscript_id = uuid4()
    temp_path = f"temp_{file.filename}"
    try:
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        text = extract_text_from_pdf(temp_path)
        if not text:
            return {"title": "", "abstract": "", "authors": [], "message": "无法读取 PDF 文本，请手动填写"}

        metadata = await parse_manuscript_metadata(text)
        
        # 异步触发查重
        background_tasks.add_task(plagiarism_check_worker, manuscript_id)
        
        return {
            "success": True,
            "id": manuscript_id,
            "data": metadata,
            "plagiarism_status": "pending"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"上传解析失败: {str(e)}")
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

# === 2. 编辑质检 (User Story 2) ===
@router.post("/{manuscript_id}/quality-check")
async def submit_quality_check(
    manuscript_id: UUID,
    passed: bool = Body(..., embed=True),
    kpi_owner_id: UUID = Body(..., embed=True),
    revision_notes: str = Body(None, embed=True)
):
    """
    提交编辑质检结果
    
    中文注释:
    1. 调用 EditorialService 处理状态变更。
    2. 显性化逻辑: 绑定 KPI 责任人。
    """
    result = await process_quality_check(manuscript_id, passed, kpi_owner_id, revision_notes)
    return {"success": True, "data": result}

# === 3. AI 审稿人推荐 (User Story 5) ===
@router.get("/{manuscript_id}/recommend-reviewers")
async def get_reviewer_recommendations(manuscript_id: UUID):
    """
    获取 AI 推荐的审稿人列表
    """
    # 模拟从数据库获取稿件摘要 (实际应查表)
    mock_abstract = "Deep learning approaches in medical imaging analysis..."
    
    # 模拟审稿人池 (实际应查 auth.users)
    mock_pool = [
        {"id": uuid4(), "email": "expert_ai@univ.edu", "domains": ["AI", "Computer Vision"]},
        {"id": uuid4(), "email": "dr_med@hospital.org", "domains": ["Medicine", "Clinical"]},
        {"id": uuid4(), "email": "prof_block@tech.io", "domains": ["Blockchain", "Security"]}
    ]
    
    recommendations = recommend_reviewers(mock_abstract, mock_pool)
    return {"success": True, "recommendations": recommendations}

# === 4. 财务确认 (User Story 4) ===
@router.post("/{manuscript_id}/payment-confirm")
async def confirm_payment(manuscript_id: UUID):
    """
    财务确认到账
    
    中文注释:
    1. 实际逻辑应更新 invoices 表状态为 'paid'。
    2. 触发状态机流转至 'pending_publication'。
    """
    # 模拟数据库更新
    print(f"财务已确认稿件 {manuscript_id} 的款项")
    return {"success": True, "status": "paid", "confirmed_at": "2026-01-27T14:00:00Z"}

# === 5. 主编终审发布 (User Story 4 - Final Gate) ===
@router.post("/{manuscript_id}/publish")
async def publish_manuscript_endpoint(
    manuscript_id: UUID,
    finance_confirmed: bool = Body(..., embed=True), # 前端传递或后端查询
    eic_approval: bool = Body(..., embed=True)
):
    """
    主编终审发布接口
    
    中文注释:
    1. 调用 PublishingService 执行严格门控校验。
    2. 只有财务和主编双重确认后，才真正发布。
    """
    result = await publish_manuscript(manuscript_id, finance_confirmed, eic_approval)
    return {"success": True, "data": result}
