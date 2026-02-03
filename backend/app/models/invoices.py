from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class Invoice(BaseModel):
    """财务账单模型"""

    id: UUID
    manuscript_id: UUID
    amount: float
    pdf_url: Optional[str] = None
    status: str = Field("unpaid", description="支付状态")
    confirmed_at: Optional[datetime] = None

