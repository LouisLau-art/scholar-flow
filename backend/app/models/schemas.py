from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field

# === 核心业务实体模型 (Pydantic v2) ===

class ManuscriptBase(BaseModel):
    """稿件基础模型"""
    title: str = Field(..., description="稿件标题")
    abstract: str = Field(..., description="稿件摘要")
    file_path: Optional[str] = Field(None, description="Supabase Storage 路径")

class ManuscriptCreate(ManuscriptBase):
    """创建稿件时使用的模型"""
    author_id: UUID

class Manuscript(ManuscriptBase):
    """数据库中的完整稿件模型"""
    id: UUID
    status: str = Field("draft", description="稿件状态 (submitted, approved, etc.)")
    kpi_owner_id: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class ReviewReport(BaseModel):
    """审稿报告模型"""
    id: UUID
    manuscript_id: UUID
    reviewer_id: UUID
    token: str
    expiry_date: datetime
    status: str = Field("invited", description="评审状态")
    content: Optional[str] = None
    score: Optional[int] = Field(None, ge=1, le=5)

class Invoice(BaseModel):
    """财务账单模型"""
    id: UUID
    manuscript_id: UUID
    amount: float
    status: str = Field("unpaid", description="支付状态")
    confirmed_at: Optional[datetime] = None
