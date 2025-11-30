"""
Tests for Rule Engine.

Requirements: 6.1, 6.3, 6.4, 6.5
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from app.modules.campaign_automation.engines.rule_engine import RuleEngine
from app.modules.campaign_automation.models import Rule, RuleCondition, RuleAction, RuleAppliesTo


@pytest.fixture
def mock_mcp_client():
    """Mock MCP client"""
    client = AsyncMock()
    client.call_tool = AsyncMock(return_value={
        "status": "success",
        "data": {"cpa": 60.0, "roas": 2.5}
    })
    return client


@pytest.fixture
def mock_redis_client():
    """Mock Redis client"""
    client = AsyncMock()
    client.set = AsyncMock()
    client.get = AsyncMock()
    client.keys = AsyncMock(return_value=[])
    client.sadd = AsyncMock()
    client.smembers = AsyncMock(return_value=[])
    client.srem = AsyncMock()
    client.delete = AsyncMock()
    return client


@pytest.fixture
def rule_engine(mock_mcp_client, mock_redis_client):
    """Create Rule Engine instance with mocked dependencies"""
    return RuleEngine(
        mcp_client=mock_mcp_client,
        redis_client=mock_redis_client,
    )


@pytest.mark.asyncio
async def test_create_rule_success(rule_engine, mock_redis_client):
    """
    Test successful rule creation.
    
    Validates: Requirements 6.1
    """
    # Arrange
    rule_name = "Auto Pause High CPA"
    condition = {
        "metric": "cpa",
        "operator": "greater_than",
        "value": 50,
        "time_range": "24h"
    }
    action = {"type": "pause_adset"}
    applies_to = {"campaign_ids": ["campaign_123"]}
    context = {"user_id": "user_123", "session_id": "session_456"}
    
    # Act
    result = await rule_engine.create_rule(
        rule_name=rule_name,
        condition=condition,
        action=action,
        applies_to=applies_to,
        context=context,
    )
    
    # Assert
    assert result["status"] == "success"
    assert "rule_id" in result
    assert result["rule_id"].startswith("rule_")
    assert "message" in result
    
    # Verify Redis calls
    assert mock_redis_client.set.called
    assert mock_redis_client.sadd.called


@pytest.mark.asyncio
async def test_create_rule_with_custom_interval(rule_engine, mock_redis_client):
    """
    Test rule creation with custom check interval.
    
    Validates: Requirements 6.1
    """
    # Arrange
    check_interval = 3600  # 1 hour
    
    # Act
    result = await rule_engine.create_rule(
        rule_name="Hourly Check",
        condition={"metric": "cpa", "operator": "greater_than", "value": 50, "time_range": "24h"},
        action={"type": "pause_adset"},
        applies_to={"campaign_ids": ["campaign_123"]},
        context={"user_id": "user_123"},
        check_interval=check_interval,
    )
    
    # Assert
    assert result["status"] == "success"
    assert "1 小时" in result["message"]


@pytest.mark.asyncio
async def test_execute_rule_action_pause_adset(rule_engine):
    """
    Test executing pause_adset action.
    
    Validates: Requirements 6.3
    """
    # Arrange
    mock_platform = AsyncMock()
    mock_platform.pause_adset = AsyncMock(return_value={"status": "success", "new_status": "paused"})
    rule_engine.platform_router.get_adapter = MagicMock(return_value=mock_platform)
    
    # Act
    result = await rule_engine.execute_rule_action(
        rule_id="rule_123",
        target_id="adset_456",
        target_type="adset",
        action={"type": "pause_adset"},
        platform="meta",
    )
    
    # Assert
    assert result["status"] == "success"
    assert result["action"] == "pause_adset"
    assert result["target_id"] == "adset_456"
    assert mock_platform.pause_adset.called


@pytest.mark.asyncio
async def test_execute_rule_action_increase_budget(rule_engine):
    """
    Test executing increase_budget action.
    
    Validates: Requirements 6.3
    """
    # Arrange
    mock_platform = AsyncMock()
    mock_platform.update_budget = AsyncMock(return_value={"status": "success"})
    rule_engine.platform_router.get_adapter = MagicMock(return_value=mock_platform)
    
    # Mock _get_current_budget
    rule_engine._get_current_budget = AsyncMock(return_value=100.0)
    
    # Act
    result = await rule_engine.execute_rule_action(
        rule_id="rule_123",
        target_id="adset_456",
        target_type="adset",
        action={"type": "increase_budget", "parameters": {"percentage": 20}},
        platform="meta",
    )
    
    # Assert
    assert result["status"] == "success"
    assert result["action"] == "increase_budget"
    # Budget should be increased by 20%: 100 * 1.2 = 120
    mock_platform.update_budget.assert_called_once_with("adset_456", 120.0)


@pytest.mark.asyncio
async def test_execute_rule_action_invalid_target_type(rule_engine):
    """
    Test executing action with invalid target type.
    
    Validates: Requirements 6.3
    """
    # Act
    result = await rule_engine.execute_rule_action(
        rule_id="rule_123",
        target_id="campaign_456",
        target_type="campaign",
        action={"type": "pause_adset"},
        platform="meta",
    )
    
    # Assert
    assert result["status"] == "error"
    assert result["error"]["code"] == "1001"
    assert "can only be applied to adsets" in result["error"]["message"]


@pytest.mark.asyncio
async def test_get_rule(rule_engine, mock_redis_client):
    """
    Test retrieving a rule by ID.
    
    Validates: Requirements 6.1
    """
    # Arrange
    rule_id = "rule_123"
    rule = Rule(
        rule_id=rule_id,
        rule_name="Test Rule",
        condition=RuleCondition(
            metric="cpa",
            operator="greater_than",
            value=50,
            time_range="24h"
        ),
        action=RuleAction(type="pause_adset"),
        applies_to=RuleAppliesTo(campaign_ids=["campaign_123"]),
        enabled=True,
        created_at=datetime.now(timezone.utc),
    )
    
    mock_redis_client.get = AsyncMock(return_value=rule.model_dump_json())
    
    # Act
    result = await rule_engine.get_rule(rule_id)
    
    # Assert
    assert result is not None
    assert result["rule_id"] == rule_id
    assert result["rule_name"] == "Test Rule"


@pytest.mark.asyncio
async def test_get_rule_not_found(rule_engine, mock_redis_client):
    """
    Test retrieving a non-existent rule.
    
    Validates: Requirements 6.1
    """
    # Arrange
    mock_redis_client.get = AsyncMock(return_value=None)
    
    # Act
    result = await rule_engine.get_rule("nonexistent_rule")
    
    # Assert
    assert result is None


@pytest.mark.asyncio
async def test_delete_rule(rule_engine, mock_redis_client):
    """
    Test deleting a rule.
    
    Validates: Requirements 6.1
    """
    # Arrange
    rule_id = "rule_123"
    user_id = "user_456"
    
    # Act
    result = await rule_engine.delete_rule(rule_id, user_id)
    
    # Assert
    assert result["status"] == "success"
    assert "deleted successfully" in result["message"]
    assert mock_redis_client.delete.called
    assert mock_redis_client.srem.called


@pytest.mark.asyncio
async def test_list_rules(rule_engine, mock_redis_client):
    """
    Test listing all rules for a user.
    
    Validates: Requirements 6.1
    """
    # Arrange
    user_id = "user_123"
    rule_ids = ["rule_1", "rule_2"]
    
    mock_redis_client.smembers = AsyncMock(return_value=rule_ids)
    
    # Mock get_rule to return rule data
    async def mock_get_rule(rule_id):
        return {
            "rule_id": rule_id,
            "rule_name": f"Rule {rule_id}",
            "enabled": True,
        }
    
    rule_engine.get_rule = AsyncMock(side_effect=mock_get_rule)
    
    # Act
    result = await rule_engine.list_rules(user_id)
    
    # Assert
    assert len(result) == 2
    assert result[0]["rule_id"] == "rule_1"
    assert result[1]["rule_id"] == "rule_2"


@pytest.mark.asyncio
async def test_parse_time_range(rule_engine):
    """
    Test time range parsing.
    
    Validates: Requirements 6.3
    """
    # Test hours
    assert rule_engine._parse_time_range("24h") == 24
    assert rule_engine._parse_time_range("1h") == 1
    
    # Test days
    assert rule_engine._parse_time_range("7d") == 168  # 7 * 24
    assert rule_engine._parse_time_range("1d") == 24
    
    # Test default
    assert rule_engine._parse_time_range("invalid") == 24


@pytest.mark.asyncio
async def test_evaluate_condition_greater_than(rule_engine):
    """
    Test condition evaluation with greater_than operator.
    
    Validates: Requirements 6.3
    """
    # Arrange
    condition = RuleCondition(
        metric="cpa",
        operator="greater_than",
        value=50,
        time_range="24h"
    )
    target = {"id": "adset_123", "type": "adset"}
    
    # Mock _get_metric_value to return 60
    rule_engine._get_metric_value = AsyncMock(return_value=60.0)
    
    # Act
    result = await rule_engine._evaluate_condition(condition, target)
    
    # Assert
    assert result is True


@pytest.mark.asyncio
async def test_evaluate_condition_less_than(rule_engine):
    """
    Test condition evaluation with less_than operator.
    
    Validates: Requirements 6.3
    """
    # Arrange
    condition = RuleCondition(
        metric="roas",
        operator="less_than",
        value=2.0,
        time_range="24h"
    )
    target = {"id": "adset_123", "type": "adset"}
    
    # Mock _get_metric_value to return 1.5
    rule_engine._get_metric_value = AsyncMock(return_value=1.5)
    
    # Act
    result = await rule_engine._evaluate_condition(condition, target)
    
    # Assert
    assert result is True


@pytest.mark.asyncio
async def test_evaluate_condition_metric_not_available(rule_engine):
    """
    Test condition evaluation when metric is not available.
    
    Validates: Requirements 6.3
    """
    # Arrange
    condition = RuleCondition(
        metric="cpa",
        operator="greater_than",
        value=50,
        time_range="24h"
    )
    target = {"id": "adset_123", "type": "adset"}
    
    # Mock _get_metric_value to return None
    rule_engine._get_metric_value = AsyncMock(return_value=None)
    
    # Act
    result = await rule_engine._evaluate_condition(condition, target)
    
    # Assert
    assert result is False


@pytest.mark.asyncio
async def test_check_rules_no_rules(rule_engine, mock_redis_client):
    """
    Test checking rules when no rules exist.
    
    Validates: Requirements 6.3
    """
    # Arrange
    mock_redis_client.keys = AsyncMock(return_value=[])
    
    # Act
    results = await rule_engine.check_rules()
    
    # Assert
    assert len(results) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
