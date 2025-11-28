"""Creative schemas for request/response validation."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class FileType(str, Enum):
    """Supported creative file types."""

    IMAGE = "image"
    VIDEO = "video"


class CreativeStatus(str, Enum):
    """Creative status."""

    ACTIVE = "active"
    DELETED = "deleted"


class CreativeCreate(BaseModel):
    """Schema for creating a new creative."""

    file_url: str = Field(..., min_length=1, max_length=1024)
    cdn_url: str = Field(..., min_length=1, max_length=1024)
    file_type: FileType
    file_size: int = Field(..., gt=0)
    name: str | None = Field(None, max_length=255)
    product_url: str | None = Field(None, max_length=1024)
    style: str | None = Field(None, max_length=100)
    score: float | None = Field(None, ge=0, le=100)
    tags: list[str] = Field(default_factory=list)


class CreativeUpdate(BaseModel):
    """Schema for updating a creative."""

    name: str | None = Field(None, max_length=255)
    product_url: str | None = Field(None, max_length=1024)
    style: str | None = Field(None, max_length=100)
    score: float | None = Field(None, ge=0, le=100)
    tags: list[str] | None = None


class CreativeResponse(BaseModel):
    """Creative response schema."""

    id: int
    user_id: int
    file_url: str
    cdn_url: str
    file_type: str
    file_size: int
    name: str | None = None
    product_url: str | None = None
    style: str | None = None
    score: float | None = None
    tags: list[str] = []
    status: str
    created_at: datetime
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class CreativeListResponse(BaseModel):
    """Response for listing creatives."""

    items: list[CreativeResponse]
    total: int
    page: int
    page_size: int
    has_more: bool


class CreativeFilter(BaseModel):
    """Filter options for listing creatives."""

    file_type: FileType | None = None
    style: str | None = None
    status: CreativeStatus = CreativeStatus.ACTIVE
    tags: list[str] | None = None


class PresignedUploadUrlRequest(BaseModel):
    """Request for generating presigned upload URL."""

    filename: str = Field(..., min_length=1, max_length=255)
    content_type: str = Field(..., min_length=1, max_length=100)
    file_size: int = Field(..., gt=0, le=100 * 1024 * 1024)  # Max 100MB


class PresignedUploadUrlResponse(BaseModel):
    """Response with presigned upload URL."""

    upload_url: str
    upload_fields: dict[str, str]
    file_key: str
    s3_url: str
    cdn_url: str
    expires_in: int = 3600
