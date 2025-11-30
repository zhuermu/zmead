"""Landing Page module node.

This module implements the real Landing Page functionality integration.
It replaces the stub with actual capability execution.

Requirements: 需求 9 (Landing Page), 需求 12.4 (Error Recovery)
"""

import uuid
from typing import Any

import structlog

from app.core.errors import ErrorHandler
from app.core.retry import retry_async
from app.core.state import AgentState
from app.modules.landing_page.capability import LandingPage
from app.services.mcp_client import (
    InsufficientCreditsError,
    MCPClient,
    MCPError,
)

logger = structlog.get_logger(__name__)


# Credit costs for landing page operations
CREDIT_COSTS = {
    "parse_product": 1.0,
    "generate_landing_page": 3.0,
    "update_landing_page": 0.5,
    "optimize_copy": 1.0,
    "translate_landing_page": 1.0,
    "create_ab_test": 2.0,
    "analyze_ab_test": 0.5,
    "publish_landing_page": 0.5,
    "export_landing_page": 0.5,
}


def estimate_landing_page_cost(action_type: str, params: dict[str, Any]) -> float:
    """Estimate credit cost for landing page action.
    
    Args:
        action_type: Type of landing page action
        params: Action parameters
        
    Returns:
        Estimated credit cost
    """
    base_cost = CREDIT_COSTS.get(action_type, 1.0)
    
    # Adjust for specific parameters
    if action_type == "translate_landing_page":
        # Multiple sections increase cost
        sections = params.get("sections_to_translate", [])
        if sections and len(sections) > 3:
            base_cost *= 1.5
    
    return base_cost


async def landing_page_node(state: AgentState) -> dict[str, Any]:
    """Landing Page module node with real capability execution.

    This node:
    1. Estimates credit cost
    2. Checks credit via MCP
    3. Executes landing page capability
    4. Deducts credit via MCP
    5. Returns actual results

    Args:
        state: Current agent state

    Returns:
        State updates with completed results

    Requirements: 需求 9.1-9.5, All landing page requirements
    """
    log = logger.bind(
        user_id=state.get("user_id"),
        session_id=state.get("session_id"),
        module="landing_page",
    )
    log.info("landing_page_node_start")

    # Get action parameters
    pending_actions = state.get("pending_actions", [])
    completed_results = state.get("completed_results", [])
    
    # Find the next landing page action to execute
    lp_actions = [
        (idx, a) for idx, a in enumerate(pending_actions) 
        if a.get("module") == "landing_page" and idx >= len(completed_results)
    ]

    if not lp_actions:
        log.warning("landing_page_node_no_actions")
        return {"completed_results": completed_results}

    action_idx, action = lp_actions[0]
    action_type = action.get("type", "generate_landing_page")
    params = action.get("params", {})

    # Step 1: Estimate cost
    estimated_cost = estimate_landing_page_cost(action_type, params)
    operation_id = f"lp_{uuid.uuid4().hex[:12]}"

    log.info(
        "landing_page_node_cost_estimated",
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
                    context="landing_page_credit_check",
                )
                log.info("landing_page_node_credit_check_passed")

            except InsufficientCreditsError as e:
                log.warning("landing_page_node_insufficient_credits")
                error_state = ErrorHandler.create_node_error_state(
                    error=e,
                    node_name="landing_page",
                    user_id=state.get("user_id"),
                    session_id=state.get("session_id"),
                )
                
                result = {
                    "action_type": action_type,
                    "module": "landing_page",
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
                log.error("landing_page_node_credit_check_failed", error=str(e))
                error_state = ErrorHandler.create_node_error_state(
                    error=e,
                    node_name="landing_page",
                    user_id=state.get("user_id"),
                    session_id=state.get("session_id"),
                )
                
                result = {
                    "action_type": action_type,
                    "module": "landing_page",
                    "status": "error",
                    "data": {},
                    "error": error_state.get("error"),
                    "cost": 0,
                }
                
                return {
                    **error_state,
                    "completed_results": completed_results + [result],
                }

            # Step 3: Execute landing page capability
            log.info("landing_page_node_executing", action_type=action_type)
            
            # Initialize landing page capability
            # Get API base URL from environment or use default
            import os
            config = {
                "api_base_url": os.environ.get("API_BASE_URL", "https://api.aae.com"),
            }
            
            landing_page = LandingPage(
                mcp_client=mcp,
                redis_client=state.get("redis_client"),
                config=config,
            )
            
            # Build context for capability
            context = {
                "user_id": state.get("user_id"),
                "session_id": state.get("session_id"),
            }
            
            # Execute the action
            capability_result = await landing_page.execute(
                action=action_type,
                parameters=params,
                context=context,
            )
            
            log.info(
                "landing_page_node_capability_executed",
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
                        context="landing_page_credit_deduct",
                    )
                    log.info("landing_page_node_credit_deducted", credits=actual_cost)

                except MCPError as e:
                    log.error("landing_page_node_credit_deduct_failed", error=str(e))
                    # Continue - credit deduction failure shouldn't fail the operation
            else:
                # Don't charge for failed operations
                actual_cost = 0
                log.info("landing_page_node_no_charge_for_failure")

    except Exception as e:
        log.error(
            "landing_page_node_unexpected_error",
            error=str(e),
            exc_info=True,
        )
        error_state = ErrorHandler.create_node_error_state(
            error=e,
            node_name="landing_page",
            user_id=state.get("user_id"),
            session_id=state.get("session_id"),
        )
        
        result = {
            "action_type": action_type,
            "module": "landing_page",
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
            "module": "landing_page",
            "status": "success",
            "data": capability_result,
            "error": None,
            "cost": actual_cost,
        }
    else:
        # Capability returned an error
        result = {
            "action_type": action_type,
            "module": "landing_page",
            "status": "error",
            "data": capability_result,
            "error": capability_result.get("error"),
            "cost": actual_cost,
        }

    log.info(
        "landing_page_node_complete",
        action_type=action_type,
        status=result["status"],
        cost=actual_cost,
    )

    return {
        "completed_results": completed_results + [result],
        "credit_checked": True,
        "credit_sufficient": True,
    }
