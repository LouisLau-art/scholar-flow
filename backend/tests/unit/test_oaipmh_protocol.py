import pytest
from app.models.oaipmh import OAIPMHRequest
from app.services.oaipmh.protocol import OAIPMHProtocol


class _FakeSupabaseResponse:
    def __init__(self, data=None):
        self.data = data


class _FakeQuery:
    def __init__(self, data=None, single=False):
        self._data = data
        self._single = single

    def select(self, _cols="*"):
        return self

    def eq(self, _col, _val):
        return self

    def gte(self, _col, _val):
        return self

    def lte(self, _col, _val):
        return self

    def limit(self, _n: int):
        return self

    def single(self):
        self._single = True
        return self

    def execute(self):
        if self._single:
            return _FakeSupabaseResponse(data=self._data)
        return _FakeSupabaseResponse(data=self._data or [])


class _FakeSupabase:
    def __init__(self, list_data=None, single_data=None):
        self._list_data = list_data or []
        self._single_data = single_data

    def table(self, _name: str):
        # 对于不同 query 场景，协议层会继续 select/eq/single/limit 链式调用
        return _FakeQuery(data=self._single_data or self._list_data)


@pytest.mark.asyncio
async def test_oaipmh_list_identifiers_errors(monkeypatch):
    from app.services.oaipmh import protocol as protocol_module

    monkeypatch.setattr(protocol_module, "supabase", _FakeSupabase(list_data=[]))
    proto = OAIPMHProtocol("http://test/api/oai-pmh")

    xml = await proto.handle_request(OAIPMHRequest(verb="ListIdentifiers"))
    assert 'code="badArgument"' in xml

    xml = await proto.handle_request(OAIPMHRequest(verb="ListIdentifiers", metadataPrefix="mods"))
    assert 'code="cannotDisseminateFormat"' in xml


@pytest.mark.asyncio
async def test_oaipmh_list_identifiers_success(monkeypatch):
    from app.services.oaipmh import protocol as protocol_module

    monkeypatch.setattr(
        protocol_module,
        "supabase",
        _FakeSupabase(
            list_data=[
                {"id": "a1", "updated_at": "2026-01-30T00:00:00Z", "status": "published"},
                {"id": "a2", "updated_at": "2026-01-29T00:00:00Z", "status": "published"},
            ]
        ),
    )
    proto = OAIPMHProtocol("http://test/api/oai-pmh")
    xml = await proto.handle_request(OAIPMHRequest(verb="ListIdentifiers", metadataPrefix="oai_dc"))

    assert "<ListIdentifiers>" in xml
    assert "oai:scholarflow:article:a1" in xml
    assert "<datestamp>2026-01-30</datestamp>" in xml


@pytest.mark.asyncio
async def test_oaipmh_get_record_success(monkeypatch):
    from app.services.oaipmh import protocol as protocol_module

    monkeypatch.setattr(
        protocol_module,
        "supabase",
        _FakeSupabase(
            single_data={
                "id": "a1",
                "title": "Hello",
                "abstract": "World",
                "updated_at": "2026-01-30T00:00:00Z",
                "status": "published",
            }
        ),
    )
    proto = OAIPMHProtocol("http://test/api/oai-pmh")
    xml = await proto.handle_request(
        OAIPMHRequest(
            verb="GetRecord",
            identifier="oai:scholarflow:article:a1",
            metadataPrefix="oai_dc",
        )
    )
    assert "<GetRecord>" in xml
    assert "oai:scholarflow:article:a1" in xml

