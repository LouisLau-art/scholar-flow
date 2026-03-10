from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator


DecisionValue = Literal["accept", "reject", "major_revision", "minor_revision"]
DecisionLetterStatus = Literal["draft", "final"]
ReviewStageExitTarget = Literal["first", "final"]
ReviewStageExitPendingAction = Literal["cancel", "wait"]


class DecisionSubmitRequest(BaseModel):
    """
    决策提交请求（草稿/最终提交通用）
    """

    content: str = Field("", description="Markdown 决策信正文")
    decision: DecisionValue = Field(..., description="决策结论")
    is_final: bool = Field(..., description="是否最终提交")
    decision_stage: Literal["first", "final"] | None = Field(
        default=None,
        description="决策阶段（可选）。未提供时由 is_final 推导",
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
        if self.decision_stage != inferred:
            raise ValueError("decision_stage and is_final are inconsistent")
        return self


class ReviewStageExitPendingResolution(BaseModel):
    assignment_id: str = Field(..., min_length=1, description="待处理 reviewer assignment id")
    action: ReviewStageExitPendingAction = Field(..., description="离开外审前对已接受未提交审稿人的处理动作")
    reason: str = Field("", max_length=500, description="显式取消该 reviewer 的原因（仅 action=cancel 时使用）")


class ReviewStageExitRequest(BaseModel):
    target_stage: ReviewStageExitTarget = Field(..., description="外审结束后进入的决策阶段")
    note: str = Field("", max_length=1000, description="本次离开外审的说明，会写入审计")
    accepted_pending_resolutions: list[ReviewStageExitPendingResolution] = Field(
        default_factory=list,
        description="针对 accepted 但未提交 reviewer 的显式处理清单",
    )


class ReviewStageExitResponse(BaseModel):
    manuscript_status: str
    target_stage: ReviewStageExitTarget
    auto_cancelled_assignment_ids: list[str] = Field(default_factory=list)
    manually_cancelled_assignment_ids: list[str] = Field(default_factory=list)
    remaining_pending_assignment_ids: list[str] = Field(default_factory=list)
    cancellation_email_sent_assignment_ids: list[str] = Field(default_factory=list)
    cancellation_email_failed_assignment_ids: list[str] = Field(default_factory=list)


class DecisionLetterPayload(BaseModel):
    id: str
    manuscript_id: str
    manuscript_version: int
    editor_id: str
    content: str
    decision: DecisionValue
    status: DecisionLetterStatus
    attachment_paths: list[str] = Field(default_factory=list)
    created_at: datetime | None = None
    updated_at: datetime | None = None


class DecisionSubmitResponse(BaseModel):
    decision_letter_id: str
    status: DecisionLetterStatus
    manuscript_status: str
    updated_at: datetime | None = None


class DecisionContextResponse(BaseModel):
    manuscript: dict
    reports: list[dict]
    draft: dict | None = None
    templates: list[dict] = Field(default_factory=list)
    permissions: dict = Field(default_factory=dict)
