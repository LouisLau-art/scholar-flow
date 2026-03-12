from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


WorkflowDecisionBucket = Literal["accept", "reject", "major_revision", "minor_revision", "add_reviewer"]
DecisionSubmissionMode = Literal["execute", "recommendation"]
AcademicRecommendationValue = Literal[
    "accept",
    "accept_after_minor_revision",
    "major_revision",
    "reject_resubmit",
    "reject_decline",
]
DecisionSubmissionValue = Literal[
    "accept",
    "reject",
    "major_revision",
    "minor_revision",
    "add_reviewer",
    "accept_after_minor_revision",
    "reject_resubmit",
    "reject_decline",
]
DecisionLetterDecision = Literal["accept", "reject", "major_revision", "minor_revision"]
DecisionLetterStatus = Literal["draft", "final"]
ReviewStageExitTarget = Literal["first", "final", "major_revision", "minor_revision"]
ReviewStageExitPendingAction = Literal["cancel", "wait"]
ReviewStageExitRequestedOutcome = AcademicRecommendationValue

_WORKFLOW_DECISION_BUCKETS: set[str] = {
    "accept",
    "reject",
    "major_revision",
    "minor_revision",
    "add_reviewer",
}

_ACADEMIC_RECOMMENDATION_TO_WORKFLOW_BUCKET: dict[str, WorkflowDecisionBucket] = {
    "accept": "accept",
    "accept_after_minor_revision": "minor_revision",
    "major_revision": "major_revision",
    "reject_resubmit": "reject",
    "reject_decline": "reject",
}


def get_workflow_decision_bucket(decision: str) -> WorkflowDecisionBucket:
    normalized = str(decision or "").strip().lower()
    if normalized in _WORKFLOW_DECISION_BUCKETS:
        return normalized  # type: ignore[return-value]
    bucket = _ACADEMIC_RECOMMENDATION_TO_WORKFLOW_BUCKET.get(normalized)
    if bucket is None:
        raise ValueError(f"Unsupported decision: {decision}")
    return bucket


def is_academic_recommendation_value(decision: str) -> bool:
    normalized = str(decision or "").strip().lower()
    return normalized in _ACADEMIC_RECOMMENDATION_TO_WORKFLOW_BUCKET


class DecisionSubmitRequest(BaseModel):
    """
    决策提交请求（草稿/最终提交通用）
    """

    content: str = Field("", description="Markdown 决策信正文")
    decision: DecisionSubmissionValue = Field(..., description="决策结论")
    is_final: bool = Field(..., description="是否提交当前决策阶段动作；false 表示保存草稿")
    decision_stage: Literal["first", "final"] | None = Field(
        default=None,
        description="决策阶段（可选）。未提供时为兼容旧客户端按 is_final 推导",
    )
    attachment_paths: list[str] = Field(default_factory=list, description="附件引用列表")
    last_updated_at: datetime | None = Field(
        default=None,
        description="乐观锁字段。若提供则必须与服务端草稿 updated_at 一致",
    )

    @model_validator(mode="after")
    def _validate_decision_stage(self) -> "DecisionSubmitRequest":
        inferred = "final" if self.is_final else "first"
        if self.decision_stage is None:
            self.decision_stage = inferred
            return self
        return self


class ReviewStageExitPendingResolution(BaseModel):
    assignment_id: str = Field(..., min_length=1, description="待处理 reviewer assignment id")
    action: ReviewStageExitPendingAction = Field(..., description="离开外审前对已接受未提交审稿人的处理动作")
    reason: str = Field("", max_length=500, description="显式取消该 reviewer 的原因（仅 action=cancel 时使用）")


class ReviewStageExitRequest(BaseModel):
    target_stage: ReviewStageExitTarget = Field(..., description="外审结束后进入的决策阶段")
    requested_outcome: ReviewStageExitRequestedOutcome | None = Field(
        default=None,
        description="当 target_stage=first 时，AE 提交给学术编辑/主编的推荐处理结论",
    )
    recipient_emails: list[str] = Field(
        default_factory=list,
        description="当 target_stage=first 时，First Decision 默认收件人列表；可由 AE 手动修改",
    )
    note: str = Field("", max_length=1000, description="本次离开外审的说明，会写入审计")
    accepted_pending_resolutions: list[ReviewStageExitPendingResolution] = Field(
        default_factory=list,
        description="针对 accepted 但未提交 reviewer 的显式处理清单",
    )

    @field_validator("recipient_emails", mode="before")
    @classmethod
    def _normalize_recipient_emails(cls, value: object) -> list[str]:
        if value is None or value == "":
            return []
        raw_items: list[str] = []
        if isinstance(value, str):
            normalized = value.replace(";", ",").replace("\n", ",")
            raw_items = [part.strip() for part in normalized.split(",")]
        elif isinstance(value, (list, tuple, set)):
            raw_items = [str(item or "").strip() for item in value]
        else:
            raw_items = [str(value).strip()]

        seen: set[str] = set()
        normalized_items: list[str] = []
        for item in raw_items:
            candidate = str(item or "").strip().lower()
            if not candidate or candidate in seen:
                continue
            seen.add(candidate)
            normalized_items.append(candidate)
        return normalized_items

    @model_validator(mode="after")
    def _validate_requested_outcome(self) -> "ReviewStageExitRequest":
        if self.target_stage == "first" and self.requested_outcome is None:
            raise ValueError("requested_outcome is required when target_stage is first")
        if self.target_stage == "first" and not self.recipient_emails:
            raise ValueError("recipient_emails is required when target_stage is first")
        if self.target_stage != "first" and self.requested_outcome is not None:
            raise ValueError("requested_outcome is only allowed when target_stage is first")
        if self.target_stage != "first" and self.recipient_emails:
            raise ValueError("recipient_emails is only allowed when target_stage is first")
        return self


class ReviewStageExitResponse(BaseModel):
    manuscript_status: str
    target_stage: ReviewStageExitTarget
    auto_cancelled_assignment_ids: list[str] = Field(default_factory=list)
    manually_cancelled_assignment_ids: list[str] = Field(default_factory=list)
    remaining_pending_assignment_ids: list[str] = Field(default_factory=list)
    cancellation_email_sent_assignment_ids: list[str] = Field(default_factory=list)
    cancellation_email_failed_assignment_ids: list[str] = Field(default_factory=list)
    first_decision_email_sent_recipients: list[str] = Field(default_factory=list)
    first_decision_email_failed_recipients: list[str] = Field(default_factory=list)
    author_revision_email_sent_recipient: str | None = None
    author_revision_email_failed_recipient: str | None = None


class ReviewStageExitRequestSummary(BaseModel):
    target_stage: ReviewStageExitTarget
    requested_outcome: ReviewStageExitRequestedOutcome | None = None
    recipient_emails: list[str] = Field(default_factory=list)
    note: str = ""
    changed_at: datetime | None = None
    changed_by: str | None = None


class DecisionLetterPayload(BaseModel):
    id: str
    manuscript_id: str
    manuscript_version: int
    editor_id: str
    content: str
    decision: DecisionLetterDecision
    status: DecisionLetterStatus
    attachment_paths: list[str] = Field(default_factory=list)
    created_at: datetime | None = None
    updated_at: datetime | None = None


class DecisionSubmitResponse(BaseModel):
    decision_letter_id: str | None = None
    status: DecisionLetterStatus | None = None
    manuscript_status: str
    updated_at: datetime | None = None


class DecisionContextResponse(BaseModel):
    manuscript: dict
    reports: list[dict]
    draft: dict | None = None
    review_stage_exit_request: ReviewStageExitRequestSummary | None = None
    latest_decision_recommendation: dict | None = None
    templates: list[dict] = Field(default_factory=list)
    permissions: dict = Field(default_factory=dict)
