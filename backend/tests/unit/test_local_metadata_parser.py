import pytest

from app.core.ai_engine import parse_manuscript_metadata


@pytest.mark.asyncio
async def test_parse_manuscript_metadata_extracts_basic_fields():
    text = """
    A Fast Local Metadata Extractor for Scholarly PDFs
    Alice Zhang, Bob Li, Carol Wang

    Abstract: This paper proposes a fast local heuristic parser for extracting title, authors, and abstract.
    Keywords: metadata, pdf, parsing
    """

    result = await parse_manuscript_metadata(text)
    assert result["title"] == "A Fast Local Metadata Extractor for Scholarly PDFs"
    assert "fast local heuristic parser" in (result["abstract"] or "").lower()
    assert "Alice Zhang" in result["authors"]


@pytest.mark.asyncio
async def test_parse_manuscript_metadata_handles_heading_abstract():
    text = """
    Another Paper Title
    John Doe and Jane Roe

    Abstract
    We present a simple approach.
    It is fast.
    Introduction
    1. Background
    """
    result = await parse_manuscript_metadata(text)
    assert result["title"] == "Another Paper Title"
    assert result["abstract"].lower().startswith("we present a simple approach")
    assert result["authors"] == ["John Doe", "Jane Roe"]


@pytest.mark.asyncio
async def test_parse_manuscript_metadata_prefers_layout_title_when_available():
    layout_lines = [
        {"page": 0, "top": 40.0, "size": 10.0, "page_height": 800.0, "text": "Some Journal Header"},
        {"page": 0, "top": 120.0, "size": 22.0, "page_height": 800.0, "text": "A Large Font Paper Title"},
        {"page": 0, "top": 150.0, "size": 22.0, "page_height": 800.0, "text": "With a Subtitle"},
        {"page": 0, "top": 190.0, "size": 12.0, "page_height": 800.0, "text": "Alice Zhang, Bob Li"},
    ]
    result = await parse_manuscript_metadata("", layout_lines=layout_lines)
    assert result["title"] == "A Large Font Paper Title With a Subtitle"
    assert "Alice Zhang" in result["authors"]
