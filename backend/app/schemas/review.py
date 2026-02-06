from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


Recommendation = Literal["accept", "minor_revision", "major_revision", "reject"]


class ReviewSubmission(BaseModel):
    comments_for_author: str = Field(min_length=1, max_length=20000)
    confidential_comments_to_editor: str = Field(default="", max_length=20000)
    recommendation: Recommendation
    attachments: list[str] = Field(default_factory=list)


class WorkspaceManuscript(BaseModel):
    id: UUID
    title: str
    abstract: str | None = None
    pdf_url: str


class WorkspaceReviewReport(BaseModel):
    id: UUID | None = None
    status: str = "pending"
    comments_for_author: str = ""
    confidential_comments_to_editor: str = ""
    recommendation: Recommendation | None = None
    attachments: list[str] = Field(default_factory=list)


class WorkspacePermissions(BaseModel):
    can_submit: bool
    is_read_only: bool


class WorkspaceData(BaseModel):
    manuscript: WorkspaceManuscript
    review_report: WorkspaceReviewReport
    permissions: WorkspacePermissions
