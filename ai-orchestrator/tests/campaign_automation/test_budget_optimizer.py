"""
Unit tests for Budget Optimizer.

Tests the budget optimization logic including:
- Performance analysis
- Budget optimization rules
- Budget change capping
"""

import pytest
from unittest.mock import AsyncMock

from app.modules.campaign_automation.optimizers.budget_optimizer import BudgetOptimizer
from app.services.mcp_client import MCPClient


@pytest.fixture
def mock_mcp_client_with_performance():
    """Mock MCP client with performance data"""
    client = AsyncMock(spec=MCPClient)
    
    async def mock_call_tool(tool_name, params):
        if tool_name == "get_reports":
            return {
                "data": {
                    "adsets": [
                        {
                            "id": "adset_1",
                            "adset_id": "adset_1",
                            "name": "Test Adset 1",
                            "daily_budget": 30.0,
                            "roas": 4.6,  # Exceeds target * 1.5 (3.0 * 1.5 = 4.5)
                            "target_roas": 3.0,
                            "cpa": 10.0,
                            "target_cpa": 15.0,
                            "conversions": 10,
                            "spend": 30.0,
                            "revenue": 138.0,
                        },
                        {
                            "id": "adset_2",
                            "adset_id": "adset_2",
                            "name": "Test Adset 2",
                            "daily_budget": 30.0,
                            "roas": 1.5,
                            "target_roas": 3.0,
                            "cpa": 30.0,  # Exceeds target * 1.5
                            "target_cpa": 15.0,
                            "conversions": 5,
                            "spend": 30.0,
                            "revenue": 45.0,
                        },
                        {
                            "id": "adset_3",
                            "adset_id": "adset_3",
                            "name": "Test Adset 3",
                            "daily_budget": 30.0,
                            "roas": 0.0,
                            "target_roas": 3.0,
                            "cpa": 0.0,
                            "target_cpa": 15.0,
                            "conversions": 0,  # No conversions
                            "spend": 30.0,
                            "revenue": 0.0,
                        },
                    ]
                }
            }
        return {"status": "success"}
    
    client.call_tool = AsyncMock(side_effect=mock_call_tool)
    return client


@pytest.fixture
def budget_optimizer(mock_mcp_client_with_performance):
    """Budget optimizer instance with mocked MCP client"""
    return BudgetOptimizer(mcp_client=mock_mcp_client_with_performance)


@pytest.mark.asyncio
async def test_analyze_performance(budget_optimizer):
    """Test performance analysis"""
    context = {"user_id": "user_123"}
    
    result = await budget_optimizer.analyze_performance(
        campaign_id="campaign_123",
        target_metric="roas",
        context=context,
    )
    
    assert result["campaign_id"] == "campaign_123"
    assert "adsets" in result
    assert len(result["adsets"]) == 3
    assert "date_range" in result


@pytest.mark.asyncio
async def test_optimize_budget_roas_increase(budget_optimizer):
    """Test budget optimization with ROAS increase rule"""
    context = {"user_id": "user_123"}
    
    result = await budget_optimizer.optimize_budget(
        campaign_id="campaign_123",
        optimization_strategy="auto",
        target_metric="roas",
        context=context,
    )
    
    assert result.campaign_id == "campaign_123"
    assert result.total_actions >= 1
    
    # Check for increase budget action
    increase_actions = [
        opt for opt in result.optimizations
        if opt.action == "increase_budget"
    ]
    assert len(increase_actions) >= 1
    
    # Verify budget increase is 20%
    for action in increase_actions:
        if action.adset_id == "adset_1":
            assert action.old_budget == 30.0
            assert action.new_budget == 36.0  # 30 * 1.2


@pytest.mark.asyncio
async def test_optimize_budget_cpa_decrease(budget_optimizer):
    """Test budget optimization with CPA decrease rule"""
    context = {"user_id": "user_123"}
    
    result = await budget_optimizer.optimize_budget(
        campaign_id="campaign_123",
        optimization_strategy="auto",
        target_metric="cpa",
        context=context,
    )
    
    assert result.campaign_id == "campaign_123"
    assert result.total_actions >= 1
    
    # Check for decrease budget action
    decrease_actions = [
        opt for opt in result.optimizations
        if opt.action == "decrease_budget"
    ]
    assert len(decrease_actions) >= 1
    
    # Verify budget decrease is 20%
    for action in decrease_actions:
        if action.adset_id == "adset_2":
            assert action.old_budget == 30.0
            assert action.new_budget == 24.0  # 30 * 0.8


@pytest.mark.asyncio
async def test_optimize_budget_pause_no_conversions(budget_optimizer):
    """Test budget optimization with pause rule for no conversions"""
    context = {"user_id": "user_123"}
    
    result = await budget_optimizer.optimize_budget(
        campaign_id="campaign_123",
        optimization_strategy="auto",
        target_metric="roas",
        context=context,
    )
    
    assert result.campaign_id == "campaign_123"
    
    # Check for pause action
    pause_actions = [
        opt for opt in result.optimizations
        if opt.action == "pause"
    ]
    assert len(pause_actions) >= 1
    
    # Verify pause reason
    for action in pause_actions:
        if action.adset_id == "adset_3":
            assert "连续" in action.reason
            assert "天无转化" in action.reason


def test_apply_budget_cap_increase(budget_optimizer):
    """Test budget cap for increases"""
    old_budget = 100.0
    proposed_budget = 200.0  # 100% increase
    
    capped_budget = budget_optimizer._apply_budget_cap(old_budget, proposed_budget)
    
    # Should be capped at 50% increase
    assert capped_budget == 150.0


def test_apply_budget_cap_decrease(budget_optimizer):
    """Test budget cap for decreases"""
    old_budget = 100.0
    proposed_budget = 40.0  # 60% decrease
    
    capped_budget = budget_optimizer._apply_budget_cap(old_budget, proposed_budget)
    
    # Should be capped at 50% decrease (minimum 66.67)
    assert capped_budget == pytest.approx(66.67, rel=0.01)


def test_apply_budget_cap_no_change(budget_optimizer):
    """Test budget cap when within limits"""
    old_budget = 100.0
    proposed_budget = 120.0  # 20% increase (within 50% cap)
    
    capped_budget = budget_optimizer._apply_budget_cap(old_budget, proposed_budget)
    
    # Should not be capped
    assert capped_budget == 120.0


def test_optimization_rules_roas(budget_optimizer):
    """Test optimization rules for ROAS metric"""
    adset = {
        "id": "adset_1",
        "daily_budget": 30.0,
        "roas": 4.6,  # Exceeds target * 1.5 (3.0 * 1.5 = 4.5)
        "target_roas": 3.0,
        "conversions": 10,
        "days_running": 7,
    }
    
    actions = budget_optimizer._apply_optimization_rules(adset, "roas")
    
    assert len(actions) == 1
    assert actions[0].action == "increase_budget"
    assert actions[0].new_budget == 36.0


def test_optimization_rules_cpa(budget_optimizer):
    """Test optimization rules for CPA metric"""
    adset = {
        "id": "adset_2",
        "daily_budget": 30.0,
        "cpa": 30.0,
        "target_cpa": 15.0,
        "conversions": 5,
        "days_running": 7,
    }
    
    actions = budget_optimizer._apply_optimization_rules(adset, "cpa")
    
    assert len(actions) == 1
    assert actions[0].action == "decrease_budget"
    assert actions[0].new_budget == 24.0


def test_optimization_rules_pause(budget_optimizer):
    """Test optimization rules for pause action"""
    adset = {
        "id": "adset_3",
        "daily_budget": 30.0,
        "roas": 0.0,
        "target_roas": 3.0,
        "conversions": 0,
        "days_running": 3,
    }
    
    actions = budget_optimizer._apply_optimization_rules(adset, "roas")
    
    assert len(actions) == 1
    assert actions[0].action == "pause"
    assert "连续" in actions[0].reason
