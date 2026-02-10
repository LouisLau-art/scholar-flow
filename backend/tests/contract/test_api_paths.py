import pytest
from main import app

# === API 路径一致性测试 ===

EXPECTED_ROUTES = {
    ("GET", "/api/v1/manuscripts"),
    ("POST", "/api/v1/manuscripts"),
    ("POST", "/api/v1/manuscripts/upload"),
    ("POST", "/api/v1/manuscripts/{manuscript_id}/quality-check"),
    ("GET", "/api/v1/manuscripts/search"),
    ("GET", "/api/v1/manuscripts/mine"),  # Added missing route
    ("GET", "/api/v1/manuscripts/articles/{id}"),
    ("GET", "/api/v1/manuscripts/journals/{slug}"),
    ("GET", "/api/v1/editor/pipeline"),
    ("GET", "/api/v1/editor/available-reviewers"),
    ("GET", "/api/v1/editor/intake"),
    ("GET", "/api/v1/editor/workspace"),
    ("GET", "/api/v1/editor/academic"),
    ("GET", "/api/v1/editor/finance/invoices"),
    ("GET", "/api/v1/editor/finance/invoices/export"),
    ("GET", "/api/v1/editor/rbac/context"),
    ("GET", "/api/v1/editor/assistant-editors"),
    ("POST", "/api/v1/editor/manuscripts/{id}/assign-ae"),
    ("POST", "/api/v1/editor/manuscripts/{id}/intake-return"),
    ("POST", "/api/v1/editor/manuscripts/{id}/submit-check"),
    ("POST", "/api/v1/editor/manuscripts/{id}/academic-check"),
    ("GET", "/api/v1/editor/manuscripts/{id}/tasks"),
    ("POST", "/api/v1/editor/manuscripts/{id}/tasks"),
    ("PATCH", "/api/v1/editor/manuscripts/{id}/tasks/{task_id}"),
    ("GET", "/api/v1/editor/manuscripts/{id}/tasks/{task_id}/activity"),
    ("POST", "/api/v1/editor/decision"),
    ("GET", "/api/v1/user/profile"),
    ("PUT", "/api/v1/user/profile"),
    ("GET", "/api/v1/user/notifications"),
    ("GET", "/api/v1/notifications"),
    ("PATCH", "/api/v1/notifications/{id}/read"),
    ("POST", "/api/v1/matchmaking/analyze"),
    ("GET", "/api/v1/cms/pages"),
    ("POST", "/api/v1/cms/pages"),
    ("PATCH", "/api/v1/cms/pages/{slug}"),
    ("GET", "/api/v1/cms/pages/{slug}"),
    ("POST", "/api/v1/cms/upload"),
    ("GET", "/api/v1/cms/menu"),
    ("PUT", "/api/v1/cms/menu"),
    ("POST", "/api/v1/internal/cron/chase-reviews"),
    ("POST", "/api/v1/internal/release-validation/runs"),
    ("GET", "/api/v1/internal/release-validation/runs"),
    ("POST", "/api/v1/internal/release-validation/runs/{run_id}/readiness"),
    ("POST", "/api/v1/internal/release-validation/runs/{run_id}/regression"),
    ("POST", "/api/v1/internal/release-validation/runs/{run_id}/finalize"),
    ("GET", "/api/v1/internal/release-validation/runs/{run_id}/report"),
    ("GET", "/api/v1/plagiarism/report/{report_id}/download"),
    ("POST", "/api/v1/plagiarism/retry"),
    ("POST", "/api/v1/reviews/assign"),
    ("GET", "/api/v1/reviews/my-tasks"),
    ("POST", "/api/v1/reviews/submit"),
    ("GET", "/api/v1/stats/author"),
    ("GET", "/api/v1/stats/editor"),
    ("GET", "/api/v1/stats/system"),
    ("POST", "/api/v1/stats/download/{article_id}"),
    ("GET", "/api/v1/public/topics"),
    ("GET", "/api/v1/public/announcements"),
    ("GET", "/"),
    # Admin User Management (017)
    ("GET", "/api/v1/admin/users"),
    ("POST", "/api/v1/admin/users"),
    ("PUT", "/api/v1/admin/users/{user_id}/role"),
    ("GET", "/api/v1/admin/users/{user_id}/role-changes"),
    ("POST", "/api/v1/admin/users/invite-reviewer"),
    ("GET", "/api/v1/admin/journal-scopes"),
    ("POST", "/api/v1/admin/journal-scopes"),
    ("DELETE", "/api/v1/admin/journal-scopes/{scope_id}"),
}

@pytest.mark.asyncio
async def test_api_paths_match_expected():
    """验证关键 API 路径与方法存在且无尾随斜杠偏差"""
    actual_routes = set()
    for route in app.routes:
        methods = getattr(route, "methods", None)
        if not methods or not hasattr(route, "path"):
            continue
        for method in methods:
            if method in {"HEAD", "OPTIONS"}:
                continue
            actual_routes.add((method, route.path))
    
    # 允许 EXPECTED_ROUTES 是 actual_routes 的子集 (即允许有未测试的新路由)
    # 但反过来，所有 Expected 的必须存在
    missing = EXPECTED_ROUTES - actual_routes
    assert not missing, f"Missing routes: {sorted(missing)}"
