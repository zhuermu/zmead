"""Integration tests for Landing Page module with AI Orchestrator.

This module tests the integration between the Landing Page capability
and the AI Orchestrator graph.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.core.state import AgentState
from app.nodes.landing_page_node import landing_page_node


@pytest.fixture
def mock_mcp_client():
    """Mock MCP client for testing."""
    mock = AsyncMock()
    mock.check_credit = AsyncMock(return_value={"sufficient": True})
    mock.deduct_credit = AsyncMock(return_value={"success": True})
    mock.call_tool = AsyncMock(return_value={
        "landing_page": {
            "landing_page_id": "lp_test123",
            "title": "Test Product",
            "url": "https://test.aae-pages.com/lp_test123",
            "template": "modern",
            "status": "draft",
        }
    })
    return mock


@pytest.fixture
def mock_landing_page_capability():
    """Mock Landing Page capability for testing."""
    mock = AsyncMock()
    mock.execute = AsyncMock(return_value={
        "status": "success",
        "landing_page_id": "lp_test123",
        "url": "https://test.aae-pages.com/lp_test123",
        "sections": {
            "hero": {
                "headline": "Test Headline",
                "subheadline": "Test Subheadline",
                "image": "https://example.com/image.jpg",
                "cta_text": "Buy Now",
            },
            "features": [],
            "reviews": [],
            "faq": [],
            "cta": {
                "text": "Get Started",
                "url": "https://example.com/checkout",
            },
        },
        "message": "落地页生成成功",
    })
    return mock


@pytest.mark.asyncio
async def test_landing_page_node_generate_success(
    mock_mcp_client,
    mock_landing_page_capability,
):
    """Test successful landing page generation through the node."""
    
    # Create test state
    state: AgentState = {
        "user_id": "test_user",
        "session_id": "test_session",
        "messages": [],
        "pending_actions": [
            {
                "type": "generate_landing_page",
                "module": "landing_page",
                "params": {
                    "product_info": {
                        "title": "Test Product",
                        "price": 99.99,
                        "currency": "USD",
                        "main_image": "https://example.com/image.jpg",
                        "description": "Test description",
                        "features": ["Feature 1", "Feature 2"],
                        "reviews": [],
                        "source": "shopify",
                    },
                    "template": "modern",
                    "language": "en",
                },
            }
        ],
        "completed_results": [],
    }
    
    # Mock the MCP client and Landing Page capability
    with patch("app.nodes.landing_page_node.MCPClient") as MockMCPClient, \
         patch("app.nodes.landing_page_node.LandingPage") as MockLandingPage:
        
        # Configure mocks
        MockMCPClient.return_value.__aenter__.return_value = mock_mcp_client
        MockMCPClient.return_value.__aexit__.return_value = None
        MockLandingPage.return_value = mock_landing_page_capability
        
        # Execute node
        result = await landing_page_node(state)
        
        # Verify credit check was called
        mock_mcp_client.check_credit.assert_called_once()
        
        # Verify capability was executed
        mock_landing_page_capability.execute.assert_called_once_with(
            action="generate_landing_page",
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
        assert completed["module"] == "landing_page"
        assert completed["action_type"] == "generate_landing_page"
        assert completed["cost"] == 3.0  # Expected cost for generate_landing_page
        assert "landing_page_id" in completed["data"]


@pytest.mark.asyncio
async def test_landing_page_node_insufficient_credits(mock_mcp_client):
    """Test landing page node with insufficient credits."""
    from app.services.mcp_client import InsufficientCreditsError
    
    # Configure mock to raise insufficient credits error
    mock_mcp_client.check_credit = AsyncMock(
        side_effect=InsufficientCreditsError(
            message="Insufficient credits",
            required=3.0,
            available=1.0,
        )
    )
    
    # Create test state
    state: AgentState = {
        "user_id": "test_user",
        "session_id": "test_session",
        "messages": [],
        "pending_actions": [
            {
                "type": "generate_landing_page",
                "module": "landing_page",
                "params": {
                    "product_info": {
                        "title": "Test Product",
                        "price": 99.99,
                    },
                },
            }
        ],
        "completed_results": [],
    }
    
    # Mock the MCP client
    with patch("app.nodes.landing_page_node.MCPClient") as MockMCPClient:
        MockMCPClient.return_value.__aenter__.return_value = mock_mcp_client
        MockMCPClient.return_value.__aexit__.return_value = None
        
        # Execute node
        result = await landing_page_node(state)
        
        # Verify error was returned
        assert "error" in result
        assert result["error"]["type"] == "INSUFFICIENT_CREDITS"
        
        # Verify result shows error
        assert len(result["completed_results"]) == 1
        completed = result["completed_results"][0]
        assert completed["status"] == "error"
        assert completed["cost"] == 0  # No charge for failed operation


@pytest.mark.asyncio
async def test_landing_page_node_multiple_actions():
    """Test landing page node with multiple actions."""
    
    # Create test state with multiple actions
    state: AgentState = {
        "user_id": "test_user",
        "session_id": "test_session",
        "messages": [],
        "pending_actions": [
            {
                "type": "generate_landing_page",
                "module": "landing_page",
                "params": {"product_info": {"title": "Product 1"}},
            },
            {
                "type": "translate_landing_page",
                "module": "landing_page",
                "params": {
                    "landing_page_id": "lp_123",
                    "target_language": "es",
                },
            },
        ],
        "completed_results": [],
    }
    
    mock_mcp = AsyncMock()
    mock_mcp.check_credit = AsyncMock(return_value={"sufficient": True})
    mock_mcp.deduct_credit = AsyncMock(return_value={"success": True})
    
    mock_capability = AsyncMock()
    mock_capability.execute = AsyncMock(return_value={
        "status": "success",
        "landing_page_id": "lp_test",
        "message": "Success",
    })
    
    with patch("app.nodes.landing_page_node.MCPClient") as MockMCPClient, \
         patch("app.nodes.landing_page_node.LandingPage") as MockLandingPage:
        
        MockMCPClient.return_value.__aenter__.return_value = mock_mcp
        MockMCPClient.return_value.__aexit__.return_value = None
        MockLandingPage.return_value = mock_capability
        
        # Execute node - should process first action
        result = await landing_page_node(state)
        
        # Verify only first action was processed
        assert len(result["completed_results"]) == 1
        assert result["completed_results"][0]["action_type"] == "generate_landing_page"
        
        # Execute node again with updated state - should process second action
        state["completed_results"] = result["completed_results"]
        result2 = await landing_page_node(state)
        
        # Verify second action was processed
        assert len(result2["completed_results"]) == 2
        assert result2["completed_results"][1]["action_type"] == "translate_landing_page"


@pytest.mark.asyncio
async def test_landing_page_node_capability_error(
    mock_mcp_client,
    mock_landing_page_capability,
):
    """Test landing page node when capability returns an error."""
    
    # Configure capability to return error
    mock_landing_page_capability.execute = AsyncMock(return_value={
        "status": "error",
        "error": {
            "code": "6007",
            "type": "PRODUCT_INFO_EXTRACTION_FAILED",
            "message": "Failed to extract product info",
        },
    })
    
    # Create test state
    state: AgentState = {
        "user_id": "test_user",
        "session_id": "test_session",
        "messages": [],
        "pending_actions": [
            {
                "type": "parse_product",
                "module": "landing_page",
                "params": {
                    "product_url": "https://invalid.url",
                },
            }
        ],
        "completed_results": [],
    }
    
    with patch("app.nodes.landing_page_node.MCPClient") as MockMCPClient, \
         patch("app.nodes.landing_page_node.LandingPage") as MockLandingPage:
        
        MockMCPClient.return_value.__aenter__.return_value = mock_mcp_client
        MockMCPClient.return_value.__aexit__.return_value = None
        MockLandingPage.return_value = mock_landing_page_capability
        
        # Execute node
        result = await landing_page_node(state)
        
        # Verify credit was NOT deducted for failed operation
        mock_mcp_client.deduct_credit.assert_not_called()
        
        # Verify error result
        assert len(result["completed_results"]) == 1
        completed = result["completed_results"][0]
        assert completed["status"] == "error"
        assert completed["cost"] == 0
        assert completed["error"]["type"] == "PRODUCT_INFO_EXTRACTION_FAILED"
