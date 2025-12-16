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
    is_manager: bool = False
    manager_account_id: str | None = None


class AdAccountUpdate(BaseModel):
    """Schema for updating an ad account."""

    account_name: str | None = Field(None, min_length=1, max_length=255)
    is_active: bool | None = None


class AdAccountResponse(BaseModel):
    """Ad account response schema."""

    id: int
    user_id: int
    platform: str
    platform_account_id: str = Field(..., serialization_alias="platformAccountId")
    account_name: str = Field(..., serialization_alias="accountName")
    status: str
    is_active: bool = Field(..., serialization_alias="isActive")
    is_manager: bool = Field(default=False, serialization_alias="isManager")
    manager_account_id: str | None = Field(None, serialization_alias="managerAccountId")
    token_expires_at: datetime | None = Field(None, serialization_alias="tokenExpiresAt")
    created_at: datetime = Field(..., serialization_alias="createdAt")
    updated_at: datetime | None = Field(None, serialization_alias="updatedAt")
    last_synced_at: datetime | None = Field(None, serialization_alias="lastSyncedAt")

    model_config = {"from_attributes": True, "populate_by_name": True}


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


class AvailableAdAccount(BaseModel):
    """Available ad account from OAuth provider."""

    id: str = Field(..., description="Platform account ID")
    name: str = Field(..., description="Account name")
    currency: str | None = Field(None, description="Account currency")
    timezone: str | None = Field(None, description="Account timezone")
    is_manager: bool = Field(False, serialization_alias="isManager", description="Whether this is a manager account")
    manager_id: str | None = Field(None, serialization_alias="managerId", description="Parent manager account ID if applicable")

    model_config = {"from_attributes": True, "populate_by_name": True}


class OAuthAvailableAccountsRequest(BaseModel):
    """Request to get available accounts from OAuth."""

    platform: AdPlatform
    code: str
    state: str | None = None
    redirect_uri: str | None = None


class OAuthAvailableAccountsResponse(BaseModel):
    """Response with available accounts from OAuth provider."""

    accounts: list[AvailableAdAccount]
    total: int
    session_token: str = Field(..., description="Temporary session token for binding selected accounts")


class OAuthSelectAccountsRequest(BaseModel):
    """Request to bind selected accounts after OAuth."""

    platform: AdPlatform
    session_token: str = Field(..., description="Session token from available-accounts response")
    selected_account_ids: list[str] = Field(..., description="List of account IDs to bind")
