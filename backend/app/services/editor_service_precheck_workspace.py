from __future__ import annotations

from app.services.editor_service_precheck_workspace_decisions import (
    EditorServicePrecheckWorkspaceDecisionMixin,
)
from app.services.editor_service_precheck_workspace_views import (
    EditorServicePrecheckWorkspaceViewMixin,
)


class EditorServicePrecheckWorkspaceMixin(
    EditorServicePrecheckWorkspaceViewMixin,
    EditorServicePrecheckWorkspaceDecisionMixin,
):
    """
    Pre-check workspace 聚合 mixin。

    中文注释:
    - 该入口仅负责组合子模块，保持对外 import 路径不变；
    - 具体实现拆到 views / decisions 子模块，降低单文件复杂度。
    """

