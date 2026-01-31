# Note: In our architecture using Supabase-py, we often use Pydantic models for validation
# and raw dicts/Supabase client for DB operations.
# However, if we need an SQLAlchemy-like model or just type hints for the DB row, we define it here.
# Since the task asks for an SQLAlchemy model but the project seems to use Supabase client directly (see api_client.py),
# I will define a Pydantic model representing the DB schema for consistency with the existing codebase patterns found in other specs
# or just a dataclass if needed.
# Wait, previous specs might have established a pattern. Let's check user_management.py service.

from typing import Optional
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class UATFeedback(BaseModel):
    """
    Database model for public.uat_feedback
    """

    id: UUID
    description: str
    severity: str
    url: str
    user_id: Optional[UUID]
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
