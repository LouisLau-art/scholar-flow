from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class PlatformReadinessStatus(str, Enum):
    PASSED = "passed"
    FAILED = "failed"
    BLOCKED = "blocked"


class PlatformReadinessCheck(BaseModel):
    key: str = Field(..., min_length=1, max_length=128)
    title: str = Field(..., min_length=1, max_length=200)
    status: PlatformReadinessStatus
    detail: str
    evidence: dict[str, Any] = Field(default_factory=dict)


class PlatformReadinessResponse(BaseModel):
    status: PlatformReadinessStatus
    checks: list[PlatformReadinessCheck] = Field(default_factory=list)
