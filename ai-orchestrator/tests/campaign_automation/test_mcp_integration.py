"""
Tests for MCP Client Integration in Campaign Automation.

This module tests the integration of MCP client calls in the Campaign Manager:
- get_active_ad_account
- get_ad_account_token
- get_creatives
- create_campaign
- update_campaign
- get_reports

Requirements: 2.1, 4.3, 8.1
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from app.modules.campaign_automation.managers.campaign_manager import CampaignManager
from app.services.mcp_client import MCPClient
from app.services.gemini_client import GeminiClient


@pytest.fixture
def mock_mcp_client():
    """Create a mock MCP client."""
    client = AsyncMock(spec=MCPClient)
    return client


@pytest.fixture
def mock_gemini_client():
    """Create a mock Gemini client."""
    client = AsyncMock(spec=GeminiClient)
    return client


@pytest.fixture
def campaign_manager(mock_mcp_client, mock_gemini_client):
    """Create a Campaign Manager with mocked dependencies."""
    return CampaignManager(
        mcp_client=mock_mcp_client,
        gemini_client=mock_gemini_client,
    )


@pytest.mark.asyncio
async def test_create_campaign_calls_get_active_ad_account(
    campaign_manager,
    mock_mcp_client,
):
    """
    Test that create_campaign calls get_active_ad_account MCP tool.
    
    Requirements: 2.1
    """
    # Setup mock responses
    mock_mcp_client.call_tool.side_effect = [
        # get_active_ad_account
        {
            "active_account": {
                "id": 123,
                "platform": "meta",
                "account_name": "Test Account",
            }
        },
        # get_ad_account_token
        {
            "access_token": "test_token_123",
            "ad_account_id": 123,
        },
        # create_campaign (MCP)
        {
            "id": 1,
            "name": "Test Campaign",
        },
    ]
    
    # Mock platform adapter
    with patch.object(
        campaign_manager.platform_router,
        "get_adapter"
    ) as mock_get_adapter:
        mock_adapter = AsyncMock()
        mock_adapter.create_campaign.return_value = {
            "status": "success",
            "id": "campaign_123",
            "name": "Test Campaign",
        }
        mock_adapter.create_adset.return_value = {
            "status": "success",
            "id": "adset_123",
            "name": "US 18-35",
            "daily_budget": 33.33,
        }
        mock_adapter.create_ad.return_value = {
            "status": "success",
            "id": "ad_123",
        }
        mock_get_adapter.return_value = mock_adapter
        
        # Mock AI client
        campaign_manager.ai_client.generate_ad_copy = AsyncMock(
            return_value="Test ad copy"
        )
        
        # Execute
        result = await campaign_manager.create_campaign(
            objective="sales",
            daily_budget=100.0,
            target_countries=["US"],
            creative_ids=["1", "2"],
            platform="meta",
            context={"user_id": "user_123"},
            product_url="https://example.com/product",
        )
        
        # Verify get_active_ad_account was called
        assert mock_mcp_client.call_tool.call_count >= 1
        first_call = mock_mcp_client.call_tool.call_args_list[0]
        assert first_call[0][0] == "get_active_ad_account"
        assert first_call[0][1]["platform"] == "meta"


@pytest.mark.asyncio
async def test_create_campaign_calls_get_ad_account_token(
    campaign_manager,
    mock_mcp_client,
):
    """
    Test that create_campaign calls get_ad_account_token MCP tool.
    
    Requirements: 2.1
    """
    # Setup mock responses
    mock_mcp_client.call_tool.side_effect = [
        # get_active_ad_account
        {
            "active_account": {
                "id": 123,
                "platform": "meta",
            }
        },
        # get_ad_account_token
        {
            "access_token": "test_token_123",
            "ad_account_id": 123,
        },
        # create_campaign (MCP)
        {"id": 1},
    ]
    
    # Mock platform adapter
    with patch.object(
        campaign_manager.platform_router,
        "get_adapter"
    ) as mock_get_adapter:
        mock_adapter = AsyncMock()
        mock_adapter.create_campaign.return_value = {
            "status": "success",
            "id": "campaign_123",
        }
        mock_adapter.create_adset.return_value = {
            "status": "success",
            "id": "adset_123",
            "daily_budget": 33.33,
        }
        mock_adapter.create_ad.return_value = {
            "status": "success",
            "id": "ad_123",
        }
        mock_get_adapter.return_value = mock_adapter
        
        campaign_manager.ai_client.generate_ad_copy = AsyncMock(
            return_value="Test ad copy"
        )
        
        # Execute
        await campaign_manager.create_campaign(
            objective="sales",
            daily_budget=100.0,
            target_countries=["US"],
            creative_ids=["1"],
            platform="meta",
            context={"user_id": "user_123"},
        )
        
        # Verify get_ad_account_token was called with ad_account_id
        calls = mock_mcp_client.call_tool.call_args_list
        token_call = next(
            (c for c in calls if c[0][0] == "get_ad_account_token"),
            None
        )
        assert token_call is not None
        assert token_call[0][1]["ad_account_id"] == 123


@pytest.mark.asyncio
async def test_create_campaign_calls_get_creatives(
    campaign_manager,
    mock_mcp_client,
):
    """
    Test that create_campaign calls get_creatives MCP tool.
    
    Requirements: 2.1
    """
    # Setup mock responses
    mock_mcp_client.call_tool.side_effect = [
        # get_active_ad_account
        {"active_account": {"id": 123}},
        # get_ad_account_token
        {"access_token": "test_token"},
        # get_creatives
        {
            "creatives": [
                {
                    "id": 1,
                    "cdn_url": "https://cdn.example.com/creative1.jpg",
                    "file_url": "https://s3.example.com/creative1.jpg",
                },
                {
                    "id": 2,
                    "cdn_url": "https://cdn.example.com/creative2.jpg",
                },
            ],
            "total": 2,
        },
        # create_campaign (MCP)
        {"id": 1},
    ]
    
    # Mock platform adapter
    with patch.object(
        campaign_manager.platform_router,
        "get_adapter"
    ) as mock_get_adapter:
        mock_adapter = AsyncMock()
        mock_adapter.create_campaign.return_value = {
            "status": "success",
            "id": "campaign_123",
        }
        mock_adapter.create_adset.return_value = {
            "status": "success",
            "id": "adset_123",
            "daily_budget": 100.0,
        }
        mock_adapter.create_ad.return_value = {
            "status": "success",
            "id": "ad_123",
        }
        mock_get_adapter.return_value = mock_adapter
        
        campaign_manager.ai_client.generate_ad_copy = AsyncMock(
            return_value="Test ad copy"
        )
        
        # Execute
        await campaign_manager.create_campaign(
            objective="sales",
            daily_budget=100.0,
            target_countries=["US"],
            creative_ids=["1", "2"],
            platform="meta",
            context={"user_id": "user_123"},
        )
        
        # Verify get_creatives was called
        calls = mock_mcp_client.call_tool.call_args_list
        creatives_call = next(
            (c for c in calls if c[0][0] == "get_creatives"),
            None
        )
        assert creatives_call is not None
        assert creatives_call[0][1]["page"] == 1
        assert creatives_call[0][1]["status"] == "active"


@pytest.mark.asyncio
async def test_create_campaign_calls_create_campaign_mcp(
    campaign_manager,
    mock_mcp_client,
):
    """
    Test that create_campaign calls create_campaign MCP tool to persist data.
    
    Requirements: 4.3
    """
    # Setup mock responses
    mock_mcp_client.call_tool.side_effect = [
        # get_active_ad_account
        {"active_account": {"id": 123}},
        # get_ad_account_token
        {"access_token": "test_token"},
        # get_creatives
        {"creatives": [], "total": 0},
        # create_campaign (MCP)
        {"id": 1, "name": "Test Campaign"},
    ]
    
    # Mock platform adapter
    with patch.object(
        campaign_manager.platform_router,
        "get_adapter"
    ) as mock_get_adapter:
        mock_adapter = AsyncMock()
        mock_adapter.create_campaign.return_value = {
            "status": "success",
            "id": "campaign_123",
            "name": "Test Campaign",
        }
        mock_adapter.create_adset.return_value = {
            "status": "success",
            "id": "adset_123",
            "daily_budget": 33.33,
        }
        mock_get_adapter.return_value = mock_adapter
        
        # Execute
        await campaign_manager.create_campaign(
            objective="sales",
            daily_budget=100.0,
            target_countries=["US"],
            creative_ids=[],
            platform="meta",
            context={"user_id": "user_123"},
            target_roas=3.0,
        )
        
        # Verify create_campaign MCP tool was called
        calls = mock_mcp_client.call_tool.call_args_list
        create_call = next(
            (c for c in calls if c[0][0] == "create_campaign"),
            None
        )
        assert create_call is not None
        params = create_call[0][1]
        assert params["ad_account_id"] == 123
        assert params["objective"] == "sales"
        assert params["budget"] == 100.0
        assert params["budget_type"] == "daily"


@pytest.mark.asyncio
async def test_update_campaign_status_calls_update_campaign_mcp(
    campaign_manager,
    mock_mcp_client,
):
    """
    Test that update_campaign_status calls update_campaign MCP tool.
    
    Requirements: 4.3
    """
    # Setup mock responses
    mock_mcp_client.call_tool.side_effect = [
        # get_active_ad_account
        {"active_account": {"id": 123}},
        # get_ad_account_token
        {"access_token": "test_token"},
        # get_campaigns (to find internal ID)
        {
            "campaigns": [
                {
                    "id": 456,
                    "platform_campaign_id": "campaign_123",
                    "name": "Test Campaign",
                }
            ],
            "total": 1,
        },
        # update_campaign
        {"id": 456, "status": "paused"},
    ]
    
    # Mock platform adapter
    with patch.object(
        campaign_manager.platform_router,
        "get_adapter"
    ) as mock_get_adapter:
        mock_adapter = AsyncMock()
        mock_get_adapter.return_value = mock_adapter
        
        # Execute
        result = await campaign_manager.update_campaign_status(
            campaign_id="campaign_123",
            status="pause",
            platform="meta",
            context={"user_id": "user_123"},
        )
        
        # Verify update_campaign was called
        calls = mock_mcp_client.call_tool.call_args_list
        update_call = next(
            (c for c in calls if c[0][0] == "update_campaign"),
            None
        )
        assert update_call is not None
        params = update_call[0][1]
        assert params["campaign_id"] == 456
        assert params["status"] == "pause"


@pytest.mark.asyncio
async def test_get_campaign_details_calls_get_reports(
    campaign_manager,
    mock_mcp_client,
):
    """
    Test that get_campaign_details calls get_reports MCP tool.
    
    Requirements: 8.1
    """
    # Setup mock responses
    mock_mcp_client.call_tool.side_effect = [
        # get_active_ad_account
        {"active_account": {"id": 123}},
        # get_ad_account_token
        {"access_token": "test_token"},
        # get_reports
        {
            "metrics": [
                {
                    "spend": "50.00",
                    "revenue": "150.00",
                    "conversions": 10,
                    "impressions": 1000,
                    "clicks": 50,
                }
            ],
            "total": 1,
        },
    ]
    
    # Mock platform adapter
    with patch.object(
        campaign_manager.platform_router,
        "get_adapter"
    ) as mock_get_adapter:
        mock_adapter = AsyncMock()
        mock_adapter.get_campaign_status.return_value = {
            "status": "success",
            "campaign": {
                "campaign_id": "campaign_123",
                "name": "Test Campaign",
                "status": "active",
            },
            "adsets": [],
        }
        mock_get_adapter.return_value = mock_adapter
        
        # Execute
        result = await campaign_manager.get_campaign_details(
            campaign_id="campaign_123",
            platform="meta",
            context={"user_id": "user_123"},
        )
        
        # Verify get_reports was called
        calls = mock_mcp_client.call_tool.call_args_list
        reports_call = next(
            (c for c in calls if c[0][0] == "get_reports"),
            None
        )
        assert reports_call is not None
        params = reports_call[0][1]
        assert params["ad_account_id"] == 123
        assert params["entity_type"] == "campaign"
        assert params["entity_id"] == "campaign_123"
        
        # Verify metrics were calculated
        assert result["status"] == "success"
        campaign_data = result["campaign"]
        assert "spend_today" in campaign_data
        assert "revenue_today" in campaign_data
        assert "roas_today" in campaign_data
        assert campaign_data["roas_today"] == 3.0  # 150 / 50


@pytest.mark.asyncio
async def test_create_campaign_handles_no_active_account(
    campaign_manager,
    mock_mcp_client,
):
    """
    Test that create_campaign handles missing active ad account gracefully.
    
    Requirements: 2.1
    """
    # Setup mock response with no active account
    mock_mcp_client.call_tool.return_value = {
        "active_account": None,
        "platform": "meta",
        "message": "No active ad account for meta",
    }
    
    # Execute
    result = await campaign_manager.create_campaign(
        objective="sales",
        daily_budget=100.0,
        target_countries=["US"],
        creative_ids=["1"],
        platform="meta",
        context={"user_id": "user_123"},
    )
    
    # Verify error response
    assert result["status"] == "error"
    assert result["error"]["code"] == "6000"
    assert result["error"]["type"] == "AD_ACCOUNT_NOT_BOUND"
    assert "未找到" in result["error"]["message"]
