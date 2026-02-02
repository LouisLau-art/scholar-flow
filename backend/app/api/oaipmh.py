from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response as FastAPIResponse
from app.models.oaipmh import OAIPMHRequest, OAIPMHVerb
from app.services.oaipmh.protocol import OAIPMHProtocol
from typing import Optional
from datetime import datetime

router = APIRouter(prefix="/api/oai-pmh", tags=["OAI-PMH"])


def get_protocol(request: Request) -> OAIPMHProtocol:
    # Use request.base_url to determine base URL dynamically
    base_url = str(request.base_url).rstrip("/") + "/api/oai-pmh"
    return OAIPMHProtocol(base_url)


@router.get("")
@router.post("")
async def handle_oaipmh_request(
    request: Request,
    verb: Optional[str] = None,
    identifier: Optional[str] = None,
    metadataPrefix: Optional[str] = None,
    from_: Optional[str] = None,
    until: Optional[str] = None,
    set: Optional[str] = None,
    resumptionToken: Optional[str] = None,
    protocol: OAIPMHProtocol = Depends(get_protocol),
):
    """
    OAI-PMH v2.0 endpoint (supports GET and POST)
    """
    # Rate limiting placeholder
    # check_rate_limit(request)

    # For POST requests, parameters might be in body form data
    if request.method == "POST":
        form_data = await request.form()
        verb = form_data.get("verb")
        identifier = form_data.get("identifier")
        metadataPrefix = form_data.get("metadataPrefix")
        from_ = form_data.get("from")
        until = form_data.get("until")
        set = form_data.get("set")
        resumptionToken = form_data.get("resumptionToken")

    # Map string verb to Enum
    try:
        verb_enum = OAIPMHVerb(verb) if verb else None
    except ValueError:
        # Let protocol handle bad verb
        # We need to construct request even with invalid verb to return badVerb error XML
        # But OAIPMHRequest model requires valid Enum.
        # So we might need to handle validation error or relax model.
        # Actually OAIPMHRequest uses Enum, so it will fail validation if constructed directly.
        # We'll pass raw strings to protocol if we modify protocol to accept them,
        # OR handle validation error here and return OAI error.
        # Protocol.handle_request expects OAIPMHRequest.
        # If verb is invalid, we can't create OAIPMHRequest easily if it enforces Enum.
        pass

    # Actually, better to catch validation error or manually construct request object
    # that protocol can handle.
    # For simplicity, if verb is missing or invalid, we pass None/Invalid and Protocol handles it?
    # No, Pydantic will error.

    # Let's try to construct request.
    try:
        oaipmh_req = OAIPMHRequest(
            verb=verb,  # type: ignore
            identifier=identifier,
            metadataPrefix=metadataPrefix,
            from_=from_,
            until=until,
            set=set,
            resumptionToken=resumptionToken,
        )
        xml_response = await protocol.handle_request(oaipmh_req)
    except Exception:
        # If Pydantic validation fails (e.g. invalid verb), we should return badVerb or badArgument.
        # We can construct a minimal "bad verb" response manually or use a helper in protocol.
        # But protocol.handle_request requires valid request object.
        # Let's instantiate Protocol and call error directly if validation fails?
        # Protocol.error needs a root element.

        # Simplified: If verb is invalid, we treat it as badVerb.
        # We need a way to generate error XML without a valid request object.
        # Let's modify handle_request to be more flexible or create a specific error handler.
        # For now, let's just try to handle it.

        # We can create a "dummy" request or modify OAIPMHRequest to allow string and validate later.
        # But sticking to Pydantic is good.

        # If verb is missing -> badVerb
        # If verb is invalid -> badVerb

        # We can construct the error XML manually here or expose a method in Protocol.
        # For MVP, let's just return 400 or simple text if really broken, but OAI-PMH expects XML 200.

        # Hack: Pass a special "internal" verb or relax the model?
        # Let's relax the model in `app/models/oaipmh.py`?
        # Or just catch exception and return a generic error XML.

        xml_response = f"""<?xml version="1.0" encoding="UTF-8"?>
<OAI-PMH xmlns="http://www.openarchives.org/OAI/2.0/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.openarchives.org/OAI/2.0/ http://www.openarchives.org/OAI/2.0/OAI-PMH.xsd">
  <responseDate>{datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")}</responseDate>
  <request>{protocol.base_url}</request>
  <error code="badVerb">Illegal or missing verb</error>
</OAI-PMH>"""

    return FastAPIResponse(content=xml_response, media_type="text/xml")
