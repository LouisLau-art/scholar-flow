from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


DecisionValue = Literal["accept", "reject", "major_revision", "minor_revision"]
DecisionLetterStatus = Literal["draft", "final"]


class DecisionSubmitRequest(BaseModel):
    """
    决策提交请求（草稿/最终提交通用）
    """

    content: str = Field("", description="Markdown 决策信正文")
    decision: DecisionValue = Field(..., description="决策结论")
    is_final: bool = Field(..., description="是否最终提交")
    attachment_paths: list[str] = Field(default_factory=list, description="附件引用列表")
    last_updated_at: datetime | None = Field(
        default=None,
        description="乐观锁字段。若提供则必须与服务端草稿 updated_at 一致",
    )


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
