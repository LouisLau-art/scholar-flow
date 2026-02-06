from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class MagicLinkPayload(BaseModel):
    """
    Magic Link JWT 载荷（Feature 039）

    中文注释:
    - 载荷只包含必要的 ID（不包含邮箱/姓名等 PII）。
    - exp 为 JWT 标准字段（Unix timestamp seconds）。
    """

    type: Literal["magic_link"] = "magic_link"
    reviewer_id: UUID
    manuscript_id: UUID
    assignment_id: UUID
    exp: int = Field(..., description="Unix timestamp (seconds)")


class MagicLinkVerifyRequest(BaseModel):
    token: str = Field(..., min_length=16, description="Magic Link JWT from URL query")


class MagicLinkVerifyResponseData(BaseModel):
    reviewer_id: UUID
    manuscript_id: UUID
    assignment_id: UUID
    expires_at: datetime


class MagicLinkVerifyResponse(BaseModel):
    success: bool = True
    data: MagicLinkVerifyResponseData

