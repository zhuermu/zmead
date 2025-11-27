"""MCP tools for campaign management.

Implements tools for managing advertising campaigns:
- get_campaigns: List campaigns with filtering
- get_campaign: Get single campaign details
- create_campaign: Create a new campaign
- update_campaign: Update campaign settings
- delete_campaign: Delete a campaign
- sync_campaign: Sync campaign to ad platform
"""

from decimal import Decimal
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.mcp.registry import tool
from app.mcp.types import MCPToolParameter
from app.schemas.campaign import (
    AdPlatform,
    BudgetType,
    CampaignCreate,
    CampaignFilter,
    CampaignObjective,
    CampaignStatus,
    CampaignUpdate,
)
from app.services.campaign import (
    AdAccountNotActiveError,
    AdAccountNotFoundError,
    CampaignNotFoundError,
    CampaignService,
)


@tool(
    name="get_campaigns",
    description="Get a paginated list of campaigns for the current user. Supports filtering by platform, status, and ad account.",
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
            name="platform",
            type="string",
            description="Filter by ad platform",
            required=False,
            enum=["meta", "tiktok", "google"],
        ),
        MCPToolParameter(
            name="status",
            type="string",
            description="Filter by status",
            required=False,
            enum=["draft", "active", "paused", "deleted"],
        ),
        MCPToolParameter(
            name="ad_account_id",
            type="integer",
            description="Filter by ad account ID",
            required=False,
        ),
    ],
    category="campaign",
)
async def get_campaigns(
    user_id: int,
    db: AsyncSession,
    page: int = 1,
    page_size: int = 20,
    platform: str | None = None,
    status: str | None = None,
    ad_account_id: int | None = None,
) -> dict[str, Any]:
    """Get list of campaigns."""
    # Validate page_size
    page_size = min(page_size, 100)

    # Build filter
    filters = CampaignFilter(
        platform=AdPlatform(platform) if platform else None,
        status=CampaignStatus(status) if status else None,
        ad_account_id=ad_account_id,
    )

    service = CampaignService(db)
    result = await service.get_list(
        user_id=user_id,
        filters=filters,
        page=page,
        page_size=page_size,
    )

    # Convert to serializable format
    campaigns = [
        {
            "id": c.id,
            "user_id": c.user_id,
            "ad_account_id": c.ad_account_id,
            "platform": c.platform,
            "platform_campaign_id": c.platform_campaign_id,
            "name": c.name,
            "objective": c.objective,
            "status": c.status,
            "budget": str(c.budget),
            "budget_type": c.budget_type,
            "targeting": c.targeting or {},
            "creative_ids": c.creative_ids or [],
            "landing_page_id": c.landing_page_id,
            "created_at": c.created_at.isoformat() if c.created_at else None,
            "updated_at": c.updated_at.isoformat() if c.updated_at else None,
        }
        for c in result["campaigns"]
    ]

    return {
        "campaigns": campaigns,
        "total": result["total"],
        "page": result["page"],
        "page_size": result["page_size"],
        "has_more": result["has_more"],
    }


@tool(
    name="get_campaign",
    description="Get details of a specific campaign by ID.",
    parameters=[
        MCPToolParameter(
            name="campaign_id",
            type="integer",
            description="ID of the campaign to retrieve",
            required=True,
        ),
    ],
    category="campaign",
)
async def get_campaign(
    user_id: int,
    db: AsyncSession,
    campaign_id: int,
) -> dict[str, Any]:
    """Get a single campaign by ID."""
    service = CampaignService(db)
    campaign = await service.get_by_id(campaign_id, user_id)

    if not campaign:
        raise ValueError(f"Campaign {campaign_id} not found")

    return {
        "id": campaign.id,
        "user_id": campaign.user_id,
        "ad_account_id": campaign.ad_account_id,
        "platform": campaign.platform,
        "platform_campaign_id": campaign.platform_campaign_id,
        "name": campaign.name,
        "objective": campaign.objective,
        "status": campaign.status,
        "budget": str(campaign.budget),
        "budget_type": campaign.budget_type,
        "targeting": campaign.targeting or {},
        "creative_ids": campaign.creative_ids or [],
        "landing_page_id": campaign.landing_page_id,
        "created_at": campaign.created_at.isoformat() if campaign.created_at else None,
        "updated_at": campaign.updated_at.isoformat() if campaign.updated_at else None,
    }


@tool(
    name="create_campaign",
    description="Create a new advertising campaign. Requires an active ad account.",
    parameters=[
        MCPToolParameter(
            name="ad_account_id",
            type="integer",
            description="Ad account ID to use for this campaign",
            required=True,
        ),
        MCPToolParameter(
            name="name",
            type="string",
            description="Campaign name",
            required=True,
        ),
        MCPToolParameter(
            name="objective",
            type="string",
            description="Campaign objective",
            required=True,
            enum=["awareness", "traffic", "engagement", "leads", "conversions", "sales"],
        ),
        MCPToolParameter(
            name="budget",
            type="number",
            description="Campaign budget amount",
            required=True,
        ),
        MCPToolParameter(
            name="budget_type",
            type="string",
            description="Budget type",
            required=False,
            default="daily",
            enum=["daily", "lifetime"],
        ),
        MCPToolParameter(
            name="targeting",
            type="object",
            description="Targeting configuration (audience, locations, etc.)",
            required=False,
        ),
        MCPToolParameter(
            name="creative_ids",
            type="array",
            description="List of creative IDs to use in this campaign",
            required=False,
        ),
        MCPToolParameter(
            name="landing_page_id",
            type="integer",
            description="Landing page ID to use",
            required=False,
        ),
    ],
    category="campaign",
)
async def create_campaign(
    user_id: int,
    db: AsyncSession,
    ad_account_id: int,
    name: str,
    objective: str,
    budget: float,
    budget_type: str = "daily",
    targeting: dict | None = None,
    creative_ids: list[int] | None = None,
    landing_page_id: int | None = None,
) -> dict[str, Any]:
    """Create a new campaign."""
    data = CampaignCreate(
        ad_account_id=ad_account_id,
        name=name,
        objective=CampaignObjective(objective),
        budget=Decimal(str(budget)),
        budget_type=BudgetType(budget_type),
        targeting=targeting or {},
        creative_ids=creative_ids or [],
        landing_page_id=landing_page_id,
    )

    service = CampaignService(db)
    try:
        campaign = await service.create(user_id, data)
    except AdAccountNotFoundError:
        raise ValueError(f"Ad account {ad_account_id} not found")
    except AdAccountNotActiveError:
        raise ValueError(f"Ad account {ad_account_id} is not active")

    return {
        "id": campaign.id,
        "user_id": campaign.user_id,
        "ad_account_id": campaign.ad_account_id,
        "platform": campaign.platform,
        "name": campaign.name,
        "objective": campaign.objective,
        "status": campaign.status,
        "budget": str(campaign.budget),
        "budget_type": campaign.budget_type,
        "targeting": campaign.targeting or {},
        "creative_ids": campaign.creative_ids or [],
        "landing_page_id": campaign.landing_page_id,
        "created_at": campaign.created_at.isoformat() if campaign.created_at else None,
    }


@tool(
    name="update_campaign",
    description="Update an existing campaign's settings.",
    parameters=[
        MCPToolParameter(
            name="campaign_id",
            type="integer",
            description="ID of the campaign to update",
            required=True,
        ),
        MCPToolParameter(
            name="name",
            type="string",
            description="New campaign name",
            required=False,
        ),
        MCPToolParameter(
            name="objective",
            type="string",
            description="New campaign objective",
            required=False,
            enum=["awareness", "traffic", "engagement", "leads", "conversions", "sales"],
        ),
        MCPToolParameter(
            name="status",
            type="string",
            description="New campaign status",
            required=False,
            enum=["draft", "active", "paused"],
        ),
        MCPToolParameter(
            name="budget",
            type="number",
            description="New budget amount",
            required=False,
        ),
        MCPToolParameter(
            name="budget_type",
            type="string",
            description="New budget type",
            required=False,
            enum=["daily", "lifetime"],
        ),
        MCPToolParameter(
            name="targeting",
            type="object",
            description="New targeting configuration",
            required=False,
        ),
        MCPToolParameter(
            name="creative_ids",
            type="array",
            description="New list of creative IDs",
            required=False,
        ),
        MCPToolParameter(
            name="landing_page_id",
            type="integer",
            description="New landing page ID",
            required=False,
        ),
    ],
    category="campaign",
)
async def update_campaign(
    user_id: int,
    db: AsyncSession,
    campaign_id: int,
    name: str | None = None,
    objective: str | None = None,
    status: str | None = None,
    budget: float | None = None,
    budget_type: str | None = None,
    targeting: dict | None = None,
    creative_ids: list[int] | None = None,
    landing_page_id: int | None = None,
) -> dict[str, Any]:
    """Update a campaign."""
    # Build update data with only provided fields
    update_data = {}
    if name is not None:
        update_data["name"] = name
    if objective is not None:
        update_data["objective"] = CampaignObjective(objective)
    if status is not None:
        update_data["status"] = CampaignStatus(status)
    if budget is not None:
        update_data["budget"] = Decimal(str(budget))
    if budget_type is not None:
        update_data["budget_type"] = BudgetType(budget_type)
    if targeting is not None:
        update_data["targeting"] = targeting
    if creative_ids is not None:
        update_data["creative_ids"] = creative_ids
    if landing_page_id is not None:
        update_data["landing_page_id"] = landing_page_id

    if not update_data:
        raise ValueError("No fields to update")

    data = CampaignUpdate(**update_data)

    service = CampaignService(db)
    try:
        campaign = await service.update(campaign_id, user_id, data)
    except CampaignNotFoundError:
        raise ValueError(f"Campaign {campaign_id} not found")

    return {
        "id": campaign.id,
        "user_id": campaign.user_id,
        "ad_account_id": campaign.ad_account_id,
        "platform": campaign.platform,
        "platform_campaign_id": campaign.platform_campaign_id,
        "name": campaign.name,
        "objective": campaign.objective,
        "status": campaign.status,
        "budget": str(campaign.budget),
        "budget_type": campaign.budget_type,
        "targeting": campaign.targeting or {},
        "creative_ids": campaign.creative_ids or [],
        "landing_page_id": campaign.landing_page_id,
        "created_at": campaign.created_at.isoformat() if campaign.created_at else None,
        "updated_at": campaign.updated_at.isoformat() if campaign.updated_at else None,
    }


@tool(
    name="delete_campaign",
    description="Delete a campaign. Performs a soft delete (marks as deleted) to preserve history.",
    parameters=[
        MCPToolParameter(
            name="campaign_id",
            type="integer",
            description="ID of the campaign to delete",
            required=True,
        ),
    ],
    category="campaign",
)
async def delete_campaign(
    user_id: int,
    db: AsyncSession,
    campaign_id: int,
) -> dict[str, Any]:
    """Delete a campaign."""
    service = CampaignService(db)
    try:
        await service.delete(campaign_id, user_id)
    except CampaignNotFoundError:
        raise ValueError(f"Campaign {campaign_id} not found")

    return {
        "deleted": True,
        "campaign_id": campaign_id,
    }


@tool(
    name="sync_campaign",
    description="Sync a campaign to its ad platform. Creates or updates the campaign on Meta/TikTok/Google.",
    parameters=[
        MCPToolParameter(
            name="campaign_id",
            type="integer",
            description="ID of the campaign to sync",
            required=True,
        ),
    ],
    category="campaign",
)
async def sync_campaign(
    user_id: int,
    db: AsyncSession,
    campaign_id: int,
) -> dict[str, Any]:
    """Sync campaign to ad platform."""
    service = CampaignService(db)
    try:
        result = await service.sync_to_platform(campaign_id, user_id)
    except CampaignNotFoundError:
        raise ValueError(f"Campaign {campaign_id} not found")

    return {
        "success": result.success,
        "platform_campaign_id": result.platform_campaign_id,
        "error_message": result.error_message,
        "error_code": result.error_code,
    }
