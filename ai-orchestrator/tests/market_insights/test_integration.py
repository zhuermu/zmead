"""Integration tests for Market Insights module with AI Orchestrator.

This module tests the end-to-end integration between the Market Insights
capability and the AI Orchestrator graph.

Requirements: All (1.1-1.5, 2.1-2.5, 3.1-3.5, 4.1-4.5, 5.1-5.5, 6.1-6.6, 7.1-7.5)
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.core.state import AgentState
from app.nodes.market_insights_node import (
    market_insights_node,
    estimate_market_insights_cost,
    CREDIT_COSTS,
)


@pytest.fixture
def mock_mcp_client():
    """Mock MCP client for testing."""
    mock = AsyncMock()
    mock.check_credit = AsyncMock(return_value={"sufficient": True})
    mock.deduct_credit = AsyncMock(return_value={"success": True})
    mock.call_tool = AsyncMock(return_value={"status": "success"})
    mock.close = AsyncMock()
    return mock


@pytest.fixture
def mock_market_insights_capability():
    """Mock Market Insights capability for testing."""
    mock = AsyncMock()
    return mock


# =============================================================================
# Cost Estimation Tests
# =============================================================================


class TestCostEstimation:
    """Tests for credit cost estimation."""

    def test_analyze_competitor_cost(self):
        """Test cost estimation for analyze_competitor action."""
        cost = estimate_market_insights_cost("analyze_competitor", {})
        assert cost == CREDIT_COSTS["analyze_competitor"]

    def test_get_trending_creatives_cost(self):
        """Test cost estimation for get_trending_creatives action."""
        cost = estimate_market_insights_cost("get_trending_creatives", {})
        assert cost == CREDIT_COSTS["get_trending_creatives"]

    def test_analyze_creative_trend_cost(self):
        """Test cost estimation for analyze_creative_trend action."""
        cost = estimate_market_insights_cost("analyze_creative_trend", {})
        assert cost == CREDIT_COSTS["analyze_creative_trend"]

    def test_get_market_trends_cost(self):
        """Test cost estimation for get_market_trends action."""
        cost = estimate_market_insights_cost("get_market_trends", {})
        assert cost == CREDIT_COSTS["get_market_trends"]

    def test_generate_ad_strategy_base_cost(self):
        """Test base cost for generate_ad_strategy action."""
        cost = estimate_market_insights_cost(
            "generate_ad_strategy",
            {"competitor_analysis": False, "trend_analysis": False},
        )
        assert cost == CREDIT_COSTS["generate_ad_strategy"]

    def test_generate_ad_strategy_with_competitor_analysis(self):
        """Test cost increase when competitor analysis is included."""
        cost = estimate_market_insights_cost(
            "generate_ad_strategy",
            {"competitor_analysis": True, "trend_analysis": False},
        )
        assert cost == CREDIT_COSTS["generate_ad_strategy"] + 0.5

    def test_generate_ad_strategy_with_trend_analysis(self):
        """Test cost increase when trend analysis is included."""
        cost = estimate_market_insights_cost(
            "generate_ad_strategy",
            {"competitor_analysis": False, "trend_analysis": True},
        )
        assert cost == CREDIT_COSTS["generate_ad_strategy"] + 0.5

    def test_generate_ad_strategy_full_cost(self):
        """Test full cost with both analyses."""
        cost = estimate_market_insights_cost(
            "generate_ad_strategy",
            {"competitor_analysis": True, "trend_analysis": True},
        )
        assert cost == CREDIT_COSTS["generate_ad_strategy"] + 1.0

    def test_get_market_trends_many_keywords(self):
        """Test cost increase for many keywords."""
        cost = estimate_market_insights_cost(
            "get_market_trends",
            {"keywords": ["a", "b", "c", "d", "e"]},
        )
        assert cost == CREDIT_COSTS["get_market_trends"] * 1.2

    def test_track_strategy_performance_cost(self):
        """Test cost for track_strategy_performance action."""
        cost = estimate_market_insights_cost("track_strategy_performance", {})
        assert cost == CREDIT_COSTS["track_strategy_performance"]

    def test_unknown_action_default_cost(self):
        """Test default cost for unknown action."""
        cost = estimate_market_insights_cost("unknown_action", {})
        assert cost == 1.0


# =============================================================================
# Analyze Competitor Integration Tests
# =============================================================================


class TestAnalyzeCompetitorIntegration:
    """Integration tests for analyze_competitor action.
    
    Requirements: 1.1, 1.2, 1.3, 1.4, 1.5
    """

    @pytest.mark.asyncio
    async def test_analyze_competitor_success(
        self,
        mock_mcp_client,
        mock_market_insights_capability,
    ):
        """Test successful competitor analysis through the node."""
        # Configure capability mock
        mock_market_insights_capability.execute = AsyncMock(return_value={
            "status": "success",
            "competitor_info": {
                "name": "Competitor X",
                "price": "$79.99",
                "features": ["Feature 1", "Feature 2"],
                "target_audience": "25-35岁年轻人",
                "selling_points": ["高性价比", "时尚设计"],
            },
            "insights": {
                "pricing_strategy": "中端定价策略",
                "marketing_approach": "社交媒体营销为主",
                "strengths": ["品牌知名度高"],
                "weaknesses": ["价格偏高"],
            },
            "recommendations": ["可以采用更具竞争力的定价"],
        })

        state: AgentState = {
            "user_id": "test_user",
            "session_id": "test_session",
            "messages": [],
            "pending_actions": [
                {
                    "type": "analyze_competitor",
                    "module": "market_insights",
                    "params": {
                        "competitor_url": "https://competitor.com/product",
                        "analysis_type": "product",
                        "depth": "detailed",
                    },
                }
            ],
            "completed_results": [],
        }

        with patch("app.nodes.market_insights_node.MCPClient") as MockMCPClient, \
             patch("app.nodes.market_insights_node.MarketInsights") as MockMI:
            
            MockMCPClient.return_value.__aenter__.return_value = mock_mcp_client
            MockMCPClient.return_value.__aexit__.return_value = None
            MockMI.return_value = mock_market_insights_capability

            result = await market_insights_node(state)

            # Verify credit check was called
            mock_mcp_client.check_credit.assert_called_once()

            # Verify capability was executed
            mock_market_insights_capability.execute.assert_called_once_with(
                action="analyze_competitor",
                parameters=state["pending_actions"][0]["params"],
                context={
                    "user_id": "test_user",
                    "session_id": "test_session",
                },
            )

            # Verify credit was deducted
            mock_mcp_client.deduct_credit.assert_called_once()

            # Verify result
            assert "completed_results" in result
            assert len(result["completed_results"]) == 1

            completed = result["completed_results"][0]
            assert completed["status"] == "success"
            assert completed["module"] == "market_insights"
            assert completed["action_type"] == "analyze_competitor"
            assert completed["cost"] == CREDIT_COSTS["analyze_competitor"]
            assert "competitor_info" in completed["data"]

    @pytest.mark.asyncio
    async def test_analyze_competitor_failure(
        self,
        mock_mcp_client,
        mock_market_insights_capability,
    ):
        """Test competitor analysis failure returns error info.
        
        Requirements: 1.5
        """
        mock_market_insights_capability.execute = AsyncMock(return_value={
            "status": "error",
            "error": {
                "code": "1001",
                "type": "INVALID_URL",
                "message": "Invalid competitor URL",
            },
        })

        state: AgentState = {
            "user_id": "test_user",
            "session_id": "test_session",
            "messages": [],
            "pending_actions": [
                {
                    "type": "analyze_competitor",
                    "module": "market_insights",
                    "params": {
                        "competitor_url": "invalid-url",
                    },
                }
            ],
            "completed_results": [],
        }

        with patch("app.nodes.market_insights_node.MCPClient") as MockMCPClient, \
             patch("app.nodes.market_insights_node.MarketInsights") as MockMI:
            
            MockMCPClient.return_value.__aenter__.return_value = mock_mcp_client
            MockMCPClient.return_value.__aexit__.return_value = None
            MockMI.return_value = mock_market_insights_capability

            result = await market_insights_node(state)

            # Verify credit was NOT deducted for failed operation
            mock_mcp_client.deduct_credit.assert_not_called()

            # Verify error result
            completed = result["completed_results"][0]
            assert completed["status"] == "error"
            assert completed["cost"] == 0


# =============================================================================
# Get Trending Creatives Integration Tests
# =============================================================================


class TestGetTrendingCreativesIntegration:
    """Integration tests for get_trending_creatives action.
    
    Requirements: 2.1, 2.2, 2.3
    """

    @pytest.mark.asyncio
    async def test_get_trending_creatives_success(
        self,
        mock_mcp_client,
        mock_market_insights_capability,
    ):
        """Test successful trending creatives retrieval."""
        mock_market_insights_capability.execute = AsyncMock(return_value={
            "status": "success",
            "creatives": [
                {
                    "id": "creative_123",
                    "title": "Summer Fashion Trends",
                    "thumbnail_url": "https://example.com/thumb.jpg",
                    "views": 1500000,
                    "engagement_rate": 8.5,
                    "platform": "tiktok",
                },
                {
                    "id": "creative_456",
                    "title": "Fall Collection",
                    "thumbnail_url": "https://example.com/thumb2.jpg",
                    "views": 800000,
                    "engagement_rate": 6.2,
                    "platform": "tiktok",
                },
            ],
            "total": 2,
        })

        state: AgentState = {
            "user_id": "test_user",
            "session_id": "test_session",
            "messages": [],
            "pending_actions": [
                {
                    "type": "get_trending_creatives",
                    "module": "market_insights",
                    "params": {
                        "industry": "fashion",
                        "region": "US",
                        "time_range": "7d",
                        "limit": 20,
                    },
                }
            ],
            "completed_results": [],
        }

        with patch("app.nodes.market_insights_node.MCPClient") as MockMCPClient, \
             patch("app.nodes.market_insights_node.MarketInsights") as MockMI:
            
            MockMCPClient.return_value.__aenter__.return_value = mock_mcp_client
            MockMCPClient.return_value.__aexit__.return_value = None
            MockMI.return_value = mock_market_insights_capability

            result = await market_insights_node(state)

            completed = result["completed_results"][0]
            assert completed["status"] == "success"
            assert completed["action_type"] == "get_trending_creatives"
            assert completed["cost"] == CREDIT_COSTS["get_trending_creatives"]
            assert "creatives" in completed["data"]
            assert len(completed["data"]["creatives"]) == 2


# =============================================================================
# Get Market Trends Integration Tests
# =============================================================================


class TestGetMarketTrendsIntegration:
    """Integration tests for get_market_trends action.
    
    Requirements: 3.1, 3.2, 3.3, 3.4, 3.5
    """

    @pytest.mark.asyncio
    async def test_get_market_trends_success(
        self,
        mock_mcp_client,
        mock_market_insights_capability,
    ):
        """Test successful market trends retrieval."""
        mock_market_insights_capability.execute = AsyncMock(return_value={
            "status": "success",
            "trends": [
                {
                    "keyword": "sustainable fashion",
                    "search_volume": 125000,
                    "growth_rate": 15.5,
                    "trend_direction": "rising",
                    "related_queries": ["eco fashion", "ethical clothing"],
                },
            ],
            "insights": {
                "hot_topics": ["可持续时尚", "环保材料"],
                "emerging_trends": ["二手服装", "租赁模式"],
                "seasonal_patterns": "夏季搜索量增加 30%",
            },
        })

        state: AgentState = {
            "user_id": "test_user",
            "session_id": "test_session",
            "messages": [],
            "pending_actions": [
                {
                    "type": "get_market_trends",
                    "module": "market_insights",
                    "params": {
                        "keywords": ["sustainable fashion", "eco-friendly"],
                        "region": "US",
                        "time_range": "30d",
                    },
                }
            ],
            "completed_results": [],
        }

        with patch("app.nodes.market_insights_node.MCPClient") as MockMCPClient, \
             patch("app.nodes.market_insights_node.MarketInsights") as MockMI:
            
            MockMCPClient.return_value.__aenter__.return_value = mock_mcp_client
            MockMCPClient.return_value.__aexit__.return_value = None
            MockMI.return_value = mock_market_insights_capability

            result = await market_insights_node(state)

            completed = result["completed_results"][0]
            assert completed["status"] == "success"
            assert completed["action_type"] == "get_market_trends"
            assert "trends" in completed["data"]
            assert "insights" in completed["data"]


# =============================================================================
# Generate Ad Strategy Integration Tests
# =============================================================================


class TestGenerateAdStrategyIntegration:
    """Integration tests for generate_ad_strategy action.
    
    Requirements: 4.1, 4.2, 4.3, 4.4, 4.5
    """

    @pytest.mark.asyncio
    async def test_generate_ad_strategy_success(
        self,
        mock_mcp_client,
        mock_market_insights_capability,
    ):
        """Test successful ad strategy generation."""
        mock_market_insights_capability.execute = AsyncMock(return_value={
            "status": "success",
            "strategy": {
                "audience_recommendations": {
                    "age_range": "25-45",
                    "gender": "all",
                    "interests": ["sustainability", "fitness"],
                    "behaviors": ["eco-conscious shoppers"],
                },
                "creative_direction": {
                    "visual_style": "清新自然",
                    "key_messages": ["环保", "健康"],
                    "content_types": ["产品演示", "使用场景"],
                    "color_recommendations": ["绿色", "蓝色"],
                },
                "budget_planning": {
                    "recommended_daily_budget": 50,
                    "campaign_duration": "30 days",
                    "expected_reach": "50,000-100,000",
                },
                "campaign_structure": {
                    "ad_groups": [
                        {
                            "name": "环保意识人群",
                            "targeting": "sustainability interests",
                            "budget_allocation": "40%",
                        },
                    ],
                },
            },
            "rationale": "基于市场趋势分析和竞品研究...",
        })

        state: AgentState = {
            "user_id": "test_user",
            "session_id": "test_session",
            "messages": [],
            "pending_actions": [
                {
                    "type": "generate_ad_strategy",
                    "module": "market_insights",
                    "params": {
                        "product_info": {
                            "name": "Eco-Friendly Water Bottle",
                            "category": "home & garden",
                            "price": 29.99,
                            "target_market": "US",
                        },
                        "competitor_analysis": True,
                        "trend_analysis": True,
                    },
                }
            ],
            "completed_results": [],
        }

        with patch("app.nodes.market_insights_node.MCPClient") as MockMCPClient, \
             patch("app.nodes.market_insights_node.MarketInsights") as MockMI:
            
            MockMCPClient.return_value.__aenter__.return_value = mock_mcp_client
            MockMCPClient.return_value.__aexit__.return_value = None
            MockMI.return_value = mock_market_insights_capability

            result = await market_insights_node(state)

            completed = result["completed_results"][0]
            assert completed["status"] == "success"
            assert completed["action_type"] == "generate_ad_strategy"
            # Cost includes base + competitor + trend analysis
            expected_cost = CREDIT_COSTS["generate_ad_strategy"] + 1.0
            assert completed["cost"] == expected_cost
            assert "strategy" in completed["data"]
            assert "audience_recommendations" in completed["data"]["strategy"]
            assert "creative_direction" in completed["data"]["strategy"]
            assert "budget_planning" in completed["data"]["strategy"]
            assert "campaign_structure" in completed["data"]["strategy"]


# =============================================================================
# Track Strategy Performance Integration Tests
# =============================================================================


class TestTrackStrategyPerformanceIntegration:
    """Integration tests for track_strategy_performance action.
    
    Requirements: 5.1, 5.2, 5.3, 5.4, 5.5
    """

    @pytest.mark.asyncio
    async def test_track_strategy_performance_success(
        self,
        mock_mcp_client,
        mock_market_insights_capability,
    ):
        """Test successful strategy performance tracking."""
        mock_market_insights_capability.execute = AsyncMock(return_value={
            "status": "success",
            "performance": {
                "campaigns_with_strategy": {
                    "avg_roas": 3.5,
                    "avg_ctr": 2.8,
                    "avg_conversion_rate": 4.2,
                },
                "campaigns_without_strategy": {
                    "avg_roas": 2.1,
                    "avg_ctr": 1.9,
                    "avg_conversion_rate": 2.8,
                },
                "improvement": {
                    "roas_lift": "+66.7%",
                    "ctr_lift": "+47.4%",
                    "conversion_rate_lift": "+50%",
                },
            },
            "insights": "采纳 AI 策略的广告表现显著优于未采纳策略的广告",
        })

        state: AgentState = {
            "user_id": "test_user",
            "session_id": "test_session",
            "messages": [],
            "pending_actions": [
                {
                    "type": "track_strategy_performance",
                    "module": "market_insights",
                    "params": {
                        "strategy_id": "strategy_123",
                        "campaign_ids": ["campaign_1", "campaign_2"],
                        "comparison_period": "7d",
                    },
                }
            ],
            "completed_results": [],
        }

        with patch("app.nodes.market_insights_node.MCPClient") as MockMCPClient, \
             patch("app.nodes.market_insights_node.MarketInsights") as MockMI:
            
            MockMCPClient.return_value.__aenter__.return_value = mock_mcp_client
            MockMCPClient.return_value.__aexit__.return_value = None
            MockMI.return_value = mock_market_insights_capability

            result = await market_insights_node(state)

            completed = result["completed_results"][0]
            assert completed["status"] == "success"
            assert completed["action_type"] == "track_strategy_performance"
            assert completed["cost"] == CREDIT_COSTS["track_strategy_performance"]
            assert "performance" in completed["data"]
            assert "insights" in completed["data"]

    @pytest.mark.asyncio
    async def test_track_strategy_performance_failure(
        self,
        mock_mcp_client,
        mock_market_insights_capability,
    ):
        """Test strategy tracking failure returns error info.
        
        Requirements: 5.5
        """
        mock_market_insights_capability.execute = AsyncMock(return_value={
            "status": "error",
            "error": {
                "code": "STRATEGY_NOT_FOUND",
                "type": "NOT_FOUND",
                "message": "Strategy not found",
            },
        })

        state: AgentState = {
            "user_id": "test_user",
            "session_id": "test_session",
            "messages": [],
            "pending_actions": [
                {
                    "type": "track_strategy_performance",
                    "module": "market_insights",
                    "params": {
                        "strategy_id": "nonexistent",
                        "campaign_ids": ["c1"],
                    },
                }
            ],
            "completed_results": [],
        }

        with patch("app.nodes.market_insights_node.MCPClient") as MockMCPClient, \
             patch("app.nodes.market_insights_node.MarketInsights") as MockMI:
            
            MockMCPClient.return_value.__aenter__.return_value = mock_mcp_client
            MockMCPClient.return_value.__aexit__.return_value = None
            MockMI.return_value = mock_market_insights_capability

            result = await market_insights_node(state)

            completed = result["completed_results"][0]
            assert completed["status"] == "error"
            assert completed["cost"] == 0


# =============================================================================
# Degradation Scenario Tests
# =============================================================================


class TestDegradationScenarios:
    """Integration tests for degradation scenarios.
    
    Requirements: 6.4, 6.6
    """

    @pytest.mark.asyncio
    async def test_insufficient_credits(self, mock_mcp_client):
        """Test handling of insufficient credits."""
        from app.services.mcp_client import InsufficientCreditsError

        mock_mcp_client.check_credit = AsyncMock(
            side_effect=InsufficientCreditsError(
                message="Insufficient credits",
                required=2.0,
                available=0.5,
            )
        )

        state: AgentState = {
            "user_id": "test_user",
            "session_id": "test_session",
            "messages": [],
            "pending_actions": [
                {
                    "type": "analyze_competitor",
                    "module": "market_insights",
                    "params": {
                        "competitor_url": "https://example.com",
                    },
                }
            ],
            "completed_results": [],
        }

        with patch("app.nodes.market_insights_node.MCPClient") as MockMCPClient:
            MockMCPClient.return_value.__aenter__.return_value = mock_mcp_client
            MockMCPClient.return_value.__aexit__.return_value = None

            result = await market_insights_node(state)

            assert "error" in result
            assert result["error"]["type"] == "INSUFFICIENT_CREDITS"

            completed = result["completed_results"][0]
            assert completed["status"] == "error"
            assert completed["cost"] == 0

    @pytest.mark.asyncio
    async def test_mcp_error_during_credit_check(self, mock_mcp_client):
        """Test handling of MCP error during credit check."""
        from app.services.mcp_client import MCPError

        mock_mcp_client.check_credit = AsyncMock(
            side_effect=MCPError(message="Connection failed")
        )

        state: AgentState = {
            "user_id": "test_user",
            "session_id": "test_session",
            "messages": [],
            "pending_actions": [
                {
                    "type": "analyze_competitor",
                    "module": "market_insights",
                    "params": {
                        "competitor_url": "https://example.com",
                    },
                }
            ],
            "completed_results": [],
        }

        with patch("app.nodes.market_insights_node.MCPClient") as MockMCPClient:
            MockMCPClient.return_value.__aenter__.return_value = mock_mcp_client
            MockMCPClient.return_value.__aexit__.return_value = None

            result = await market_insights_node(state)

            assert "error" in result
            completed = result["completed_results"][0]
            assert completed["status"] == "error"
            assert completed["cost"] == 0

    @pytest.mark.asyncio
    async def test_no_pending_actions(self):
        """Test handling when no market insights actions are pending."""
        state: AgentState = {
            "user_id": "test_user",
            "session_id": "test_session",
            "messages": [],
            "pending_actions": [],
            "completed_results": [],
        }

        result = await market_insights_node(state)

        assert "completed_results" in result
        assert len(result["completed_results"]) == 0

    @pytest.mark.asyncio
    async def test_no_market_insights_actions(self):
        """Test handling when pending actions are for other modules."""
        state: AgentState = {
            "user_id": "test_user",
            "session_id": "test_session",
            "messages": [],
            "pending_actions": [
                {
                    "type": "generate_landing_page",
                    "module": "landing_page",
                    "params": {},
                }
            ],
            "completed_results": [],
        }

        result = await market_insights_node(state)

        assert "completed_results" in result
        assert len(result["completed_results"]) == 0

    @pytest.mark.asyncio
    async def test_credit_deduction_failure_continues(
        self,
        mock_mcp_client,
        mock_market_insights_capability,
    ):
        """Test that credit deduction failure doesn't fail the operation."""
        from app.services.mcp_client import MCPError

        mock_market_insights_capability.execute = AsyncMock(return_value={
            "status": "success",
            "competitor_info": {"name": "Test"},
            "insights": {},
            "recommendations": [],
        })

        # Credit check succeeds, but deduction fails
        mock_mcp_client.check_credit = AsyncMock(return_value={"sufficient": True})
        mock_mcp_client.deduct_credit = AsyncMock(
            side_effect=MCPError(message="Deduction failed")
        )

        state: AgentState = {
            "user_id": "test_user",
            "session_id": "test_session",
            "messages": [],
            "pending_actions": [
                {
                    "type": "analyze_competitor",
                    "module": "market_insights",
                    "params": {
                        "competitor_url": "https://example.com",
                    },
                }
            ],
            "completed_results": [],
        }

        with patch("app.nodes.market_insights_node.MCPClient") as MockMCPClient, \
             patch("app.nodes.market_insights_node.MarketInsights") as MockMI:
            
            MockMCPClient.return_value.__aenter__.return_value = mock_mcp_client
            MockMCPClient.return_value.__aexit__.return_value = None
            MockMI.return_value = mock_market_insights_capability

            result = await market_insights_node(state)

            # Operation should still succeed even if credit deduction fails
            completed = result["completed_results"][0]
            assert completed["status"] == "success"


# =============================================================================
# Capability Unit Integration Tests
# =============================================================================


class TestCapabilityIntegration:
    """Tests for MarketInsights capability integration."""

    @pytest.mark.asyncio
    async def test_capability_unknown_action(self):
        """Test capability returns error for unknown action."""
        from app.modules.market_insights.capability import MarketInsights

        mock_mcp = AsyncMock()
        mock_gemini = AsyncMock()

        capability = MarketInsights(
            mcp_client=mock_mcp,
            gemini_client=mock_gemini,
        )

        result = await capability.execute(
            action="unknown_action",
            parameters={},
            context={"user_id": "test"},
        )

        assert result["status"] == "error"
        assert "Unknown action" in result["error"]["message"]
        assert "unknown_action" in result["error"]["details"]["action"]
        assert "supported_actions" in result["error"]["details"]

    @pytest.mark.asyncio
    async def test_capability_action_routing(self):
        """Test capability routes to correct action handlers."""
        from app.modules.market_insights.capability import MarketInsights

        mock_mcp = AsyncMock()
        mock_gemini = AsyncMock()

        capability = MarketInsights(
            mcp_client=mock_mcp,
            gemini_client=mock_gemini,
        )

        # Test that all supported actions are recognized
        supported_actions = [
            "analyze_competitor",
            "get_trending_creatives",
            "analyze_creative_trend",
            "get_market_trends",
            "generate_ad_strategy",
            "track_strategy_performance",
        ]

        for action in supported_actions:
            # Just verify the action doesn't return "Unknown action" error
            # The actual execution may fail due to missing dependencies
            result = await capability.execute(
                action=action,
                parameters={},
                context={"user_id": "test"},
            )
            
            # Should not be an "Unknown action" error
            if result.get("status") == "error":
                assert "Unknown action" not in result.get("error", {}).get("message", "")


# =============================================================================
# Multiple Actions Tests
# =============================================================================


class TestMultipleActions:
    """Tests for handling multiple market insights actions."""

    @pytest.mark.asyncio
    async def test_sequential_actions(
        self,
        mock_mcp_client,
        mock_market_insights_capability,
    ):
        """Test processing multiple actions sequentially."""
        mock_market_insights_capability.execute = AsyncMock(return_value={
            "status": "success",
            "data": {"test": "data"},
        })

        state: AgentState = {
            "user_id": "test_user",
            "session_id": "test_session",
            "messages": [],
            "pending_actions": [
                {
                    "type": "analyze_competitor",
                    "module": "market_insights",
                    "params": {"competitor_url": "https://example1.com"},
                },
                {
                    "type": "get_market_trends",
                    "module": "market_insights",
                    "params": {"keywords": ["test"]},
                },
            ],
            "completed_results": [],
        }

        with patch("app.nodes.market_insights_node.MCPClient") as MockMCPClient, \
             patch("app.nodes.market_insights_node.MarketInsights") as MockMI:
            
            MockMCPClient.return_value.__aenter__.return_value = mock_mcp_client
            MockMCPClient.return_value.__aexit__.return_value = None
            MockMI.return_value = mock_market_insights_capability

            # First call processes first action
            result1 = await market_insights_node(state)
            assert len(result1["completed_results"]) == 1
            assert result1["completed_results"][0]["action_type"] == "analyze_competitor"

            # Update state with completed results
            state["completed_results"] = result1["completed_results"]

            # Second call processes second action
            result2 = await market_insights_node(state)
            assert len(result2["completed_results"]) == 2
            assert result2["completed_results"][1]["action_type"] == "get_market_trends"

    @pytest.mark.asyncio
    async def test_mixed_module_actions(
        self,
        mock_mcp_client,
        mock_market_insights_capability,
    ):
        """Test that only market_insights actions are processed."""
        mock_market_insights_capability.execute = AsyncMock(return_value={
            "status": "success",
            "data": {},
        })

        state: AgentState = {
            "user_id": "test_user",
            "session_id": "test_session",
            "messages": [],
            "pending_actions": [
                {
                    "type": "generate_landing_page",
                    "module": "landing_page",
                    "params": {},
                },
                {
                    "type": "analyze_competitor",
                    "module": "market_insights",
                    "params": {"competitor_url": "https://example.com"},
                },
            ],
            "completed_results": [
                # First action (landing_page) already completed
                {"action_type": "generate_landing_page", "module": "landing_page"},
            ],
        }

        with patch("app.nodes.market_insights_node.MCPClient") as MockMCPClient, \
             patch("app.nodes.market_insights_node.MarketInsights") as MockMI:
            
            MockMCPClient.return_value.__aenter__.return_value = mock_mcp_client
            MockMCPClient.return_value.__aexit__.return_value = None
            MockMI.return_value = mock_market_insights_capability

            result = await market_insights_node(state)

            # Should process the market_insights action
            assert len(result["completed_results"]) == 2
            assert result["completed_results"][1]["action_type"] == "analyze_competitor"
            assert result["completed_results"][1]["module"] == "market_insights"
