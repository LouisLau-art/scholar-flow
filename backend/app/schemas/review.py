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
    # 中文注释:
    # - Reviewer Workspace v2 简化交互：不再强制 reviewer 选择 recommendation。
    # - 后端保留字段用于兼容决策流水线，默认值为 minor_revision。
    recommendation: Recommendation = "minor_revision"
    attachments: list[str] = Field(default_factory=list)


class WorkspaceAttachment(BaseModel):
    path: str
    filename: str
    signed_url: str | None = None


class WorkspaceManuscript(BaseModel):
    id: UUID
    title: str
    abstract: str | None = None
    pdf_url: str
    dataset_url: str | None = None
    source_code_url: str | None = None
    cover_letter_url: str | None = None


class WorkspaceReviewReport(BaseModel):
    id: UUID | None = None
    status: str = "pending"
    comments_for_author: str = ""
    confidential_comments_to_editor: str = ""
    recommendation: Recommendation | None = None
    attachments: list[WorkspaceAttachment] = Field(default_factory=list)
    submitted_at: datetime | None = None


class WorkspaceAssignment(BaseModel):
    id: UUID
    status: str
    due_at: datetime | None = None
    invited_at: datetime | None = None
    opened_at: datetime | None = None
    accepted_at: datetime | None = None
    submitted_at: datetime | None = None
    decline_reason: str | None = None


class WorkspaceTimelineEvent(BaseModel):
    id: str
    timestamp: datetime
    actor: Literal["reviewer", "editor", "author", "system"]
    channel: Literal["public", "private", "system"]
    title: str
    message: str | None = None


class WorkspacePermissions(BaseModel):
    can_submit: bool
    is_read_only: bool


class WorkspaceData(BaseModel):
    manuscript: WorkspaceManuscript
    assignment: WorkspaceAssignment
    review_report: WorkspaceReviewReport
    permissions: WorkspacePermissions
    timeline: list[WorkspaceTimelineEvent] = Field(default_factory=list)


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
