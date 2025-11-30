"""Ad Engine stub module node.

This module implements a stub for the Campaign Automation functionality.
Phase 1: Returns mock data but exercises full credit check/deduct flow.

Requirements: 需求 10 (Campaign Automation), 需求 12.4 (Error Recovery)
"""

import asyncio
import random
import uuid
from typing import Any

import structlog

from app.core.errors import ErrorHandler
from app.core.retry import retry_async
from app.core.state import AgentState
from app.services.mcp_client import (
    InsufficientCreditsError,
    MCPClient,
    MCPError,
)

logger = structlog.get_logger(__name__)


# Credit costs
CREDIT_CREATE_CAMPAIGN = 2.0
CREDIT_UPDATE_BUDGET = 0.5
CREDIT_PAUSE = 0.5
CREDIT_OPTIMIZE = 1.5


def estimate_ad_engine_cost(action_type: str) -> float:
    """Estimate credit cost for ad engine action."""
    costs = {
        "create_campaign": CREDIT_CREATE_CAMPAIGN,
        "update_budget": CREDIT_UPDATE_BUDGET,
        "pause_campaign": CREDIT_PAUSE,
        "pause_all": CREDIT_PAUSE,
        "resume_campaign": CREDIT_PAUSE,
        "delete_campaign": CREDIT_PAUSE,
        "optimize_budget": CREDIT_OPTIMIZE,
        "apply_rules": CREDIT_OPTIMIZE,
    }
    return costs.get(action_type, 1.0)


def generate_mock_campaign(params: dict[str, Any]) -> dict[str, Any]:
    """Generate mock campaign data."""
    campaign_id = f"camp_{uuid.uuid4().hex[:8]}"
    budget = params.get("budget", 100)
    target_roas = params.get("target_roas", 3.0)

    return {
        "campaign_id": campaign_id,
        "name": f"Campaign {campaign_id[-4:]}",
        "status": "active",
        "platform": params.get("platform", "facebook"),
        "budget": {
            "daily": budget,
            "currency": "USD",
            "type": "daily",
        },
        "targeting": {
            "objective": params.get("objective", "conversions"),
            "target_roas": target_roas,
            "audience": "自动优化受众",
        },
        "creatives": params.get("creative_ids", []),
        "created_at": "2024-01-15T10:30:00Z",
        "estimated_reach": f"{random.randint(10, 50)}K - {random.randint(50, 100)}K",
    }


def generate_mock_budget_update(params: dict[str, Any]) -> dict[str, Any]:
    """Generate mock budget update result."""
    campaign_id = params.get("campaign_id", "camp_unknown")
    new_budget = params.get("budget", 100)

    return {
        "campaign_id": campaign_id,
        "previous_budget": random.randint(50, 150),
        "new_budget": new_budget,
        "currency": "USD",
        "effective_from": "immediately",
        "status": "updated",
    }


def generate_mock_pause_result(params: dict[str, Any], action_type: str) -> dict[str, Any]:
    """Generate mock pause/resume result."""
    if action_type == "pause_all":
        return {
            "action": "pause_all",
            "campaigns_affected": random.randint(3, 8),
            "status": "paused",
            "message": "所有广告已暂停",
        }

    campaign_id = params.get("campaign_id", "camp_unknown")
    new_status = "paused" if action_type == "pause_campaign" else "active"

    return {
        "campaign_id": campaign_id,
        "previous_status": "active" if new_status == "paused" else "paused",
        "new_status": new_status,
        "message": f"广告已{'暂停' if new_status == 'paused' else '恢复'}",
    }


def generate_mock_optimization(params: dict[str, Any]) -> dict[str, Any]:
    """Generate mock budget optimization result."""
    return {
        "optimization_id": f"opt_{uuid.uuid4().hex[:8]}",
        "campaigns_analyzed": random.randint(3, 8),
        "recommendations": [
            {
                "campaign_id": f"camp_{uuid.uuid4().hex[:4]}",
                "action": "increase_budget",
                "current_budget": 100,
                "recommended_budget": 150,
                "reason": "ROAS 高于目标，建议增加预算",
            },
            {
                "campaign_id": f"camp_{uuid.uuid4().hex[:4]}",
                "action": "decrease_budget",
                "current_budget": 200,
                "recommended_budget": 100,
                "reason": "ROAS 低于目标，建议减少预算",
            },
        ],
        "total_budget_change": "+$50",
        "expected_impact": "预计 ROAS 提升 15%",
    }


async def ad_engine_stub_node(state: AgentState) -> dict[str, Any]:
    """Ad Engine stub node with credit check.

    This stub:
    1. Estimates credit cost
    2. Checks credit via MCP
    3. Simulates campaign operation (1.5s delay)
    4. Deducts credit via MCP
    5. Returns mock campaign data

    Args:
        state: Current agent state

    Returns:
        State updates with completed results

    Requirements: 需求 10.1-10.5
    """
    log = logger.bind(
        user_id=state.get("user_id"),
        session_id=state.get("session_id"),
        module="ad_engine_stub",
    )
    log.info("ad_engine_stub_start")

    # Get action parameters
    pending_actions = state.get("pending_actions", [])
    ad_actions = [a for a in pending_actions if a.get("module") == "ad_engine"]

    if not ad_actions:
        log.warning("ad_engine_stub_no_actions")
        return {"completed_results": []}

    action = ad_actions[0]
    action_type = action.get("type", "create_campaign")
    params = action.get("params", {})

    # Step 1: Estimate cost
    estimated_cost = estimate_ad_engine_cost(action_type)
    operation_id = f"ad_{uuid.uuid4().hex[:12]}"

    log.info(
        "ad_engine_stub_cost_estimated",
        action_type=action_type,
        estimated_cost=estimated_cost,
    )

    try:
        async with MCPClient() as mcp:
            # Step 2: Check credit with retry
            try:
                await retry_async(
                    lambda: mcp.check_credit(
                        user_id=state.get("user_id", ""),
                        estimated_credits=estimated_cost,
                        operation_type=action_type,
                    ),
                    max_retries=3,
                    context="ad_engine_credit_check",
                )
                log.info("ad_engine_stub_credit_check_passed")

            except InsufficientCreditsError as e:
                log.warning("ad_engine_stub_insufficient_credits")
                error_state = ErrorHandler.create_node_error_state(
                    error=e,
                    node_name="ad_engine_stub",
                    user_id=state.get("user_id"),
                    session_id=state.get("session_id"),
                )
                error_state["completed_results"] = [
                    {
                        "action_type": action_type,
                        "module": "ad_engine",
                        "status": "error",
                        "data": {},
                        "error": error_state.get("error"),
                        "cost": 0,
                        "mock": True,
                    }
                ]
                return error_state

            except MCPError as e:
                log.error("ad_engine_stub_credit_check_failed", error=str(e))
                error_state = ErrorHandler.create_node_error_state(
                    error=e,
                    node_name="ad_engine_stub",
                    user_id=state.get("user_id"),
                    session_id=state.get("session_id"),
                )
                error_state["completed_results"] = [
                    {
                        "action_type": action_type,
                        "module": "ad_engine",
                        "status": "error",
                        "data": {},
                        "error": error_state.get("error"),
                        "cost": 0,
                        "mock": True,
                    }
                ]
                return error_state

            # Step 3: Simulate operation
            log.info("ad_engine_stub_executing", action_type=action_type)
            await asyncio.sleep(1.5)

            # Step 4: Generate mock data based on action type
            if action_type == "create_campaign":
                mock_data = generate_mock_campaign(params)
                message = f"✅ 广告创建成功（模拟数据）\n📋 Campaign ID: {mock_data['campaign_id']}"
            elif action_type == "update_budget":
                mock_data = generate_mock_budget_update(params)
                message = f"✅ 预算已更新（模拟数据）\n💰 新预算: ${mock_data['new_budget']}/天"
            elif action_type in ("pause_campaign", "pause_all", "resume_campaign"):
                mock_data = generate_mock_pause_result(params, action_type)
                message = f"✅ {mock_data['message']}（模拟数据）"
            elif action_type in ("optimize_budget", "apply_rules"):
                mock_data = generate_mock_optimization(params)
                message = (
                    f"✅ 优化完成（模拟数据）\n📊 分析了 {mock_data['campaigns_analyzed']} 个广告"
                )
            else:
                mock_data = {"action": action_type, "status": "completed"}
                message = "✅ 操作完成（模拟数据）"

            mock_data["message"] = message

            # Step 5: Deduct credit with retry
            try:
                await retry_async(
                    lambda: mcp.deduct_credit(
                        user_id=state.get("user_id", ""),
                        credits=estimated_cost,
                        operation_type=action_type,
                        operation_id=operation_id,
                    ),
                    max_retries=3,
                    context="ad_engine_credit_deduct",
                )
                log.info("ad_engine_stub_credit_deducted", credits=estimated_cost)

            except MCPError as e:
                log.error("ad_engine_stub_credit_deduct_failed", error=str(e))

    except Exception as e:
        log.error(
            "ad_engine_stub_unexpected_error",
            error=str(e),
            exc_info=True,
        )
        error_state = ErrorHandler.create_node_error_state(
            error=e,
            node_name="ad_engine_stub",
            user_id=state.get("user_id"),
            session_id=state.get("session_id"),
        )
        error_state["completed_results"] = [
            {
                "action_type": action_type,
                "module": "ad_engine",
                "status": "error",
                "data": {},
                "error": error_state.get("error"),
                "cost": 0,
                "mock": True,
            }
        ]
        return error_state

    # Step 6: Return result
    result = {
        "action_type": action_type,
        "module": "ad_engine",
        "status": "success",
        "data": mock_data,
        "error": None,
        "cost": estimated_cost,
        "mock": True,
    }

    log.info("ad_engine_stub_complete", action_type=action_type)

    return {
        "completed_results": [result],
        "credit_checked": True,
        "credit_sufficient": True,
    }
