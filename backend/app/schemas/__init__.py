"""Pydantic schemas."""

from app.schemas.ad_account import (
    AdAccountCreate,
    AdAccountListResponse,
    AdAccountResponse,
    AdAccountStatus,
    AdAccountTokenRefreshResponse,
    AdAccountUpdate,
    AdPlatform,
    OAuthBindCallbackRequest,
    OAuthBindRequest,
)
from app.schemas.auth import (
    AuthResponse,
    GoogleUserInfo,
    OAuthCallbackRequest,
    TokenRefreshRequest,
    TokenResponse,
)
from app.schemas.auth import (
    UserResponse as AuthUserResponse,
)
from app.schemas.campaign import (
    AdPlatform as CampaignAdPlatform,
)
from app.schemas.campaign import (
    BudgetType,
    CampaignCreate,
    CampaignFilter,
    CampaignListResponse,
    CampaignObjective,
    CampaignResponse,
    CampaignStatus,
    CampaignUpdate,
    PlatformSyncResult,
)
from app.schemas.creative import (
    CreativeCreate,
    CreativeFilter,
    CreativeListResponse,
    CreativeResponse,
    CreativeStatus,
    CreativeUpdate,
    FileType,
    PresignedUploadUrlRequest,
    PresignedUploadUrlResponse,
)
from app.schemas.credit import (
    CreditBalanceResponse,
    CreditDeductRequest,
    CreditHistoryResponse,
    CreditRefundRequest,
    CreditTransactionResponse,
    OperationType,
    TransactionType,
)
from app.schemas.landing_page import (
    LandingPageCreate,
    LandingPageFilter,
    LandingPageListResponse,
    LandingPagePublishResponse,
    LandingPageResponse,
    LandingPageStatus,
    LandingPageUpdate,
)
from app.schemas.report import (
    AggregatedMetrics,
    ArchivalResult,
    EntityType,
    MetricsBatchCreate,
    MetricsCreate,
    MetricsFilter,
    MetricsListResponse,
    MetricsResponse,
    TrendDataPoint,
    TrendResponse,
)
from app.schemas.user import (
    NotificationPreferences,
    UserDeleteRequest,
    UserResponse,
    UserUpdateRequest,
)

__all__ = [
    # Ad Account schemas
    "AdAccountCreate",
    "AdAccountListResponse",
    "AdAccountResponse",
    "AdAccountStatus",
    "AdAccountTokenRefreshResponse",
    "AdAccountUpdate",
    "AdPlatform",
    "OAuthBindCallbackRequest",
    "OAuthBindRequest",
    # Auth schemas
    "AuthResponse",
    "GoogleUserInfo",
    "OAuthCallbackRequest",
    "TokenRefreshRequest",
    "TokenResponse",
    "AuthUserResponse",
    # Campaign schemas
    "BudgetType",
    "CampaignAdPlatform",
    "CampaignCreate",
    "CampaignFilter",
    "CampaignListResponse",
    "CampaignObjective",
    "CampaignResponse",
    "CampaignStatus",
    "CampaignUpdate",
    "PlatformSyncResult",
    # Creative schemas
    "CreativeCreate",
    "CreativeFilter",
    "CreativeListResponse",
    "CreativeResponse",
    "CreativeStatus",
    "CreativeUpdate",
    "FileType",
    "PresignedUploadUrlRequest",
    "PresignedUploadUrlResponse",
    # Credit schemas
    "CreditBalanceResponse",
    "CreditDeductRequest",
    "CreditHistoryResponse",
    "CreditRefundRequest",
    "CreditTransactionResponse",
    "OperationType",
    "TransactionType",
    # Landing Page schemas
    "LandingPageCreate",
    "LandingPageFilter",
    "LandingPageListResponse",
    "LandingPagePublishResponse",
    "LandingPageResponse",
    "LandingPageStatus",
    "LandingPageUpdate",
    # Report schemas
    "AggregatedMetrics",
    "ArchivalResult",
    "EntityType",
    "MetricsBatchCreate",
    "MetricsCreate",
    "MetricsFilter",
    "MetricsListResponse",
    "MetricsResponse",
    "TrendDataPoint",
    "TrendResponse",
    # User schemas
    "NotificationPreferences",
    "UserDeleteRequest",
    "UserResponse",
    "UserUpdateRequest",
]
