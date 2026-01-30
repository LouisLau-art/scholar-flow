from typing import Dict, Any
from datetime import datetime
from lxml import etree
from app.models.oaipmh import OAIPMHRequest, OAIPMHVerb, OAIErrorCode, OAIMetadataPrefix
from app.services.oaipmh.dublin_core import DublinCoreMapper
from app.lib.api_client import supabase


class OAIPMHProtocol:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.repository_name = "Scholar Flow"
        self.admin_email = "admin@example.com"  # Should come from config
        self.dc_mapper = DublinCoreMapper()
        self.ns = {
            "default": "http://www.openarchives.org/OAI/2.0/",
            "xsi": "http://www.w3.org/2001/XMLSchema-instance",
        }
        self.schema_location = "http://www.openarchives.org/OAI/2.0/ http://www.openarchives.org/OAI/2.0/OAI-PMH.xsd"

    async def handle_request(self, request: OAIPMHRequest) -> str:
        root = etree.Element(
            "OAI-PMH", nsmap={None: self.ns["default"], "xsi": self.ns["xsi"]}
        )
        root.set(f"{{{self.ns['xsi']}}}schemaLocation", self.schema_location)

        etree.SubElement(root, "responseDate").text = datetime.utcnow().strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )

        req_elem = etree.SubElement(root, "request")
        req_elem.text = self.base_url
        req_elem.set("verb", request.verb)
        if request.identifier:
            req_elem.set("identifier", request.identifier)
        if request.metadataPrefix:
            req_elem.set("metadataPrefix", request.metadataPrefix)
        if request.resumptionToken:
            req_elem.set("resumptionToken", request.resumptionToken)
        if request.from_:
            req_elem.set("from", request.from_)
        if request.until:
            req_elem.set("until", request.until)
        if request.set:
            req_elem.set("set", request.set)

        try:
            if request.verb == OAIPMHVerb.IDENTIFY:
                await self.identify(root)
            elif request.verb == OAIPMHVerb.LIST_METADATA_FORMATS:
                await self.list_metadata_formats(root, request)
            elif request.verb == OAIPMHVerb.LIST_SETS:
                await self.list_sets(root, request)
            elif request.verb == OAIPMHVerb.LIST_IDENTIFIERS:
                await self.list_identifiers(root, request)
            elif request.verb == OAIPMHVerb.LIST_RECORDS:
                await self.list_records(root, request)
            elif request.verb == OAIPMHVerb.GET_RECORD:
                await self.get_record(root, request)
            else:
                self.error(root, OAIErrorCode.BAD_VERB, "Illegal verb")
        except Exception as e:
            # Catch-all for internal errors
            print(f"OAI-PMH Error: {e}")
            self.error(root, OAIErrorCode.BAD_ARGUMENT, str(e))

        return etree.tostring(
            root, pretty_print=True, xml_declaration=True, encoding="UTF-8"
        ).decode("utf-8")

    def error(self, root: etree.Element, code: OAIErrorCode, message: str):
        err = etree.SubElement(root, "error", code=code)
        err.text = message

    async def identify(self, root: etree.Element):
        identify = etree.SubElement(root, "Identify")
        etree.SubElement(identify, "repositoryName").text = self.repository_name
        etree.SubElement(identify, "baseURL").text = self.base_url
        etree.SubElement(identify, "protocolVersion").text = "2.0"
        etree.SubElement(identify, "adminEmail").text = self.admin_email
        etree.SubElement(
            identify, "earliestDatestamp"
        ).text = "2020-01-01"  # Placeholder
        etree.SubElement(identify, "deletedRecord").text = "no"
        etree.SubElement(identify, "granularity").text = "YYYY-MM-DD"

    async def list_metadata_formats(self, root: etree.Element, request: OAIPMHRequest):
        lmf = etree.SubElement(root, "ListMetadataFormats")
        mf = etree.SubElement(lmf, "metadataFormat")
        etree.SubElement(mf, "metadataPrefix").text = "oai_dc"
        etree.SubElement(
            mf, "schema"
        ).text = "http://www.openarchives.org/OAI/2.0/oai_dc.xsd"
        etree.SubElement(
            mf, "metadataNamespace"
        ).text = "http://www.openarchives.org/OAI/2.0/oai_dc/"

    async def list_sets(self, root: etree.Element, request: OAIPMHRequest):
        self.error(
            root, OAIErrorCode.NO_SET_HIERARCHY, "This repository does not support sets"
        )

    async def get_record(self, root: etree.Element, request: OAIPMHRequest):
        if not request.identifier or not request.metadataPrefix:
            self.error(
                root, OAIErrorCode.BAD_ARGUMENT, "Missing identifier or metadataPrefix"
            )
            return

        if request.metadataPrefix != OAIMetadataPrefix.OAI_DC:
            self.error(
                root, OAIErrorCode.CANNOT_DISSEMINATE_FORMAT, "Only oai_dc is supported"
            )
            return

        # Parse identifier "oai:scholarflow:article:UUID"
        try:
            parts = request.identifier.split(":")
            article_id = parts[-1]
        except:
            self.error(
                root, OAIErrorCode.ID_DOES_NOT_EXIST, "Invalid identifier format"
            )
            return

        # Fetch from Supabase
        res = (
            supabase.table("manuscripts")
            .select("*")
            .eq("id", article_id)
            .eq("status", "published")
            .single()
            .execute()
        )
        if not res.data:
            self.error(
                root,
                OAIErrorCode.ID_DOES_NOT_EXIST,
                "Record not found or not published",
            )
            return

        gr = etree.SubElement(root, "GetRecord")
        self._append_record(gr, res.data)

    async def list_identifiers(self, root: etree.Element, request: OAIPMHRequest):
        if not request.metadataPrefix and not request.resumptionToken:
            self.error(root, OAIErrorCode.BAD_ARGUMENT, "Missing metadataPrefix")
            return

        if (
            request.metadataPrefix
            and request.metadataPrefix != OAIMetadataPrefix.OAI_DC
        ):
            self.error(
                root, OAIErrorCode.CANNOT_DISSEMINATE_FORMAT, "Only oai_dc is supported"
            )
            return

        # TODO: Pagination logic with resumptionToken
        # For now, fetch top 20

        query = (
            supabase.table("manuscripts")
            .select("id, updated_at, status")
            .eq("status", "published")
        )
        if request.from_:
            query = query.gte("updated_at", request.from_)
        if request.until:
            query = query.lte("updated_at", request.until)

        res = query.limit(20).execute()  # Naive limit

        if not res.data:
            self.error(root, OAIErrorCode.NO_RECORDS_MATCH, "No matching records")
            return

        li = etree.SubElement(root, "ListIdentifiers")
        for article in res.data:
            self._append_header(li, article)

    async def list_records(self, root: etree.Element, request: OAIPMHRequest):
        if not request.metadataPrefix and not request.resumptionToken:
            self.error(root, OAIErrorCode.BAD_ARGUMENT, "Missing metadataPrefix")
            return

        if (
            request.metadataPrefix
            and request.metadataPrefix != OAIMetadataPrefix.OAI_DC
        ):
            self.error(
                root, OAIErrorCode.CANNOT_DISSEMINATE_FORMAT, "Only oai_dc is supported"
            )
            return

        # Fetch full data
        query = supabase.table("manuscripts").select("*").eq("status", "published")
        if request.from_:
            query = query.gte("updated_at", request.from_)
        if request.until:
            query = query.lte("updated_at", request.until)

        res = query.limit(20).execute()

        if not res.data:
            self.error(root, OAIErrorCode.NO_RECORDS_MATCH, "No matching records")
            return

        lr = etree.SubElement(root, "ListRecords")
        for article in res.data:
            self._append_record(lr, article)

    def _append_header(self, parent: etree.Element, article: Dict[str, Any]):
        header = etree.SubElement(parent, "header")
        etree.SubElement(
            header, "identifier"
        ).text = f"oai:scholarflow:article:{article['id']}"
        date_str = article.get("updated_at") or article.get("created_at")
        if date_str:
            # Normalize date to YYYY-MM-DD
            etree.SubElement(header, "datestamp").text = date_str.split("T")[0]

    def _append_record(self, parent: etree.Element, article: Dict[str, Any]):
        record = etree.SubElement(parent, "record")
        self._append_header(record, article)
        metadata = etree.SubElement(record, "metadata")

        # We need authors and journal title which might not be in the simple select(*)
        # In a real impl, we would join or fetch separately.
        # Here we mock missing fields or rely on what's available.
        # Ideally ListRecords should fetch relations.
        # But supabase-py select can do relations: select("*, authors(*), journals(*)")
        # For simplicity, assuming basic mapping or mocking enrichment.

        # Enrich article data for mapper if needed
        # article['journal_title'] = ...

        xml_metadata = self.dc_mapper.to_xml(article)
        metadata.append(xml_metadata)
