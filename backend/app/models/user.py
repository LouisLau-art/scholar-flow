from typing import List, Optional
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field

class UserProfile(BaseModel):
    """
    Database model for public.user_profiles
    """
    id: UUID
    email: Optional[str]
    full_name: Optional[str]
    avatar_url: Optional[str]
    affiliation: Optional[str]
    title: Optional[str]
    orcid_id: Optional[str]
    google_scholar_url: Optional[str]
    research_interests: List[str] = Field(default_factory=list)
    roles: List[str] = Field(default_factory=lambda: ["author"])
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
