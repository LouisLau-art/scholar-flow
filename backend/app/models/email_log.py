from datetime import datetime
from typing import Optional
from uuid import UUID
from enum import Enum
from pydantic import BaseModel, ConfigDict


class EmailStatus(str, Enum):
    QUEUED = "queued"
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
    assignment_id: Optional[UUID] = None
    manuscript_id: Optional[UUID] = None
    idempotency_key: Optional[str] = None
    scene: Optional[str] = None
    event_type: Optional[str] = None
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
    assignment_id: Optional[UUID] = None
    manuscript_id: Optional[UUID] = None
    idempotency_key: Optional[str] = None
    scene: Optional[str] = None
    event_type: Optional[str] = None
    provider_id: Optional[str] = None
    error_message: Optional[str] = None
    retry_count: int = 0
