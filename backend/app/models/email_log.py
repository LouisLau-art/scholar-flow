from datetime import datetime
from typing import Any, Optional
from uuid import UUID
from enum import Enum
from pydantic import BaseModel, ConfigDict, Field


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
    actor_user_id: Optional[UUID] = None
    idempotency_key: Optional[str] = None
    scene: Optional[str] = None
    event_type: Optional[str] = None
    to_recipients: list[str] = Field(default_factory=list)
    cc_recipients: list[str] = Field(default_factory=list)
    bcc_recipients: list[str] = Field(default_factory=list)
    reply_to_recipients: list[str] = Field(default_factory=list)
    delivery_mode: Optional[str] = None
    communication_status: Optional[str] = None
    provider: Optional[str] = None
    attachment_count: int = 0
    attachment_manifest: list[dict[str, Any]] = Field(default_factory=list)
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
    actor_user_id: Optional[UUID] = None
    idempotency_key: Optional[str] = None
    scene: Optional[str] = None
    event_type: Optional[str] = None
    to_recipients: list[str] = Field(default_factory=list)
    cc_recipients: list[str] = Field(default_factory=list)
    bcc_recipients: list[str] = Field(default_factory=list)
    reply_to_recipients: list[str] = Field(default_factory=list)
    delivery_mode: Optional[str] = None
    communication_status: Optional[str] = None
    provider: Optional[str] = None
    attachment_count: int = 0
    attachment_manifest: list[dict[str, Any]] = Field(default_factory=list)
    provider_id: Optional[str] = None
    error_message: Optional[str] = None
    retry_count: int = 0
