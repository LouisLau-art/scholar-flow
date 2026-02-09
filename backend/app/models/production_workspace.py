from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


ProductionCycleStatus = Literal[
    "draft",
    "awaiting_author",
    "author_confirmed",
    "author_corrections_submitted",
    "in_layout_revision",
    "approved_for_publish",
    "cancelled",
]

ProofreadingDecision = Literal["confirm_clean", "submit_corrections"]


class CreateProductionCycleRequest(BaseModel):
    layout_editor_id: UUID
    proofreader_author_id: UUID
    proof_due_at: datetime


class CorrectionItemInput(BaseModel):
    line_ref: str | None = None
    original_text: str | None = None
    suggested_text: str = Field(..., min_length=1)
    reason: str | None = None


class SubmitProofreadingRequest(BaseModel):
    decision: ProofreadingDecision
    summary: str | None = None
    corrections: list[CorrectionItemInput] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_decision_payload(self) -> "SubmitProofreadingRequest":
        if self.decision == "submit_corrections" and not self.corrections:
            raise ValueError("corrections are required when decision=submit_corrections")
        if self.decision == "confirm_clean" and self.corrections:
            raise ValueError("corrections must be empty when decision=confirm_clean")
        return self


class ProductionCyclePayload(BaseModel):
    id: str
    manuscript_id: str
    cycle_no: int
    status: ProductionCycleStatus
    layout_editor_id: str
    proofreader_author_id: str
    galley_bucket: str | None = None
    galley_path: str | None = None
    galley_signed_url: str | None = None
    version_note: str | None = None
    proof_due_at: datetime | None = None
    approved_by: str | None = None
    approved_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    latest_response: dict[str, Any] | None = None


class ProductionWorkspaceResponse(BaseModel):
    manuscript: dict[str, Any]
    active_cycle: ProductionCyclePayload | None = None
    cycle_history: list[ProductionCyclePayload] = Field(default_factory=list)
    permissions: dict[str, Any] = Field(default_factory=dict)


class ProofreadingResponsePayload(BaseModel):
    response_id: str
    cycle_id: str
    decision: ProofreadingDecision
    submitted_at: datetime


class ProductionApproveResponse(BaseModel):
    cycle_id: str
    status: Literal["approved_for_publish"]
    approved_at: datetime
    approved_by: str


class ProofreadingContextResponse(BaseModel):
    manuscript: dict[str, Any]
    cycle: ProductionCyclePayload
    can_submit: bool = True
    is_read_only: bool = False
