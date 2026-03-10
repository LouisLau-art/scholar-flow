from __future__ import annotations

from typing import List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, HttpUrl, field_validator

from app.core.email_normalization import normalize_email


ReviewerTitle = Literal[
    "Prof.",
    "Professor",
    "Dr.",
    "Mr.",
    "Ms.",
    "Mrs.",
    "Mx.",
    "Other",
]


class ReviewerCreate(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=200)
    title: ReviewerTitle | str
    affiliation: Optional[str] = Field(default=None, max_length=300)
    homepage_url: Optional[HttpUrl] = None
    research_interests: List[str] = Field(default_factory=list, max_length=50)

    @field_validator("email", mode="before")
    @classmethod
    def normalize_request_email(cls, v):
        return normalize_email(v)


class ReviewerUpdate(BaseModel):
    full_name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    title: Optional[ReviewerTitle | str] = None
    affiliation: Optional[str] = Field(default=None, max_length=300)
    homepage_url: Optional[HttpUrl] = None
    research_interests: Optional[List[str]] = Field(default=None, max_length=50)
    is_reviewer_active: Optional[bool] = None


class ReviewerLibraryItem(BaseModel):
    id: UUID
    email: Optional[str] = None
    full_name: Optional[str] = None
    title: Optional[str] = None
    affiliation: Optional[str] = None
    homepage_url: Optional[str] = None
    research_interests: List[str] = Field(default_factory=list)
    roles: List[str] = Field(default_factory=list)
    is_reviewer_active: bool = True
