from datetime import datetime
from enum import Enum
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict


class DOIRegistrationStatus(str, Enum):
    PENDING = "pending"
    SUBMITTING = "submitting"
    REGISTERED = "registered"
    FAILED = "failed"


class DOITaskStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class DOITaskType(str, Enum):
    REGISTER = "register"
    UPDATE = "update"


class DOIRegistrationBase(BaseModel):
    article_id: UUID
    doi: Optional[str] = Field(
        None,
        pattern=r"(?i)^10\.\d{4,9}/[-._;()/:A-Z0-9]+$",
    )
    status: DOIRegistrationStatus = DOIRegistrationStatus.PENDING
    attempts: int = 0
    crossref_batch_id: Optional[str] = None
    error_message: Optional[str] = None
    registered_at: Optional[datetime] = None


class DOIRegistrationCreate(BaseModel):
    article_id: UUID


class DOIRegistration(DOIRegistrationBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DOITaskBase(BaseModel):
    registration_id: UUID
    task_type: DOITaskType
    status: DOITaskStatus = DOITaskStatus.PENDING
    priority: int = 0
    run_at: datetime
    locked_at: Optional[datetime] = None
    locked_by: Optional[str] = None
    attempts: int = 0
    max_attempts: int = 4
    last_error: Optional[str] = None


class DOITask(DOITaskBase):
    id: UUID
    created_at: datetime
    completed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class DOITaskList(BaseModel):
    items: List[DOITask]
    total: int
    limit: int
    offset: int
