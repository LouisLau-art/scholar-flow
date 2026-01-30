import logging
from types import SimpleNamespace
from uuid import UUID

import pytest
from fastapi import HTTPException

from app.core import ai_engine, pdf_processor, plagiarism_worker, recommender
from app.services import editorial_service, publishing_service


@pytest.mark.asyncio
async def test_parse_manuscript_metadata_missing_env(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)

    result = await ai_engine.parse_manuscript_metadata("content")

    assert result == {"title": "", "abstract": "", "authors": []}


@pytest.mark.asyncio
async def test_parse_manuscript_metadata_parses_json(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://example.com")

    class DummyClient:
        def __init__(self, *args, **kwargs):
            content = '```json {"title":"T","abstract":"A","authors":["X"]} ```'

            self.chat = SimpleNamespace(
                completions=SimpleNamespace(
                    create=lambda *a, **k: SimpleNamespace(
                        choices=[SimpleNamespace(message=SimpleNamespace(content=content))]
                    )
                )
            )

    monkeypatch.setattr(ai_engine, "OpenAI", DummyClient)

    result = await ai_engine.parse_manuscript_metadata("content")

    assert result["title"] == "T"
    assert result["abstract"] == "A"
    assert result["authors"] == ["X"]


@pytest.mark.asyncio
async def test_parse_manuscript_metadata_handles_error(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://example.com")

    class DummyClient:
        def __init__(self, *args, **kwargs):
            raise RuntimeError("boom")

    monkeypatch.setattr(ai_engine, "OpenAI", DummyClient)

    result = await ai_engine.parse_manuscript_metadata("content")

    assert result == {"title": "", "abstract": "", "authors": []}


def test_extract_text_from_pdf_success(monkeypatch):
    class DummyPage:
        def __init__(self, text):
            self._text = text

        def extract_text(self):
            return self._text

    class DummyPDF:
        pages = [DummyPage("A"), DummyPage("B")]

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(pdf_processor.pdfplumber, "open", lambda *_: DummyPDF())

    result = pdf_processor.extract_text_from_pdf("file.pdf")

    assert result == "A\nB"


def test_extract_text_from_pdf_error(monkeypatch):
    def raise_error(*_):
        raise RuntimeError("boom")

    monkeypatch.setattr(pdf_processor.pdfplumber, "open", raise_error)

    result = pdf_processor.extract_text_from_pdf("file.pdf")

    assert result is None


def test_recommend_reviewers_empty_inputs():
    assert recommender.recommend_reviewers("", []) == []


def test_recommend_reviewers_returns_sorted_scores():
    reviewers = [
        {"id": "1", "email": "a@example.com", "domains": ["ai"]},
        {"id": "2", "email": "b@example.com", "domains": ["biology"]},
    ]

    results = recommender.recommend_reviewers("ai systems", reviewers)

    assert results[0]["reviewer_id"] == "1"
    assert results[0]["score"] >= results[1]["score"]


@pytest.mark.asyncio
async def test_publish_manuscript_requires_finance():
    with pytest.raises(HTTPException) as exc:
        await publishing_service.publish_manuscript(UUID(int=1), False, True)

    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_publish_manuscript_requires_eic_approval():
    with pytest.raises(HTTPException) as exc:
        await publishing_service.publish_manuscript(UUID(int=1), True, False)

    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_publish_manuscript_success():
    result = await publishing_service.publish_manuscript(UUID(int=1), True, True)

    assert result["status"] == "published"
    assert result["id"] == UUID(int=1)


@pytest.mark.asyncio
async def test_process_quality_check_passed():
    manuscript_id = UUID(int=2)
    kpi_owner_id = UUID(int=3)

    result = await editorial_service.process_quality_check(manuscript_id, True, kpi_owner_id)

    assert result["status"] == "under_review"
    assert result["kpi_owner_id"] == kpi_owner_id


@pytest.mark.asyncio
async def test_process_quality_check_failed_with_notes():
    manuscript_id = UUID(int=4)
    kpi_owner_id = UUID(int=5)

    result = await editorial_service.process_quality_check(
        manuscript_id, False, kpi_owner_id, revision_notes="Need fixes"
    )

    assert result["status"] == "returned_for_revision"


@pytest.mark.asyncio
async def test_handle_plagiarism_result_threshold():
    manuscript_id = UUID(int=6)

    result = await editorial_service.handle_plagiarism_result(manuscript_id, 0.35)

    assert result == "high_similarity"


@pytest.mark.asyncio
async def test_handle_plagiarism_result_safe():
    manuscript_id = UUID(int=7)

    result = await editorial_service.handle_plagiarism_result(manuscript_id, 0.1)

    assert result == "submitted"


@pytest.mark.asyncio
async def test_plagiarism_worker_success(monkeypatch, caplog):
    async def fast_sleep(*_args, **_kwargs):
        return None

    class DummyClient:
        async def submit_manuscript(self, _path):
            return "ext-id"

        async def get_check_status(self, _external_id):
            return {"status": "completed", "similarity_score": 0.2}

    monkeypatch.setattr(plagiarism_worker, "CrossrefClient", DummyClient)
    monkeypatch.setattr(plagiarism_worker.asyncio, "sleep", fast_sleep)

    with caplog.at_level(logging.INFO, logger="plagiarism_worker"):
        await plagiarism_worker.plagiarism_check_worker(UUID(int=8))

    assert "查重完成" in caplog.text


@pytest.mark.asyncio
async def test_plagiarism_worker_submit_failure(monkeypatch, caplog):
    async def fast_sleep(*_args, **_kwargs):
        return None

    class DummyClient:
        async def submit_manuscript(self, _path):
            return None

        async def get_check_status(self, _external_id):
            return {"status": "completed", "similarity_score": 0.2}

    monkeypatch.setattr(plagiarism_worker, "CrossrefClient", DummyClient)
    monkeypatch.setattr(plagiarism_worker.asyncio, "sleep", fast_sleep)

    with caplog.at_level(logging.ERROR, logger="plagiarism_worker"):
        await plagiarism_worker.plagiarism_check_worker(UUID(int=9))

    assert "查重 Worker 异常" in caplog.text


@pytest.mark.asyncio
async def test_plagiarism_worker_timeout(monkeypatch, caplog):
    async def fast_sleep(*_args, **_kwargs):
        return None

    class DummyClient:
        async def submit_manuscript(self, _path):
            return "ext-id"

        async def get_check_status(self, _external_id):
            return {"status": "running", "similarity_score": 0.2}

    monkeypatch.setattr(plagiarism_worker, "CrossrefClient", DummyClient)
    monkeypatch.setattr(plagiarism_worker.asyncio, "sleep", fast_sleep)

    with caplog.at_level(logging.ERROR, logger="plagiarism_worker"):
        await plagiarism_worker.plagiarism_check_worker(UUID(int=10))

    assert "查重 Worker 异常" in caplog.text
