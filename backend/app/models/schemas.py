from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field, field_validator
from pydantic.config import ConfigDict

# === 核心业务实体模型 (Pydantic v2) ===

class ManuscriptBase(BaseModel):
    """稿件基础模型"""
    title: str = Field(..., min_length=5, max_length=500, description="稿件标题")
    abstract: str = Field(..., min_length=30, max_length=5000, description="稿件摘要")
    file_path: Optional[str] = Field(None, description="Supabase Storage 路径")
    cover_letter_path: Optional[str] = Field(None, max_length=1000, description="Cover Letter 在 Storage 中的路径")
    cover_letter_filename: Optional[str] = Field(None, max_length=255, description="Cover Letter 原始文件名")
    cover_letter_content_type: Optional[str] = Field(None, max_length=255, description="Cover Letter MIME 类型")
    dataset_url: Optional[str] = Field(None, max_length=1000, description="外部数据集链接")
    source_code_url: Optional[str] = Field(None, max_length=1000, description="代码仓库链接")
    journal_id: Optional[UUID] = Field(None, description="绑定的期刊 ID")

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str) -> str:
        # 中文注释: 标题必须有意义，避免空白或过短提交
        trimmed = value.strip()
        if len(trimmed) < 5:
            raise ValueError("title must be at least 5 characters")
        return trimmed

    @field_validator("abstract")
    @classmethod
    def validate_abstract(cls, value: str) -> str:
        # 中文注释: 摘要必须有足够内容，避免空白或过短提交
        trimmed = value.strip()
        if len(trimmed) < 30:
            raise ValueError("abstract must be at least 30 characters")
        return trimmed

    @field_validator("file_path", "cover_letter_path", "cover_letter_filename", "cover_letter_content_type", mode="before")
    @classmethod
    def normalize_optional_strings(cls, value):
        # 中文注释: 允许可选字段为空字符串；写入前统一做 trim
        if value is None:
            return None
        if isinstance(value, str):
            trimmed = value.strip()
            return trimmed or None
        return value

    @field_validator("dataset_url", "source_code_url", mode="before")
    @classmethod
    def normalize_optional_urls(cls, value):
        # 中文注释: 链接字段允许为空，但若填写必须是 http(s) URL
        if value is None:
            return None
        if isinstance(value, str):
            trimmed = value.strip()
            if trimmed == "":
                return None
            if not (trimmed.startswith("http://") or trimmed.startswith("https://")):
                raise ValueError("url must start with http:// or https://")
            return trimmed
        return value

class ManuscriptCreate(ManuscriptBase):
    """创建稿件时使用的模型"""
    author_id: UUID

class Manuscript(ManuscriptBase):
    """数据库中的完整稿件模型"""
    id: UUID
    status: str = Field("draft", description="稿件状态 (submitted, approved, etc.)")
    pre_check_status: Optional[str] = Field("intake", description="Pre-check Sub-status")
    assistant_editor_id: Optional[UUID] = Field(None, description="Assigned Assistant Editor")
    owner_id: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
