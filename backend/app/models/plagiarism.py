from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field

# === 查重报告实体模型 (Pydantic v2) ===

class PlagiarismReportBase(BaseModel):
    """查重报告基础模型"""
    manuscript_id: UUID = Field(..., description="关联的稿件 ID")
    external_id: Optional[str] = Field(None, description="外部查重 API 的任务 ID")
    similarity_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="相似度得分 (0.0 - 1.0)")
    report_url: Optional[str] = Field(None, description="查重报告 PDF 存储路径")

class PlagiarismReport(PlagiarismReportBase):
    """数据库中的查重报告完整模型"""
    id: UUID
    status: str = Field("pending", description="查重状态 (pending, running, completed, failed)")
    retry_count: int = Field(0, description="自动重试计数")
    error_log: Optional[str] = Field(None, description="错误日志记录")
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class PlagiarismRetryRequest(BaseModel):
    """手动重试请求模型"""
    manuscript_id: UUID
