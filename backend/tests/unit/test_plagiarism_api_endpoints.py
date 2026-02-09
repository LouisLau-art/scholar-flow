from uuid import UUID

import pytest
from fastapi import BackgroundTasks, HTTPException

from app.api.v1 import plagiarism as plagiarism_api
from app.models.plagiarism import PlagiarismRetryRequest


@pytest.mark.asyncio
async def test_get_plagiarism_status_not_started(monkeypatch):
    class _Svc:
        def get_report_by_manuscript(self, _mid: str):
            return None

    monkeypatch.setattr(plagiarism_api, "PlagiarismService", _Svc)

    result = await plagiarism_api.get_plagiarism_status(UUID(int=1))
    assert result["success"] is True
    assert result["data"]["status"] == "not_started"


@pytest.mark.asyncio
async def test_get_report_download_url_not_found(monkeypatch):
    class _Svc:
        def get_report_by_id(self, _rid: str):
            return None

    monkeypatch.setattr(plagiarism_api, "PlagiarismService", _Svc)

    with pytest.raises(HTTPException) as exc:
        await plagiarism_api.get_report_download_url(UUID(int=1))
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_retry_plagiarism_check_idempotent_when_running(monkeypatch):
    class _Svc:
        def get_report_by_manuscript(self, _mid: str):
            return {"manuscript_id": _mid, "status": "running"}

        def ensure_report(self, manuscript_id: str, *, reset_status: bool = False):
            return {"manuscript_id": manuscript_id, "status": "pending", "reset": reset_status}

    monkeypatch.setattr(plagiarism_api, "PlagiarismService", _Svc)
    monkeypatch.setenv("PLAGIARISM_CHECK_ENABLED", "1")

    tasks = BackgroundTasks()
    result = await plagiarism_api.retry_plagiarism_check(
        PlagiarismRetryRequest(manuscript_id=UUID(int=2)),
        tasks,
    )

    assert result["success"] is True
    assert "队列" in result["message"]
    assert len(tasks.tasks) == 0
