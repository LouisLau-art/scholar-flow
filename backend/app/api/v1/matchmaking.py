from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, model_validator

from app.core.auth_utils import get_current_user
from app.core.roles import require_any_role
from app.services.matchmaking_service import MatchmakingService


router = APIRouter(prefix="/matchmaking", tags=["Matchmaking"])


class MatchmakingAnalyzeRequest(BaseModel):
    manuscript_id: Optional[str] = Field(default=None, description="Optional manuscript UUID")
    title: Optional[str] = Field(default=None, description="Manuscript title (optional if manuscript_id provided)")
    abstract: Optional[str] = Field(default=None, description="Manuscript abstract (optional)")

    @model_validator(mode="after")
    def validate_input(self):
        # 中文注释:
        # - 允许仅传 manuscript_id（后端将从 manuscripts 表拉取 title/abstract）。
        # - 若没有 manuscript_id，则至少需要 title 或 abstract 之一。
        if not self.manuscript_id and not ((self.title or "").strip() or (self.abstract or "").strip()):
            raise ValueError("Either manuscript_id or title/abstract must be provided")
        return self


@router.post("/analyze")
async def analyze_matchmaking(
    req: MatchmakingAnalyzeRequest,
    _current_user: dict = Depends(get_current_user),
    _profile: dict = Depends(require_any_role(["editor", "admin"])),
):
    """
    AI 分析：为稿件推荐审稿人

    中文注释:
    - 权限：仅 editor/admin 可用（SEC-004）。
    - 输出：只返回 reviewer_id + 联系信息 + match_score，不暴露 embedding（SEC-005）。
    """

    result = MatchmakingService().analyze(
        manuscript_id=req.manuscript_id,
        title=req.title,
        abstract=req.abstract,
    )
    return {"success": True, "data": result}

