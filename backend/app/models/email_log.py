from datetime import datetime
from typing import Optional
from uuid import UUID
from enum import Enum
from pydantic import BaseModel, ConfigDict, Field


class EmailStatus(str, Enum):
    SENT = "sent"
    FAILED = "failed"
    PENDING_RETRY = "pending_retry"


class EmailLog(BaseModel):
    """
    Model for public.email_logs
    """
    id: Optional[UUID] = None  # DB generated
    recipient: str
    subject: str
    template_name: str
    status: EmailStatus
    provider_id: Optional[str] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class EmailLogCreate(BaseModel):
    recipient: str
    subject: str
    template_name: str
    status: EmailStatus = EmailStatus.SENT
    provider_id: Optional[str] = None
    error_message: Optional[str] = None
    retry_count: int = 0
