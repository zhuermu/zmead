"""Campaign schemas for request/response validation."""

from datetime import datetime
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, Field


class CampaignStatus(str, Enum):
    """Campaign status."""

    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    DELETED = "deleted"


class BudgetType(str, Enum):
    """Budget type."""

    DAILY = "daily"
    LIFETIME = "lifetime"


class CampaignObjective(str, Enum):
    """Campaign objective types."""

    AWARENESS = "awareness"
    TRAFFIC = "traffic"
    ENGAGEMENT = "engagement"
    LEADS = "leads"
    CONVERSIONS = "conversions"
    SALES = "sales"


class AdPlatform(str, Enum):
    """Supported ad platforms."""

    META = "meta"
    TIKTOK = "tiktok"
    GOOGLE = "google"


class CampaignCreate(BaseModel):
    """Schema for creating a new campaign."""

    ad_account_id: int = Field(..., description="Ad account ID to use for this campaign")
    name: str = Field(..., min_length=1, max_length=255)
    objective: CampaignObjective
    budget: Decimal = Field(..., gt=0, decimal_places=2)
    budget_type: BudgetType = BudgetType.DAILY
    targeting: dict = Field(default_factory=dict)
    creative_ids: list[int] = Field(default_factory=list)
    landing_page_id: int | None = None



class CampaignUpdate(BaseModel):
    """Schema for updating a campaign."""

    name: str | None = Field(None, min_length=1, max_length=255)
    objective: CampaignObjective | None = None
    status: CampaignStatus | None = None
    budget: Decimal | None = Field(None, gt=0, decimal_places=2)
    budget_type: BudgetType | None = None
    targeting: dict | None = None
    creative_ids: list[int] | None = None
    landing_page_id: int | None = None


class CampaignResponse(BaseModel):
    """Campaign response schema."""

    id: int
    user_id: int = Field(..., serialization_alias="userId")
    ad_account_id: int = Field(..., serialization_alias="adAccountId")
    platform: str
    platform_campaign_id: str | None = Field(None, serialization_alias="platformCampaignId")
    name: str
    objective: str
    status: str
    budget: Decimal
    budget_type: str = Field(..., serialization_alias="budgetType")
    targeting: dict = {}
    creative_ids: list[int] = Field(default_factory=list, serialization_alias="creativeIds")
    landing_page_id: int | None = Field(None, serialization_alias="landingPageId")
    created_at: datetime = Field(..., serialization_alias="createdAt")
    updated_at: datetime | None = Field(None, serialization_alias="updatedAt")

    model_config = {"from_attributes": True, "populate_by_name": True}


class CampaignListResponse(BaseModel):
    """Response for listing campaigns."""

    items: list[CampaignResponse]
    total: int
    page: int
    page_size: int
    has_more: bool


class CampaignFilter(BaseModel):
    """Filter options for listing campaigns."""

    platform: AdPlatform | None = None
    status: CampaignStatus | None = None
    ad_account_id: int | None = None


class PlatformSyncResult(BaseModel):
    """Result of syncing campaign to ad platform."""

    success: bool
    platform_campaign_id: str | None = None
    error_message: str | None = None
    error_code: str | None = None
