"""MCP tools for Google Ads campaign management.

Implements tools for creating and managing Google Ads campaigns via API:
- create_google_campaign: Create a new Google Ads campaign with budget
- create_google_ad_group: Create an ad group within a campaign
- create_google_ad: Create a responsive search ad
- update_google_campaign_status: Enable/pause/remove campaigns
"""

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.mcp.registry import tool
from app.mcp.types import MCPToolParameter
from app.services.ad_account import AdAccountService
from app.services.google_ads_campaign_service import get_google_ads_campaign_service


@tool(
    name="create_google_campaign",
    description="Create a new Google Ads campaign with budget. Returns campaign details. Campaign starts in PAUSED status for safety.",
    parameters=[
        MCPToolParameter(
            name="ad_account_id",
            type="integer",
            description="ID of the Google Ads account to create campaign in",
            required=True,
        ),
        MCPToolParameter(
            name="campaign_name",
            type="string",
            description="Name of the campaign",
            required=True,
        ),
        MCPToolParameter(
            name="daily_budget_usd",
            type="number",
            description="Daily budget in USD (max $1000 for safety)",
            required=True,
        ),
        MCPToolParameter(
            name="campaign_type",
            type="string",
            description="Campaign type: SEARCH, DISPLAY, VIDEO, SHOPPING, etc.",
            required=False,
            default="SEARCH",
            enum=["SEARCH", "DISPLAY", "VIDEO", "SHOPPING", "PERFORMANCE_MAX"],
        ),
        MCPToolParameter(
            name="start_date",
            type="string",
            description="Campaign start date in YYYY-MM-DD format (optional)",
            required=False,
        ),
        MCPToolParameter(
            name="end_date",
            type="string",
            description="Campaign end date in YYYY-MM-DD format (optional)",
            required=False,
        ),
    ],
    category="google_ads",
)
async def create_google_campaign(
    user_id: int,
    db: AsyncSession,
    ad_account_id: int,
    campaign_name: str,
    daily_budget_usd: float,
    campaign_type: str = "SEARCH",
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict[str, Any]:
    """Create a new Google Ads campaign."""
    try:
        # Get ad account with credentials
        ad_account_service = AdAccountService(db)
        ad_account = await ad_account_service.get_ad_account_model(user_id, ad_account_id)

        if not ad_account:
            return {
                "status": "error",
                "error": {
                    "code": "AD_ACCOUNT_NOT_FOUND",
                    "message": f"Ad account {ad_account_id} not found",
                },
            }

        if ad_account.platform != "google":
            return {
                "status": "error",
                "error": {
                    "code": "INVALID_PLATFORM",
                    "message": f"Account {ad_account_id} is not a Google Ads account",
                },
            }

        if ad_account.is_manager:
            return {
                "status": "error",
                "error": {
                    "code": "MANAGER_ACCOUNT_NOT_ALLOWED",
                    "message": "Cannot create campaigns on Manager accounts. Please select a client account.",
                },
            }

        # Get decrypted tokens
        access_token = ad_account_service._decrypt_token(ad_account.access_token_encrypted)
        refresh_token = (
            ad_account_service._decrypt_token(ad_account.refresh_token_encrypted)
            if ad_account.refresh_token_encrypted
            else None
        )

        if not access_token or not refresh_token:
            return {
                "status": "error",
                "error": {
                    "code": "INVALID_CREDENTIALS",
                    "message": "Ad account credentials are missing or invalid",
                },
            }

        # Create campaign
        campaign_service = get_google_ads_campaign_service()
        daily_budget_micros = int(daily_budget_usd * 1_000_000)

        result = await campaign_service.create_campaign(
            customer_id=ad_account.platform_account_id,
            access_token=access_token,
            refresh_token=refresh_token,
            campaign_name=campaign_name,
            daily_budget_micros=daily_budget_micros,
            campaign_type=campaign_type,
            start_date=start_date,
            end_date=end_date,
        )

        return {
            "status": "success",
            "data": result,
        }

    except ValueError as e:
        return {
            "status": "error",
            "error": {
                "code": "VALIDATION_ERROR",
                "message": str(e),
            },
        }
    except Exception as e:
        return {
            "status": "error",
            "error": {
                "code": "CAMPAIGN_CREATION_FAILED",
                "message": str(e),
            },
        }


@tool(
    name="create_google_ad_group",
    description="Create a new ad group within a Google Ads campaign",
    parameters=[
        MCPToolParameter(
            name="ad_account_id",
            type="integer",
            description="ID of the Google Ads account",
            required=True,
        ),
        MCPToolParameter(
            name="campaign_id",
            type="string",
            description="Google Ads campaign ID (from create_google_campaign)",
            required=True,
        ),
        MCPToolParameter(
            name="ad_group_name",
            type="string",
            description="Name of the ad group",
            required=True,
        ),
        MCPToolParameter(
            name="cpc_bid_usd",
            type="number",
            description="CPC bid in USD (optional)",
            required=False,
        ),
    ],
    category="google_ads",
)
async def create_google_ad_group(
    user_id: int,
    db: AsyncSession,
    ad_account_id: int,
    campaign_id: str,
    ad_group_name: str,
    cpc_bid_usd: float | None = None,
) -> dict[str, Any]:
    """Create a new ad group."""
    try:
        # Get ad account and credentials (same as create_campaign)
        ad_account_service = AdAccountService(db)
        ad_account = await ad_account_service.get_ad_account_model(user_id, ad_account_id)

        if not ad_account or ad_account.platform != "google":
            return {
                "status": "error",
                "error": {
                    "code": "AD_ACCOUNT_NOT_FOUND",
                    "message": f"Google Ads account {ad_account_id} not found",
                },
            }

        access_token = ad_account_service._decrypt_token(ad_account.access_token_encrypted)
        refresh_token = (
            ad_account_service._decrypt_token(ad_account.refresh_token_encrypted)
            if ad_account.refresh_token_encrypted
            else None
        )

        # Create ad group
        campaign_service = get_google_ads_campaign_service()
        cpc_bid_micros = int(cpc_bid_usd * 1_000_000) if cpc_bid_usd else None

        result = await campaign_service.create_ad_group(
            customer_id=ad_account.platform_account_id,
            access_token=access_token,
            refresh_token=refresh_token,
            campaign_id=campaign_id,
            ad_group_name=ad_group_name,
            cpc_bid_micros=cpc_bid_micros,
        )

        return {
            "status": "success",
            "data": result,
        }

    except Exception as e:
        return {
            "status": "error",
            "error": {
                "code": "AD_GROUP_CREATION_FAILED",
                "message": str(e),
            },
        }


@tool(
    name="create_google_responsive_search_ad",
    description="Create a responsive search ad in Google Ads. Requires 3-15 headlines (max 30 chars) and 2-4 descriptions (max 90 chars)",
    parameters=[
        MCPToolParameter(
            name="ad_account_id",
            type="integer",
            description="ID of the Google Ads account",
            required=True,
        ),
        MCPToolParameter(
            name="ad_group_id",
            type="string",
            description="Google Ads ad group ID (from create_google_ad_group)",
            required=True,
        ),
        MCPToolParameter(
            name="headlines",
            type="array",
            description="List of 3-15 headlines (max 30 characters each)",
            required=True,
        ),
        MCPToolParameter(
            name="descriptions",
            type="array",
            description="List of 2-4 descriptions (max 90 characters each)",
            required=True,
        ),
        MCPToolParameter(
            name="final_url",
            type="string",
            description="Landing page URL",
            required=True,
        ),
    ],
    category="google_ads",
)
async def create_google_responsive_search_ad(
    user_id: int,
    db: AsyncSession,
    ad_account_id: int,
    ad_group_id: str,
    headlines: list[str],
    descriptions: list[str],
    final_url: str,
) -> dict[str, Any]:
    """Create a responsive search ad."""
    try:
        # Get ad account and credentials
        ad_account_service = AdAccountService(db)
        ad_account = await ad_account_service.get_ad_account_model(user_id, ad_account_id)

        if not ad_account or ad_account.platform != "google":
            return {
                "status": "error",
                "error": {
                    "code": "AD_ACCOUNT_NOT_FOUND",
                    "message": f"Google Ads account {ad_account_id} not found",
                },
            }

        access_token = ad_account_service._decrypt_token(ad_account.access_token_encrypted)
        refresh_token = (
            ad_account_service._decrypt_token(ad_account.refresh_token_encrypted)
            if ad_account.refresh_token_encrypted
            else None
        )

        # Create ad
        campaign_service = get_google_ads_campaign_service()

        result = await campaign_service.create_responsive_search_ad(
            customer_id=ad_account.platform_account_id,
            access_token=access_token,
            refresh_token=refresh_token,
            ad_group_id=ad_group_id,
            headlines=headlines,
            descriptions=descriptions,
            final_url=final_url,
        )

        return {
            "status": "success",
            "data": result,
        }

    except Exception as e:
        return {
            "status": "error",
            "error": {
                "code": "AD_CREATION_FAILED",
                "message": str(e),
            },
        }


@tool(
    name="update_google_campaign_status",
    description="Update the status of a Google Ads campaign (ENABLED, PAUSED, or REMOVED)",
    parameters=[
        MCPToolParameter(
            name="ad_account_id",
            type="integer",
            description="ID of the Google Ads account",
            required=True,
        ),
        MCPToolParameter(
            name="campaign_id",
            type="string",
            description="Google Ads campaign ID",
            required=True,
        ),
        MCPToolParameter(
            name="status",
            type="string",
            description="New campaign status",
            required=True,
            enum=["ENABLED", "PAUSED", "REMOVED"],
        ),
    ],
    category="google_ads",
)
async def update_google_campaign_status(
    user_id: int,
    db: AsyncSession,
    ad_account_id: int,
    campaign_id: str,
    status: str,
) -> dict[str, Any]:
    """Update campaign status."""
    try:
        # Get ad account and credentials
        ad_account_service = AdAccountService(db)
        ad_account = await ad_account_service.get_ad_account_model(user_id, ad_account_id)

        if not ad_account or ad_account.platform != "google":
            return {
                "status": "error",
                "error": {
                    "code": "AD_ACCOUNT_NOT_FOUND",
                    "message": f"Google Ads account {ad_account_id} not found",
                },
            }

        access_token = ad_account_service._decrypt_token(ad_account.access_token_encrypted)
        refresh_token = (
            ad_account_service._decrypt_token(ad_account.refresh_token_encrypted)
            if ad_account.refresh_token_encrypted
            else None
        )

        # Update status
        campaign_service = get_google_ads_campaign_service()

        result = await campaign_service.update_campaign_status(
            customer_id=ad_account.platform_account_id,
            access_token=access_token,
            refresh_token=refresh_token,
            campaign_id=campaign_id,
            status=status,
        )

        return {
            "status": "success",
            "data": result,
        }

    except Exception as e:
        return {
            "status": "error",
            "error": {
                "code": "STATUS_UPDATE_FAILED",
                "message": str(e),
            },
        }
