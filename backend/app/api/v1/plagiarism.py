import os
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, HTTPException

from app.core.plagiarism_worker import plagiarism_check_worker
from app.models.plagiarism import PlagiarismRetryRequest
from app.services.plagiarism_service import PlagiarismService

router = APIRouter(prefix="/plagiarism", tags=["Plagiarism"])


def _is_truthy_env(name: str, default: str = "0") -> bool:
    v = (os.environ.get(name, default) or "").strip().lower()
    return v in {"1", "true", "yes", "on"}


def _require_plagiarism_enabled() -> None:
    # 当前查重依赖外部服务，默认关闭；开启后走异步队列，不阻塞投稿主流程。
    if not _is_truthy_env("PLAGIARISM_CHECK_ENABLED", "0"):
        raise HTTPException(
            status_code=503,
            detail="Plagiarism check is disabled (PLAGIARISM_CHECK_ENABLED=0)",
        )


def _similarity_threshold() -> float:
    raw = (os.environ.get("PLAGIARISM_SIMILARITY_THRESHOLD") or "0.3").strip()
    try:
        return float(raw)
    except Exception:
        return 0.3


@router.get("/status/{manuscript_id}")
async def get_plagiarism_status(manuscript_id: UUID):
    """
    获取稿件查重状态。
    """
    svc = PlagiarismService()
    report = svc.get_report_by_manuscript(str(manuscript_id))
    if not report:
        return {
            "success": True,
            "data": {
                "manuscript_id": str(manuscript_id),
                "status": "not_started",
                "high_similarity": False,
            },
        }

    score = float(report.get("similarity_score") or 0.0)
    threshold = _similarity_threshold()
    report_data = {
        **report,
        "high_similarity": score > threshold,
        "threshold": threshold,
    }
    return {"success": True, "data": report_data}


@router.get("/report/{report_id}/download")
async def get_report_download_url(report_id: UUID):
    """
    获取查重报告的下载链接（外链或 signed URL）。
    """
    svc = PlagiarismService()
    report = svc.get_report_by_id(str(report_id))
    if not report:
        raise HTTPException(status_code=404, detail="Plagiarism report not found")

    try:
        download_url = svc.get_download_url(report)
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Report download unavailable: {e}") from e

    return {"download_url": download_url}


@router.post("/retry")
async def retry_plagiarism_check(
    request: PlagiarismRetryRequest,
    background_tasks: BackgroundTasks,
):
    """
    手动重新触发查重任务（幂等）。
    """
    _require_plagiarism_enabled()
    manuscript_id = str(request.manuscript_id)

    svc = PlagiarismService()
    current = svc.get_report_by_manuscript(manuscript_id)
    current_status = str((current or {}).get("status") or "").lower()
    if current_status in {"pending", "running"}:
        return {
            "success": True,
            "message": "任务已在队列中",
            "data": current,
        }

    report = svc.ensure_report(manuscript_id, reset_status=True)
    background_tasks.add_task(plagiarism_check_worker, manuscript_id)

    return {
        "success": True,
        "message": "任务已重新加入队列",
        "data": report,
    }
