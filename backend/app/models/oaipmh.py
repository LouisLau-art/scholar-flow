from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class OAIPMHVerb(str, Enum):
    IDENTIFY = "Identify"
    LIST_METADATA_FORMATS = "ListMetadataFormats"
    LIST_SETS = "ListSets"
    LIST_IDENTIFIERS = "ListIdentifiers"
    LIST_RECORDS = "ListRecords"
    GET_RECORD = "GetRecord"


class OAIMetadataPrefix(str, Enum):
    OAI_DC = "oai_dc"


class OAIErrorCode(str, Enum):
    BAD_VERB = "badVerb"
    BAD_ARGUMENT = "badArgument"
    CANNOT_DISSEMINATE_FORMAT = "cannotDisseminateFormat"
    ID_DOES_NOT_EXIST = "idDoesNotExist"
    NO_RECORDS_MATCH = "noRecordsMatch"
    BAD_RESUMPTION_TOKEN = "badResumptionToken"
    NO_SET_HIERARCHY = "noSetHierarchy"
    NO_METADATA_FORMATS = "noMetadataFormats"


class OAIPMHRequest(BaseModel):
    verb: OAIPMHVerb
    identifier: Optional[str] = None
    metadataPrefix: Optional[str] = None
    from_: Optional[str] = Field(None, alias="from")
    until: Optional[str] = None
    set: Optional[str] = None
    resumptionToken: Optional[str] = None

    model_config = ConfigDict(populate_by_name=True)
