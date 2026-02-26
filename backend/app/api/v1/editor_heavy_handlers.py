from __future__ import annotations

"""
Editor 重型处理器聚合导出。

中文注释:
- 该模块保留原导入路径，避免影响现有路由与 monkeypatch 测试；
- 具体实现已按职责拆分到子模块（pipeline/reviewer/revision/decision/publish）。
"""

from app.api.v1.editor_heavy_decision import submit_final_decision_impl
from app.api.v1.editor_heavy_pipeline import get_editor_pipeline_impl
from app.api.v1.editor_heavy_publish import publish_manuscript_dev_impl
from app.api.v1.editor_heavy_reviewer import (
    get_available_reviewers_impl,
    search_reviewer_library_impl,
)
from app.api.v1.editor_heavy_revision import request_revision_impl

__all__ = [
    "get_editor_pipeline_impl",
    "request_revision_impl",
    "get_available_reviewers_impl",
    "search_reviewer_library_impl",
    "submit_final_decision_impl",
    "publish_manuscript_dev_impl",
]

