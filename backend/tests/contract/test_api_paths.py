import pytest
from main import app

# === API 路径一致性测试 ===

EXPECTED_ROUTES = {
    ("GET", "/api/v1/manuscripts"),
    ("POST", "/api/v1/manuscripts"),
    ("POST", "/api/v1/manuscripts/upload"),
    ("POST", "/api/v1/manuscripts/{manuscript_id}/quality-check"),
    ("GET", "/api/v1/manuscripts/search"),
    ("GET", "/api/v1/manuscripts/articles/{id}"),
    ("GET", "/api/v1/manuscripts/journals/{slug}"),
    ("GET", "/api/v1/editor/pipeline"),
    ("GET", "/api/v1/editor/available-reviewers"),
    ("POST", "/api/v1/editor/decision"),
    ("GET", "/api/v1/user/profile"),
    ("PUT", "/api/v1/user/profile"),
    ("GET", "/api/v1/user/notifications"),
    ("GET", "/api/v1/notifications"),
    ("PATCH", "/api/v1/notifications/{id}/read"),
    ("POST", "/api/v1/internal/cron/chase-reviews"),
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

    missing = EXPECTED_ROUTES - actual_routes
    assert not missing, f"Missing routes: {sorted(missing)}"
