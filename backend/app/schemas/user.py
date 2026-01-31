from typing import Optional, List
from pydantic import BaseModel, Field, HttpUrl, validator

class UserProfileUpdate(BaseModel):
    full_name: Optional[str] = Field(None, min_length=1, max_length=100)
    title: Optional[str] = Field(None, max_length=50)
    affiliation: Optional[str] = Field(None, max_length=200)
    orcid_id: Optional[str] = Field(None, pattern=r'^\d{4}-\d{4}-\d{4}-\d{3}[0-9X]$')
    google_scholar_url: Optional[HttpUrl] = None
    avatar_url: Optional[HttpUrl] = None
    research_interests: Optional[List[str]] = Field(None, max_items=10)

    @validator('research_interests', each_item=True)
    def validate_interest_length(cls, v):
        if len(v) > 50:
            raise ValueError('Research interest tag must be less than 50 characters')
        return v

class PasswordUpdate(BaseModel):
    password: str = Field(..., min_length=8)
    confirm_password: str = Field(..., min_length=8)

    @validator('confirm_password')
    def passwords_match(cls, v, values, **kwargs):
        if 'password' in values and v != values['password']:
            raise ValueError('Passwords do not match')
        return v
