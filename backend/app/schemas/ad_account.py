"""Ad Account schemas."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class AdPlatform(str, Enum):
    """Supported advertising platforms."""

    META = "meta"
    TIKTOK = "tiktok"
    GOOGLE = "google"


class AdAccountStatus(str, Enum):
    """Ad account status."""

    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"


class AdAccountCreate(BaseModel):
    """Schema for binding a new ad account."""

    platform: AdPlatform
    platform_account_id: str = Field(..., min_length=1, max_length=255)
    account_name: str = Field(..., min_length=1, max_length=255)
    access_token: str = Field(..., min_length=1)
    refresh_token: str | None = None
    token_expires_at: datetime | None = None


class AdAccountUpdate(BaseModel):
    """Schema for updating an ad account."""

    account_name: str | None = Field(None, min_length=1, max_length=255)
    is_active: bool | None = None


class AdAccountResponse(BaseModel):
    """Ad account response schema."""

    id: int
    user_id: int
    platform: str
    platform_account_id: str
    account_name: str
    status: str
    is_active: bool
    token_expires_at: datetime | None = None
    created_at: datetime
    updated_at: datetime | None = None
    last_synced_at: datetime | None = None

    model_config = {"from_attributes": True}


class AdAccountListResponse(BaseModel):
    """Response for listing ad accounts."""

    items: list[AdAccountResponse]
    total: int


class AdAccountTokenRefreshResponse(BaseModel):
    """Response for token refresh operation."""

    success: bool
    message: str
    new_expires_at: datetime | None = None


class OAuthBindRequest(BaseModel):
    """Request to initiate OAuth binding for an ad platform."""

    platform: AdPlatform
    redirect_uri: str | None = None


class OAuthBindCallbackRequest(BaseModel):
    """OAuth callback request for ad account binding."""

    platform: AdPlatform
    code: str
    state: str | None = None
