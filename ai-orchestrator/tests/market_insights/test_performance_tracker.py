"""
Tests for PerformanceTracker.

Tests the strategy performance tracking functionality including
metric calculation, improvement percentages, and insights generation.

Requirements: 5.1, 5.2, 5.3, 5.4, 5.5
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.modules.market_insights.trackers import (
    PerformanceTracker,
    PerformanceTrackerError,
    StrategyNotFoundError,
    CampaignDataError,
)
from app.modules.market_insights.models import (
    PerformanceMetrics,
    PerformanceImprovement,
)


@pytest.fixture
def mock_mcp_client():
    """Create a mock MCP client for testing."""
    mock = MagicMock()
    mock.close = AsyncMock()
    return mock


@pytest.fixture
def tracker(mock_mcp_client):
    """Create a PerformanceTracker with mock MCP client."""
    return PerformanceTracker(mcp_client=mock_mcp_client)


class TestPerformanceTrackerInit:
    """Tests for PerformanceTracker initialization."""

    def test_init_with_mcp_client(self):
        """Test initialization with custom MCP client."""
        mock_mcp = MagicMock()
        tracker = PerformanceTracker(mcp_client=mock_mcp)
        assert tracker.mcp_client == mock_mcp


class TestCalculateImprovement:
    """Tests for calculate_improvement method."""

    def test_positive_improvement(self, tracker):
        """Test calculation with positive improvement."""
        with_strategy = PerformanceMetrics(
            avg_roas=3.5,
            avg_ctr=2.8,
            avg_conversion_rate=4.2,
        )
        without_strategy = PerformanceMetrics(
            avg_roas=2.1,
            avg_ctr=1.9,
            avg_conversion_rate=2.8,
        )

        improvement = tracker.calculate_improvement(with_strategy, without_strategy)

        assert improvement.roas_lift == "+66.7%"
        assert improvement.ctr_lift == "+47.4%"
        assert improvement.conversion_rate_lift == "+50.0%"

    def test_negative_improvement(self, tracker):
        """Test calculation with negative improvement (decline)."""
        with_strategy = PerformanceMetrics(
            avg_roas=1.5,
            avg_ctr=1.0,
            avg_conversion_rate=2.0,
        )
        without_strategy = PerformanceMetrics(
            avg_roas=2.0,
            avg_ctr=2.0,
            avg_conversion_rate=4.0,
        )

        improvement = tracker.calculate_improvement(with_strategy, without_strategy)

        assert improvement.roas_lift == "-25.0%"
        assert improvement.ctr_lift == "-50.0%"
        assert improvement.conversion_rate_lift == "-50.0%"

    def test_zero_baseline(self, tracker):
        """Test calculation when baseline is zero."""
        with_strategy = PerformanceMetrics(
            avg_roas=3.5,
            avg_ctr=2.8,
            avg_conversion_rate=4.2,
        )
        without_strategy = PerformanceMetrics(
            avg_roas=0.0,
            avg_ctr=0.0,
            avg_conversion_rate=0.0,
        )

        improvement = tracker.calculate_improvement(with_strategy, without_strategy)

        assert improvement.roas_lift == "+∞%"
        assert improvement.ctr_lift == "+∞%"
        assert improvement.conversion_rate_lift == "+∞%"

    def test_both_zero(self, tracker):
        """Test calculation when both values are zero."""
        with_strategy = PerformanceMetrics(
            avg_roas=0.0,
            avg_ctr=0.0,
            avg_conversion_rate=0.0,
        )
        without_strategy = PerformanceMetrics(
            avg_roas=0.0,
            avg_ctr=0.0,
            avg_conversion_rate=0.0,
        )

        improvement = tracker.calculate_improvement(with_strategy, without_strategy)

        assert improvement.roas_lift == "0%"
        assert improvement.ctr_lift == "0%"
        assert improvement.conversion_rate_lift == "0%"


class TestCalculateAverageMetrics:
    """Tests for _calculate_average_metrics method."""

    def test_average_metrics_calculation(self, tracker):
        """Test average metrics calculation."""
        campaigns = [
            {
                "campaign_id": "c1",
                "metrics": {"roas": 3.0, "ctr": 2.0, "conversion_rate": 4.0},
            },
            {
                "campaign_id": "c2",
                "metrics": {"roas": 4.0, "ctr": 3.0, "conversion_rate": 5.0},
            },
        ]

        metrics = tracker._calculate_average_metrics(campaigns)

        assert metrics.avg_roas == 3.5
        assert metrics.avg_ctr == 2.5
        assert metrics.avg_conversion_rate == 4.5

    def test_empty_campaigns(self, tracker):
        """Test with empty campaign list."""
        metrics = tracker._calculate_average_metrics([])

        assert metrics.avg_roas == 0.0
        assert metrics.avg_ctr == 0.0
        assert metrics.avg_conversion_rate == 0.0

    def test_missing_metrics(self, tracker):
        """Test with missing metrics in campaign data."""
        campaigns = [
            {"campaign_id": "c1", "metrics": {}},
            {"campaign_id": "c2", "metrics": {"roas": 4.0}},
        ]

        metrics = tracker._calculate_average_metrics(campaigns)

        assert metrics.avg_roas == 2.0  # (0 + 4) / 2
        assert metrics.avg_ctr == 0.0
        assert metrics.avg_conversion_rate == 0.0


class TestGenerateInsights:
    """Tests for _generate_insights method."""

    def test_insights_with_positive_improvement(self, tracker):
        """Test insights generation with positive improvement."""
        metrics_with = PerformanceMetrics(
            avg_roas=3.5, avg_ctr=2.8, avg_conversion_rate=4.2
        )
        metrics_without = PerformanceMetrics(
            avg_roas=2.1, avg_ctr=1.9, avg_conversion_rate=2.8
        )
        improvement = PerformanceImprovement(
            roas_lift="+66.7%",
            ctr_lift="+47.4%",
            conversion_rate_lift="+50.0%",
        )

        insights = tracker._generate_insights(
            metrics_with=metrics_with,
            metrics_without=metrics_without,
            improvement=improvement,
            campaigns_with_count=3,
            campaigns_without_count=2,
        )

        assert "采纳 AI 策略的广告表现显著优于未采纳策略的广告" in insights
        assert "3 个采纳策略" in insights
        assert "2 个未采纳策略" in insights

    def test_insights_no_campaigns_with_strategy(self, tracker):
        """Test insights when no campaigns adopted strategy."""
        metrics_with = PerformanceMetrics(
            avg_roas=0.0, avg_ctr=0.0, avg_conversion_rate=0.0
        )
        metrics_without = PerformanceMetrics(
            avg_roas=2.1, avg_ctr=1.9, avg_conversion_rate=2.8
        )
        improvement = PerformanceImprovement(
            roas_lift="0%", ctr_lift="0%", conversion_rate_lift="0%"
        )

        insights = tracker._generate_insights(
            metrics_with=metrics_with,
            metrics_without=metrics_without,
            improvement=improvement,
            campaigns_with_count=0,
            campaigns_without_count=5,
        )

        assert "没有广告系列采纳了该策略" in insights

    def test_insights_all_campaigns_with_strategy(self, tracker):
        """Test insights when all campaigns adopted strategy."""
        metrics_with = PerformanceMetrics(
            avg_roas=3.5, avg_ctr=2.8, avg_conversion_rate=4.2
        )
        metrics_without = PerformanceMetrics(
            avg_roas=0.0, avg_ctr=0.0, avg_conversion_rate=0.0
        )
        improvement = PerformanceImprovement(
            roas_lift="+∞%", ctr_lift="+∞%", conversion_rate_lift="+∞%"
        )

        insights = tracker._generate_insights(
            metrics_with=metrics_with,
            metrics_without=metrics_without,
            improvement=improvement,
            campaigns_with_count=5,
            campaigns_without_count=0,
        )

        assert "所有 5 个广告系列都采纳了该策略" in insights
        assert "ROAS: 3.5" in insights


class TestParseLiftValue:
    """Tests for _parse_lift_value method."""

    def test_parse_positive_lift(self, tracker):
        """Test parsing positive lift value."""
        assert tracker._parse_lift_value("+25.5%") == 25.5

    def test_parse_negative_lift(self, tracker):
        """Test parsing negative lift value."""
        assert tracker._parse_lift_value("-10.2%") == -10.2

    def test_parse_infinity(self, tracker):
        """Test parsing infinity lift value."""
        assert tracker._parse_lift_value("+∞%") == float("inf")

    def test_parse_zero(self, tracker):
        """Test parsing zero lift value."""
        assert tracker._parse_lift_value("0%") == 0.0


class TestTrackMethod:
    """Tests for track method."""

    @pytest.mark.asyncio
    async def test_track_missing_strategy_id(self, tracker):
        """Test track with missing strategy ID."""
        result = await tracker.track(
            strategy_id="",
            campaign_ids=["c1", "c2"],
            comparison_period="7d",
        )

        assert result.status == "error"
        assert result.error_code == "INVALID_PARAMS"
        assert "Strategy ID is required" in result.message

    @pytest.mark.asyncio
    async def test_track_missing_campaign_ids(self, tracker):
        """Test track with missing campaign IDs."""
        result = await tracker.track(
            strategy_id="strategy_123",
            campaign_ids=[],
            comparison_period="7d",
        )

        assert result.status == "error"
        assert result.error_code == "INVALID_PARAMS"
        assert "campaign ID is required" in result.message

    @pytest.mark.asyncio
    async def test_track_success(self):
        """Test successful tracking."""
        mock_mcp = AsyncMock()

        # Mock strategy data
        mock_mcp.call_tool.side_effect = [
            # get_insight response
            {
                "strategy_id": "strategy_123",
                "applied_campaign_ids": ["c1", "c2"],
            },
            # get_campaign_performance response
            {
                "campaigns": [
                    {
                        "campaign_id": "c1",
                        "metrics": {"roas": 3.5, "ctr": 2.8, "conversion_rate": 4.2},
                    },
                    {
                        "campaign_id": "c2",
                        "metrics": {"roas": 3.0, "ctr": 2.5, "conversion_rate": 3.8},
                    },
                    {
                        "campaign_id": "c3",
                        "metrics": {"roas": 2.1, "ctr": 1.9, "conversion_rate": 2.8},
                    },
                ]
            },
        ]
        mock_mcp.close = AsyncMock()

        tracker = PerformanceTracker(mcp_client=mock_mcp)

        result = await tracker.track(
            strategy_id="strategy_123",
            campaign_ids=["c1", "c2", "c3"],
            comparison_period="7d",
        )

        assert result.status == "success"
        assert result.performance is not None
        assert result.performance.campaigns_with_strategy.avg_roas == 3.25
        assert result.performance.campaigns_without_strategy.avg_roas == 2.1
        assert result.insights != ""

    @pytest.mark.asyncio
    async def test_track_strategy_not_found(self):
        """Test tracking when strategy is not found."""
        mock_mcp = AsyncMock()

        from app.services.mcp_client import MCPToolError

        mock_mcp.call_tool.side_effect = MCPToolError(
            message="Not found",
            code="NOT_FOUND",
        )
        mock_mcp.close = AsyncMock()

        tracker = PerformanceTracker(mcp_client=mock_mcp)

        result = await tracker.track(
            strategy_id="nonexistent",
            campaign_ids=["c1"],
            comparison_period="7d",
        )

        assert result.status == "error"
        assert result.error_code == "STRATEGY_NOT_FOUND"

