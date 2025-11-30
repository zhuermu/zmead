"""
Performance Tracker for Strategy Effectiveness Measurement.

This module provides the PerformanceTracker class for comparing campaign
performance with and without AI-generated strategies.

Requirements: 5.1, 5.2, 5.3, 5.4, 5.5
"""

from typing import Any

import structlog

from app.services.mcp_client import MCPClient, MCPError

from ..models import (
    PerformanceMetrics,
    PerformanceImprovement,
    StrategyPerformance,
    StrategyPerformanceResponse,
)

logger = structlog.get_logger(__name__)


class PerformanceTrackerError(Exception):
    """Base exception for performance tracker errors."""

    def __init__(
        self,
        message: str,
        code: str = "TRACKING_ERROR",
        details: dict[str, Any] | None = None,
    ):
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(message)


class StrategyNotFoundError(PerformanceTrackerError):
    """Raised when strategy is not found."""

    def __init__(self, strategy_id: str):
        super().__init__(
            message=f"Strategy not found: {strategy_id}",
            code="STRATEGY_NOT_FOUND",
            details={"strategy_id": strategy_id},
        )


class CampaignDataError(PerformanceTrackerError):
    """Raised when campaign data cannot be retrieved."""

    def __init__(self, message: str, campaign_ids: list[str] | None = None):
        super().__init__(
            message=message,
            code="CAMPAIGN_DATA_ERROR",
            details={"campaign_ids": campaign_ids or []},
        )


class PerformanceTracker:
    """Strategy Performance Tracker.

    Compares performance of campaigns with and without AI-generated strategies
    to measure the effectiveness of AI recommendations.

    Features:
    - Fetches campaign performance data via MCP
    - Calculates ROAS, CTR, and conversion rate improvements
    - Generates insights text based on comparison
    - Handles tracking failures gracefully

    Requirements: 5.1, 5.2, 5.3, 5.4, 5.5
    """

    def __init__(
        self,
        mcp_client: MCPClient | None = None,
    ):
        """Initialize Performance Tracker.

        Args:
            mcp_client: MCP client for Web Platform communication
        """
        self.mcp_client = mcp_client or MCPClient()

        logger.info("performance_tracker_initialized")

    async def close(self) -> None:
        """Close the tracker and release resources."""
        if self.mcp_client:
            await self.mcp_client.close()

    async def track(
        self,
        strategy_id: str,
        campaign_ids: list[str],
        comparison_period: str = "7d",
    ) -> StrategyPerformanceResponse:
        """Track strategy performance by comparing campaigns.

        Compares performance metrics between campaigns that adopted the
        AI strategy and those that didn't.

        Args:
            strategy_id: ID of the strategy to track
            campaign_ids: List of campaign IDs to analyze
            comparison_period: Time period for comparison (e.g., "7d", "30d")

        Returns:
            StrategyPerformanceResponse with comparison data and insights

        Requirements: 5.1, 5.2, 5.3, 5.4, 5.5
        """
        log = logger.bind(
            strategy_id=strategy_id,
            campaign_count=len(campaign_ids),
            comparison_period=comparison_period,
        )
        log.info("track_strategy_performance_start")

        try:
            # Validate inputs
            if not strategy_id:
                raise PerformanceTrackerError(
                    message="Strategy ID is required",
                    code="INVALID_PARAMS",
                )

            if not campaign_ids:
                raise PerformanceTrackerError(
                    message="At least one campaign ID is required",
                    code="INVALID_PARAMS",
                )

            # Fetch strategy details to identify which campaigns used it
            strategy_data = await self._get_strategy_data(strategy_id)

            # Fetch campaign performance data
            campaign_data = await self._get_campaign_performance(
                campaign_ids=campaign_ids,
                period=comparison_period,
            )

            # Separate campaigns by strategy adoption
            campaigns_with_strategy = []
            campaigns_without_strategy = []

            strategy_campaign_ids = set(
                strategy_data.get("applied_campaign_ids", [])
            )

            for campaign in campaign_data:
                if campaign.get("campaign_id") in strategy_campaign_ids:
                    campaigns_with_strategy.append(campaign)
                else:
                    campaigns_without_strategy.append(campaign)

            # Calculate metrics for each group
            metrics_with = self._calculate_average_metrics(campaigns_with_strategy)
            metrics_without = self._calculate_average_metrics(campaigns_without_strategy)

            # Calculate improvement percentages
            improvement = self.calculate_improvement(metrics_with, metrics_without)

            # Generate insights text
            insights = self._generate_insights(
                metrics_with=metrics_with,
                metrics_without=metrics_without,
                improvement=improvement,
                campaigns_with_count=len(campaigns_with_strategy),
                campaigns_without_count=len(campaigns_without_strategy),
            )

            # Build performance response
            performance = StrategyPerformance(
                campaigns_with_strategy=metrics_with,
                campaigns_without_strategy=metrics_without,
                improvement=improvement,
            )

            log.info(
                "track_strategy_performance_success",
                campaigns_with_strategy=len(campaigns_with_strategy),
                campaigns_without_strategy=len(campaigns_without_strategy),
                roas_lift=improvement.roas_lift,
            )

            return StrategyPerformanceResponse(
                status="success",
                performance=performance,
                insights=insights,
            )

        except PerformanceTrackerError as e:
            log.error(
                "track_strategy_performance_error",
                error=str(e),
                code=e.code,
            )
            return StrategyPerformanceResponse(
                status="error",
                performance=None,
                insights="",
                error_code=e.code,
                message=e.message,
            )

        except MCPError as e:
            log.error(
                "track_strategy_performance_mcp_error",
                error=str(e),
                code=getattr(e, "code", "MCP_ERROR"),
            )
            return StrategyPerformanceResponse(
                status="error",
                performance=None,
                insights="",
                error_code=getattr(e, "code", "MCP_ERROR"),
                message=f"Failed to fetch data: {e.message}",
            )

        except Exception as e:
            log.error(
                "track_strategy_performance_unexpected_error",
                error=str(e),
                error_type=type(e).__name__,
                exc_info=True,
            )
            return StrategyPerformanceResponse(
                status="error",
                performance=None,
                insights="",
                error_code="TRACKING_ERROR",
                message=f"Tracking failed: {str(e)}",
            )

    async def _get_strategy_data(self, strategy_id: str) -> dict[str, Any]:
        """Fetch strategy data from Web Platform.

        Args:
            strategy_id: Strategy ID to fetch

        Returns:
            Strategy data dict

        Raises:
            StrategyNotFoundError: If strategy not found
        """
        log = logger.bind(strategy_id=strategy_id)
        log.debug("fetching_strategy_data")

        try:
            result = await self.mcp_client.call_tool(
                "get_insight",
                {
                    "insight_id": strategy_id,
                    "insight_type": "ad_strategy",
                },
            )

            if not result:
                raise StrategyNotFoundError(strategy_id)

            return result

        except MCPError as e:
            if "NOT_FOUND" in str(e.code):
                raise StrategyNotFoundError(strategy_id)
            raise

    async def _get_campaign_performance(
        self,
        campaign_ids: list[str],
        period: str,
    ) -> list[dict[str, Any]]:
        """Fetch campaign performance data from Web Platform.

        Args:
            campaign_ids: List of campaign IDs
            period: Time period for metrics

        Returns:
            List of campaign performance dicts

        Raises:
            CampaignDataError: If data cannot be retrieved
        """
        log = logger.bind(
            campaign_count=len(campaign_ids),
            period=period,
        )
        log.debug("fetching_campaign_performance")

        try:
            result = await self.mcp_client.call_tool(
                "get_campaign_performance",
                {
                    "campaign_ids": campaign_ids,
                    "period": period,
                    "metrics": ["roas", "ctr", "conversion_rate", "spend", "revenue"],
                },
            )

            campaigns = result.get("campaigns", [])

            if not campaigns:
                log.warning("no_campaign_data_returned")
                # Return empty list - will be handled in track()
                return []

            return campaigns

        except MCPError as e:
            raise CampaignDataError(
                message=f"Failed to fetch campaign data: {e.message}",
                campaign_ids=campaign_ids,
            )

    def _calculate_average_metrics(
        self,
        campaigns: list[dict[str, Any]],
    ) -> PerformanceMetrics:
        """Calculate average metrics for a group of campaigns.

        Args:
            campaigns: List of campaign performance dicts

        Returns:
            PerformanceMetrics with averaged values
        """
        if not campaigns:
            return PerformanceMetrics(
                avg_roas=0.0,
                avg_ctr=0.0,
                avg_conversion_rate=0.0,
            )

        total_roas = 0.0
        total_ctr = 0.0
        total_conversion_rate = 0.0
        count = len(campaigns)

        for campaign in campaigns:
            metrics = campaign.get("metrics", {})
            total_roas += float(metrics.get("roas", 0))
            total_ctr += float(metrics.get("ctr", 0))
            total_conversion_rate += float(metrics.get("conversion_rate", 0))

        return PerformanceMetrics(
            avg_roas=round(total_roas / count, 2),
            avg_ctr=round(total_ctr / count, 2),
            avg_conversion_rate=round(total_conversion_rate / count, 2),
        )

    def calculate_improvement(
        self,
        with_strategy: PerformanceMetrics,
        without_strategy: PerformanceMetrics,
    ) -> PerformanceImprovement:
        """Calculate improvement percentages between two metric sets.

        Computes the percentage lift for ROAS, CTR, and conversion rate
        when comparing campaigns with strategy vs without.

        Args:
            with_strategy: Metrics for campaigns using the strategy
            without_strategy: Metrics for campaigns not using the strategy

        Returns:
            PerformanceImprovement with lift percentages

        Requirements: 5.2
        """
        roas_lift = self._calculate_lift(
            with_strategy.avg_roas,
            without_strategy.avg_roas,
        )

        ctr_lift = self._calculate_lift(
            with_strategy.avg_ctr,
            without_strategy.avg_ctr,
        )

        conversion_lift = self._calculate_lift(
            with_strategy.avg_conversion_rate,
            without_strategy.avg_conversion_rate,
        )

        return PerformanceImprovement(
            roas_lift=roas_lift,
            ctr_lift=ctr_lift,
            conversion_rate_lift=conversion_lift,
        )

    def _calculate_lift(self, new_value: float, baseline: float) -> str:
        """Calculate percentage lift between two values.

        Args:
            new_value: The new/improved value
            baseline: The baseline value to compare against

        Returns:
            Formatted lift string (e.g., "+25.5%" or "-10.2%")
        """
        if baseline == 0:
            if new_value > 0:
                return "+∞%"
            return "0%"

        lift = ((new_value - baseline) / baseline) * 100

        if lift >= 0:
            return f"+{lift:.1f}%"
        return f"{lift:.1f}%"

    def _generate_insights(
        self,
        metrics_with: PerformanceMetrics,
        metrics_without: PerformanceMetrics,
        improvement: PerformanceImprovement,
        campaigns_with_count: int,
        campaigns_without_count: int,
    ) -> str:
        """Generate insights text based on performance comparison.

        Creates a human-readable summary of the strategy effectiveness.

        Args:
            metrics_with: Metrics for campaigns with strategy
            metrics_without: Metrics for campaigns without strategy
            improvement: Calculated improvement percentages
            campaigns_with_count: Number of campaigns with strategy
            campaigns_without_count: Number of campaigns without strategy

        Returns:
            Insights text string

        Requirements: 5.4
        """
        # Handle edge cases
        if campaigns_with_count == 0:
            return "没有广告系列采纳了该策略，无法进行效果对比。"

        if campaigns_without_count == 0:
            return (
                f"所有 {campaigns_with_count} 个广告系列都采纳了该策略。"
                f"平均 ROAS: {metrics_with.avg_roas}，"
                f"平均 CTR: {metrics_with.avg_ctr}%，"
                f"平均转化率: {metrics_with.avg_conversion_rate}%。"
            )

        # Parse lift values for comparison
        roas_lift_value = self._parse_lift_value(improvement.roas_lift)
        ctr_lift_value = self._parse_lift_value(improvement.ctr_lift)
        conversion_lift_value = self._parse_lift_value(improvement.conversion_rate_lift)

        # Determine overall performance
        positive_metrics = sum([
            1 if roas_lift_value > 0 else 0,
            1 if ctr_lift_value > 0 else 0,
            1 if conversion_lift_value > 0 else 0,
        ])

        if positive_metrics >= 2:
            performance_summary = "采纳 AI 策略的广告表现显著优于未采纳策略的广告"
        elif positive_metrics == 1:
            performance_summary = "采纳 AI 策略的广告在部分指标上表现更好"
        else:
            performance_summary = "采纳 AI 策略的广告表现与未采纳策略的广告相近"

        # Build detailed insights
        insights_parts = [
            performance_summary,
            f"（对比 {campaigns_with_count} 个采纳策略 vs {campaigns_without_count} 个未采纳策略的广告系列）。",
        ]

        # Add specific metric insights
        metric_insights = []

        if roas_lift_value > 10:
            metric_insights.append(f"ROAS 提升 {improvement.roas_lift}")
        elif roas_lift_value < -10:
            metric_insights.append(f"ROAS 下降 {improvement.roas_lift}")

        if ctr_lift_value > 10:
            metric_insights.append(f"CTR 提升 {improvement.ctr_lift}")
        elif ctr_lift_value < -10:
            metric_insights.append(f"CTR 下降 {improvement.ctr_lift}")

        if conversion_lift_value > 10:
            metric_insights.append(f"转化率提升 {improvement.conversion_rate_lift}")
        elif conversion_lift_value < -10:
            metric_insights.append(f"转化率下降 {improvement.conversion_rate_lift}")

        if metric_insights:
            insights_parts.append("主要变化：" + "，".join(metric_insights) + "。")

        return "".join(insights_parts)

    def _parse_lift_value(self, lift_str: str) -> float:
        """Parse lift string to numeric value.

        Args:
            lift_str: Lift string (e.g., "+25.5%", "-10.2%", "+∞%")

        Returns:
            Numeric lift value
        """
        if "∞" in lift_str:
            return float("inf") if "+" in lift_str else float("-inf")

        try:
            # Remove % and parse
            value_str = lift_str.replace("%", "").replace("+", "")
            return float(value_str)
        except ValueError:
            return 0.0

