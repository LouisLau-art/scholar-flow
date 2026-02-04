from typing import List, Optional
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class UserProfile(BaseModel):
    """
    Database model for public.user_profiles
    """

    id: UUID
    email: Optional[str] = None
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    affiliation: Optional[str] = None
    title: Optional[str] = None
    homepage_url: Optional[str] = None
    orcid_id: Optional[str] = None
    google_scholar_url: Optional[str] = None
    research_interests: List[str] = Field(default_factory=list)
    roles: List[str] = Field(default_factory=lambda: ["author"])
    is_reviewer_active: Optional[bool] = True
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
