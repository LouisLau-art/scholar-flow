import pytest
from httpx import AsyncClient, ASGITransport
from main import app


@pytest.mark.asyncio
async def test_identify_verb():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.get("/api/oai-pmh?verb=Identify")
        assert response.status_code == 200
        assert "text/xml" in response.headers["content-type"]
        assert "<Identify>" in response.text
        assert "<repositoryName>Scholar Flow</repositoryName>" in response.text


@pytest.mark.asyncio
async def test_list_metadata_formats():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.get("/api/oai-pmh?verb=ListMetadataFormats")
        assert response.status_code == 200
        assert "<metadataPrefix>oai_dc</metadataPrefix>" in response.text


@pytest.mark.asyncio
async def test_bad_verb():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.get("/api/oai-pmh?verb=InvalidVerb")
        # OAI-PMH errors usually return 200 OK with <error> tag, but implementation choice might vary.
        # Standard says HTTP 200 with XML error response.
        assert response.status_code == 200
        assert 'code="badVerb"' in response.text
