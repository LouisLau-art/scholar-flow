from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator
from pydantic.config import ConfigDict


CMSMenuLocation = Literal["header", "footer"]


class CMSPage(BaseModel):
    """
    CMS 页面实体（用于 API 输出）。

    中文注释:
    - content 存储为「已消毒的 HTML」，仍建议前端渲染前再次进行 sanitize（Defense in Depth）。
    """

    id: UUID
    slug: str
    title: str
    content: Optional[str] = None
    is_published: bool = False
    created_at: datetime
    updated_at: datetime
    updated_by: Optional[UUID] = None

    model_config = ConfigDict(from_attributes=True)


class CMSPageCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    slug: str = Field(..., min_length=1, max_length=80)
    content: Optional[str] = Field(None, max_length=200_000)
    is_published: bool = False

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, value: str) -> str:
        trimmed = value.strip().lower()
        if trimmed == "":
            raise ValueError("slug is required")
        return trimmed

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str) -> str:
        trimmed = value.strip()
        if trimmed == "":
            raise ValueError("title is required")
        return trimmed


class CMSPageUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    content: Optional[str] = Field(None, max_length=200_000)
    is_published: Optional[bool] = None

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        trimmed = value.strip()
        if trimmed == "":
            raise ValueError("title cannot be empty")
        return trimmed


class CMSMenuItem(BaseModel):
    """
    菜单项实体（用于 API 输出）。
    """

    id: UUID
    parent_id: Optional[UUID] = None
    label: str
    url: Optional[str] = None
    page_slug: Optional[str] = None
    order_index: int = 0
    location: CMSMenuLocation
    children: list["CMSMenuItem"] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class CMSMenuItemInput(BaseModel):
    label: str = Field(..., min_length=1, max_length=80)
    url: Optional[str] = Field(None, max_length=1000)
    page_slug: Optional[str] = Field(None, max_length=80)
    children: list["CMSMenuItemInput"] = Field(default_factory=list)

    @field_validator("label")
    @classmethod
    def validate_label(cls, value: str) -> str:
        trimmed = value.strip()
        if trimmed == "":
            raise ValueError("label is required")
        return trimmed

    @field_validator("url")
    @classmethod
    def validate_url(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        trimmed = value.strip()
        if trimmed == "":
            return None
        if not (trimmed.startswith("/") or trimmed.startswith("http://") or trimmed.startswith("https://")):
            raise ValueError("url must start with / or http(s)://")
        return trimmed

    @field_validator("page_slug")
    @classmethod
    def validate_page_slug(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        trimmed = value.strip().lower()
        if trimmed == "":
            return None
        return trimmed

    @field_validator("children")
    @classmethod
    def validate_children_depth(cls, value: list["CMSMenuItemInput"]) -> list["CMSMenuItemInput"]:
        # 中文注释: MVP 阶段限制层级深度，避免无限递归/异常配置导致渲染和管理复杂度暴涨。
        return value


class CMSMenuUpdateRequest(BaseModel):
    location: CMSMenuLocation
    items: list[CMSMenuItemInput]

