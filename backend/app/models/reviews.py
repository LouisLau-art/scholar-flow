from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class ReviewReport(BaseModel):
    """审稿报告模型（支持双通道评论）"""

    id: UUID
    manuscript_id: UUID
    reviewer_id: UUID
    token: str
    expiry_date: datetime
    status: str = "invited"

    # Public (Author-visible)
    comments_for_author: Optional[str] = None
    content: Optional[str] = None

    # Confidential (Editor-only)
    confidential_comments_to_editor: Optional[str] = None
    attachment_path: Optional[str] = None
