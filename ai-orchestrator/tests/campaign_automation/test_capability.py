"""
Unit tests for Campaign Automation capability.

Tests the main entry point and action routing.
"""

import pytest

from app.modules.campaign_automation import CampaignAutomation


@pytest.mark.asyncio
async def test_campaign_automation_initialization(
    mock_mcp_client,
    mock_gemini_client,
    mock_redis_client,
):
    """Test Campaign Automation initialization"""
    automation = CampaignAutomation(
        mcp_client=mock_mcp_client,
        gemini_client=mock_gemini_client,
        redis_client=mock_redis_client,
    )
    
    assert automation.mcp_client is not None
    assert automation.gemini_client is not None
    assert automation.redis_client is not None


@pytest.mark.asyncio
async def test_execute_unknown_action(campaign_automation, sample_context):
    """Test execute with unknown action returns error"""
    result = await campaign_automation.execute(
        action="unknown_action",
        parameters={},
        context=sample_context,
    )
    
    assert result["status"] == "error"
    assert result["error"]["code"] == "1001"
    assert result["error"]["type"] == "INVALID_ACTION"
    assert "unknown_action" in result["error"]["message"].lower()


@pytest.mark.asyncio
async def test_execute_create_campaign_stub(
    campaign_automation,
    sample_campaign_parameters,
    sample_context,
):
    """Test create_campaign action (stub implementation)"""
    result = await campaign_automation.execute(
        action="create_campaign",
        parameters=sample_campaign_parameters,
        context=sample_context,
    )
    
    # Stub should return success with placeholder data
    assert result["status"] == "success"
    assert "campaign_id" in result
    assert "message" in result


@pytest.mark.asyncio
async def test_execute_optimize_budget_stub(
    campaign_automation,
    sample_optimization_parameters,
    sample_context,
):
    """Test optimize_budget action (stub implementation)"""
    result = await campaign_automation.execute(
        action="optimize_budget",
        parameters=sample_optimization_parameters,
        context=sample_context,
    )
    
    # Stub should return success
    assert result["status"] == "success"
    assert "optimizations" in result
    assert "message" in result


@pytest.mark.asyncio
async def test_execute_manage_campaign_stub(
    campaign_automation,
    sample_context,
):
    """Test manage_campaign action (stub implementation)"""
    result = await campaign_automation.execute(
        action="manage_campaign",
        parameters={
            "campaign_id": "campaign_123",
            "action": "pause",
        },
        context=sample_context,
    )
    
    # Stub should return success
    assert result["status"] == "success"
    assert "campaign_id" in result
    assert "new_status" in result


@pytest.mark.asyncio
async def test_execute_create_ab_test_stub(
    campaign_automation,
    sample_ab_test_parameters,
    sample_context,
):
    """Test create_ab_test action (stub implementation)"""
    result = await campaign_automation.execute(
        action="create_ab_test",
        parameters=sample_ab_test_parameters,
        context=sample_context,
    )
    
    # Stub should return success
    assert result["status"] == "success"
    assert "test_id" in result
    assert "campaign_id" in result


@pytest.mark.asyncio
async def test_execute_analyze_ab_test_stub(
    campaign_automation,
    sample_context,
):
    """Test analyze_ab_test action (stub implementation)"""
    result = await campaign_automation.execute(
        action="analyze_ab_test",
        parameters={"test_id": "test_123"},
        context=sample_context,
    )
    
    # Stub should return success
    assert result["status"] == "success"
    assert "test_id" in result
    assert "results" in result


@pytest.mark.asyncio
async def test_execute_create_rule_stub(
    campaign_automation,
    sample_rule_parameters,
    sample_context,
):
    """Test create_rule action (stub implementation)"""
    result = await campaign_automation.execute(
        action="create_rule",
        parameters=sample_rule_parameters,
        context=sample_context,
    )
    
    # Stub should return success
    assert result["status"] == "success"
    assert "rule_id" in result


@pytest.mark.asyncio
async def test_execute_get_campaign_status_stub(
    campaign_automation,
    sample_context,
):
    """Test get_campaign_status action (stub implementation)"""
    result = await campaign_automation.execute(
        action="get_campaign_status",
        parameters={"campaign_id": "campaign_123"},
        context=sample_context,
    )
    
    # Stub should return success
    assert result["status"] == "success"
    assert "campaign" in result
    assert "adsets" in result


@pytest.mark.asyncio
async def test_supported_actions_list(campaign_automation, sample_context):
    """Test that error response includes list of supported actions"""
    result = await campaign_automation.execute(
        action="invalid_action",
        parameters={},
        context=sample_context,
    )
    
    assert result["status"] == "error"
    assert "supported_actions" in result["error"]["details"]
    
    supported = result["error"]["details"]["supported_actions"]
    assert "create_campaign" in supported
    assert "optimize_budget" in supported
    assert "manage_campaign" in supported
    assert "create_ab_test" in supported
    assert "analyze_ab_test" in supported
    assert "create_rule" in supported
    assert "get_campaign_status" in supported
