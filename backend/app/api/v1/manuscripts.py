from fastapi import APIRouter, UploadFile, File, BackgroundTasks, HTTPException
from app.core.pdf_processor import extract_text_from_pdf
from app.core.ai_engine import parse_manuscript_metadata
from typing import Dict, Any
import shutil
import os

router = APIRouter(prefix="/manuscripts", tags=["Manuscripts"])

@router.post("/upload")
async def upload_manuscript(file: UploadFile = File(...)):
    """
    稿件上传与 AI 自动解析入口
    
    中文注释:
    1. 接收 PDF 文件，临时保存并执行文本提取。
    2. 同步调用 AI 解析逻辑以返回初步结果供作者校对。
    3. 遵循章程：逻辑直观，核心流程显性化。
    """
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="仅支持 PDF 格式文件")

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
        
        return {
            "success": True,
            "data": metadata,
            "temp_file": temp_path  # 后续正式提交时再持久化到 Supabase
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"上传解析失败: {str(e)}")
    finally:
        # 清理工作由具体业务逻辑决定，此处为 MVP 流程保留
        pass
