"""MCP tools for report data management.

Implements tools for managing advertising performance data:
- get_reports: Get paginated metrics with filtering
- get_metrics: Get aggregated metrics for a time period
- save_metrics: Save metrics data from ad platforms
- analyze_performance: Get trend analysis data
"""

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.mcp.registry import tool
from app.mcp.types import MCPToolParameter
from app.schemas.report import EntityType, MetricsCreate, MetricsFilter
from app.services.report import ReportService


@tool(
    name="get_reports",
    description="Get paginated list of report metrics with optional filtering by ad account, entity type, entity ID, and date range.",
    parameters=[
        MCPToolParameter(
            name="page",
            type="integer",
            description="Page number (1-indexed)",
            required=False,
            default=1,
        ),
        MCPToolParameter(
            name="page_size",
            type="integer",
            description="Number of items per page (max 100)",
            required=False,
            default=20,
        ),
        MCPToolParameter(
            name="ad_account_id",
            type="integer",
            description="Filter by ad account ID",
            required=False,
        ),
        MCPToolParameter(
            name="entity_type",
            type="string",
            description="Filter by entity type",
            required=False,
            enum=["campaign", "adset", "ad"],
        ),
        MCPToolParameter(
            name="entity_id",
            type="string",
            description="Filter by entity ID",
            required=False,
        ),
        MCPToolParameter(
            name="start_date",
            type="string",
            description="Start date (ISO format: YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)",
            required=False,
        ),
        MCPToolParameter(
            name="end_date",
            type="string",
            description="End date (ISO format: YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)",
            required=False,
        ),
    ],
    category="report",
)
async def get_reports(
    user_id: int,
    db: AsyncSession,
    page: int = 1,
    page_size: int = 20,
    ad_account_id: int | None = None,
    entity_type: str | None = None,
    entity_id: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict[str, Any]:
    """Get paginated report metrics."""
    # Validate page_size
    page_size = min(page_size, 100)

    # Parse dates
    parsed_start = None
    parsed_end = None
    if start_date:
        parsed_start = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
    if end_date:
        parsed_end = datetime.fromisoformat(end_date.replace("Z", "+00:00"))

    # Build filter
    filters = MetricsFilter(
        ad_account_id=ad_account_id,
        entity_type=EntityType(entity_type) if entity_type else None,
        entity_id=entity_id,
        start_date=parsed_start,
        end_date=parsed_end,
    )

    service = ReportService(db)
    result = await service.get_metrics(
        user_id=user_id,
        filters=filters,
        page=page,
        page_size=page_size,
    )

    # Convert to serializable format
    metrics = [
        {
            "id": m.id,
            "timestamp": m.timestamp.isoformat() if m.timestamp else None,
            "user_id": m.user_id,
            "ad_account_id": m.ad_account_id,
            "entity_type": m.entity_type,
            "entity_id": m.entity_id,
            "entity_name": m.entity_name,
            "impressions": m.impressions,
            "clicks": m.clicks,
            "spend": str(m.spend),
            "conversions": m.conversions,
            "revenue": str(m.revenue),
            "ctr": m.ctr,
            "cpc": str(m.cpc),
            "cpa": str(m.cpa),
            "roas": m.roas,
            "created_at": m.created_at.isoformat() if m.created_at else None,
        }
        for m in result["metrics"]
    ]

    return {
        "metrics": metrics,
        "total": result["total"],
        "page": result["page"],
        "page_size": result["page_size"],
        "has_more": result["has_more"],
    }


@tool(
    name="get_metrics",
    description="Get aggregated metrics for a time period. Returns totals and averages for impressions, clicks, spend, conversions, revenue, CTR, CPC, CPA, and ROAS.",
    parameters=[
        MCPToolParameter(
            name="start_date",
            type="string",
            description="Start date (ISO format). Defaults to 7 days ago.",
            required=False,
        ),
        MCPToolParameter(
            name="end_date",
            type="string",
            description="End date (ISO format). Defaults to now.",
            required=False,
        ),
        MCPToolParameter(
            name="ad_account_id",
            type="integer",
            description="Filter by ad account ID",
            required=False,
        ),
        MCPToolParameter(
            name="entity_type",
            type="string",
            description="Filter by entity type",
            required=False,
            enum=["campaign", "adset", "ad"],
        ),
    ],
    category="report",
)
async def get_metrics(
    user_id: int,
    db: AsyncSession,
    start_date: str | None = None,
    end_date: str | None = None,
    ad_account_id: int | None = None,
    entity_type: str | None = None,
) -> dict[str, Any]:
    """Get aggregated metrics."""
    # Parse dates
    parsed_start = None
    parsed_end = None
    if start_date:
        parsed_start = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
    if end_date:
        parsed_end = datetime.fromisoformat(end_date.replace("Z", "+00:00"))

    service = ReportService(db)
    result = await service.get_aggregated_metrics(
        user_id=user_id,
        start_date=parsed_start,
        end_date=parsed_end,
        ad_account_id=ad_account_id,
        entity_type=EntityType(entity_type) if entity_type else None,
    )

    return {
        "total_impressions": result.total_impressions,
        "total_clicks": result.total_clicks,
        "total_spend": str(result.total_spend),
        "total_conversions": result.total_conversions,
        "total_revenue": str(result.total_revenue),
        "avg_ctr": result.avg_ctr,
        "avg_cpc": str(result.avg_cpc),
        "avg_cpa": str(result.avg_cpa),
        "avg_roas": result.avg_roas,
        "period_start": result.period_start.isoformat() if result.period_start else None,
        "period_end": result.period_end.isoformat() if result.period_end else None,
    }


@tool(
    name="save_metrics",
    description="Save metrics data from ad platforms. Used by Ad Performance module to store fetched data.",
    parameters=[
        MCPToolParameter(
            name="timestamp",
            type="string",
            description="Timestamp for the metrics (ISO format)",
            required=True,
        ),
        MCPToolParameter(
            name="ad_account_id",
            type="integer",
            description="Ad account ID",
            required=True,
        ),
        MCPToolParameter(
            name="entity_type",
            type="string",
            description="Entity type",
            required=True,
            enum=["campaign", "adset", "ad"],
        ),
        MCPToolParameter(
            name="entity_id",
            type="string",
            description="Entity ID from the ad platform",
            required=True,
        ),
        MCPToolParameter(
            name="entity_name",
            type="string",
            description="Entity name",
            required=True,
        ),
        MCPToolParameter(
            name="impressions",
            type="integer",
            description="Number of impressions",
            required=False,
            default=0,
        ),
        MCPToolParameter(
            name="clicks",
            type="integer",
            description="Number of clicks",
            required=False,
            default=0,
        ),
        MCPToolParameter(
            name="spend",
            type="number",
            description="Amount spent",
            required=False,
            default=0,
        ),
        MCPToolParameter(
            name="conversions",
            type="integer",
            description="Number of conversions",
            required=False,
            default=0,
        ),
        MCPToolParameter(
            name="revenue",
            type="number",
            description="Revenue generated",
            required=False,
            default=0,
        ),
    ],
    category="report",
)
async def save_metrics(
    user_id: int,
    db: AsyncSession,
    timestamp: str,
    ad_account_id: int,
    entity_type: str,
    entity_id: str,
    entity_name: str,
    impressions: int = 0,
    clicks: int = 0,
    spend: float = 0,
    conversions: int = 0,
    revenue: float = 0,
) -> dict[str, Any]:
    """Save metrics data."""
    # Parse timestamp
    parsed_timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))

    data = MetricsCreate(
        timestamp=parsed_timestamp,
        ad_account_id=ad_account_id,
        entity_type=EntityType(entity_type),
        entity_id=entity_id,
        entity_name=entity_name,
        impressions=impressions,
        clicks=clicks,
        spend=Decimal(str(spend)),
        conversions=conversions,
        revenue=Decimal(str(revenue)),
    )

    service = ReportService(db)
    metrics = await service.save_metrics(user_id, data)

    return {
        "id": metrics.id,
        "timestamp": metrics.timestamp.isoformat() if metrics.timestamp else None,
        "user_id": metrics.user_id,
        "ad_account_id": metrics.ad_account_id,
        "entity_type": metrics.entity_type,
        "entity_id": metrics.entity_id,
        "entity_name": metrics.entity_name,
        "impressions": metrics.impressions,
        "clicks": metrics.clicks,
        "spend": str(metrics.spend),
        "conversions": metrics.conversions,
        "revenue": str(metrics.revenue),
        "ctr": metrics.ctr,
        "cpc": str(metrics.cpc),
        "cpa": str(metrics.cpa),
        "roas": metrics.roas,
        "created_at": metrics.created_at.isoformat() if metrics.created_at else None,
    }


@tool(
    name="analyze_performance",
    description="Get trend analysis data aggregated by time period. Returns time series data for performance metrics.",
    parameters=[
        MCPToolParameter(
            name="start_date",
            type="string",
            description="Start date (ISO format). Defaults to 7 days ago.",
            required=False,
        ),
        MCPToolParameter(
            name="end_date",
            type="string",
            description="End date (ISO format). Defaults to now.",
            required=False,
        ),
        MCPToolParameter(
            name="ad_account_id",
            type="integer",
            description="Filter by ad account ID",
            required=False,
        ),
        MCPToolParameter(
            name="granularity",
            type="string",
            description="Time granularity for aggregation",
            required=False,
            default="daily",
            enum=["daily", "weekly", "monthly"],
        ),
    ],
    category="report",
)
async def analyze_performance(
    user_id: int,
    db: AsyncSession,
    start_date: str | None = None,
    end_date: str | None = None,
    ad_account_id: int | None = None,
    granularity: str = "daily",
) -> dict[str, Any]:
    """Get trend analysis data."""
    # Parse dates
    parsed_start = None
    parsed_end = None
    if start_date:
        parsed_start = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
    if end_date:
        parsed_end = datetime.fromisoformat(end_date.replace("Z", "+00:00"))

    service = ReportService(db)
    trend_data = await service.get_trend_data(
        user_id=user_id,
        start_date=parsed_start,
        end_date=parsed_end,
        ad_account_id=ad_account_id,
        granularity=granularity,
    )

    # Convert to serializable format
    data_points = [
        {
            "date": point.date.isoformat() if point.date else None,
            "impressions": point.impressions,
            "clicks": point.clicks,
            "spend": str(point.spend),
            "conversions": point.conversions,
            "revenue": str(point.revenue),
            "ctr": point.ctr,
            "cpc": str(point.cpc),
            "cpa": str(point.cpa),
            "roas": point.roas,
        }
        for point in trend_data
    ]

    return {
        "data": data_points,
        "granularity": granularity,
        "period_start": parsed_start.isoformat() if parsed_start else None,
        "period_end": parsed_end.isoformat() if parsed_end else None,
    }
