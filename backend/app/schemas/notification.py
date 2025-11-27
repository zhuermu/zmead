"""Notification schemas for API requests and responses."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class NotificationType(str, Enum):
    """Notification urgency types."""

    URGENT = "urgent"
    IMPORTANT = "important"
    GENERAL = "general"


class NotificationCategory(str, Enum):
    """Notification categories."""

    TOKEN_EXPIRED = "token_expired"
    AD_REJECTED = "ad_rejected"
    CREDIT_LOW = "credit_low"
    CREDIT_DEPLETED = "credit_depleted"
    PAYMENT_SUCCESS = "payment_success"
    PAYMENT_FAILED = "payment_failed"
    REPORT_READY = "report_ready"
    CREATIVE_READY = "creative_ready"
    LANDING_PAGE_READY = "landing_page_ready"
    BUDGET_EXHAUSTED = "budget_exhausted"
    AD_PAUSED = "ad_paused"
    OPTIMIZATION_SUGGESTION = "optimization_suggestion"
    WEEKLY_SUMMARY = "weekly_summary"
    NEW_FEATURE = "new_feature"
    SYSTEM_MAINTENANCE = "system_maintenance"
    SYSTEM = "system"


class NotificationResponse(BaseModel):
    """Notification response schema."""

    id: int
    user_id: int
    type: str
    category: str
    title: str
    message: str
    action_url: str | None = None
    action_text: str | None = None
    is_read: bool
    read_at: datetime | None = None
    sent_via: list[str]
    extra_data: dict
    created_at: datetime

    model_config = {"from_attributes": True}


class NotificationListResponse(BaseModel):
    """Response for notification list endpoint."""

    notifications: list[NotificationResponse]
    total: int
    unread_count: int


class NotificationUnreadCountResponse(BaseModel):
    """Response for unread count endpoint."""

    unread_count: int


class NotificationMarkReadResponse(BaseModel):
    """Response for mark as read endpoint."""

    success: bool
    message: str


class NotificationMarkAllReadResponse(BaseModel):
    """Response for mark all as read endpoint."""

    success: bool
    marked_count: int
    message: str


class NotificationCreateRequest(BaseModel):
    """Request to create a notification (internal use)."""

    user_id: int
    type: NotificationType
    category: NotificationCategory
    title: str = Field(..., min_length=1, max_length=255)
    message: str = Field(..., min_length=1)
    action_url: str | None = Field(None, max_length=1024)
    action_text: str | None = Field(None, max_length=100)
    extra_data: dict | None = None
    send_email: bool = False


class NotificationPreferencesUpdate(BaseModel):
    """Request to update notification preferences."""

    email_enabled: bool | None = None
    in_app_enabled: bool | None = None
    credit_warning_threshold: int | None = Field(None, ge=0)
    credit_critical_threshold: int | None = Field(None, ge=0)
    # Per-category preferences
    category_preferences: dict[str, dict[str, bool]] | None = None
