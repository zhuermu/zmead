"""Report metrics schemas for request/response validation."""

from datetime import datetime
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, Field


class EntityType(str, Enum):
    """Entity types for report metrics."""

    CAMPAIGN = "campaign"
    ADSET = "adset"
    AD = "ad"


class MetricsCreate(BaseModel):
    """Schema for creating/saving metrics."""

    timestamp: datetime
    ad_account_id: int
    entity_type: EntityType
    entity_id: str = Field(..., min_length=1, max_length=255)
    entity_name: str = Field(..., min_length=1, max_length=255)
    impressions: int = Field(default=0, ge=0)
    clicks: int = Field(default=0, ge=0)
    spend: Decimal = Field(default=Decimal("0.00"), ge=0)
    conversions: int = Field(default=0, ge=0)
    revenue: Decimal = Field(default=Decimal("0.00"), ge=0)


class MetricsBatchCreate(BaseModel):
    """Schema for batch creating metrics."""

    metrics: list[MetricsCreate] = Field(..., min_length=1, max_length=1000)


class MetricsResponse(BaseModel):
    """Metrics response schema."""

    id: int
    timestamp: datetime
    user_id: int
    ad_account_id: int
    entity_type: str
    entity_id: str
    entity_name: str
    impressions: int
    clicks: int
    spend: Decimal
    conversions: int
    revenue: Decimal
    ctr: float
    cpc: Decimal
    cpa: Decimal
    roas: float
    created_at: datetime

    model_config = {"from_attributes": True}



class MetricsListResponse(BaseModel):
    """Response for listing metrics."""

    items: list[MetricsResponse]
    total: int
    page: int
    page_size: int
    has_more: bool


class MetricsFilter(BaseModel):
    """Filter options for listing metrics."""

    ad_account_id: int | None = None
    entity_type: EntityType | None = None
    entity_id: str | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None


class AggregatedMetrics(BaseModel):
    """Aggregated metrics response."""

    total_impressions: int = 0
    total_clicks: int = 0
    total_spend: Decimal = Decimal("0.00")
    total_conversions: int = 0
    total_revenue: Decimal = Decimal("0.00")
    avg_ctr: float = 0.0
    avg_cpc: Decimal = Decimal("0.00")
    avg_cpa: Decimal = Decimal("0.00")
    avg_roas: float = 0.0
    period_start: datetime | None = None
    period_end: datetime | None = None


class TrendDataPoint(BaseModel):
    """Single data point in trend data."""

    date: datetime
    impressions: int = 0
    clicks: int = 0
    spend: Decimal = Decimal("0.00")
    conversions: int = 0
    revenue: Decimal = Decimal("0.00")
    ctr: float = 0.0
    cpc: Decimal = Decimal("0.00")
    cpa: Decimal = Decimal("0.00")
    roas: float = 0.0


class TrendResponse(BaseModel):
    """Response for trend data."""

    data: list[TrendDataPoint]
    period_start: datetime
    period_end: datetime
    granularity: str  # 'daily', 'weekly', 'monthly'


class ArchivalResult(BaseModel):
    """Result of archival operation."""

    archived_count: int
    archived_before: datetime
    summary_created: bool
