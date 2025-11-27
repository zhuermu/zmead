"""MCP tools for ad account management.

Implements tools for managing ad accounts:
- get_ad_account_token: Get decrypted access token for an ad account
- list_ad_accounts: List all ad accounts for the user
- get_active_ad_account: Get the currently active ad account for a platform
- set_active_ad_account: Set an ad account as active
- refresh_ad_account_token: Manually trigger token refresh
"""

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.mcp.registry import tool
from app.mcp.types import MCPToolParameter
from app.services.ad_account import AdAccountService


@tool(
    name="list_ad_accounts",
    description="List all ad accounts bound to the user's account.",
    parameters=[],
    category="ad_account",
)
async def list_ad_accounts(
    user_id: int,
    db: AsyncSession,
) -> dict[str, Any]:
    """List all ad accounts for the user."""
    service = AdAccountService(db)
    accounts = await service.list_ad_accounts(user_id)

    # Convert to serializable format
    items = [
        {
            "id": acc.id,
            "user_id": acc.user_id,
            "platform": acc.platform,
            "platform_account_id": acc.platform_account_id,
            "account_name": acc.account_name,
            "status": acc.status,
            "is_active": acc.is_active,
            "token_expires_at": acc.token_expires_at.isoformat() if acc.token_expires_at else None,
            "created_at": acc.created_at.isoformat() if acc.created_at else None,
            "updated_at": acc.updated_at.isoformat() if acc.updated_at else None,
            "last_synced_at": acc.last_synced_at.isoformat() if acc.last_synced_at else None,
        }
        for acc in accounts
    ]

    return {
        "ad_accounts": items,
        "total": len(items),
    }


@tool(
    name="get_ad_account_token",
    description="Get the decrypted access token for an ad account. Used for making API calls to ad platforms.",
    parameters=[
        MCPToolParameter(
            name="ad_account_id",
            type="integer",
            description="ID of the ad account",
            required=True,
        ),
    ],
    category="ad_account",
)
async def get_ad_account_token(
    user_id: int,
    db: AsyncSession,
    ad_account_id: int,
) -> dict[str, Any]:
    """Get decrypted access token for an ad account."""
    service = AdAccountService(db)

    # Get account details first
    account = await service.get_ad_account(user_id, ad_account_id)
    if not account:
        raise ValueError(f"Ad account {ad_account_id} not found")

    # Check if token is expired
    if account.status == "expired":
        raise ValueError(f"Ad account {ad_account_id} token has expired. Please re-authorize.")

    # Get decrypted token
    access_token = await service.get_decrypted_access_token(user_id, ad_account_id)
    if not access_token:
        raise ValueError(f"Could not retrieve access token for ad account {ad_account_id}")

    return {
        "ad_account_id": ad_account_id,
        "platform": account.platform,
        "platform_account_id": account.platform_account_id,
        "access_token": access_token,
        "token_expires_at": account.token_expires_at.isoformat() if account.token_expires_at else None,
    }


@tool(
    name="get_active_ad_account",
    description="Get the currently active ad account for a specific platform.",
    parameters=[
        MCPToolParameter(
            name="platform",
            type="string",
            description="Ad platform",
            required=True,
            enum=["meta", "tiktok", "google"],
        ),
    ],
    category="ad_account",
)
async def get_active_ad_account(
    user_id: int,
    db: AsyncSession,
    platform: str,
) -> dict[str, Any]:
    """Get the active ad account for a platform."""
    service = AdAccountService(db)
    account = await service.get_active_ad_account(user_id, platform)

    if not account:
        return {
            "active_account": None,
            "platform": platform,
            "message": f"No active ad account for {platform}",
        }

    return {
        "active_account": {
            "id": account.id,
            "user_id": account.user_id,
            "platform": account.platform,
            "platform_account_id": account.platform_account_id,
            "account_name": account.account_name,
            "status": account.status,
            "is_active": account.is_active,
            "token_expires_at": account.token_expires_at.isoformat() if account.token_expires_at else None,
            "created_at": account.created_at.isoformat() if account.created_at else None,
            "last_synced_at": account.last_synced_at.isoformat() if account.last_synced_at else None,
        },
        "platform": platform,
    }


@tool(
    name="set_active_ad_account",
    description="Set an ad account as the active one for its platform. Only one account can be active per platform.",
    parameters=[
        MCPToolParameter(
            name="ad_account_id",
            type="integer",
            description="ID of the ad account to set as active",
            required=True,
        ),
    ],
    category="ad_account",
)
async def set_active_ad_account(
    user_id: int,
    db: AsyncSession,
    ad_account_id: int,
) -> dict[str, Any]:
    """Set an ad account as active."""
    service = AdAccountService(db)
    account = await service.set_active_ad_account(user_id, ad_account_id)

    if not account:
        raise ValueError(f"Ad account {ad_account_id} not found")

    return {
        "id": account.id,
        "platform": account.platform,
        "account_name": account.account_name,
        "is_active": account.is_active,
        "message": f"Ad account '{account.account_name}' is now active for {account.platform}",
    }


@tool(
    name="refresh_ad_account_token",
    description="Manually trigger a token refresh for an ad account. Use when token is about to expire.",
    parameters=[
        MCPToolParameter(
            name="ad_account_id",
            type="integer",
            description="ID of the ad account",
            required=True,
        ),
    ],
    category="ad_account",
)
async def refresh_ad_account_token(
    user_id: int,
    db: AsyncSession,
    ad_account_id: int,
) -> dict[str, Any]:
    """Trigger token refresh for an ad account."""
    service = AdAccountService(db)

    # Get account details
    account = await service.get_ad_account(user_id, ad_account_id)
    if not account:
        raise ValueError(f"Ad account {ad_account_id} not found")

    # Get refresh token
    refresh_token = await service.get_decrypted_refresh_token(user_id, ad_account_id)
    if not refresh_token:
        raise ValueError(f"No refresh token available for ad account {ad_account_id}. Please re-authorize.")

    # Note: Actual token refresh would require calling the platform's OAuth API
    # This is a placeholder that would be implemented with platform-specific logic
    # For now, we return the current status

    return {
        "ad_account_id": ad_account_id,
        "platform": account.platform,
        "status": account.status,
        "token_expires_at": account.token_expires_at.isoformat() if account.token_expires_at else None,
        "message": "Token refresh initiated. Check status for updates.",
        "note": "Actual refresh requires platform-specific OAuth implementation.",
    }


@tool(
    name="get_ad_account",
    description="Get details of a specific ad account by ID.",
    parameters=[
        MCPToolParameter(
            name="ad_account_id",
            type="integer",
            description="ID of the ad account",
            required=True,
        ),
    ],
    category="ad_account",
)
async def get_ad_account(
    user_id: int,
    db: AsyncSession,
    ad_account_id: int,
) -> dict[str, Any]:
    """Get ad account details."""
    service = AdAccountService(db)
    account = await service.get_ad_account(user_id, ad_account_id)

    if not account:
        raise ValueError(f"Ad account {ad_account_id} not found")

    return {
        "id": account.id,
        "user_id": account.user_id,
        "platform": account.platform,
        "platform_account_id": account.platform_account_id,
        "account_name": account.account_name,
        "status": account.status,
        "is_active": account.is_active,
        "token_expires_at": account.token_expires_at.isoformat() if account.token_expires_at else None,
        "created_at": account.created_at.isoformat() if account.created_at else None,
        "updated_at": account.updated_at.isoformat() if account.updated_at else None,
        "last_synced_at": account.last_synced_at.isoformat() if account.last_synced_at else None,
    }
