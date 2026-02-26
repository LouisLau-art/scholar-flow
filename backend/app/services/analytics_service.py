"""
Analytics Service - 分析服务层
功能: 封装 Supabase RPC 和 View 调用，提供分析数据访问

中文注释:
- 使用 Supabase-py v2 客户端执行 RPC 和 View 查询
- 所有数据库聚合逻辑在 PostgreSQL 中执行，Python 层仅做数据转发
- 遵循章程: 核心计算逻辑放在 SQL 层，服务层保持简单
"""

import os
from datetime import date, datetime, timezone
from typing import Literal, Optional, cast

from supabase import Client, create_client

from app.models.analytics import (
    DecisionData,
    EditorEfficiencyItem,
    GeoData,
    KPISummary,
    PipelineData,
    SLAAlertItem,
    StageDurationItem,
    TrendData,
)

StageName = Literal["pre_check", "under_review", "decision", "production"]


def get_supabase_client() -> Client:
    """
    获取 Supabase 客户端实例
    中文注释: 使用环境变量配置，确保安全
    """
    url = os.environ.get("SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
    if not url or not key:
        raise ValueError("SUPABASE_URL 和 SUPABASE_SERVICE_ROLE_KEY 环境变量必须设置")
    return create_client(url, key)


class AnalyticsService:
    """
    分析数据服务类
    封装所有分析相关的数据库操作
    """

    def __init__(self, supabase_client: Optional[Client] = None):
        """
        初始化服务
        中文注释: 允许注入客户端以便测试
        """
        self._client = supabase_client

    @property
    def client(self) -> Client:
        """延迟初始化 Supabase 客户端"""
        if self._client is None:
            self._client = get_supabase_client()
        return self._client

    def _is_missing_rpc_error(self, error: Exception | str) -> bool:
        text = str(error or "").lower()
        return "function" in text and "does not exist" in text

    def _to_sla_severity(self, *, overdue_tasks_count: int, max_overdue_days: float) -> str:
        """
        SLA 风险等级规则（显性）：
        - high: 逾期任务 >=3 或最长逾期 >=7 天
        - medium: 逾期任务 >=2 或最长逾期 >=3 天
        - low: 其余
        """
        if overdue_tasks_count >= 3 or max_overdue_days >= 7:
            return "high"
        if overdue_tasks_count >= 2 or max_overdue_days >= 3:
            return "medium"
        return "low"

    @staticmethod
    def _normalize_journal_ids(journal_ids: list[str] | None) -> list[str] | None:
        if journal_ids is None:
            return None
        normalized: list[str] = []
        seen: set[str] = set()
        for raw in journal_ids:
            jid = str(raw or "").strip()
            if not jid or jid in seen:
                continue
            seen.add(jid)
            normalized.append(jid)
        return normalized

    @staticmethod
    def _parse_dt(value: object) -> datetime | None:
        raw = str(value or "").strip()
        if not raw:
            return None
        try:
            return datetime.fromisoformat(raw.replace("Z", "+00:00")).astimezone(timezone.utc)
        except Exception:
            return None

    @staticmethod
    def _month_bucket(dt: datetime) -> date:
        return date(dt.year, dt.month, 1)

    async def get_kpi_summary(self, *, journal_ids: list[str] | None = None) -> KPISummary:
        """
        获取 KPI 汇总数据
        调用 get_journal_kpis() RPC

        中文注释:
        - RPC 返回 JSON，直接解析为 KPISummary 模型
        - 所有计算逻辑在 PostgreSQL 中完成
        """
        scope_ids = self._normalize_journal_ids(journal_ids)
        if scope_ids is None:
            response = self.client.rpc("get_journal_kpis").execute()
            if response.data is None:
                return KPISummary(
                    new_submissions_month=0,
                    total_pending=0,
                    avg_first_decision_days=0,
                    yearly_acceptance_rate=0,
                    apc_revenue_month=0,
                    apc_revenue_year=0,
                )
            data = response.data
            return KPISummary(
                new_submissions_month=data.get("new_submissions_month", 0),
                total_pending=data.get("total_pending", 0),
                avg_first_decision_days=data.get("avg_first_decision_days", 0),
                yearly_acceptance_rate=data.get("yearly_acceptance_rate", 0),
                apc_revenue_month=data.get("apc_revenue_month", 0),
                apc_revenue_year=data.get("apc_revenue_year", 0),
            )

        if not scope_ids:
            return KPISummary(
                new_submissions_month=0,
                total_pending=0,
                avg_first_decision_days=0,
                yearly_acceptance_rate=0,
                apc_revenue_month=0,
                apc_revenue_year=0,
            )

        now = datetime.now(timezone.utc)
        month_start = datetime(now.year, now.month, 1, tzinfo=timezone.utc)
        year_start = datetime(now.year, 1, 1, tzinfo=timezone.utc)

        ms_resp = (
            self.client.table("manuscripts")
            .select("status,created_at,updated_at,journal_id")
            .in_("journal_id", scope_ids)
            .execute()
        )
        rows = ms_resp.data or []

        new_submissions_month = 0
        total_pending = 0
        first_decision_deltas: list[float] = []
        accepted_year = 0
        rejected_year = 0

        pending_statuses = {
            "submitted",
            "pre_check",
            "under_review",
            "revision",
            "revision_requested",
            "major_revision",
            "minor_revision",
            "resubmitted",
            "decision",
        }
        accept_statuses = {"accepted", "approved", "published"}

        for row in rows:
            status = str(row.get("status") or "").strip().lower()
            created_at = self._parse_dt(row.get("created_at"))
            updated_at = self._parse_dt(row.get("updated_at"))

            if created_at and created_at >= month_start:
                new_submissions_month += 1
            if status in pending_statuses:
                total_pending += 1

            if created_at and updated_at and updated_at > created_at:
                delta_days = (updated_at - created_at).total_seconds() / 86400.0
                if delta_days >= 0 and status in (accept_statuses | {"rejected", "major_revision", "minor_revision"}):
                    first_decision_deltas.append(delta_days)

            if created_at and created_at >= year_start:
                if status in accept_statuses:
                    accepted_year += 1
                elif status == "rejected":
                    rejected_year += 1

        avg_first_decision_days = (
            round(sum(first_decision_deltas) / len(first_decision_deltas), 1)
            if first_decision_deltas
            else 0.0
        )
        yearly_acceptance_rate = (
            float(accepted_year) / float(accepted_year + rejected_year)
            if (accepted_year + rejected_year) > 0
            else 0.0
        )

        apc_revenue_month = 0.0
        apc_revenue_year = 0.0
        try:
            inv_resp = (
                self.client.table("invoices")
                .select("amount,status,confirmed_at,created_at,manuscripts(journal_id)")
                .execute()
            )
            inv_rows = inv_resp.data or []
            allowed = set(scope_ids)
            for row in inv_rows:
                ms = row.get("manuscripts")
                if isinstance(ms, list):
                    ms = ms[0] if ms else {}
                if not isinstance(ms, dict):
                    ms = {}
                journal_id = str(ms.get("journal_id") or "").strip()
                if journal_id not in allowed:
                    continue

                status = str(row.get("status") or "").strip().lower()
                if status not in {"paid", "confirmed"}:
                    continue

                try:
                    amount = float(row.get("amount") or 0)
                except Exception:
                    amount = 0.0

                anchor = self._parse_dt(row.get("confirmed_at")) or self._parse_dt(row.get("created_at"))
                if not anchor:
                    continue
                if anchor >= month_start:
                    apc_revenue_month += amount
                if anchor >= year_start:
                    apc_revenue_year += amount
        except Exception:
            # 中文注释: 发票统计失败时不阻断 KPI 主体，收入字段降级为 0。
            apc_revenue_month = 0.0
            apc_revenue_year = 0.0

        return KPISummary(
            new_submissions_month=new_submissions_month,
            total_pending=total_pending,
            avg_first_decision_days=float(avg_first_decision_days),
            yearly_acceptance_rate=float(round(yearly_acceptance_rate, 4)),
            apc_revenue_month=float(round(apc_revenue_month, 2)),
            apc_revenue_year=float(round(apc_revenue_year, 2)),
        )

    async def get_submission_trends(self, *, journal_ids: list[str] | None = None) -> list[TrendData]:
        """
        获取投稿趋势数据
        查询 view_submission_trends 视图

        中文注释: 返回过去 12 个月的投稿和接受趋势
        """
        scope_ids = self._normalize_journal_ids(journal_ids)
        if scope_ids is None:
            response = self.client.table("view_submission_trends").select("*").execute()
            if not response.data:
                return []
            return [
                TrendData(
                    month=row["month"],
                    submission_count=row["submission_count"],
                    acceptance_count=row["acceptance_count"],
                )
                for row in response.data
            ]

        if not scope_ids:
            return []

        now = datetime.now(timezone.utc)
        current_idx = now.year * 12 + now.month - 1
        start_idx = current_idx - 11
        start_year = start_idx // 12
        start_month = start_idx % 12 + 1
        start_dt = datetime(start_year, start_month, 1, tzinfo=timezone.utc)

        response = (
            self.client.table("manuscripts")
            .select("created_at,status")
            .in_("journal_id", scope_ids)
            .gte("created_at", start_dt.isoformat())
            .execute()
        )
        rows = response.data or []
        acceptance_statuses = {"accepted", "approved", "published"}
        buckets: dict[int, dict[str, int]] = {
            idx: {"submission_count": 0, "acceptance_count": 0}
            for idx in range(start_idx, current_idx + 1)
        }

        for row in rows:
            created_at = self._parse_dt(row.get("created_at"))
            if not created_at:
                continue
            idx = created_at.year * 12 + created_at.month - 1
            if idx < start_idx or idx > current_idx:
                continue
            buckets[idx]["submission_count"] += 1
            status = str(row.get("status") or "").strip().lower()
            if status in acceptance_statuses:
                buckets[idx]["acceptance_count"] += 1

        out: list[TrendData] = []
        for idx in range(start_idx, current_idx + 1):
            year = idx // 12
            month = idx % 12 + 1
            out.append(
                TrendData(
                    month=date(year, month, 1),
                    submission_count=int(buckets[idx]["submission_count"]),
                    acceptance_count=int(buckets[idx]["acceptance_count"]),
                )
            )
        return out

    async def get_status_pipeline(self, *, journal_ids: list[str] | None = None) -> list[PipelineData]:
        """
        获取状态流水线数据
        查询 view_status_pipeline 视图

        中文注释: 返回当前活跃稿件的状态分布
        """
        scope_ids = self._normalize_journal_ids(journal_ids)
        if scope_ids is None:
            response = self.client.table("view_status_pipeline").select("*").execute()
            if not response.data:
                return []
            return [
                PipelineData(
                    stage=row["stage"],
                    count=row["count"],
                )
                for row in response.data
            ]

        if not scope_ids:
            return []

        response = (
            self.client.table("manuscripts")
            .select("status")
            .in_("journal_id", scope_ids)
            .execute()
        )
        rows = response.data or []
        counters = {
            "submitted": 0,
            "under_review": 0,
            "revision": 0,
            "in_production": 0,
        }
        for row in rows:
            status = str(row.get("status") or "").strip().lower()
            if status in {"submitted", "pre_check"}:
                counters["submitted"] += 1
            elif status == "under_review":
                counters["under_review"] += 1
            elif status in {"revision", "revision_requested", "major_revision", "minor_revision", "resubmitted", "decision"}:
                counters["revision"] += 1
            elif status in {"in_production", "approved", "layout", "english_editing", "proofreading"}:
                counters["in_production"] += 1

        return [
            PipelineData(stage=stage, count=count)
            for stage, count in (
                ("submitted", counters["submitted"]),
                ("under_review", counters["under_review"]),
                ("revision", counters["revision"]),
                ("in_production", counters["in_production"]),
            )
            if count > 0
        ]

    async def get_decision_distribution(self, *, journal_ids: list[str] | None = None) -> list[DecisionData]:
        """
        获取决定分布数据
        查询 view_decision_distribution 视图

        中文注释: 返回年度决定分布（接受/拒绝/修改）
        """
        scope_ids = self._normalize_journal_ids(journal_ids)
        if scope_ids is None:
            response = self.client.table("view_decision_distribution").select("*").execute()
            if not response.data:
                return []
            return [
                DecisionData(
                    decision=row["decision"],
                    count=row["count"],
                )
                for row in response.data
            ]

        if not scope_ids:
            return []

        now = datetime.now(timezone.utc)
        year_start = datetime(now.year, 1, 1, tzinfo=timezone.utc)
        response = (
            self.client.table("manuscripts")
            .select("status,created_at")
            .in_("journal_id", scope_ids)
            .gte("created_at", year_start.isoformat())
            .execute()
        )
        rows = response.data or []
        counters = {"accepted": 0, "rejected": 0, "revision": 0, "desk_reject": 0}
        for row in rows:
            status = str(row.get("status") or "").strip().lower()
            if status in {"accepted", "approved", "published"}:
                counters["accepted"] += 1
            elif status == "rejected":
                counters["rejected"] += 1
            elif status in {"revision", "revision_requested", "major_revision", "minor_revision", "resubmitted"}:
                counters["revision"] += 1
            elif status == "desk_reject":
                counters["desk_reject"] += 1

        return [
            DecisionData(decision=decision, count=count)
            for decision, count in counters.items()
            if count > 0
        ]

    async def get_author_geography(self, *, journal_ids: list[str] | None = None) -> list[GeoData]:
        """
        获取作者地理分布数据
        调用 get_author_geography() RPC

        中文注释: 返回 Top 10 国家的投稿数
        """
        scope_ids = self._normalize_journal_ids(journal_ids)
        if scope_ids is None:
            response = self.client.rpc("get_author_geography").execute()
            if not response.data:
                return []
            return [
                GeoData(
                    country=row["country"],
                    submission_count=row["submission_count"],
                )
                for row in response.data
            ]

        if not scope_ids:
            return []

        ms_resp = (
            self.client.table("manuscripts")
            .select("author_id")
            .in_("journal_id", scope_ids)
            .execute()
        )
        ms_rows = ms_resp.data or []
        if not ms_rows:
            return []

        author_ids = sorted(
            {
                str(row.get("author_id") or "").strip()
                for row in ms_rows
                if str(row.get("author_id") or "").strip()
            }
        )
        if not author_ids:
            return []

        profile_resp = (
            self.client.table("user_profiles")
            .select("id,country")
            .in_("id", author_ids)
            .execute()
        )
        profile_rows = profile_resp.data or []
        country_by_author = {
            str(row.get("id") or ""): str(row.get("country") or "").strip()
            for row in profile_rows
            if str(row.get("id") or "").strip()
        }

        counts: dict[str, int] = {}
        for row in ms_rows:
            aid = str(row.get("author_id") or "").strip()
            if not aid:
                continue
            country = country_by_author.get(aid, "")
            if not country:
                continue
            counts[country] = counts.get(country, 0) + 1

        ranked = sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:10]
        return [
            GeoData(country=country, submission_count=count)
            for country, count in ranked
        ]

    async def get_editor_efficiency_ranking(
        self,
        *,
        limit: int = 10,
        journal_ids: list[str] | None = None,
    ) -> list[EditorEfficiencyItem]:
        """
        获取编辑效率排行（处理量 + 平均首次决定耗时）。
        """
        params = {
            "limit_count": int(max(1, limit)),
            "journal_ids": journal_ids or None,
        }
        try:
            response = self.client.rpc("get_editor_efficiency_ranking", params).execute()
        except Exception as e:
            if self._is_missing_rpc_error(e):
                return []
            raise

        rows = response.data or []
        return [
            EditorEfficiencyItem(
                editor_id=str(row.get("editor_id") or ""),
                editor_name=str(row.get("editor_name") or "Unknown Editor"),
                editor_email=row.get("editor_email"),
                handled_count=int(row.get("handled_count") or 0),
                avg_first_decision_days=float(row.get("avg_first_decision_days") or 0),
            )
            for row in rows
            if row.get("editor_id")
        ]

    async def get_stage_duration_breakdown(
        self,
        *,
        journal_ids: list[str] | None = None,
    ) -> list[StageDurationItem]:
        """
        获取阶段耗时分解（预审/外审/终审/生产）。
        """
        params = {
            "journal_ids": journal_ids or None,
        }
        try:
            response = self.client.rpc("get_stage_duration_breakdown", params).execute()
        except Exception as e:
            if self._is_missing_rpc_error(e):
                return []
            raise

        rows = response.data or []
        out: list[StageDurationItem] = []
        for row in rows:
            stage = str(row.get("stage") or "").strip()
            if stage not in {"pre_check", "under_review", "decision", "production"}:
                continue
            stage_value = cast(StageName, stage)
            out.append(
                StageDurationItem(
                    stage=stage_value,
                    avg_days=float(row.get("avg_days") or 0),
                    sample_size=int(row.get("sample_size") or 0),
                )
            )
        return out

    async def get_sla_alerts(
        self,
        *,
        limit: int = 20,
        journal_ids: list[str] | None = None,
    ) -> list[SLAAlertItem]:
        """
        获取超 SLA 稿件预警列表。
        """
        params = {
            "limit_count": int(max(1, limit)),
            "journal_ids": journal_ids or None,
        }
        try:
            response = self.client.rpc("get_sla_overdue_manuscripts", params).execute()
        except Exception as e:
            if self._is_missing_rpc_error(e):
                return []
            raise

        rows = response.data or []
        out: list[SLAAlertItem] = []
        for row in rows:
            manuscript_id = str(row.get("manuscript_id") or "")
            if not manuscript_id:
                continue
            overdue_tasks_count = int(row.get("overdue_tasks_count") or 0)
            max_overdue_days = float(row.get("max_overdue_days") or 0)
            out.append(
                SLAAlertItem(
                    manuscript_id=manuscript_id,
                    title=str(row.get("title") or manuscript_id),
                    status=str(row.get("status") or ""),
                    journal_id=str(row.get("journal_id") or "") or None,
                    journal_title=row.get("journal_title"),
                    editor_id=str(row.get("editor_id") or "") or None,
                    editor_name=row.get("editor_name"),
                    owner_id=str(row.get("owner_id") or "") or None,
                    owner_name=row.get("owner_name"),
                    overdue_tasks_count=overdue_tasks_count,
                    max_overdue_days=max_overdue_days,
                    earliest_due_at=row.get("earliest_due_at"),
                    severity=self._to_sla_severity(
                        overdue_tasks_count=overdue_tasks_count,
                        max_overdue_days=max_overdue_days,
                    ),
                )
            )
        return out


# 单例服务实例（可选，用于依赖注入）
_analytics_service: Optional[AnalyticsService] = None


def get_analytics_service() -> AnalyticsService:
    """
    获取 AnalyticsService 单例
    中文注释: 用于 FastAPI 依赖注入
    """
    global _analytics_service
    if _analytics_service is None:
        _analytics_service = AnalyticsService()
    return _analytics_service
