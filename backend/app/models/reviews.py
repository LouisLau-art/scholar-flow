from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ReviewReport(BaseModel):
    """审稿报告模型（支持双通道评论）"""

    id: UUID
    manuscript_id: UUID
    reviewer_id: UUID
    token: str
    expiry_date: datetime
    status: str = Field("invited", description="评审状态")

    # Public (Author-visible)
    content: Optional[str] = None

    # Confidential (Editor-only)
    confidential_comments_to_editor: Optional[str] = None
    attachment_path: Optional[str] = None

    score: Optional[int] = Field(None, ge=1, le=5)

