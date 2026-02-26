from __future__ import annotations

from datetime import datetime
from typing import Any

from app.services.production_workspace_service_workflow_author import (
    ProductionWorkspaceWorkflowAuthorMixin,
)
from app.services.production_workspace_service_workflow_common import (
    ACTIVE_CYCLE_STATUSES,
    AUTHOR_CONTEXT_VISIBLE_STATUSES,
    POST_ACCEPTANCE_ALLOWED,
    is_missing_column_error,
    is_table_missing_error,
    is_truthy_env,
    safe_filename,
    to_utc_datetime,
    utc_now,
    utc_now_iso,
)
from app.services.production_workspace_service_workflow_cycle import (
    ProductionWorkspaceWorkflowCycleMixin,
)


# 兼容旧代码路径（保留原命名）
def _utc_now() -> datetime:
    return utc_now()


def _utc_now_iso() -> str:
    return utc_now_iso()


def _to_utc_datetime(raw: Any) -> datetime | None:
    return to_utc_datetime(raw)


def _is_truthy_env(name: str, default: str = "0") -> bool:
    return is_truthy_env(name=name, default=default)


def _is_table_missing_error(error: Exception, table_name: str) -> bool:
    return is_table_missing_error(error=error, table_name=table_name)


def _is_missing_column_error(error: Exception, column_name: str) -> bool:
    return is_missing_column_error(error=error, column_name=column_name)


def _safe_filename(filename: str) -> str:
    return safe_filename(filename)


class ProductionWorkspaceWorkflowMixin(
    ProductionWorkspaceWorkflowCycleMixin,
    ProductionWorkspaceWorkflowAuthorMixin,
):
    """Production workflow 组合 Mixin（cycle + author）。"""

