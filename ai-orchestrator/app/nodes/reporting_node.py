"""Reporting module node with Ad Performance integration.

This module implements the Ad Performance functionality by delegating to
the AdPerformance capability module. It handles:
- Action routing to Ad Performance module
- Credit management with proper error handling
- Result formatting for AI Orchestrator
- Error recovery and retry logic

Requirements: 需求 8 (Ad Performance), 需求 12.4 (Error Recovery)
"""

import uuid
from typing import Any

import structlog

from app.core.errors import ErrorHandler
from app.core.retry import retry_async
from app.core.state import AgentState
from app.modules import AdPerformance
from app.services.mcp_client import (
    InsufficientCreditsError,
    MCPClient,
    MCPError,
)

logger = structlog.get_logger(__name__)


# Credit costs for different actions
CREDIT_COSTS = {
    "get_report": 1.0,
    "analyze_performance": 2.0,
    "detect_anomaly": 1.5,
    "generate_recommendations": 2.0,
    "export_report": 1.0,
    "get_metrics_summary": 0.5,
}



def estimate_reporting_cost(action_type: str, params: dict[str, Any]) -> float:
    """Estimate credit cost for reporting action.

    Args:
        action_type: Type of reporting action
        params: Action parameters

    Returns:
        Estimated credit cost
    """
    return CREDIT_COSTS.get(action_type, 1.0)


def map_action_type(action_type: str) -> str:
    """Map AI Orchestrator action types to Ad Performance action types.
    
    Args:
        action_type: AI Orchestrator action type
        
    Returns:
        Ad Performance action type
    """
    # Map common action types
    action_map = {
        "get_report": "get_metrics_summary",
        "analyze_performance": "analyze_performance",
        "detect_anomaly": "detect_anomalies",
        "generate_recommendations": "generate_recommendations",
        "export_report": "export_report",
    }
    
    return action_map.get(action_type, action_type)


async def reporting_node(state: AgentState) -> dict[str, Any]:
    """Ad Performance node with Ad Performance module integration.

    This node:
    1. Estimates credit cost
    2. Checks credit via MCP
    3. Delegates to AdPerformance capability module
    4. Deducts credit via MCP
    5. Returns formatted results

    Args:
        state: Current agent state

    Returns:
        State updates with completed results

    Requirements: 需求 8.1-8.5, Task 14
    """
    log = logger.bind(
        user_id=state.get("user_id"),
        session_id=state.get("session_id"),
        module="reporting",
    )
    log.info("reporting_node_start")

    # Get action parameters
    pending_actions = state.get("pending_actions", [])
    report_actions = [a for a in pending_actions if a.get("module") == "reporting"]

    if not report_actions:
        log.warning("reporting_node_no_actions")
        return {"completed_results": []}

    action = report_actions[0]
    action_type = action.get("type", "get_report")
    params = action.get("params", {})

    # Step 1: Estimate cost
    estimated_cost = estimate_reporting_cost(action_type, params)
    operation_id = f"report_{uuid.uuid4().hex[:12]}"

    log.info(
        "reporting_node_cost_estimated",
        action_type=action_type,
        estimated_cost=estimated_cost,
        params=params,
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
                    context="reporting_credit_check",
                )
                log.info("reporting_node_credit_check_passed")

            except InsufficientCreditsError as e:
                log.warning("reporting_node_insufficient_credits")
                error_state = ErrorHandler.create_node_error_state(
                    error=e,
                    node_name="reporting",
                    user_id=state.get("user_id"),
                    session_id=state.get("session_id"),
                )
                error_state["completed_results"] = [
                    {
                        "action_type": action_type,
                        "module": "reporting",
                        "status": "error",
                        "data": {},
                        "error": error_state.get("error"),
                        "cost": 0,
                        "mock": False,
                    }
                ]
                return error_state

            except MCPError as e:
                log.error("reporting_node_credit_check_failed", error=str(e))
                error_state = ErrorHandler.create_node_error_state(
                    error=e,
                    node_name="reporting",
                    user_id=state.get("user_id"),
                    session_id=state.get("session_id"),
                )
                error_state["completed_results"] = [
                    {
                        "action_type": action_type,
                        "module": "reporting",
                        "status": "error",
                        "data": {},
                        "error": error_state.get("error"),
                        "cost": 0,
                        "mock": False,
                    }
                ]
                return error_state

            # Step 3: Initialize Ad Performance module
            ad_performance = AdPerformance(mcp_client=mcp)
            
            # Map action type to Ad Performance action
            mapped_action = map_action_type(action_type)
            
            log.info(
                "calling_ad_performance_module",
                action=mapped_action,
                original_action=action_type,
            )

            # Step 4: Call Ad Performance module
            try:
                result = await retry_async(
                    lambda: ad_performance.execute(
                        action=mapped_action,
                        parameters=params,
                        context={
                            "user_id": state.get("user_id", ""),
                            "session_id": state.get("session_id", ""),
                        },
                    ),
                    max_retries=3,
                    context="ad_performance_execute",
                )
                
                log.info(
                    "ad_performance_module_complete",
                    status=result.get("status"),
                )

            except Exception as e:
                log.error(
                    "ad_performance_module_error",
                    error=str(e),
                    exc_info=True,
                )
                error_state = ErrorHandler.create_node_error_state(
                    error=e,
                    node_name="reporting",
                    user_id=state.get("user_id"),
                    session_id=state.get("session_id"),
                )
                error_state["completed_results"] = [
                    {
                        "action_type": action_type,
                        "module": "reporting",
                        "status": "error",
                        "data": {},
                        "error": error_state.get("error"),
                        "cost": 0,
                        "mock": False,
                    }
                ]
                return error_state

            # Step 5: Deduct credit if successful
            if result.get("status") == "success":
                try:
                    await retry_async(
                        lambda: mcp.deduct_credit(
                            user_id=state.get("user_id", ""),
                            credits=estimated_cost,
                            operation_type=action_type,
                            operation_id=operation_id,
                        ),
                        max_retries=3,
                        context="reporting_credit_deduct",
                    )
                    log.info("reporting_node_credit_deducted", credits=estimated_cost)

                except MCPError as e:
                    log.error("reporting_node_credit_deduct_failed", error=str(e))

    except Exception as e:
        log.error(
            "reporting_node_unexpected_error",
            error=str(e),
            exc_info=True,
        )
        error_state = ErrorHandler.create_node_error_state(
            error=e,
            node_name="reporting",
            user_id=state.get("user_id"),
            session_id=state.get("session_id"),
        )
        error_state["completed_results"] = [
            {
                "action_type": action_type,
                "module": "reporting",
                "status": "error",
                "data": {},
                "error": error_state.get("error"),
                "cost": 0,
                "mock": False,
            }
        ]
        return error_state

    # Step 6: Format result for AI Orchestrator
    formatted_result = {
        "action_type": action_type,
        "module": "reporting",
        "status": result.get("status", "error"),
        "data": result.get("data", result.get("summary", {})),
        "error": result.get("error"),
        "cost": estimated_cost if result.get("status") == "success" else 0,
        "mock": False,
    }
    
    # Add notifications if present
    if "notifications" in result:
        formatted_result["notifications"] = result["notifications"]

    log.info("reporting_node_complete", action_type=action_type, status=result.get("status"))

    return {
        "completed_results": [formatted_result],
        "credit_checked": True,
        "credit_sufficient": True,
    }
