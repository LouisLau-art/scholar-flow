from __future__ import annotations

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


Recommendation = Literal["accept", "minor_revision", "major_revision", "reject"]
DeclineReason = Literal[
    "out_of_scope",
    "conflict_of_interest",
    "too_busy",
    "insufficient_expertise",
    "other",
]


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


class InviteActionWindow(BaseModel):
    min_due_date: date
    max_due_date: date
    default_due_date: date


class InviteTimeline(BaseModel):
    invited_at: datetime | None = None
    opened_at: datetime | None = None
    accepted_at: datetime | None = None
    declined_at: datetime | None = None
    submitted_at: datetime | None = None


class InviteAssignmentState(BaseModel):
    assignment_id: UUID
    manuscript_id: UUID
    reviewer_id: UUID
    status: str
    due_at: datetime | None = None
    decline_reason: DeclineReason | None = None
    decline_note: str | None = None
    timeline: InviteTimeline


class InviteManuscriptPreview(BaseModel):
    id: UUID
    title: str
    abstract: str | None = None


class InviteViewData(BaseModel):
    assignment: InviteAssignmentState
    manuscript: InviteManuscriptPreview
    window: InviteActionWindow
    can_open_workspace: bool


class InviteAcceptPayload(BaseModel):
    due_date: date


class InviteDeclinePayload(BaseModel):
    reason: DeclineReason
    note: str = Field(default="", max_length=1000)
