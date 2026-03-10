from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator
from pydantic.config import ConfigDict

# === 核心业务实体模型 (Pydantic v2) ===

class ManuscriptAuthorContact(BaseModel):
    """稿件作者联系方式快照"""

    name: str = Field(..., min_length=1, max_length=200, description="作者姓名")
    email: EmailStr = Field(..., description="作者邮箱")
    affiliation: str = Field(..., min_length=1, max_length=500, description="作者机构")
    is_corresponding: bool = Field(False, description="是否为通讯作者")

    @field_validator("name", "affiliation")
    @classmethod
    def validate_non_empty_strings(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("field cannot be empty")
        return trimmed


class ManuscriptBase(BaseModel):
    """稿件基础模型"""
    title: str = Field(..., min_length=5, max_length=500, description="稿件标题")
    abstract: str = Field(..., min_length=30, max_length=5000, description="稿件摘要")
    submission_email: EmailStr = Field(..., description="投稿联系邮箱")
    author_contacts: list[ManuscriptAuthorContact] = Field(
        ..., min_length=1, max_length=20, description="作者列表（含通讯作者标记）"
    )
    file_path: Optional[str] = Field(None, description="Supabase Storage 路径")
    manuscript_word_path: Optional[str] = Field(None, max_length=1000, description="Word 主稿在 Storage 中的路径")
    manuscript_word_filename: Optional[str] = Field(None, max_length=255, description="Word 主稿原始文件名")
    manuscript_word_content_type: Optional[str] = Field(None, max_length=255, description="Word 主稿 MIME 类型")
    cover_letter_path: Optional[str] = Field(None, max_length=1000, description="Cover Letter 在 Storage 中的路径")
    cover_letter_filename: Optional[str] = Field(None, max_length=255, description="Cover Letter 原始文件名")
    cover_letter_content_type: Optional[str] = Field(None, max_length=255, description="Cover Letter MIME 类型")
    dataset_url: Optional[str] = Field(None, max_length=1000, description="外部数据集链接")
    source_code_url: Optional[str] = Field(None, max_length=1000, description="代码仓库链接")
    journal_id: Optional[UUID] = Field(None, description="绑定的期刊 ID")
    special_issue: Optional[str] = Field(None, max_length=255, description="目标专刊")

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

    @field_validator("special_issue", mode="before")
    @classmethod
    def normalize_optional_special_issue(cls, value):
        if value is None:
            return None
        if isinstance(value, str):
            trimmed = value.strip()
            return trimmed or None
        return value

    @field_validator(
        "file_path",
        "manuscript_word_path",
        "manuscript_word_filename",
        "manuscript_word_content_type",
        "cover_letter_path",
        "cover_letter_filename",
        "cover_letter_content_type",
        mode="before",
    )
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

    @model_validator(mode="after")
    def validate_author_contacts(self):
        corresponding_count = sum(1 for item in self.author_contacts if item.is_corresponding)
        if corresponding_count != 1:
            raise ValueError("exactly one corresponding author is required")
        return self

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
