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

