import pytest
from httpx import AsyncClient
from unittest.mock import MagicMock, patch


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("ext", "expected_content_type", "must_contain"),
    [
        ("bib", "application/x-bibtex", "@article{"),
        ("ris", "application/x-research-info-systems", "TY  - JOUR"),
    ],
)
async def test_download_article_citation_success(
    client: AsyncClient,
    ext: str,
    expected_content_type: str,
    must_contain: str,
):
    article_id = "00000000-0000-0000-0000-000000000123"
    fake_article = {
        "id": article_id,
        "title": "Transformer-based Scientific Discovery",
        "doi": "10.12345/sf.2026.00123",
        "published_at": "2026-02-01T12:30:00Z",
        "journal_id": "00000000-0000-0000-0000-000000000777",
        "author_id": "00000000-0000-0000-0000-000000000888",
        "authors": ["Alice Johnson", "Bob Lee"],
        "status": "published",
    }
    fake_journal = {
        "id": "00000000-0000-0000-0000-000000000777",
        "title": "Journal of Applied AI",
        "slug": "journal-of-applied-ai",
        "issn": "1234-5678",
    }

    with patch("app.api.v1.manuscripts.supabase_admin") as mock_supabase:
        manuscripts_table = MagicMock()
        (
            manuscripts_table.select.return_value.eq.return_value.eq.return_value.single.return_value.execute.return_value.data
        ) = fake_article

        journals_table = MagicMock()
        (
            journals_table.select.return_value.eq.return_value.single.return_value.execute.return_value.data
        ) = fake_journal

        def table_side_effect(name: str):
            if name == "manuscripts":
                return manuscripts_table
            if name == "journals":
                return journals_table
            return MagicMock()

        mock_supabase.table.side_effect = table_side_effect

        resp = await client.get(f"/api/v1/manuscripts/articles/{article_id}/citation.{ext}")

    assert resp.status_code == 200
    assert expected_content_type in resp.headers.get("content-type", "")
    assert must_contain in resp.text
    assert "ScholarFlow" not in resp.text  # 确保是结构化引用而非固定营销文案
    assert "Content-Disposition" in resp.headers


@pytest.mark.asyncio
async def test_get_all_topics_dynamic_aggregation(client: AsyncClient):
    fake_rows = [
        {"title": "AI for Clinical Imaging", "abstract": "machine learning for patient diagnosis"},
        {"title": "Quantum Materials", "abstract": "physics and photon transport"},
        {"title": "Education Policy Reform", "abstract": "social governance and policy design"},
    ]

    with patch("app.api.v1.public.supabase_admin") as mock_supabase:
        manuscripts_table = MagicMock()
        (
            manuscripts_table.select.return_value.eq.return_value.limit.return_value.execute.return_value.data
        ) = fake_rows
        mock_supabase.table.return_value = manuscripts_table

        resp = await client.get("/api/v1/public/topics")

    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert isinstance(data["data"], list)
    assert any(item["id"] == "technology" and item["count"] >= 1 for item in data["data"])
    assert all("query" in item for item in data["data"])
