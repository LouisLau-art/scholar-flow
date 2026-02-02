"""
Revision & ManuscriptVersion Pydantic Models

中文注释: 修订循环的核心模型，用于支持 Editor 请求修改和 Author 提交修订稿的工作流。
"""

from datetime import datetime
from typing import Optional, Literal
from uuid import UUID
from pydantic import BaseModel, Field
from pydantic.config import ConfigDict


# === Manuscript Version Models ===


class ManuscriptVersionBase(BaseModel):
    """稿件版本基础模型"""

    version_number: int = Field(..., ge=1, description="版本号，从 1 开始")
    file_path: str = Field(..., description="文件在 Storage 中的路径")
    title: Optional[str] = Field(None, description="该版本的标题快照")
    abstract: Optional[str] = Field(None, description="该版本的摘要快照")


class ManuscriptVersionCreate(ManuscriptVersionBase):
    """创建稿件版本时使用的模型"""

    manuscript_id: UUID


class ManuscriptVersion(ManuscriptVersionBase):
    """数据库中完整的稿件版本模型"""

    id: UUID
    manuscript_id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# === Revision Models ===


class RevisionBase(BaseModel):
    """修订请求基础模型"""

    round_number: int = Field(..., ge=1, description="修订轮次，从 1 开始")
    decision_type: Literal["major", "minor"] = Field(
        ..., description="修订类型: major (大修) 或 minor (小修)"
    )
    editor_comment: str = Field(
        ..., min_length=10, max_length=5000, description="编辑给作者的修改意见"
    )


class RevisionCreate(BaseModel):
    """Editor 请求修订时使用的模型"""

    manuscript_id: UUID
    decision_type: Literal["major", "minor"] = Field(..., description="修订类型")
    comment: str = Field(..., min_length=10, max_length=5000, description="修改意见")


class RevisionSubmit(BaseModel):
    """Author 提交修订稿时使用的模型"""

    response_letter: str = Field(
        ..., min_length=20, max_length=10000, description="回复信"
    )
    # file 通过 multipart/form-data 传递，不在此模型中


class Revision(RevisionBase):
    """数据库中完整的修订记录模型"""

    id: UUID
    manuscript_id: UUID
    response_letter: Optional[str] = Field(
        None, description="作者的回复信（提交后填写）"
    )
    status: Literal["pending", "submitted"] = Field(
        "pending", description="pending=等待作者提交, submitted=已提交"
    )
    created_at: datetime
    submitted_at: Optional[datetime] = Field(None, description="作者提交修订稿的时间")

    model_config = ConfigDict(from_attributes=True)


# === Response Schemas ===


class RevisionRequestResponse(BaseModel):
    """请求修订后的响应"""

    success: bool = True
    message: str = "Revision requested successfully"
    data: Revision


class RevisionSubmitResponse(BaseModel):
    """提交修订稿后的响应"""

    success: bool = True
    message: str = "Revision submitted successfully"
    data: dict  # 包含 revision 和新的 manuscript_version


class VersionHistoryResponse(BaseModel):
    """版本历史响应"""

    success: bool = True
    data: dict  # 包含 versions 和 revisions 列表
