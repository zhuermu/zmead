"""Landing page schemas for request/response validation."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class LandingPageStatus(str, Enum):
    """Landing page status."""

    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class LandingPageCreate(BaseModel):
    """Schema for creating a new landing page."""

    name: str = Field(..., min_length=1, max_length=255)
    product_url: str = Field(..., min_length=1, max_length=1024)
    template: str = Field(default="modern", max_length=100)
    language: str = Field(default="en", max_length=10)
    html_content: str | None = Field(None)


class LandingPageUpdate(BaseModel):
    """Schema for updating a landing page."""

    name: str | None = Field(None, min_length=1, max_length=255)
    product_url: str | None = Field(None, min_length=1, max_length=1024)
    template: str | None = Field(None, max_length=100)
    language: str | None = Field(None, max_length=10)
    html_content: str | None = None


class LandingPageResponse(BaseModel):
    """Landing page response schema."""

    id: int
    user_id: int
    name: str
    url: str
    s3_key: str
    product_url: str
    template: str
    language: str
    html_content: str | None = None
    status: str
    created_at: datetime
    updated_at: datetime | None = None
    published_at: datetime | None = None

    model_config = {"from_attributes": True}


class LandingPageListResponse(BaseModel):
    """Response for listing landing pages."""

    items: list[LandingPageResponse]
    total: int
    page: int
    page_size: int
    has_more: bool


class LandingPageFilter(BaseModel):
    """Filter options for listing landing pages."""

    status: LandingPageStatus | None = None
    template: str | None = None
    language: str | None = None


class LandingPagePublishResponse(BaseModel):
    """Response after publishing a landing page."""

    id: int
    url: str
    cdn_url: str
    status: str
    published_at: datetime
