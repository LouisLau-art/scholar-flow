import asyncio
import logging
from datetime import datetime, timedelta
import random
from typing import Optional
from app.lib.api_client import supabase
from app.services.doi_service import DOIService
from app.core.config import CrossrefConfig, SMTPConfig
from app.core.mail import EmailService
from app.models.doi import DOITaskStatus, DOITaskType

logger = logging.getLogger("doi_worker")


class DOIWorker:
    def __init__(self):
        self.config = CrossrefConfig.from_env()
        self.smtp_config = SMTPConfig.from_env()
        self.doi_service = DOIService(self.config)
        self.email_service = EmailService() if self.smtp_config else None
        self.worker_id = f"worker-{datetime.now().timestamp()}"
        self.running = False

    async def start(self):
        logger.info(f"DOI Worker {self.worker_id} started")
        self.running = True
        while self.running:
            try:
                task = await self.claim_task()
                if task:
                    await self.process_task(task)
                else:
                    await asyncio.sleep(5)  # Poll interval
            except Exception as e:
                logger.error(f"Worker loop error: {e}")
                await asyncio.sleep(5)

    async def claim_task(self):
        # Atomic claim using Postgres SKIP LOCKED is hard with Supabase API client (REST).
        # We need to call an RPC function or use a specific strategy.
        # For MVP using standard supabase-py, we simulate atomic claim or use RPC if available.
        # Assuming we can't create RPC easily here without running migration against DB directly.
        # We'll use a best-effort approach: Update where status=pending and locked_at is null.

        # 1. Fetch pending tasks
        now = datetime.now().isoformat()
        res = (
            supabase.table("doi_tasks")
            .select("*")
            .eq("status", DOITaskStatus.PENDING)
            .lte("run_at", now)
            .order("priority", desc=True)
            .order("run_at", desc=False)
            .limit(1)
            .execute()
        )

        if not res.data:
            return None

        task = res.data[0]

        # 2. Try to lock
        update_res = (
            supabase.table("doi_tasks")
            .update(
                {
                    "status": DOITaskStatus.PROCESSING,
                    "locked_at": now,
                    "locked_by": self.worker_id,
                    "attempts": task["attempts"] + 1,
                }
            )
            .eq("id", task["id"])
            .eq("status", DOITaskStatus.PENDING)
            .execute()
        )

        if update_res.data:
            return update_res.data[0]
        return None

    async def process_task(self, task):
        logger.info(f"Processing task {task['id']} type={task['task_type']}")
        try:
            if task["task_type"] == DOITaskType.REGISTER:
                await self.doi_service.register_doi(task["registration_id"])

            # Complete
            supabase.table("doi_tasks").update(
                {
                    "status": DOITaskStatus.COMPLETED,
                    "completed_at": datetime.now().isoformat(),
                    "locked_by": None,
                }
            ).eq("id", task["id"]).execute()

        except Exception as e:
            logger.error(f"Task failed: {e}")
            await self.handle_failure(task, str(e))

    async def handle_failure(self, task, error_msg):
        attempts = task["attempts"]
        max_attempts = task["max_attempts"]

        if attempts >= max_attempts:
            # Final failure
            supabase.table("doi_tasks").update(
                {
                    "status": DOITaskStatus.FAILED,
                    "last_error": error_msg,
                    "locked_by": None,
                }
            ).eq("id", task["id"]).execute()

            # Notify admin
            await self.notify_failure(task, error_msg)
        else:
            # Retry with exponential backoff
            # 1min, 5min, 30min, 2h
            delay_minutes = [1, 5, 30, 120][min(attempts - 1, 3)]
            next_run = datetime.now() + timedelta(minutes=delay_minutes)

            supabase.table("doi_tasks").update(
                {
                    "status": DOITaskStatus.PENDING,
                    "run_at": next_run.isoformat(),
                    "last_error": error_msg,
                    "locked_by": None,
                    "locked_at": None,
                }
            ).eq("id", task["id"]).execute()

    async def notify_failure(self, task, error_msg):
        if not self.email_service or not self.config:
            return

        # Assuming there's a configured admin email
        admin_email = "admin@example.com"  # Should be in config

        try:
            self.email_service.send_template_email(
                to_email=admin_email,
                subject=f"DOI Task Failed: {task['id']}",
                template_name="doi_failure.html",  # Mock template
                context={
                    "task_id": task["id"],
                    "error": error_msg,
                    "registration_id": task["registration_id"],
                },
            )
        except Exception as e:
            logger.error(f"Failed to send notification: {e}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    worker = DOIWorker()
    asyncio.run(worker.start())
