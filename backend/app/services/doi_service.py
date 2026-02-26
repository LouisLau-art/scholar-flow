from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from app.core.config import CrossrefConfig
from app.lib.api_client import supabase_admin
from app.services.crossref_client import CrossrefClient
from app.services.doi_service_data import DOIServiceDataMixin
from app.services.doi_service_workflow import DOIServiceWorkflowMixin


class DOIService(DOIServiceDataMixin, DOIServiceWorkflowMixin):
    """
    DOI/Crossref 服务（GAP-P2-01）。

    中文注释:
    - 使用数据库队列（doi_tasks）实现“异步可重试”。
    - 落库 `doi_registrations` + `doi_audit_log`，保证可追踪。
    """

    def __init__(
        self,
        config: Optional[CrossrefConfig] = None,
        *,
        client: Any | None = None,
        crossref_client: CrossrefClient | None = None,
    ):
        self.config = config
        self.client = client or supabase_admin
        self.crossref = crossref_client or CrossrefClient(config)
        self.worker_id = f"doi-service-{int(datetime.now(timezone.utc).timestamp())}"

    def generate_doi(self, year: int, sequence: int) -> str:
        """
        Generate DOI string: prefix/sf.{year}.{sequence}
        e.g. 10.12345/sf.2026.00001
        """
        prefix = self.config.doi_prefix if self.config else "10.12345"
        return f"{prefix}/sf.{year}.{sequence:05d}"
