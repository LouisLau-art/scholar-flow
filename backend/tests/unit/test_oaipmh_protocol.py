"""
Tests for OAI-PMH Protocol implementation
Coverage target: 80%+
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from lxml import etree

from app.services.oaipmh.protocol import OAIPMHProtocol
from app.models.oaipmh import OAIPMHRequest, OAIPMHVerb, OAIMetadataPrefix


class MockSupabaseResponse:
    """Mock Supabase response"""

    def __init__(self, data=None):
        self.data = data


class MockQueryBuilder:
    """Mock Supabase query builder chain"""

    def __init__(self, return_data=None, raise_error=None):
        self._data = return_data
        self._raise_error = raise_error

    def select(self, *args, **kwargs):
        return self

    def eq(self, *args):
        return self

    def gte(self, *args):
        return self

    def lte(self, *args):
        return self

    def single(self):
        return self

    def limit(self, n):
        return self

    def execute(self):
        if self._raise_error:
            raise self._raise_error
        return MockSupabaseResponse(data=self._data)


@pytest.fixture
def protocol():
    """Create protocol instance"""
    return OAIPMHProtocol(base_url="http://test.example.com/oai")


class TestOAIPMHProtocolInit:
    """Test protocol initialization"""

    def test_init_sets_properties(self):
        """Test initialization sets correct properties"""
        proto = OAIPMHProtocol(base_url="http://example.com/oai")

        assert proto.base_url == "http://example.com/oai"
        assert proto.repository_name == "Scholar Flow"
        assert proto.admin_email == "admin@example.com"
        assert proto.dc_mapper is not None


class TestIdentify:
    """Test Identify verb"""

    @pytest.mark.asyncio
    async def test_identify_returns_repository_info(self, protocol):
        """Test Identify returns correct repository information"""
        request = OAIPMHRequest(verb=OAIPMHVerb.IDENTIFY)

        result = await protocol.handle_request(request)

        assert "Scholar Flow" in result
        assert "http://test.example.com/oai" in result
        assert "2.0" in result  # Protocol version
        assert "admin@example.com" in result


class TestListMetadataFormats:
    """Test ListMetadataFormats verb"""

    @pytest.mark.asyncio
    async def test_list_metadata_formats(self, protocol):
        """Test ListMetadataFormats returns oai_dc"""
        request = OAIPMHRequest(verb=OAIPMHVerb.LIST_METADATA_FORMATS)

        result = await protocol.handle_request(request)

        assert "oai_dc" in result
        assert "oai_dc.xsd" in result


class TestListSets:
    """Test ListSets verb"""

    @pytest.mark.asyncio
    async def test_list_sets_returns_no_hierarchy_error(self, protocol):
        """Test ListSets returns noSetHierarchy error"""
        request = OAIPMHRequest(verb=OAIPMHVerb.LIST_SETS)

        result = await protocol.handle_request(request)

        assert "noSetHierarchy" in result


class TestGetRecord:
    """Test GetRecord verb"""

    @pytest.mark.asyncio
    async def test_get_record_missing_identifier(self, protocol):
        """Test GetRecord with missing identifier"""
        request = OAIPMHRequest(verb=OAIPMHVerb.GET_RECORD, metadataPrefix="oai_dc")

        result = await protocol.handle_request(request)

        assert "badArgument" in result
        assert "Missing identifier" in result

    @pytest.mark.asyncio
    async def test_get_record_missing_prefix(self, protocol):
        """Test GetRecord with missing metadataPrefix"""
        request = OAIPMHRequest(
            verb=OAIPMHVerb.GET_RECORD, identifier="oai:scholarflow:article:123"
        )

        result = await protocol.handle_request(request)

        assert "badArgument" in result

    @pytest.mark.asyncio
    async def test_get_record_invalid_prefix(self, protocol):
        """Test GetRecord with unsupported metadataPrefix"""
        request = OAIPMHRequest(
            verb=OAIPMHVerb.GET_RECORD,
            identifier="oai:scholarflow:article:123",
            metadataPrefix="marc21",  # Not supported
        )

        result = await protocol.handle_request(request)

        assert "cannotDisseminateFormat" in result

    @pytest.mark.asyncio
    async def test_get_record_not_found(self, protocol):
        """Test GetRecord when record not found"""
        request = OAIPMHRequest(
            verb=OAIPMHVerb.GET_RECORD,
            identifier="oai:scholarflow:article:nonexistent-id",
            metadataPrefix="oai_dc",
        )

        with patch("app.services.oaipmh.protocol.supabase") as mock_supabase:
            mock_query = MockQueryBuilder(return_data=None)
            mock_supabase.table.return_value = mock_query

            result = await protocol.handle_request(request)

        assert "idDoesNotExist" in result

    @pytest.mark.asyncio
    async def test_get_record_success(self, protocol):
        """Test GetRecord success"""
        article_data = {
            "id": "article-123",
            "title": "Test Article",
            "abstract": "Test abstract",
            "status": "published",
            "updated_at": "2024-01-15T10:00:00Z",
            "created_at": "2024-01-01T10:00:00Z",
        }

        request = OAIPMHRequest(
            verb=OAIPMHVerb.GET_RECORD,
            identifier="oai:scholarflow:article:article-123",
            metadataPrefix="oai_dc",
        )

        with patch("app.services.oaipmh.protocol.supabase") as mock_supabase:
            mock_query = MockQueryBuilder(return_data=article_data)
            mock_supabase.table.return_value = mock_query

            result = await protocol.handle_request(request)

        assert "GetRecord" in result
        assert "oai:scholarflow:article:article-123" in result


class TestListIdentifiers:
    """Test ListIdentifiers verb"""

    @pytest.mark.asyncio
    async def test_list_identifiers_missing_prefix(self, protocol):
        """Test ListIdentifiers with missing metadataPrefix"""
        request = OAIPMHRequest(verb=OAIPMHVerb.LIST_IDENTIFIERS)

        result = await protocol.handle_request(request)

        assert "badArgument" in result

    @pytest.mark.asyncio
    async def test_list_identifiers_invalid_prefix(self, protocol):
        """Test ListIdentifiers with unsupported prefix"""
        request = OAIPMHRequest(
            verb=OAIPMHVerb.LIST_IDENTIFIERS, metadataPrefix="marc21"
        )

        result = await protocol.handle_request(request)

        assert "cannotDisseminateFormat" in result

    @pytest.mark.asyncio
    async def test_list_identifiers_no_records(self, protocol):
        """Test ListIdentifiers with no matching records"""
        request = OAIPMHRequest(
            verb=OAIPMHVerb.LIST_IDENTIFIERS, metadataPrefix="oai_dc"
        )

        with patch("app.services.oaipmh.protocol.supabase") as mock_supabase:
            mock_query = MockQueryBuilder(return_data=[])
            mock_supabase.table.return_value = mock_query

            result = await protocol.handle_request(request)

        assert "noRecordsMatch" in result

    @pytest.mark.asyncio
    async def test_list_identifiers_success(self, protocol):
        """Test ListIdentifiers success"""
        articles = [
            {
                "id": "article-1",
                "updated_at": "2024-01-15T10:00:00Z",
                "status": "published",
            },
            {
                "id": "article-2",
                "updated_at": "2024-01-14T10:00:00Z",
                "status": "published",
            },
        ]

        request = OAIPMHRequest(
            verb=OAIPMHVerb.LIST_IDENTIFIERS, metadataPrefix="oai_dc"
        )

        with patch("app.services.oaipmh.protocol.supabase") as mock_supabase:
            mock_query = MockQueryBuilder(return_data=articles)
            mock_supabase.table.return_value = mock_query

            result = await protocol.handle_request(request)

        assert "ListIdentifiers" in result
        assert "oai:scholarflow:article:article-1" in result
        assert "oai:scholarflow:article:article-2" in result

    @pytest.mark.asyncio
    async def test_list_identifiers_with_date_filters(self, protocol):
        """Test ListIdentifiers with from/until filters"""
        articles = [
            {
                "id": "article-1",
                "updated_at": "2024-01-15T10:00:00Z",
                "status": "published",
            },
        ]

        request = OAIPMHRequest(
            verb=OAIPMHVerb.LIST_IDENTIFIERS,
            metadataPrefix="oai_dc",
            from_="2024-01-01",
            until="2024-01-31",
        )

        with patch("app.services.oaipmh.protocol.supabase") as mock_supabase:
            mock_query = MockQueryBuilder(return_data=articles)
            mock_supabase.table.return_value = mock_query

            result = await protocol.handle_request(request)

        assert "ListIdentifiers" in result


class TestListRecords:
    """Test ListRecords verb"""

    @pytest.mark.asyncio
    async def test_list_records_missing_prefix(self, protocol):
        """Test ListRecords with missing metadataPrefix"""
        request = OAIPMHRequest(verb=OAIPMHVerb.LIST_RECORDS)

        result = await protocol.handle_request(request)

        assert "badArgument" in result

    @pytest.mark.asyncio
    async def test_list_records_invalid_prefix(self, protocol):
        """Test ListRecords with unsupported prefix"""
        request = OAIPMHRequest(verb=OAIPMHVerb.LIST_RECORDS, metadataPrefix="marc21")

        result = await protocol.handle_request(request)

        assert "cannotDisseminateFormat" in result

    @pytest.mark.asyncio
    async def test_list_records_no_records(self, protocol):
        """Test ListRecords with no matching records"""
        request = OAIPMHRequest(verb=OAIPMHVerb.LIST_RECORDS, metadataPrefix="oai_dc")

        with patch("app.services.oaipmh.protocol.supabase") as mock_supabase:
            mock_query = MockQueryBuilder(return_data=[])
            mock_supabase.table.return_value = mock_query

            result = await protocol.handle_request(request)

        assert "noRecordsMatch" in result

    @pytest.mark.asyncio
    async def test_list_records_success(self, protocol):
        """Test ListRecords success"""
        articles = [
            {
                "id": "article-1",
                "title": "First Article",
                "abstract": "Abstract 1",
                "updated_at": "2024-01-15T10:00:00Z",
                "status": "published",
            },
        ]

        request = OAIPMHRequest(verb=OAIPMHVerb.LIST_RECORDS, metadataPrefix="oai_dc")

        with patch("app.services.oaipmh.protocol.supabase") as mock_supabase:
            mock_query = MockQueryBuilder(return_data=articles)
            mock_supabase.table.return_value = mock_query

            result = await protocol.handle_request(request)

        assert "ListRecords" in result


class TestBadVerb:
    """Test bad verb handling"""

    @pytest.mark.asyncio
    async def test_bad_verb_via_pydantic_validation(self):
        """Test that invalid verb is rejected by Pydantic validation"""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            OAIPMHRequest(verb="InvalidVerb")


class TestErrorMethod:
    """Test error helper method"""

    def test_error_creates_error_element(self, protocol):
        """Test error method creates proper error element"""
        root = etree.Element("OAI-PMH")

        protocol.error(root, "badArgument", "Missing required parameter")

        error_elem = root.find("error")
        assert error_elem is not None
        assert error_elem.get("code") == "badArgument"
        assert error_elem.text == "Missing required parameter"


class TestAppendHeader:
    """Test _append_header helper method"""

    def test_append_header_with_updated_at(self, protocol):
        """Test _append_header with updated_at date"""
        parent = etree.Element("ListIdentifiers")
        article = {"id": "article-123", "updated_at": "2024-01-15T10:00:00Z"}

        protocol._append_header(parent, article)

        header = parent.find("header")
        assert header is not None

        identifier = header.find("identifier")
        assert identifier is not None
        assert identifier.text == "oai:scholarflow:article:article-123"

        datestamp = header.find("datestamp")
        assert datestamp is not None
        assert datestamp.text == "2024-01-15"

    def test_append_header_with_created_at_fallback(self, protocol):
        """Test _append_header falls back to created_at"""
        parent = etree.Element("ListIdentifiers")
        article = {"id": "article-123", "created_at": "2024-01-01T10:00:00Z"}

        protocol._append_header(parent, article)

        header = parent.find("header")
        datestamp = header.find("datestamp")
        assert datestamp.text == "2024-01-01"

    def test_append_header_no_date(self, protocol):
        """Test _append_header without any date"""
        parent = etree.Element("ListIdentifiers")
        article = {"id": "article-123"}

        protocol._append_header(parent, article)

        header = parent.find("header")
        datestamp = header.find("datestamp")
        # Should not crash, datestamp might be None or empty
        assert header is not None


class TestExceptionHandling:
    """Test exception handling in handle_request"""

    @pytest.mark.asyncio
    async def test_exception_in_identify_handled(self, protocol):
        """Test that exceptions are caught and returned as errors"""
        request = OAIPMHRequest(verb=OAIPMHVerb.IDENTIFY)

        # Force an exception
        with patch.object(protocol, "identify", side_effect=RuntimeError("Test error")):
            result = await protocol.handle_request(request)

        assert "error" in result.lower() or "badArgument" in result
