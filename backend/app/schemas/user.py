"""User schemas for API requests and responses."""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, EmailStr, Field


class UserResponse(BaseModel):
    """User response schema."""

    id: int
    email: EmailStr
    display_name: str
    avatar_url: str | None = None
    oauth_provider: str
    gifted_credits: Decimal
    purchased_credits: Decimal
    total_credits: Decimal
    language: str
    timezone: str
    notification_preferences: dict
    is_active: bool
    created_at: datetime
    updated_at: datetime | None = None
    last_login_at: datetime | None = None

    model_config = {"from_attributes": True}


class UserUpdateRequest(BaseModel):
    """User profile update request."""

    display_name: str | None = Field(None, min_length=1, max_length=255)
    avatar_url: str | None = Field(None, max_length=512)
    language: str | None = Field(None, min_length=2, max_length=10)
    timezone: str | None = Field(None, max_length=50)
    notification_preferences: dict | None = None


class UserDeleteRequest(BaseModel):
    """User account deletion request."""

    confirmation: str = Field(
        ...,
        description="Must be 'DELETE' to confirm account deletion"
    )


class NotificationPreferences(BaseModel):
    """User notification preferences."""

    email_enabled: bool = True
    in_app_enabled: bool = True
    credit_warning_threshold: int = Field(default=50, ge=0)
    credit_critical_threshold: int = Field(default=10, ge=0)
