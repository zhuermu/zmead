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
    ga_measurement_id: str | None = Field(None, max_length=20, pattern=r"^G-[A-Z0-9]+$")


class LandingPageResponse(BaseModel):
    """Landing page response schema."""

    id: int
    user_id: int
    name: str
    url: str
    signed_url: str | None = None  # Signed URL for secure access (1 hour expiry)
    s3_key: str
    product_url: str
    template: str
    language: str
    # 草稿内容：编辑器始终操作这个字段
    draft_content: str | None = None
    # 已发布内容：发布后才会有值，线上显示的内容
    html_content: str | None = None
    # 是否有未发布的更改
    has_unpublished_changes: bool = False
    # GA4 Measurement ID for analytics
    ga_measurement_id: str | None = None
    status: str
    created_at: datetime
    updated_at: datetime | None = None
    published_at: datetime | None = None

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_with_changes(cls, obj) -> "LandingPageResponse":
        """Create response from ORM object with has_unpublished_changes computed.

        For draft pages:
        - url: Frontend edit page URL (e.g., http://localhost:3000/landing-pages/{id})
        - signed_url: None

        For published pages:
        - url: CloudFront CDN URL for public access
        - signed_url: None (not needed for public pages)
        """
        from app.core.config import settings

        # Generate appropriate URL based on status
        if obj.status == LandingPageStatus.DRAFT.value:
            # Draft pages: return frontend edit page URL
            url = f"{settings.frontend_url}/landing-pages/{obj.id}"
            signed_url = None
        else:
            # Published pages use CloudFront URL from database
            url = obj.url or ""
            signed_url = None

        data = {
            "id": obj.id,
            "user_id": obj.user_id,
            "name": obj.name,
            "url": url,
            "signed_url": signed_url,
            "s3_key": obj.s3_key,
            "product_url": obj.product_url,
            "template": obj.template,
            "language": obj.language,
            "draft_content": obj.draft_content,
            "html_content": obj.html_content,
            "ga_measurement_id": obj.ga_measurement_id,
            "status": obj.status,
            "created_at": obj.created_at,
            "updated_at": obj.updated_at,
            "published_at": obj.published_at,
            # 计算是否有未发布的更改：草稿内容与已发布内容不同
            "has_unpublished_changes": (
                obj.draft_content is not None
                and obj.html_content is not None
                and obj.draft_content != obj.html_content
            ),
        }
        return cls(**data)


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
