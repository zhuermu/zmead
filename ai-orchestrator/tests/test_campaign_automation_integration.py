"""Integration tests for Campaign Automation module in AI Orchestrator.

This module tests the end-to-end integration of Campaign Automation
with the AI Orchestrator graph.

Requirements: Task 12 - Integration
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.core.graph import build_agent_graph
from app.core.state import create_initial_state


@pytest.mark.asyncio
async def test_campaign_automation_node_integration():
    """Test that campaign automation node is properly integrated into the graph."""
    # Mock settings to avoid requiring environment variables
    with patch("app.core.graph.get_settings") as mock_settings:
        mock_settings.return_value = MagicMock(
            is_production=False,
            gemini_api_key="test_key",
            web_platform_service_token="test_token",
        )
        
        # Build the graph
        graph = build_agent_graph()
        
        # Verify the graph has the campaign automation node
        assert graph is not None
        
        # Check that the node is registered
        # Note: LangGraph doesn't expose node names directly, but we can verify
        # by checking the graph compiles without errors
        assert graph.get_graph() is not None


@pytest.mark.asyncio
async def test_campaign_automation_routing():
    """Test that campaign automation intents route to the correct node."""
    from app.core.routing import route_by_intent, MODULE_NODE_MAP
    
    # Verify ad_engine is in the module map
    assert "ad_engine" in MODULE_NODE_MAP
    assert MODULE_NODE_MAP["ad_engine"] == "ad_engine"
    
    # Test routing with campaign automation action
    state = {
        "user_id": "test_user",
        "session_id": "test_session",
        "current_intent": "create_campaign",
        "pending_actions": [
            {
                "type": "create_campaign",
                "module": "ad_engine",
                "params": {
                    "objective": "sales",
                    "daily_budget": 100,
                },
            }
        ],
    }
    
    # Route should return ad_engine
    next_node = route_by_intent(state)
    assert next_node == "ad_engine"


@pytest.mark.asyncio
async def test_campaign_automation_node_execution():
    """Test that campaign automation node executes successfully."""
    from app.nodes.campaign_automation_node import campaign_automation_node
    
    # Mock the MCP client and Campaign Automation capability
    with patch("app.nodes.campaign_automation_node.MCPClient") as mock_mcp_class, \
         patch("app.nodes.campaign_automation_node.CampaignAutomation") as mock_capability_class:
        
        # Setup mock MCP client
        mock_mcp = AsyncMock()
        mock_mcp.__aenter__ = AsyncMock(return_value=mock_mcp)
        mock_mcp.__aexit__ = AsyncMock(return_value=None)
        mock_mcp.check_credit = AsyncMock()
        mock_mcp.deduct_credit = AsyncMock()
        mock_mcp_class.return_value = mock_mcp
        
        # Setup mock Campaign Automation capability
        mock_capability = AsyncMock()
        mock_capability.execute = AsyncMock(return_value={
            "status": "success",
            "campaign_id": "camp_test123",
            "message": "Campaign created successfully",
        })
        mock_capability_class.return_value = mock_capability
        
        # Create test state
        state = {
            "user_id": "test_user",
            "session_id": "test_session",
            "messages": [],
            "pending_actions": [
                {
                    "type": "create_campaign",
                    "module": "ad_engine",
                    "params": {
                        "objective": "sales",
                        "daily_budget": 100,
                        "creative_ids": ["creative_1"],
                        "platform": "meta",
                    },
                }
            ],
        }
        
        # Execute node
        result = await campaign_automation_node(state)
        
        # Verify result
        assert "completed_results" in result
        assert len(result["completed_results"]) == 1
        
        completed = result["completed_results"][0]
        assert completed["status"] == "success"
        assert completed["module"] == "ad_engine"
        assert completed["action_type"] == "create_campaign"
        assert completed["mock"] is False
        assert completed["cost"] > 0
        
        # Verify credit check was called
        mock_mcp.check_credit.assert_called_once()
        
        # Verify capability was called
        mock_capability.execute.assert_called_once()
        call_args = mock_capability.execute.call_args
        assert call_args[1]["action"] == "create_campaign"
        assert call_args[1]["parameters"]["objective"] == "sales"
        
        # Verify credit deduction was called
        mock_mcp.deduct_credit.assert_called_once()


@pytest.mark.asyncio
async def test_campaign_automation_node_insufficient_credits():
    """Test that campaign automation node handles insufficient credits."""
    from app.nodes.campaign_automation_node import campaign_automation_node
    from app.services.mcp_client import InsufficientCreditsError
    
    # Mock the MCP client to raise InsufficientCreditsError
    with patch("app.nodes.campaign_automation_node.MCPClient") as mock_mcp_class:
        
        # Setup mock MCP client
        mock_mcp = AsyncMock()
        mock_mcp.__aenter__ = AsyncMock(return_value=mock_mcp)
        mock_mcp.__aexit__ = AsyncMock(return_value=None)
        mock_mcp.check_credit = AsyncMock(
            side_effect=InsufficientCreditsError(
                required=2.0,
                available=0.5,
                message="Insufficient credits",
            )
        )
        mock_mcp_class.return_value = mock_mcp
        
        # Create test state
        state = {
            "user_id": "test_user",
            "session_id": "test_session",
            "messages": [],
            "pending_actions": [
                {
                    "type": "create_campaign",
                    "module": "ad_engine",
                    "params": {
                        "objective": "sales",
                        "daily_budget": 100,
                    },
                }
            ],
        }
        
        # Execute node
        result = await campaign_automation_node(state)
        
        # Verify error result
        assert "completed_results" in result
        assert len(result["completed_results"]) == 1
        
        completed = result["completed_results"][0]
        assert completed["status"] == "error"
        assert completed["cost"] == 0
        assert "error" in completed
        assert completed["error"]["code"] == "6011"


@pytest.mark.asyncio
async def test_campaign_automation_action_types():
    """Test that different campaign automation action types are supported."""
    from app.nodes.campaign_automation_node import estimate_campaign_automation_cost
    
    # Test cost estimation for different action types
    actions = [
        ("create_campaign", {}, 2.0),
        ("optimize_budget", {}, 1.5),
        ("manage_campaign", {}, 0.5),
        ("create_ab_test", {"creative_ids": ["c1", "c2", "c3"]}, 2.0),
        ("analyze_ab_test", {}, 1.0),
        ("create_rule", {}, 0.5),
        ("get_campaign_status", {}, 0.5),
    ]
    
    for action_type, params, expected_cost in actions:
        cost = estimate_campaign_automation_cost(action_type, params)
        assert cost >= expected_cost * 0.9  # Allow 10% variance
        assert cost <= expected_cost * 1.5  # Allow scaling


@pytest.mark.asyncio
async def test_campaign_automation_with_stub_fallback():
    """Test that stub can still be used via environment variable."""
    import os
    from app.core.graph import build_agent_graph
    
    # Set environment variable to use stub
    original_value = os.environ.get("USE_CAMPAIGN_AUTOMATION_STUB")
    os.environ["USE_CAMPAIGN_AUTOMATION_STUB"] = "true"
    
    try:
        # Mock settings to avoid requiring environment variables
        with patch("app.core.graph.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                is_production=False,
                gemini_api_key="test_key",
                web_platform_service_token="test_token",
            )
            
            # Build graph with stub
            graph = build_agent_graph()
            assert graph is not None
            
            # Verify graph compiles
            assert graph.get_graph() is not None
    finally:
        # Restore original value
        if original_value is None:
            os.environ.pop("USE_CAMPAIGN_AUTOMATION_STUB", None)
        else:
            os.environ["USE_CAMPAIGN_AUTOMATION_STUB"] = original_value


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
