"""Market Insights module node.

This module implements the real Market Insights functionality integration.
It replaces the stub with actual capability execution.

Requirements: 需求 1-7 (Market Insights), 需求 12.4 (Error Recovery)
"""

import os
import uuid
from typing import Any

import structlog

from app.core.errors import ErrorHandler
from app.core.retry import retry_async
from app.core.state import AgentState
from app.modules.market_insights.capability import MarketInsights
from app.services.mcp_client import (
    InsufficientCreditsError,
    MCPClient,
    MCPError,
)

logger = structlog.get_logger(__name__)


# Credit costs for market insights operations
CREDIT_COSTS = {
    "analyze_competitor": 2.0,
    "get_trending_creatives": 1.0,
    "analyze_creative_trend": 1.5,
    "get_market_trends": 1.0,
    "generate_ad_strategy": 3.0,
    "track_strategy_performance": 0.5,
}


def estimate_market_insights_cost(action_type: str, params: dict[str, Any]) -> float:
    """Estimate credit cost for market insights action.
    
    Args:
        action_type: Type of market insights action
        params: Action parameters
        
    Returns:
        Estimated credit cost
    """
    base_cost = CREDIT_COSTS.get(action_type, 1.0)
    
    # Adjust for specific parameters
    if action_type == "generate_ad_strategy":
        # Including competitor and trend analysis increases cost
        if params.get("competitor_analysis", True):
            base_cost += 0.5
        if params.get("trend_analysis", True):
            base_cost += 0.5
    
    if action_type == "get_market_trends":
        # More keywords increase cost
        keywords = params.get("keywords", [])
        if len(keywords) > 3:
            base_cost *= 1.2
    
    return base_cost


async def market_insights_node(state: AgentState) -> dict[str, Any]:
    """Market Insights module node with real capability execution.

    This node:
    1. Estimates credit cost
    2. Checks credit via MCP
    3. Executes market insights capability
    4. Deducts credit via MCP
    5. Returns actual results

    Args:
        state: Current agent state

    Returns:
        State updates with completed results

    Requirements: 需求 1.1-1.5, 2.1-2.5, 3.1-3.5, 4.1-4.5, 5.1-5.5, 6.1-6.6, 7.1-7.5
    """
    log = logger.bind(
        user_id=state.get("user_id"),
        session_id=state.get("session_id"),
        module="market_insights",
    )
    log.info("market_insights_node_start")

    # Get action parameters
    pending_actions = state.get("pending_actions", [])
    completed_results = state.get("completed_results", [])
    
    # Find the next market insights action to execute
    mi_actions = [
        (idx, a) for idx, a in enumerate(pending_actions) 
        if a.get("module") == "market_insights" and idx >= len(completed_results)
    ]

    if not mi_actions:
        log.warning("market_insights_node_no_actions")
        return {"completed_results": completed_results}

    action_idx, action = mi_actions[0]
    action_type = action.get("type", "analyze_competitor")
    params = action.get("params", {})

    # Step 1: Estimate cost
    estimated_cost = estimate_market_insights_cost(action_type, params)
    operation_id = f"mi_{uuid.uuid4().hex[:12]}"

    log.info(
        "market_insights_node_cost_estimated",
        action_type=action_type,
        estimated_cost=estimated_cost,
        action_index=action_idx,
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
                    context="market_insights_credit_check",
                )
                log.info("market_insights_node_credit_check_passed")

            except InsufficientCreditsError as e:
                log.warning("market_insights_node_insufficient_credits")
                error_state = ErrorHandler.create_node_error_state(
                    error=e,
                    node_name="market_insights",
                    user_id=state.get("user_id"),
                    session_id=state.get("session_id"),
                )
                
                result = {
                    "action_type": action_type,
                    "module": "market_insights",
                    "status": "error",
                    "data": {},
                    "error": error_state.get("error"),
                    "cost": 0,
                }
                
                return {
                    **error_state,
                    "completed_results": completed_results + [result],
                }

            except MCPError as e:
                log.error("market_insights_node_credit_check_failed", error=str(e))
                error_state = ErrorHandler.create_node_error_state(
                    error=e,
                    node_name="market_insights",
                    user_id=state.get("user_id"),
                    session_id=state.get("session_id"),
                )
                
                result = {
                    "action_type": action_type,
                    "module": "market_insights",
                    "status": "error",
                    "data": {},
                    "error": error_state.get("error"),
                    "cost": 0,
                }
                
                return {
                    **error_state,
                    "completed_results": completed_results + [result],
                }

            # Step 3: Execute market insights capability
            log.info("market_insights_node_executing", action_type=action_type)
            
            # Initialize market insights capability
            market_insights = MarketInsights(
                mcp_client=mcp,
                redis_client=state.get("redis_client"),
            )
            
            # Build context for capability
            context = {
                "user_id": state.get("user_id"),
                "session_id": state.get("session_id"),
            }
            
            # Execute the action
            capability_result = await market_insights.execute(
                action=action_type,
                parameters=params,
                context=context,
            )
            
            log.info(
                "market_insights_node_capability_executed",
                action_type=action_type,
                status=capability_result.get("status"),
            )

            # Step 4: Deduct credit with retry (only if successful)
            actual_cost = estimated_cost
            if capability_result.get("status") == "success":
                try:
                    await retry_async(
                        lambda: mcp.deduct_credit(
                            user_id=state.get("user_id", ""),
                            credits=actual_cost,
                            operation_type=action_type,
                            operation_id=operation_id,
                        ),
                        max_retries=3,
                        context="market_insights_credit_deduct",
                    )
                    log.info("market_insights_node_credit_deducted", credits=actual_cost)

                except MCPError as e:
                    log.error("market_insights_node_credit_deduct_failed", error=str(e))
                    # Continue - credit deduction failure shouldn't fail the operation
            else:
                # Don't charge for failed operations
                actual_cost = 0
                log.info("market_insights_node_no_charge_for_failure")

    except Exception as e:
        log.error(
            "market_insights_node_unexpected_error",
            error=str(e),
            exc_info=True,
        )
        error_state = ErrorHandler.create_node_error_state(
            error=e,
            node_name="market_insights",
            user_id=state.get("user_id"),
            session_id=state.get("session_id"),
        )
        
        result = {
            "action_type": action_type,
            "module": "market_insights",
            "status": "error",
            "data": {},
            "error": error_state.get("error"),
            "cost": 0,
        }
        
        return {
            **error_state,
            "completed_results": completed_results + [result],
        }

    # Step 5: Build result
    if capability_result.get("status") == "success":
        result = {
            "action_type": action_type,
            "module": "market_insights",
            "status": "success",
            "data": capability_result,
            "error": None,
            "cost": actual_cost,
        }
    else:
        # Capability returned an error
        result = {
            "action_type": action_type,
            "module": "market_insights",
            "status": "error",
            "data": capability_result,
            "error": capability_result.get("error"),
            "cost": actual_cost,
        }

    log.info(
        "market_insights_node_complete",
        action_type=action_type,
        status=result["status"],
        cost=actual_cost,
    )

    return {
        "completed_results": completed_results + [result],
        "credit_checked": True,
        "credit_sufficient": True,
    }
