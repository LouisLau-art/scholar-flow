import asyncio
import logging
from datetime import datetime, timezone

from app.core.config import CrossrefConfig
from app.services.doi_service import DOIService

logger = logging.getLogger("doi_worker")


class DOIWorker:
    """
    兼容保留的 DOI Worker 入口。

    中文注释:
    - 实际处理逻辑委托给 DOIService，保证 internal cron 与独立 worker 行为一致。
    """

    def __init__(self):
        self.config = CrossrefConfig.from_env()
        self.doi_service = DOIService(self.config)
        self.worker_id = f"worker-{int(datetime.now(timezone.utc).timestamp())}"
        self.running = False

    async def start(self):
        logger.info("DOI Worker %s started", self.worker_id)
        self.running = True
        while self.running:
            try:
                result = await self.doi_service.process_due_tasks(limit=1)
                if int(result.get("processed_count") or 0) == 0:
                    await asyncio.sleep(5)
            except Exception as e:
                logger.error("Worker loop error: %s", e)
                await asyncio.sleep(5)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    worker = DOIWorker()
    asyncio.run(worker.start())
