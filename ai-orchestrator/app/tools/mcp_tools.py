"""MCP Server Tools integration.

This module provides wrappers for MCP Server tools (backend API) to integrate
them with the unified tools architecture. MCP tools handle data interactions
and should NOT contain AI logic.
"""

import structlog
from typing import Any

from app.services.mcp_client import MCPClient, MCPError
from app.tools.base import (
    AgentTool,
    ToolCategory,
    ToolExecutionError,
    ToolMetadata,
    ToolParameter,
)

logger = structlog.get_logger(__name__)


class MCPToolWrapper(AgentTool):
    """Base wrapper for MCP Server tools.

    This class wraps MCP tools and provides a unified interface
    for calling backend API tools via MCP protocol.
    """

    def __init__(
        self,
        tool_name: str,
        description: str,
        parameters: list[ToolParameter],
        returns: str = "object",
        credit_cost: float | None = None,
        requires_confirmation: bool = False,
        tags: list[str] | None = None,
        mcp_client: MCPClient | None = None,
    ):
        """Initialize MCP tool wrapper.

        Args:
            tool_name: MCP tool name
            description: Tool description
            parameters: Tool parameters
            returns: Return type description
            credit_cost: Credit cost
            requires_confirmation: Whether confirmation is required
            tags: Tool tags
            mcp_client: MCP client instance
        """
        metadata = ToolMetadata(
            name=tool_name,
            description=description,
            category=ToolCategory.MCP_SERVER,
            parameters=parameters,
            returns=returns,
            credit_cost=credit_cost,
            requires_confirmation=requires_confirmation,
            tags=tags or ["mcp", "backend", "data"],
        )

        super().__init__(metadata)

        self.mcp_client = mcp_client or MCPClient()

    async def execute(
        self,
        parameters: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Execute MCP tool call.

        Args:
            parameters: Tool parameters
            context: Execution context with user_id

        Returns:
            Tool execution result

        Raises:
            ToolExecutionError: If MCP call fails
        """
        user_id = context.get("user_id") if context else None

        log = logger.bind(
            tool=self.name,
            user_id=user_id,
            parameters=parameters,
        )
        log.info("mcp_tool_start")

        # Add user_id to parameters if available
        if user_id and "user_id" not in parameters:
            parameters["user_id"] = user_id

        try:
            # Call MCP tool
            result = await self.mcp_client.call_tool(
                tool_name=self.name,
                parameters=parameters,
            )

            log.info("mcp_tool_complete")

            return {
                "success": True,
                "data": result,
                "message": f"{self.name} executed successfully",
            }

        except MCPError as e:
            log.error("mcp_tool_error", error=str(e), code=e.code)
            raise ToolExecutionError(
                message=f"MCP tool failed: {e.message}",
                tool_name=self.name,
                error_code=e.code,
                details=e.details,
            )

        except Exception as e:
            log.error("mcp_tool_unexpected_error", error=str(e), exc_info=True)
            raise ToolExecutionError(
                message=f"Unexpected error: {str(e)}",
                tool_name=self.name,
            )


# Factory function to create MCP tool wrappers
def create_mcp_tools(mcp_client: MCPClient | None = None) -> list[AgentTool]:
    """Create all MCP Server tool wrappers.

    Args:
        mcp_client: MCP client instance

    Returns:
        List of MCP tool wrappers
    """
    tools = []

    # Creative Tools
    tools.append(
        MCPToolWrapper(
            tool_name="save_creative",
            description="Save a creative asset to the database",
            parameters=[
                ToolParameter(
                    name="image_data",
                    type="string",
                    description="Base64 encoded image data or image bytes",
                    required=True,
                ),
                ToolParameter(
                    name="metadata",
                    type="object",
                    description="Creative metadata (product_name, style, etc.)",
                    required=False,
                ),
            ],
            returns="object with creative_id and url",
            credit_cost=0.0,
            tags=["creative", "storage", "mcp"],
            mcp_client=mcp_client,
        )
    )

    tools.append(
        MCPToolWrapper(
            tool_name="get_creative",
            description="Get a creative asset by ID",
            parameters=[
                ToolParameter(
                    name="creative_id",
                    type="string",
                    description="Creative ID",
                    required=True,
                ),
            ],
            returns="object with creative details",
            credit_cost=0.0,
            tags=["creative", "retrieval", "mcp"],
            mcp_client=mcp_client,
        )
    )

    tools.append(
        MCPToolWrapper(
            tool_name="list_creatives",
            description="List user's creative assets with filtering",
            parameters=[
                ToolParameter(
                    name="filters",
                    type="object",
                    description="Filter criteria",
                    required=False,
                ),
                ToolParameter(
                    name="limit",
                    type="number",
                    description="Maximum number of results",
                    required=False,
                    default=20,
                ),
                ToolParameter(
                    name="offset",
                    type="number",
                    description="Pagination offset",
                    required=False,
                    default=0,
                ),
            ],
            returns="list of creatives",
            credit_cost=0.0,
            tags=["creative", "list", "mcp"],
            mcp_client=mcp_client,
        )
    )

    # Performance Tools
    tools.append(
        MCPToolWrapper(
            tool_name="fetch_ad_data",
            description="Fetch advertising performance data from platforms",
            parameters=[
                ToolParameter(
                    name="ad_account_id",
                    type="string",
                    description="Ad account ID",
                    required=True,
                ),
                ToolParameter(
                    name="date_range",
                    type="object",
                    description="Date range for data (start_date, end_date)",
                    required=True,
                ),
                ToolParameter(
                    name="metrics",
                    type="array",
                    description="Metrics to fetch",
                    required=False,
                ),
            ],
            returns="object with performance data",
            credit_cost=0.0,
            tags=["performance", "data", "mcp"],
            mcp_client=mcp_client,
        )
    )

    tools.append(
        MCPToolWrapper(
            tool_name="get_historical_data",
            description="Get historical performance data",
            parameters=[
                ToolParameter(
                    name="ad_account_id",
                    type="string",
                    description="Ad account ID",
                    required=True,
                ),
                ToolParameter(
                    name="days",
                    type="number",
                    description="Number of days of history",
                    required=False,
                    default=30,
                ),
            ],
            returns="object with historical data",
            credit_cost=0.0,
            tags=["performance", "history", "mcp"],
            mcp_client=mcp_client,
        )
    )

    tools.append(
        MCPToolWrapper(
            tool_name="save_report",
            description="Save a performance report",
            parameters=[
                ToolParameter(
                    name="report_data",
                    type="object",
                    description="Report data and metadata",
                    required=True,
                ),
            ],
            returns="object with report_id",
            credit_cost=0.0,
            tags=["performance", "report", "mcp"],
            mcp_client=mcp_client,
        )
    )

    # Campaign Tools
    tools.append(
        MCPToolWrapper(
            tool_name="create_campaign",
            description="Create a new advertising campaign. Requires an active ad account.",
            parameters=[
                ToolParameter(
                    name="ad_account_id",
                    type="integer",
                    description="Ad account ID to use for this campaign",
                    required=True,
                ),
                ToolParameter(
                    name="name",
                    type="string",
                    description="Campaign name",
                    required=True,
                ),
                ToolParameter(
                    name="objective",
                    type="string",
                    description="Campaign objective (awareness, traffic, engagement, leads, conversions, sales)",
                    required=True,
                ),
                ToolParameter(
                    name="budget",
                    type="number",
                    description="Campaign budget amount",
                    required=True,
                ),
                ToolParameter(
                    name="budget_type",
                    type="string",
                    description="Budget type: daily or lifetime (default: daily)",
                    required=False,
                ),
                ToolParameter(
                    name="targeting",
                    type="object",
                    description="Targeting configuration (audience, locations, etc.)",
                    required=False,
                ),
                ToolParameter(
                    name="creative_ids",
                    type="array",
                    description="List of creative IDs to use in this campaign",
                    required=False,
                ),
                ToolParameter(
                    name="landing_page_id",
                    type="integer",
                    description="Landing page ID to use",
                    required=False,
                ),
            ],
            returns="object with campaign details",
            credit_cost=0.0,
            requires_confirmation=True,
            tags=["campaign", "create", "mcp"],
            mcp_client=mcp_client,
        )
    )

    tools.append(
        MCPToolWrapper(
            tool_name="update_campaign",
            description="Update an existing campaign",
            parameters=[
                ToolParameter(
                    name="campaign_id",
                    type="string",
                    description="Campaign ID",
                    required=True,
                ),
                ToolParameter(
                    name="updates",
                    type="object",
                    description="Fields to update",
                    required=True,
                ),
            ],
            returns="object with updated campaign",
            credit_cost=0.0,
            requires_confirmation=True,
            tags=["campaign", "update", "mcp"],
            mcp_client=mcp_client,
        )
    )

    tools.append(
        MCPToolWrapper(
            tool_name="pause_campaign",
            description="Pause a running campaign",
            parameters=[
                ToolParameter(
                    name="campaign_id",
                    type="string",
                    description="Campaign ID",
                    required=True,
                ),
            ],
            returns="object with status",
            credit_cost=0.0,
            requires_confirmation=True,
            tags=["campaign", "pause", "mcp"],
            mcp_client=mcp_client,
        )
    )

    tools.append(
        MCPToolWrapper(
            tool_name="get_campaign",
            description="Get campaign details",
            parameters=[
                ToolParameter(
                    name="campaign_id",
                    type="string",
                    description="Campaign ID",
                    required=True,
                ),
            ],
            returns="object with campaign details",
            credit_cost=0.0,
            tags=["campaign", "retrieval", "mcp"],
            mcp_client=mcp_client,
        )
    )

    # Landing Page Tools
    tools.append(
        MCPToolWrapper(
            tool_name="create_landing_page",
            description="Create a new landing page with HTML content",
            parameters=[
                ToolParameter(
                    name="name",
                    type="string",
                    description="Name/title of the landing page",
                    required=True,
                ),
                ToolParameter(
                    name="product_url",
                    type="string",
                    description="URL of the product this landing page is for",
                    required=True,
                ),
                ToolParameter(
                    name="template",
                    type="string",
                    description="Template style (e.g., 'modern', 'bold', 'minimal')",
                    required=False,
                    default="modern",
                ),
                ToolParameter(
                    name="language",
                    type="string",
                    description="Language code (e.g., 'en', 'zh')",
                    required=False,
                    default="zh",
                ),
                ToolParameter(
                    name="html_content",
                    type="string",
                    description="Complete HTML content of the landing page",
                    required=False,
                ),
            ],
            returns="object with landing page id, url, and status",
            credit_cost=0.0,
            tags=["landing_page", "create", "mcp"],
            mcp_client=mcp_client,
        )
    )

    tools.append(
        MCPToolWrapper(
            tool_name="get_landing_page",
            description="Get a landing page by ID",
            parameters=[
                ToolParameter(
                    name="landing_page_id",
                    type="integer",
                    description="Landing page ID",
                    required=True,
                ),
            ],
            returns="object with page details",
            credit_cost=0.0,
            tags=["landing_page", "retrieval", "mcp"],
            mcp_client=mcp_client,
        )
    )

    tools.append(
        MCPToolWrapper(
            tool_name="get_landing_pages",
            description="Get a paginated list of landing pages for the current user",
            parameters=[
                ToolParameter(
                    name="page",
                    type="integer",
                    description="Page number (1-indexed)",
                    required=False,
                    default=1,
                ),
                ToolParameter(
                    name="page_size",
                    type="integer",
                    description="Number of items per page (max 100)",
                    required=False,
                    default=20,
                ),
                ToolParameter(
                    name="status",
                    type="string",
                    description="Filter by status: draft, published, archived",
                    required=False,
                ),
            ],
            returns="object with landing pages list and pagination info",
            credit_cost=0.0,
            tags=["landing_page", "list", "mcp"],
            mcp_client=mcp_client,
        )
    )

    tools.append(
        MCPToolWrapper(
            tool_name="update_landing_page",
            description="Update an existing landing page",
            parameters=[
                ToolParameter(
                    name="landing_page_id",
                    type="integer",
                    description="ID of the landing page to update",
                    required=True,
                ),
                ToolParameter(
                    name="name",
                    type="string",
                    description="New name/title",
                    required=False,
                ),
                ToolParameter(
                    name="html_content",
                    type="string",
                    description="New HTML content",
                    required=False,
                ),
            ],
            returns="object with updated landing page",
            credit_cost=0.0,
            tags=["landing_page", "update", "mcp"],
            mcp_client=mcp_client,
        )
    )

    tools.append(
        MCPToolWrapper(
            tool_name="publish_landing_page",
            description="Publish a landing page to make it publicly accessible",
            parameters=[
                ToolParameter(
                    name="landing_page_id",
                    type="integer",
                    description="ID of the landing page to publish",
                    required=True,
                ),
            ],
            returns="object with published URL and status",
            credit_cost=0.0,
            tags=["landing_page", "publish", "mcp"],
            mcp_client=mcp_client,
        )
    )

    tools.append(
        MCPToolWrapper(
            tool_name="upload_to_s3",
            description="Upload a file to S3 storage",
            parameters=[
                ToolParameter(
                    name="file_data",
                    type="string",
                    description="File data (base64 or bytes)",
                    required=True,
                ),
                ToolParameter(
                    name="file_name",
                    type="string",
                    description="File name",
                    required=True,
                ),
                ToolParameter(
                    name="content_type",
                    type="string",
                    description="MIME type",
                    required=False,
                ),
            ],
            returns="object with file_url",
            credit_cost=0.0,
            tags=["storage", "upload", "mcp"],
            mcp_client=mcp_client,
        )
    )

    tools.append(
        MCPToolWrapper(
            tool_name="create_ab_test_record",
            description="Create an A/B test record",
            parameters=[
                ToolParameter(
                    name="test_data",
                    type="object",
                    description="A/B test configuration",
                    required=True,
                ),
            ],
            returns="object with test_id",
            credit_cost=0.0,
            tags=["landing_page", "ab_test", "mcp"],
            mcp_client=mcp_client,
        )
    )

    # Market Insights Tools
    tools.append(
        MCPToolWrapper(
            tool_name="fetch_competitor_data",
            description="Fetch competitor data from external sources",
            parameters=[
                ToolParameter(
                    name="competitor_url",
                    type="string",
                    description="Competitor URL or identifier",
                    required=True,
                ),
            ],
            returns="object with competitor data",
            credit_cost=0.0,
            tags=["market", "competitor", "mcp"],
            mcp_client=mcp_client,
        )
    )

    tools.append(
        MCPToolWrapper(
            tool_name="fetch_market_data",
            description="Fetch market data and trends",
            parameters=[
                ToolParameter(
                    name="market_segment",
                    type="string",
                    description="Market segment or industry",
                    required=True,
                ),
                ToolParameter(
                    name="time_period",
                    type="string",
                    description="Time period for data",
                    required=False,
                ),
            ],
            returns="object with market data",
            credit_cost=0.0,
            tags=["market", "data", "mcp"],
            mcp_client=mcp_client,
        )
    )

    tools.append(
        MCPToolWrapper(
            tool_name="save_analysis",
            description="Save market analysis results",
            parameters=[
                ToolParameter(
                    name="analysis_data",
                    type="object",
                    description="Analysis results and metadata",
                    required=True,
                ),
            ],
            returns="object with analysis_id",
            credit_cost=0.0,
            tags=["market", "analysis", "mcp"],
            mcp_client=mcp_client,
        )
    )

    return tools
