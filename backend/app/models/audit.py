from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class StatusTransitionLog(BaseModel):
    id: UUID
    manuscript_id: UUID
    from_status: Optional[str] = None
    to_status: str
    comment: Optional[str] = None
    changed_by: Optional[UUID] = None
    created_at: datetime = Field(...)

    model_config = ConfigDict(from_attributes=True)

