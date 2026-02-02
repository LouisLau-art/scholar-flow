import pytest
from app.services.crossref_client import CrossrefClient
from app.core.config import CrossrefConfig
from lxml import etree


@pytest.fixture
def crossref_config():
    return CrossrefConfig(
        depositor_email="test@example.com",
        depositor_password="password",
        doi_prefix="10.12345",
        api_url="https://test.crossref.org",
        journal_title="Test Journal",
        journal_issn="1234-5678",
    )


@pytest.fixture
def crossref_client(crossref_config):
    return CrossrefClient(config=crossref_config)


def test_generate_xml_structure(crossref_client):
    article_data = {
        "title": "Test Article",
        "authors": [
            {"first_name": "John", "last_name": "Doe", "affiliation": "Test Univ"},
            {"first_name": "Jane", "last_name": "Smith"},
        ],
        "publication_date": "2024-01-01",
        "doi": "10.12345/sf.2024.00001",
        "url": "https://scholarflow.com/articles/123",
    }
    batch_id = "batch_20240101_001"

    xml_bytes = crossref_client.generate_xml(article_data, batch_id)
    assert xml_bytes is not None

    root = etree.fromstring(xml_bytes)
    ns = crossref_client.ns

    # Verify basic structure
    assert root.tag == f"{{{ns['default']}}}doi_batch"
    assert root.find(".//{*}head/{*}doi_batch_id").text == batch_id
    assert root.find(".//{*}journal_metadata/{*}full_title").text == "Test Journal"
    assert root.find(".//{*}journal_article/{*}titles/{*}title").text == "Test Article"

    # Verify DOI data
    doi_data = root.find(".//{*}journal_article/{*}doi_data")
    assert doi_data.find("{*}doi").text == "10.12345/sf.2024.00001"
    assert doi_data.find("{*}resource").text == "https://scholarflow.com/articles/123"


def test_generate_xml_splits_full_name_and_ignores_bad_pub_date(crossref_client):
    article_data = {
        "title": "Test Article",
        "authors": [{"full_name": "Ada Lovelace"}],
        "publication_date": 123,  # triggers exception path
        "doi": "10.12345/sf.2024.00001",
        "url": "https://scholarflow.com/articles/123",
    }
    xml_bytes = crossref_client.generate_xml(article_data, "batch")
    root = etree.fromstring(xml_bytes)

    assert root.find(".//{*}contributors/{*}person_name/{*}given_name").text == "Ada"
    assert root.find(".//{*}contributors/{*}person_name/{*}surname").text == "Lovelace"


@pytest.mark.asyncio
async def test_submit_deposit_requires_config():
    client = CrossrefClient(config=None)
    with pytest.raises(ValueError):
        await client.submit_deposit(b"<xml/>")


@pytest.mark.asyncio
async def test_submit_deposit_posts_to_httpx(monkeypatch, crossref_config):
    client = CrossrefClient(config=crossref_config)

    class _Resp:
        def __init__(self):
            self.text = "OK"

        def raise_for_status(self):
            return None

    class _HTTP:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def post(self, url, data=None, files=None, timeout=None):
            assert url == crossref_config.api_url
            assert data["login_id"] == crossref_config.depositor_email
            assert "fname" in files
            return _Resp()

    monkeypatch.setattr("app.services.crossref_client.httpx.AsyncClient", lambda: _HTTP())
    assert await client.submit_deposit(b"<xml/>", file_name="x.xml") == "OK"
