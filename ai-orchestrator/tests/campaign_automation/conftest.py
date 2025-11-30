"""
Pytest fixtures for Campaign Automation tests.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.modules.campaign_automation import CampaignAutomation
from app.services.mcp_client import MCPClient
from app.services.gemini_client import GeminiClient


@pytest.fixture
def mock_mcp_client():
    """Mock MCP client for testing"""
    client = AsyncMock(spec=MCPClient)
    
    # Mock different responses based on tool name
    async def mock_call_tool(tool_name, params):
        if tool_name == "get_active_ad_account":
            return {
                "active_account": {
                    "id": 123,
                    "platform": params.get("platform", "meta"),
                    "platform_account_id": "act_123456",
                    "account_name": "Test Account",
                    "status": "active",
                    "is_active": True,
                },
                "platform": params.get("platform", "meta"),
            }
        elif tool_name == "get_ad_account_token":
            return {
                "ad_account_id": params.get("ad_account_id", 123),
                "platform": "meta",
                "platform_account_id": "act_123456",
                "access_token": "mock_token_123",
                "token_expires_at": "2025-12-31T23:59:59Z",
            }
        elif tool_name == "get_creatives":
            return {
                "creatives": [
                    {
                        "id": 1,
                        "cdn_url": "https://cdn.example.com/creative1.jpg",
                        "file_url": "https://s3.example.com/creative1.jpg",
                        "name": "Creative 1",
                    },
                    {
                        "id": 2,
                        "cdn_url": "https://cdn.example.com/creative2.jpg",
                        "file_url": "https://s3.example.com/creative2.jpg",
                        "name": "Creative 2",
                    },
                ],
                "total": 2,
                "page": 1,
                "page_size": 100,
                "has_more": False,
            }
        elif tool_name == "create_campaign":
            return {
                "id": 1,
                "name": params.get("name", "Test Campaign"),
                "objective": params.get("objective", "sales"),
                "status": "draft",
                "budget": str(params.get("budget", 100.0)),
                "created_at": "2025-11-29T00:00:00Z",
            }
        elif tool_name == "get_campaigns":
            # Support AB test campaign lookup
            filters = params.get("filters", {})
            test_id = filters.get("metadata.test_id")
            campaign_id = params.get("campaign_id", "campaign_123")
            
            # If looking up by test_id, return AB test campaign
            if test_id == "test_123":
                return {
                    "campaigns": [
                        {
                            "id": 456,
                            "campaign_id": "campaign_test_123",
                            "platform_campaign_id": "campaign_test_123",
                            "name": "Creative Test - A/B Test",
                            "status": "active",
                            "created_at": "2025-11-22T00:00:00Z",
                        }
                    ],
                    "total": 1,
                    "page": 1,
                    "page_size": 100,
                    "has_more": False,
                }
            else:
                return {
                    "campaigns": [
                        {
                            "id": 456,
                            "platform_campaign_id": campaign_id,
                            "name": "Test Campaign",
                            "status": "active",
                        }
                    ],
                    "total": 1,
                    "page": 1,
                    "page_size": 100,
                    "has_more": False,
                }
        elif tool_name == "update_campaign":
            return {
                "id": params.get("campaign_id", 456),
                "status": params.get("status", "paused"),
                "updated_at": "2025-11-29T00:00:00Z",
            }
        elif tool_name == "get_reports":
            # Return different data based on level and campaign_id to support AB test analysis
            level = params.get("level", "campaign")
            campaign_id = params.get("campaign_id", "")
            
            # For AB test campaigns with adset level, return variant-specific data
            if level == "adset" and ("test_123" in str(campaign_id) or "A/B Test" in str(campaign_id)):
                return {
                    "adsets": [
                        {
                            "adset_id": "adset_1",
                            "creative_id": "creative_1",
                            "spend": 90.00,
                            "revenue": 315.00,
                            "conversions": 150,
                            "impressions": 5000,
                            "clicks": 140,
                            "ctr": 0.028,  # 2.8% as decimal
                            "cpc": 0.64,
                            "cpa": 0.60,
                            "roas": 3.5,
                        },
                        {
                            "adset_id": "adset_2",
                            "creative_id": "creative_2",
                            "spend": 90.00,
                            "revenue": 225.00,
                            "conversions": 120,
                            "impressions": 4800,
                            "clicks": 100,
                            "ctr": 0.021,  # 2.1% as decimal
                            "cpc": 0.90,
                            "cpa": 0.75,
                            "roas": 2.5,
                        },
                        {
                            "adset_id": "adset_3",
                            "creative_id": "creative_3",
                            "spend": 90.00,
                            "revenue": 180.00,
                            "conversions": 100,
                            "impressions": 4500,
                            "clicks": 81,
                            "ctr": 0.018,  # 1.8% as decimal
                            "cpc": 1.11,
                            "cpa": 0.90,
                            "roas": 2.0,
                        }
                    ],
                    "total": 3,
                    "page": 1,
                    "page_size": 10,
                    "has_more": False,
                }
            else:
                return {
                    "metrics": [
                        {
                            "spend": "50.00",
                            "revenue": "150.00",
                            "conversions": 10,
                            "impressions": 1000,
                            "clicks": 50,
                            "ctr": 5.0,
                            "cpc": "1.00",
                            "cpa": "5.00",
                            "roas": 3.0,
                        }
                    ],
                    "total": 1,
                    "page": 1,
                    "page_size": 10,
                    "has_more": False,
                }
        else:
            return {
                "status": "success",
                "data": {},
            }
    
    client.call_tool = AsyncMock(side_effect=mock_call_tool)
    
    return client


@pytest.fixture
def mock_gemini_client():
    """Mock Gemini client for testing"""
    client = AsyncMock(spec=GeminiClient)
    
    # Mock chat_completion and fast_completion methods
    client.chat_completion = AsyncMock(return_value="限时优惠！立即购买 https://example.com/product")
    client.fast_completion = AsyncMock(return_value="限时优惠！立即购买 https://example.com/product")
    
    return client


@pytest.fixture
def mock_redis_client():
    """Mock Redis client for testing"""
    client = AsyncMock()
    
    # Default cache miss
    client.get = AsyncMock(return_value=None)
    client.setex = AsyncMock(return_value=True)
    client.delete = AsyncMock(return_value=1)
    client.keys = AsyncMock(return_value=[])
    
    return client


@pytest.fixture
def mock_platform_adapter():
    """Mock platform adapter for testing"""
    adapter = AsyncMock()
    
    # Mock campaign creation (matches real adapter return format)
    adapter.create_campaign = AsyncMock(return_value={
        "id": "campaign_123",
        "name": "Test Campaign",
        "status": "active",
    })
    
    # Mock adset creation (matches real adapter return format)
    adapter.create_adset = AsyncMock(return_value={
        "id": "adset_123",
        "name": "Test Adset",
        "daily_budget": 33.33,
        "targeting": {},
        "status": "active",
    })
    
    # Mock ad creation (matches real adapter return format)
    adapter.create_ad = AsyncMock(return_value={
        "id": "ad_123",
        "creative_id": "creative_1",
        "status": "active",
    })
    
    # Mock campaign status
    adapter.get_campaign_status = AsyncMock(return_value={
        "campaign": {
            "campaign_id": "campaign_123",
            "name": "Test Campaign",
            "status": "active",
            "daily_budget": 100.0,
        },
        "adsets": [],
    })
    
    # Mock delete campaign
    adapter.delete_campaign = AsyncMock(return_value={
        "message": "Campaign deleted",
    })
    
    return adapter


@pytest.fixture
def campaign_automation(mock_mcp_client, mock_gemini_client, mock_redis_client, mock_platform_adapter, monkeypatch):
    """Campaign Automation instance with mocked dependencies"""
    # Mock the PlatformRouter to return our mock adapter
    from unittest.mock import MagicMock
    
    mock_router = MagicMock()
    # get_adapter is synchronous and returns the mock adapter
    mock_router.get_adapter.return_value = mock_platform_adapter
    mock_router.get_supported_platforms.return_value = ["meta", "tiktok", "google"]
    
    # Add async methods to the router that delegate to the adapter
    mock_router.create_campaign = mock_platform_adapter.create_campaign
    mock_router.create_adset = mock_platform_adapter.create_adset
    mock_router.create_ad = mock_platform_adapter.create_ad
    mock_router.update_budget = mock_platform_adapter.update_budget
    mock_router.pause_adset = mock_platform_adapter.pause_adset
    mock_router.resume_adset = mock_platform_adapter.resume_adset
    mock_router.get_campaign_status = mock_platform_adapter.get_campaign_status
    mock_router.delete_campaign = mock_platform_adapter.delete_campaign
    
    # Patch PlatformRouter in both modules
    monkeypatch.setattr(
        "app.modules.campaign_automation.managers.campaign_manager.PlatformRouter",
        lambda: mock_router
    )
    monkeypatch.setattr(
        "app.modules.campaign_automation.capability.PlatformRouter",
        lambda: mock_router
    )
    
    return CampaignAutomation(
        mcp_client=mock_mcp_client,
        gemini_client=mock_gemini_client,
        redis_client=mock_redis_client,
    )


@pytest.fixture
def sample_campaign_parameters():
    """Sample parameters for campaign creation"""
    return {
        "objective": "sales",
        "daily_budget": 100.0,
        "target_roas": 3.0,
        "product_url": "https://example.com/product",
        "creative_ids": ["creative_1", "creative_2"],
        "target_countries": ["US", "CA"],
        "platform": "meta",
    }


@pytest.fixture
def sample_context():
    """Sample context for requests"""
    return {
        "user_id": "user_123",
        "session_id": "session_456",
    }


@pytest.fixture
def sample_optimization_parameters():
    """Sample parameters for budget optimization"""
    return {
        "campaign_id": "campaign_123",
        "optimization_strategy": "auto",
        "target_metric": "roas",
    }


@pytest.fixture
def sample_ab_test_parameters():
    """Sample parameters for A/B test creation"""
    return {
        "test_name": "Creative Test",
        "creative_ids": ["creative_1", "creative_2", "creative_3"],
        "daily_budget": 90.0,
        "test_duration_days": 3,
        "platform": "meta",
    }


@pytest.fixture
def sample_rule_parameters():
    """Sample parameters for rule creation"""
    return {
        "rule_name": "Auto Pause High CPA",
        "condition": {
            "metric": "cpa",
            "operator": "greater_than",
            "value": 50.0,
            "time_range": "24h",
        },
        "action": {
            "type": "pause_adset",
        },
        "applies_to": {
            "campaign_ids": ["campaign_123"],
        },
    }
