"""Authentication schemas."""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, EmailStr, Field


class TokenResponse(BaseModel):
    """JWT token response."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = Field(description="Access token expiration in seconds")


class TokenRefreshRequest(BaseModel):
    """Token refresh request."""

    refresh_token: str


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
    conversational_provider: str = "gemini"
    conversational_model: str = "gemini-2.5-flash"
    is_active: bool
    is_approved: bool = False
    is_super_admin: bool = False  # Computed field, not stored in DB
    created_at: datetime
    last_login_at: datetime | None = None

    model_config = {"from_attributes": True}


class OAuthCallbackRequest(BaseModel):
    """OAuth callback request with authorization code."""

    code: str
    state: str | None = None


class GoogleUserInfo(BaseModel):
    """Google OAuth user info response."""

    id: str
    email: EmailStr
    name: str
    picture: str | None = None
    verified_email: bool = False


class AuthResponse(BaseModel):
    """Authentication response with tokens and user info."""

    tokens: TokenResponse
    user: UserResponse
