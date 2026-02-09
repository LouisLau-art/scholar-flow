import asyncio
import logging
import os
from uuid import UUID

from app.services.crossref_client import CrossrefClient
from app.services.plagiarism_service import PlagiarismService

# === 结构化日志配置 ===
logger = logging.getLogger("plagiarism_worker")


def _env_float(name: str, default: float) -> float:
    raw = (os.environ.get(name) or "").strip()
    if not raw:
        return default
    try:
        return float(raw)
    except Exception:
        return default


def _env_int(name: str, default: int) -> int:
    raw = (os.environ.get(name) or "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except Exception:
        return default


async def plagiarism_check_worker(manuscript_id: UUID | str):
    """
    查重处理异步 Worker。

    中文注释:
    - 上传流程只负责“投递任务”，实际外部调用与状态落库在这里执行。
    - 失败不会阻断主提交流程，仅落库为 failed 并保留错误信息。
    """
    manuscript_id_str = str(manuscript_id)
    service = PlagiarismService()
    client = CrossrefClient()

    submit_delay = max(0.0, _env_float("PLAGIARISM_SUBMIT_DELAY_SEC", 0.2))
    poll_interval = max(0.2, _env_float("PLAGIARISM_POLL_INTERVAL_SEC", 3.0))
    poll_attempts = max(1, _env_int("PLAGIARISM_POLL_MAX_ATTEMPTS", 5))
    threshold = _env_float("PLAGIARISM_SIMILARITY_THRESHOLD", 0.30)

    logger.info("开始为稿件 %s 执行查重异步任务", manuscript_id_str)

    try:
        service.ensure_report(manuscript_id_str)
        await asyncio.sleep(submit_delay)

        external_id = await client.submit_manuscript("mock_path")
        if not external_id:
            raise RuntimeError("外部查重平台任务提交失败")

        service.mark_running(manuscript_id_str, external_id=external_id)

        for _attempt in range(poll_attempts):
            await asyncio.sleep(poll_interval)
            result = await client.get_check_status(external_id)
            status = str(result.get("status") or "").strip().lower()

            if status == "completed":
                score = float(result.get("similarity_score") or 0.0)
                report_url = str(result.get("report_url") or "").strip()
                service.mark_completed(
                    manuscript_id_str,
                    similarity_score=score,
                    report_url=report_url,
                    external_id=external_id,
                )

                if score > threshold:
                    service.record_high_similarity_alert(
                        manuscript_id=manuscript_id_str,
                        similarity_score=score,
                        threshold=threshold,
                    )

                logger.info("查重完成: %s, 得分: %.4f", manuscript_id_str, score)
                return

        raise RuntimeError("查重任务轮询超时")

    except Exception as e:
        service.mark_failed(manuscript_id_str, error_message=str(e), increment_retry=True)
        logger.error("查重 Worker 异常: %s", str(e))
