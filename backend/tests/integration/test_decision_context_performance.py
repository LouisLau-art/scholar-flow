from __future__ import annotations

from time import perf_counter

import pytest

import app.api.v1.editor as editor_api
from .test_utils import make_user


@pytest.mark.integration
@pytest.mark.asyncio
async def test_decision_context_api_p95_under_500ms_with_stubbed_service(
    client,
    set_admin_emails,
    monkeypatch: pytest.MonkeyPatch,
):
    """
    Feature 041 NFR:
    在稳定输入下，决策上下文 API 的接口开销应满足 P95 < 500ms。
    """

    editor = make_user(email="decision_perf_editor@example.com")
    set_admin_emails([editor.email])

    def _stub_get_decision_context(self, *, manuscript_id: str, user_id: str, profile_roles: list[str] | None):
        return {
            "manuscript": {"id": manuscript_id, "title": "Perf Stub", "status": "decision", "pdf_url": None},
            "reports": [
                {
                    "id": "r-1",
                    "reviewer_name": "Reviewer",
                    "status": "completed",
                    "comments_for_author": "Looks good.",
                }
            ],
            "draft": None,
            "templates": [{"id": "default", "name": "Default", "content": "Template"}],
            "permissions": {"can_submit": True, "is_read_only": False},
        }

    monkeypatch.setattr(editor_api.DecisionService, "get_decision_context", _stub_get_decision_context)

    # 预热一次，避开首次 profile upsert 的冷启动开销
    warmup = await client.get(
        "/api/v1/editor/manuscripts/perf-ms-id/decision-context",
        headers={"Authorization": f"Bearer {editor.token}"},
    )
    assert warmup.status_code == 200, warmup.text

    timings: list[float] = []
    for _ in range(30):
        start = perf_counter()
        res = await client.get(
            "/api/v1/editor/manuscripts/perf-ms-id/decision-context",
            headers={"Authorization": f"Bearer {editor.token}"},
        )
        elapsed = perf_counter() - start
        assert res.status_code == 200, res.text
        timings.append(elapsed)

    ordered = sorted(timings)
    idx = max(0, int(len(ordered) * 0.95) - 1)
    p95 = ordered[idx]
    assert p95 < 0.5, f"Expected p95 < 0.5s, got {p95:.4f}s"
