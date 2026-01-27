from fastapi import APIRouter, UploadFile, File, BackgroundTasks, HTTPException
from app.core.pdf_processor import extract_text_from_pdf
from app.core.ai_engine import parse_manuscript_metadata
from app.core.plagiarism_worker import plagiarism_check_worker
from uuid import uuid4
from typing import Dict, Any
import shutil
import os

router = APIRouter(prefix="/manuscripts", tags=["Manuscripts"])

@router.post("/upload")
async def upload_manuscript(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    """
    稿件上传与 AI 自动解析入口
    
    中文注释:
    1. 接收 PDF 文件，临时保存并执行文本提取。
    2. 同步调用 AI 解析逻辑以返回初步结果供作者校对。
    3. 异步触发查重任务 (T008)。
    """
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="仅支持 PDF 格式文件")

    # 模拟生成 UUID
    manuscript_id = uuid4()
    temp_path = f"temp_{file.filename}"
    try:
        # 保存临时文件
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # 1. 提取文本
        text = extract_text_from_pdf(temp_path)
        if not text:
            return {"title": "", "abstract": "", "authors": [], "message": "无法读取 PDF 文本，请手动填写"}

        # 2. AI 解析
        metadata = await parse_manuscript_metadata(text)
        
        # 3. 异步触发查重流程 (T008)
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
        # 清理临时文件 (如果存在)
        if os.path.exists(temp_path):
            os.remove(temp_path)