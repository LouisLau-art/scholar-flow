from app.services.oaipmh.dublin_core import DublinCoreMapper


def test_dublin_core_mapping():
    mapper = DublinCoreMapper()
    article = {
        "title": "Test Title",
        "authors": [
            {"first_name": "John", "last_name": "Doe"},
            {"first_name": "Jane", "last_name": "Smith"},
        ],
        "abstract": "Test Abstract",
        "published_at": "2024-01-01T12:00:00Z",
        "doi": "10.12345/sf.2024.00001",
        "journal_title": "Test Journal",
        "id": "12345",
    }

    xml = mapper.to_xml(article)

    ns = mapper.ns
    assert xml.tag == f"{{{ns['oai_dc']}}}dc"

    # Check title
    title = xml.find(f"{{{ns['dc']}}}title")
    assert title.text == "Test Title"

    # Check creators
    creators = xml.findall(f"{{{ns['dc']}}}creator")
    assert len(creators) == 2
    assert creators[0].text == "Doe, John"
    assert creators[1].text == "Smith, Jane"

    # Check identifier
    identifiers = xml.findall(f"{{{ns['dc']}}}identifier")
    doi_identifier = next(
        (i for i in identifiers if i.text.startswith("https://doi.org/")), None
    )
    assert doi_identifier.text == "https://doi.org/10.12345/sf.2024.00001"
