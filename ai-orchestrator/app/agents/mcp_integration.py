"""MCP integration for sub-agents.

This module provides MCP client integration for sub-agents to communicate
with the Backend (Web Platform) for data persistence and retrieval.

Requirements: 需求 11 (MCP 通信)
"""

from typing import Any

import structlog

from app.services.mcp_client import MCPClient, MCPError

logger = structlog.get_logger(__name__)


class AgentMCPClient:
    """MCP client wrapper for agent operations.

    Provides typed methods for common MCP operations used by agents.
    """

    def __init__(self):
        self._mcp_client: MCPClient | None = None

    def _get_mcp_client(self) -> MCPClient:
        """Get or create MCP client."""
        if self._mcp_client is None:
            self._mcp_client = MCPClient()
        return self._mcp_client

    async def close(self):
        """Close MCP client."""
        if self._mcp_client:
            await self._mcp_client.close()
            self._mcp_client = None

    # =========================================================================
    # Creative Operations
    # =========================================================================

    async def create_creative(
        self,
        user_id: str,
        url: str,
        filename: str,
        style: str | None = None,
        score: int | None = None,
        analysis: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Save a creative to the asset library.

        Args:
            user_id: User identifier
            url: Public URL of the creative
            filename: Original filename
            style: Creative style
            score: Quality score
            analysis: AI analysis results

        Returns:
            Created creative data with ID
        """
        log = logger.bind(user_id=user_id, filename=filename)
        log.info("mcp_create_creative")

        try:
            client = self._get_mcp_client()
            result = await client.call_tool(
                "create_creative",
                {
                    "user_id": user_id,
                    "url": url,
                    "filename": filename,
                    "style": style,
                    "score": score,
                    "analysis": analysis,
                },
            )
            log.info("mcp_create_creative_success", creative_id=result.get("id"))
            return result
        except MCPError as e:
            log.error("mcp_create_creative_error", error=str(e))
            raise

    async def get_creatives(
        self,
        user_id: str,
        limit: int = 20,
        offset: int = 0,
        style: str | None = None,
    ) -> dict[str, Any]:
        """Get user's creatives from asset library.

        Args:
            user_id: User identifier
            limit: Max items to return
            offset: Pagination offset
            style: Filter by style

        Returns:
            List of creatives with pagination info
        """
        client = self._get_mcp_client()
        return await client.call_tool(
            "get_creatives",
            {
                "user_id": user_id,
                "limit": limit,
                "offset": offset,
                "style": style,
            },
        )

    # =========================================================================
    # Campaign Operations
    # =========================================================================

    async def create_campaign(
        self,
        user_id: str,
        platform: str,
        name: str,
        daily_budget: float,
        target_roas: float | None = None,
        target_cpa: float | None = None,
        creative_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        """Create an ad campaign.

        Args:
            user_id: User identifier
            platform: Ad platform (meta, tiktok, google)
            name: Campaign name
            daily_budget: Daily budget in USD
            target_roas: Target ROAS
            target_cpa: Target CPA
            creative_ids: Creative IDs to use

        Returns:
            Created campaign data
        """
        log = logger.bind(user_id=user_id, platform=platform)
        log.info("mcp_create_campaign")

        try:
            client = self._get_mcp_client()
            result = await client.call_tool(
                "create_campaign",
                {
                    "user_id": user_id,
                    "platform": platform,
                    "name": name,
                    "daily_budget": daily_budget,
                    "target_roas": target_roas,
                    "target_cpa": target_cpa,
                    "creative_ids": creative_ids,
                },
            )
            log.info("mcp_create_campaign_success", campaign_id=result.get("id"))
            return result
        except MCPError as e:
            log.error("mcp_create_campaign_error", error=str(e))
            raise

    async def update_campaign(
        self,
        user_id: str,
        campaign_id: str,
        updates: dict[str, Any],
    ) -> dict[str, Any]:
        """Update a campaign.

        Args:
            user_id: User identifier
            campaign_id: Campaign to update
            updates: Fields to update

        Returns:
            Updated campaign data
        """
        client = self._get_mcp_client()
        return await client.call_tool(
            "update_campaign",
            {
                "user_id": user_id,
                "campaign_id": campaign_id,
                **updates,
            },
        )

    async def pause_campaign(
        self,
        user_id: str,
        campaign_id: str,
    ) -> dict[str, Any]:
        """Pause a campaign.

        Args:
            user_id: User identifier
            campaign_id: Campaign to pause

        Returns:
            Updated campaign status
        """
        client = self._get_mcp_client()
        return await client.call_tool(
            "pause_campaign",
            {
                "user_id": user_id,
                "campaign_id": campaign_id,
            },
        )

    async def resume_campaign(
        self,
        user_id: str,
        campaign_id: str,
    ) -> dict[str, Any]:
        """Resume a paused campaign.

        Args:
            user_id: User identifier
            campaign_id: Campaign to resume

        Returns:
            Updated campaign status
        """
        client = self._get_mcp_client()
        return await client.call_tool(
            "resume_campaign",
            {
                "user_id": user_id,
                "campaign_id": campaign_id,
            },
        )

    # =========================================================================
    # Performance / Report Operations
    # =========================================================================

    async def get_reports(
        self,
        user_id: str,
        platform: str | None = None,
        date_range: dict[str, str] | None = None,
        campaign_id: str | None = None,
    ) -> dict[str, Any]:
        """Get ad performance reports.

        Args:
            user_id: User identifier
            platform: Filter by platform
            date_range: Date range {start_date, end_date}
            campaign_id: Filter by campaign

        Returns:
            Report data with metrics
        """
        log = logger.bind(user_id=user_id, platform=platform)
        log.info("mcp_get_reports")

        client = self._get_mcp_client()
        return await client.call_tool(
            "get_reports",
            {
                "user_id": user_id,
                "platform": platform,
                "date_range": date_range,
                "campaign_id": campaign_id,
            },
        )

    async def save_metrics(
        self,
        user_id: str,
        platform: str,
        date: str,
        metrics: dict[str, Any],
    ) -> dict[str, Any]:
        """Save performance metrics.

        Args:
            user_id: User identifier
            platform: Ad platform
            date: Metrics date
            metrics: Metrics data

        Returns:
            Save confirmation
        """
        client = self._get_mcp_client()
        return await client.call_tool(
            "save_metrics",
            {
                "user_id": user_id,
                "platform": platform,
                "date": date,
                "metrics": metrics,
            },
        )

    async def get_metrics(
        self,
        user_id: str,
        date_range: dict[str, str],
        platforms: list[str] | None = None,
    ) -> dict[str, Any]:
        """Get historical metrics.

        Args:
            user_id: User identifier
            date_range: Date range
            platforms: Filter by platforms

        Returns:
            Metrics data
        """
        client = self._get_mcp_client()
        return await client.call_tool(
            "get_metrics",
            {
                "user_id": user_id,
                "date_range": date_range,
                "platforms": platforms,
            },
        )

    # =========================================================================
    # Landing Page Operations
    # =========================================================================

    async def create_landing_page(
        self,
        user_id: str,
        product: str,
        style: str,
        html_content: str,
    ) -> dict[str, Any]:
        """Create a landing page.

        Args:
            user_id: User identifier
            product: Product name/description
            style: Page style
            html_content: Generated HTML

        Returns:
            Created page data with URL
        """
        client = self._get_mcp_client()
        return await client.call_tool(
            "create_landing_page",
            {
                "user_id": user_id,
                "product": product,
                "style": style,
                "html_content": html_content,
            },
        )

    async def get_landing_pages(
        self,
        user_id: str,
        limit: int = 20,
    ) -> dict[str, Any]:
        """Get user's landing pages.

        Args:
            user_id: User identifier
            limit: Max items

        Returns:
            List of landing pages
        """
        client = self._get_mcp_client()
        return await client.call_tool(
            "get_landing_pages",
            {
                "user_id": user_id,
                "limit": limit,
            },
        )

    # =========================================================================
    # Credit Operations (Direct HTTP, not MCP)
    # =========================================================================

    async def check_credit(
        self,
        user_id: str,
        estimated_credits: float,
        operation_type: str,
    ) -> dict[str, Any]:
        """Check if user has sufficient credits.

        Note: This uses direct HTTP API, not MCP (per requirements).

        Args:
            user_id: User identifier
            estimated_credits: Credits needed
            operation_type: Type of operation

        Returns:
            Credit check result
        """
        from app.services.credit_client import get_credit_client

        credit_client = get_credit_client()
        return await credit_client.check_credit(
            user_id=user_id,
            estimated_credits=estimated_credits,
            operation_type=operation_type,
        )

    async def deduct_credit(
        self,
        user_id: str,
        credits: float,
        operation_type: str,
        operation_id: str,
        details: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Deduct credits from user balance.

        Note: This uses direct HTTP API, not MCP (per requirements).

        Args:
            user_id: User identifier
            credits: Credits to deduct
            operation_type: Type of operation
            operation_id: Unique operation ID
            details: Additional details

        Returns:
            Deduction result
        """
        from app.services.credit_client import get_credit_client

        credit_client = get_credit_client()
        return await credit_client.deduct_credit(
            user_id=user_id,
            credits=credits,
            operation_type=operation_type,
            operation_id=operation_id,
            details=details,
        )


# Singleton instance
_agent_mcp_client: AgentMCPClient | None = None


def get_agent_mcp_client() -> AgentMCPClient:
    """Get or create AgentMCPClient singleton."""
    global _agent_mcp_client
    if _agent_mcp_client is None:
        _agent_mcp_client = AgentMCPClient()
    return _agent_mcp_client
