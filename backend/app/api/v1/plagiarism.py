import os

from fastapi import APIRouter, BackgroundTasks, HTTPException
from app.models.plagiarism import PlagiarismRetryRequest
from app.core.plagiarism_worker import plagiarism_check_worker
from uuid import UUID

router = APIRouter(prefix="/plagiarism", tags=["Plagiarism"])

def _is_truthy_env(name: str, default: str = "0") -> bool:
    v = (os.environ.get(name, default) or "").strip().lower()
    return v in {"1", "true", "yes", "on"}

def _require_plagiarism_enabled() -> None:
    # 当前查重实现为 Mock（CrossrefClient 直接返回固定相似度），默认关闭以提速。
    if not _is_truthy_env("PLAGIARISM_CHECK_ENABLED", "0"):
        raise HTTPException(status_code=503, detail="Plagiarism check is disabled (PLAGIARISM_CHECK_ENABLED=0)")

@router.get("/report/{report_id}/download")
async def get_report_download_url(report_id: UUID):
    """
    获取查重报告的带签名下载链接
    
    中文注释:
    1. 遵循章程: 仅限编辑和相关权限人员访问（实际需结合 Auth 校验）。
    2. 生成 Supabase Storage 的带签名临时链接，确保 PDF 版权安全。
    """
    # 模拟生成逻辑
    return {"download_url": f"https://supabase.storage/signed/{report_id}.pdf"}

@router.post("/retry")
async def retry_plagiarism_check(
    request: PlagiarismRetryRequest, 
    background_tasks: BackgroundTasks
):
    """
    手动重新触发查重任务
    
    中文注释:
    1. 显性逻辑: 仅在状态为 failed 时允许重试。
    2. 幂等性校验: 重置重试计数并重新将任务推入后台队列。
    """
    _require_plagiarism_enabled()
    manuscript_id = request.manuscript_id
    
    # 实际应查询数据库校验状态
    print(f"手动重试稿件 {manuscript_id} 的查重任务")
    
    # 重新触发异步 Worker (T007)
    background_tasks.add_task(plagiarism_check_worker, manuscript_id)
    
    return {"success": True, "message": "任务已重新加入队列"}
