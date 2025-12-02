"""Get Ad Performance Tool - Fetch advertising performance data.

This tool retrieves ad performance metrics from various platforms
(Meta, TikTok, Google Ads) via MCP calls to the backend.

Requirements: Architecture v2.0 - Unified Tool Layer
"""

import time
from typing import Any, Literal

import structlog
from pydantic import BaseModel, Field

from app.tools.base import (
    BaseTool,
    ToolCategory,
    ToolContext,
    ToolDefinition,
    ToolResult,
    ToolRiskLevel,
)

logger = structlog.get_logger(__name__)


class GetAdPerformanceInput(BaseModel):
    """Input parameters for get_ad_performance tool."""

    campaign_ids: list[str] | None = Field(
        default=None, description="Campaign IDs to query. Empty for all campaigns."
    )
    date_range: Literal[
        "today", "yesterday", "last_7_days", "last_14_days", "last_30_days", "custom"
    ] = Field(default="last_7_days", description="Predefined date range")
    start_date: str | None = Field(
        default=None, description="Custom start date (YYYY-MM-DD)"
    )
    end_date: str | None = Field(
        default=None, description="Custom end date (YYYY-MM-DD)"
    )
    metrics: list[str] = Field(
        default=["spend", "impressions", "clicks", "conversions", "cpa", "roas"],
        description="Metrics to retrieve",
    )
    group_by: Literal["day", "campaign", "adset", "ad"] = Field(
        default="campaign", description="Grouping dimension"
    )
    platform: Literal["meta", "tiktok", "google", "all"] = Field(
        default="all", description="Ad platform filter"
    )


class AdPerformanceRecord(BaseModel):
    """Single ad performance record."""

    campaign_id: str
    campaign_name: str
    platform: str
    date: str | None = None
    spend: float = 0.0
    impressions: int = 0
    clicks: int = 0
    conversions: int = 0
    cpa: float | None = None
    roas: float | None = None
    ctr: float | None = None


class GetAdPerformanceOutput(BaseModel):
    """Output from get_ad_performance tool."""

    records: list[AdPerformanceRecord]
    summary: dict[str, Any]
    date_range: dict[str, str]
    total_records: int
    platform: str


class GetAdPerformanceTool(BaseTool[GetAdPerformanceInput, GetAdPerformanceOutput]):
    """Tool for fetching ad performance data.

    Retrieves advertising performance metrics from the backend via MCP.
    Supports filtering by campaign, date range, platform, and grouping.
    """

    definition = ToolDefinition(
        name="get_ad_performance",
        description=(
            "获取广告投放表现数据，包括花费、展示、点击、转化等指标。"
            "支持按时间范围、广告计划、平台筛选，可按天、计划、广告组或广告分组。"
        ),
        category=ToolCategory.DATA,
        risk_level=ToolRiskLevel.LOW,
        credit_cost=1.0,
        requires_confirmation=False,
        parameters=GetAdPerformanceInput.model_json_schema(),
        returns=GetAdPerformanceOutput.model_json_schema(),
    )

    async def execute(
        self, params: GetAdPerformanceInput, context: ToolContext
    ) -> ToolResult:
        """Execute the tool to fetch ad performance data.

        Args:
            params: Query parameters
            context: Execution context

        Returns:
            ToolResult with performance data or error
        """
        log = logger.bind(
            user_id=context.user_id,
            session_id=context.session_id,
            tool="get_ad_performance",
        )
        log.info("get_ad_performance_start", params=params.model_dump())

        start_time = time.time()

        try:
            # Import MCP client here to avoid circular imports
            from app.services.mcp_client import MCPClient

            async with MCPClient() as mcp:
                # Build MCP request parameters
                mcp_params = {
                    "date_range": params.date_range,
                    "metrics": params.metrics,
                    "group_by": params.group_by,
                    "platform": params.platform,
                }

                if params.campaign_ids:
                    mcp_params["campaign_ids"] = params.campaign_ids
                if params.start_date:
                    mcp_params["start_date"] = params.start_date
                if params.end_date:
                    mcp_params["end_date"] = params.end_date

                # Call MCP tool
                result = await mcp.call_tool("get_reports", mcp_params)

            # Parse response
            records = [
                AdPerformanceRecord(**record) for record in result.get("data", [])
            ]

            output = GetAdPerformanceOutput(
                records=records,
                summary=result.get("summary", {}),
                date_range=result.get("date_range", {}),
                total_records=len(records),
                platform=params.platform,
            )

            execution_time = time.time() - start_time

            log.info(
                "get_ad_performance_success",
                record_count=len(records),
                execution_time=execution_time,
            )

            return ToolResult.success_result(
                data=output.model_dump(),
                credit_consumed=self.definition.credit_cost,
                execution_time=execution_time,
            )

        except Exception as e:
            log.error("get_ad_performance_error", error=str(e), exc_info=True)
            return ToolResult.error_result(
                error=f"获取广告数据失败: {str(e)}",
                data={"partial_results": []},
            )

    def validate_params(self, params: dict[str, Any]) -> GetAdPerformanceInput:
        """Validate input parameters."""
        return GetAdPerformanceInput(**params)
