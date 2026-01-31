from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, Optional
from uuid import UUID, uuid4

from app.core.config import CrossrefConfig
from app.models.doi import DOIRegistration, DOIRegistrationStatus
from app.services.crossref_client import CrossrefClient


class DOIService:
    """
    DOI Service（Feature 015）

    中文注释:
    - Feature 016 的核心是“回归测试可靠性”。默认测试运行不应依赖外部网络（Supabase/Crossref）。
    - 因此该服务在当前阶段使用“进程内存存根”来支持 API 行为与回归验证。
    - 数据库表/迁移已由 `supabase/migrations/` 提供；若后续要做真实持久化，可将此处替换为 DB 实现。
    """

    _registrations_by_article_id: Dict[str, DOIRegistration] = {}

    def __init__(
        self,
        config: Optional[CrossrefConfig] = None,
        crossref_client: Optional[CrossrefClient] = None,
    ):
        self.config = config
        self.crossref_client = crossref_client or CrossrefClient(config)

    def generate_doi(self, year: int, sequence: int) -> str:
        """
        生成 DOI 字符串: prefix/sf.{year}.{sequence}
        e.g. 10.12345/sf.2026.00001
        """

        # 中文注释: 为满足 `app/models/doi.py` 的 DOI 正则校验，这里使用大写字母前缀。
        prefix = self.config.doi_prefix if self.config else "10.12345"
        return f"{prefix}/SF.{year}.{sequence:05d}"

    async def create_registration(self, article_id: UUID) -> DOIRegistration:
        existing = self._registrations_by_article_id.get(str(article_id))
        if existing:
            return existing

        now = datetime.now(timezone.utc)
        reg = DOIRegistration(
            id=uuid4(),
            article_id=article_id,
            doi=self.generate_doi(now.year, 1),
            status=DOIRegistrationStatus.PENDING,
            attempts=0,
            crossref_batch_id=None,
            error_message=None,
            registered_at=None,
            created_at=now,
            updated_at=now,
        )
        self._registrations_by_article_id[str(article_id)] = reg
        return reg

    async def get_registration(self, article_id: UUID) -> Optional[DOIRegistration]:
        return self._registrations_by_article_id.get(str(article_id))

    async def register_doi(self, registration_id: UUID) -> None:
        # 中文注释: 当前存根不执行外部网络请求；worker 调用不抛错即可。
        _ = registration_id
        return
