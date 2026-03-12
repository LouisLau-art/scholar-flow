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

ProductionCycleStage = Literal[
    "received",
    "typesetting",
    "language_editing",
    "ae_internal_proof",
    "author_proofreading",
    "ae_final_review",
    "pdf_preparation",
    "ready_to_publish",
    "published",
    "cancelled",
]

ProductionArtifactKind = Literal[
    "source_manuscript_snapshot",
    "typeset_output",
    "language_output",
    "ae_internal_proof",
    "author_annotated_proof",
    "final_confirmation_pdf",
    "publication_pdf",
]

ProofreadingDecision = Literal["confirm_clean", "submit_corrections"]

_LEGACY_STATUS_STAGE_MAP: dict[ProductionCycleStatus, ProductionCycleStage] = {
    "draft": "received",
    "awaiting_author": "author_proofreading",
    "author_confirmed": "ae_final_review",
    "author_corrections_submitted": "ae_final_review",
    "in_layout_revision": "typesetting",
    "approved_for_publish": "ready_to_publish",
    "cancelled": "cancelled",
}


class CreateProductionCycleRequest(BaseModel):
    layout_editor_id: UUID
    collaborator_editor_ids: list[UUID] = Field(default_factory=list)
    proofreader_author_id: UUID
    proof_due_at: datetime


class UpdateProductionCycleEditorsRequest(BaseModel):
    layout_editor_id: UUID | None = None
    collaborator_editor_ids: list[UUID] | None = None


class UpdateProductionCycleAssignmentsRequest(BaseModel):
    coordinator_ae_id: UUID | None = None
    typesetter_id: UUID | None = None
    language_editor_id: UUID | None = None
    pdf_editor_id: UUID | None = None


class TransitionProductionCycleRequest(BaseModel):
    target_stage: ProductionCycleStage
    comment: str | None = None


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


class ProductionArtifactPayload(BaseModel):
    id: str
    artifact_kind: ProductionArtifactKind
    storage_bucket: str | None = None
    storage_path: str | None = None
    file_name: str | None = None
    mime_type: str | None = None
    uploaded_by: str | None = None
    created_at: datetime | None = None
    metadata: dict[str, Any] | None = None


class ProductionCyclePayload(BaseModel):
    id: str
    manuscript_id: str
    cycle_no: int
    status: ProductionCycleStatus
    stage: ProductionCycleStage | None = None
    layout_editor_id: str
    collaborator_editor_ids: list[str] = Field(default_factory=list)
    proofreader_author_id: str
    coordinator_ae_id: str | None = None
    typesetter_id: str | None = None
    language_editor_id: str | None = None
    pdf_editor_id: str | None = None
    current_assignee_id: str | None = None
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
    artifacts: list[ProductionArtifactPayload] = Field(default_factory=list)

    @model_validator(mode="after")
    def _default_stage_from_legacy_status(self) -> "ProductionCyclePayload":
        if self.stage is None:
            self.stage = _LEGACY_STATUS_STAGE_MAP.get(self.status, "received")
        return self


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
