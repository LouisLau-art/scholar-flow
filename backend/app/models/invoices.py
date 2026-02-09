from datetime import datetime
from typing import Literal, Optional
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


class FinanceInvoiceQuery(BaseModel):
    """
    Finance 列表查询参数。
    """

    status: Literal["all", "unpaid", "paid", "waived"] = "all"
    q: str | None = Field(default=None, max_length=100)
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    sort_by: Literal["updated_at", "amount", "status"] = "updated_at"
    sort_order: Literal["asc", "desc"] = "desc"


class FinanceInvoiceRow(BaseModel):
    """
    Finance 列表行读模型。
    """

    invoice_id: UUID
    manuscript_id: UUID
    invoice_number: str | None = None
    manuscript_title: str
    authors: str | None = None
    amount: float = 0
    currency: str = "USD"
    raw_status: str = "unpaid"
    effective_status: Literal["unpaid", "paid", "waived"] = "unpaid"
    confirmed_at: datetime | None = None
    updated_at: datetime
    payment_gate_blocked: bool = True


class FinanceInvoiceListMeta(BaseModel):
    """
    Finance 列表元信息。
    """

    page: int = 1
    page_size: int = 20
    total: int = 0
    status_filter: Literal["all", "unpaid", "paid", "waived"] = "all"
    snapshot_at: datetime
    empty: bool = True
