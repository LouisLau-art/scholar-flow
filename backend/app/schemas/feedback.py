from typing import Optional
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class FeedbackCreate(BaseModel):
    description: str = Field(..., min_length=5, description="Issue description")
    severity: str = Field(..., pattern="^(low|medium|critical)$")
    url: str = Field(..., description="URL where the issue occurred")
    user_id: Optional[UUID] = None


class FeedbackResponse(BaseModel):
    id: UUID
    description: str
    severity: str
    url: str
    user_id: Optional[UUID]
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FeedbackAck(BaseModel):
    status: str = Field(..., description="Acknowledgement status")
