import pytest


@pytest.mark.asyncio
async def test_extract_manuscript_metadata_prefers_gemini(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("GEMINI_METADATA_MODEL", "gemini-3.1-flash-lite-preview")

    from app.core.gemini_metadata import extract_manuscript_metadata

    class _Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "candidates": [
                    {
                        "content": {
                            "parts": [
                                {
                                    "text": '{"title":"LLM Parsed Title","abstract":"LLM Parsed Abstract","authors":["Alice","Bob"]}'
                                }
                            ]
                        }
                    }
                ]
            }

    class _HTTP:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, url, headers=None, json=None):
            assert "gemini-3.1-flash-lite-preview:generateContent" in url
            assert headers["x-goog-api-key"] == "test-key"
            assert json["generationConfig"]["responseMimeType"] == "application/json"
            return _Response()

    monkeypatch.setattr("app.core.gemini_metadata.httpx.AsyncClient", _HTTP)

    result = await extract_manuscript_metadata(
        "This paper text is long enough to include title and abstract.",
        parser_mode="docx",
        layout_lines=[],
    )

    assert result == {
        "title": "LLM Parsed Title",
        "abstract": "LLM Parsed Abstract",
        "authors": ["Alice", "Bob"],
        "parser_source": "gemini",
    }


@pytest.mark.asyncio
async def test_extract_manuscript_metadata_falls_back_when_gemini_fails(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    from app.core.gemini_metadata import extract_manuscript_metadata

    async def fake_local_parse(_content: str, *, layout_lines=None):
        return {
            "title": "Local Title",
            "abstract": "Local Abstract",
            "authors": ["Local Author"],
        }

    class _HTTP:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, *args, **kwargs):
            raise RuntimeError("gemini api down")

    monkeypatch.setattr("app.core.gemini_metadata.httpx.AsyncClient", _HTTP)
    monkeypatch.setattr("app.core.gemini_metadata._local_parse", lambda: fake_local_parse)

    result = await extract_manuscript_metadata(
        "Fallback content",
        parser_mode="pdf",
        layout_lines=[],
    )

    assert result == {
        "title": "Local Title",
        "abstract": "Local Abstract",
        "authors": ["Local Author"],
        "parser_source": "local",
    }


@pytest.mark.asyncio
async def test_extract_manuscript_metadata_uses_local_fill_for_missing_fields(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    from app.core.gemini_metadata import extract_manuscript_metadata

    async def fake_local_parse(_content: str, *, layout_lines=None):
        return {
            "title": "Filled Title",
            "abstract": "Filled Abstract",
            "authors": ["Filled Author"],
        }

    class _Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "candidates": [
                    {
                        "content": {
                            "parts": [
                                {
                                    "text": '{"title":"LLM Title","abstract":"","authors":[]}'
                                }
                            ]
                        }
                    }
                ]
            }

    class _HTTP:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, *args, **kwargs):
            return _Response()

    monkeypatch.setattr("app.core.gemini_metadata.httpx.AsyncClient", _HTTP)
    monkeypatch.setattr("app.core.gemini_metadata._local_parse", lambda: fake_local_parse)

    result = await extract_manuscript_metadata(
        "content",
        parser_mode="pdf",
        layout_lines=[],
    )

    assert result == {
        "title": "LLM Title",
        "abstract": "Filled Abstract",
        "authors": ["Filled Author"],
        "parser_source": "gemini+local_fill",
    }
