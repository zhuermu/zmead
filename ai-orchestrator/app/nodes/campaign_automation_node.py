"""Campaign Automation module node with real implementation.

This module implements the Campaign Automation functionality with:
- Automated campaign structure generation (Campaign/Adset/Ad)
- Multi-platform support (Meta, TikTok, Google Ads)
- Budget optimization based on performance
- A/B testing with statistical analysis
- Rule-based automation
- AI-powered ad copy generation
- Credit management with refund on failure

Requirements: 需求 10 (Campaign Automation), 需求 12.4 (Error Recovery)
"""

import uuid
from typing import Any

import structlog

from app.core.errors import ErrorHandler
from app.core.retry import retry_async
from app.core.state import AgentState
from app.modules.campaign_automation.capability import CampaignAutomation
from app.services.mcp_client import (
    InsufficientCreditsError,
    MCPClient,
    MCPError,
)

logger = structlog.get_logger(__name__)


# Credit costs per action type
CREDIT_COSTS = {
    "create_campaign": 2.0,
    "optimize_budget": 1.5,
    "manage_campaign": 0.5,
    "create_ab_test": 2.0,
    "analyze_ab_test": 1.0,
    "create_rule": 0.5,
    "get_campaign_status": 0.5,
}


def estimate_campaign_automation_cost(action_type: str, params: dict[str, Any]) -> float:
    """Estimate credit cost for campaign automation action.
    
    Args:
        action_type: Type of action
        params: Action parameters
        
    Returns:
        Estimated credit cost
    """
    base_cost = CREDIT_COSTS.get(action_type, 1.0)
    
    # Adjust for quantity parameters
    if action_type == "create_campaign":
        # Cost scales with number of creatives
        creative_count = len(params.get("creative_ids", []))
        if creative_count > 5:
            base_cost *= 1.5
    elif action_type == "create_ab_test":
        # Cost scales with number of variants
        variant_count = len(params.get("creative_ids", []))
        base_cost = base_cost * max(1, variant_count / 3)
    
    return base_cost


async def campaign_automation_node(state: AgentState) -> dict[str, Any]:
    """Campaign Automation node with real implementation.

    This node:
    1. Estimates credit cost
    2. Checks credit via MCP
    3. Executes campaign automation action via CampaignAutomation capability
    4. Deducts credit via MCP
    5. Refunds credit on failure

    Args:
        state: Current agent state

    Returns:
        State updates with completed results

    Requirements: 需求 10.1-10.5
    """
    log = logger.bind(
        user_id=state.get("user_id"),
        session_id=state.get("session_id"),
        module="campaign_automation",
    )
    log.info("campaign_automation_node_start")

    # Get action parameters
    pending_actions = state.get("pending_actions", [])
    campaign_actions = [a for a in pending_actions if a.get("module") == "ad_engine"]

    if not campaign_actions:
        log.warning("campaign_automation_node_no_actions")
        return {"completed_results": []}

    action = campaign_actions[0]
    action_type = action.get("type", "create_campaign")
    params = action.get("params", {})

    # Step 1: Estimate cost
    estimated_cost = estimate_campaign_automation_cost(action_type, params)
    operation_id = f"campaign_{uuid.uuid4().hex[:12]}"

    log.info(
        "campaign_automation_node_cost_estimated",
        action_type=action_type,
        estimated_cost=estimated_cost,
        operation_id=operation_id,
    )

    credit_deducted = False
    actual_cost = estimated_cost

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
                    context="campaign_automation_credit_check",
                )
                log.info("campaign_automation_node_credit_check_passed")

            except InsufficientCreditsError as e:
                log.warning(
                    "campaign_automation_node_insufficient_credits",
                    required=e.required,
                    available=e.available,
                )
                error_state = ErrorHandler.create_node_error_state(
                    error=e,
                    node_name="campaign_automation",
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
                        "mock": False,
                    }
                ]
                return error_state

            except MCPError as e:
                log.error("campaign_automation_node_credit_check_failed", error=str(e))
                error_state = ErrorHandler.create_node_error_state(
                    error=e,
                    node_name="campaign_automation",
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
                        "mock": False,
                    }
                ]
                return error_state

            # Step 3: Execute campaign automation action
            log.info("campaign_automation_node_executing", action_type=action_type)

            # Initialize Campaign Automation capability
            campaign_automation = CampaignAutomation(mcp_client=mcp)

            # Build context
            context = {
                "user_id": state.get("user_id"),
                "session_id": state.get("session_id"),
            }

            # Execute action with retry
            result = await retry_async(
                lambda: campaign_automation.execute(
                    action=action_type,
                    parameters=params,
                    context=context,
                ),
                max_retries=3,
                context=f"campaign_automation_{action_type}",
            )

            log.info(
                "campaign_automation_node_action_complete",
                action_type=action_type,
                status=result.get("status"),
            )

            # Check if action succeeded
            if result.get("status") != "success":
                # Action failed, don't deduct credit
                error_info = result.get("error", {})
                log.warning(
                    "campaign_automation_node_action_failed",
                    action_type=action_type,
                    error=error_info,
                )

                return {
                    "completed_results": [
                        {
                            "action_type": action_type,
                            "module": "ad_engine",
                            "status": "error",
                            "data": result.get("data", {}),
                            "error": error_info,
                            "cost": 0,
                            "mock": False,
                        }
                    ],
                    "credit_checked": True,
                    "credit_sufficient": True,
                }

            # Step 4: Deduct credit for successful operation
            try:
                await retry_async(
                    lambda: mcp.deduct_credit(
                        user_id=state.get("user_id", ""),
                        credits=actual_cost,
                        operation_type=action_type,
                        operation_id=operation_id,
                        details={
                            "action": action_type,
                            "params": params,
                        },
                    ),
                    max_retries=3,
                    context="campaign_automation_credit_deduct",
                )
                credit_deducted = True
                log.info(
                    "campaign_automation_node_credit_deducted",
                    credits=actual_cost,
                    operation_id=operation_id,
                )

            except MCPError as e:
                log.error(
                    "campaign_automation_node_credit_deduct_failed",
                    error=str(e),
                    operation_id=operation_id,
                )

    except Exception as e:
        # Step 5: Refund credit on unexpected failure
        log.error(
            "campaign_automation_node_unexpected_error",
            error=str(e),
            exc_info=True,
        )

        # Attempt refund if credit was deducted
        if credit_deducted and actual_cost > 0:
            try:
                async with MCPClient() as mcp:
                    await mcp.refund_credit(
                        user_id=state.get("user_id", ""),
                        credits=actual_cost,
                        operation_type=action_type,
                        operation_id=operation_id,
                        reason=f"Operation failed: {str(e)}",
                    )
                    log.info(
                        "campaign_automation_node_credit_refunded",
                        credits=actual_cost,
                        operation_id=operation_id,
                    )
            except MCPError as refund_error:
                log.error(
                    "campaign_automation_node_refund_failed",
                    error=str(refund_error),
                    operation_id=operation_id,
                )

        error_state = ErrorHandler.create_node_error_state(
            error=e,
            node_name="campaign_automation",
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
                "cost": actual_cost if credit_deducted else 0,
                "mock": False,
            }
        ]
        return error_state

    # Build success result
    success_result = {
        "action_type": action_type,
        "module": "ad_engine",
        "status": "success",
        "data": result.get("data", result),
        "error": None,
        "cost": actual_cost,
        "mock": False,
    }

    log.info(
        "campaign_automation_node_complete",
        action_type=action_type,
        cost=actual_cost,
    )

    return {
        "completed_results": [success_result],
        "credit_checked": True,
        "credit_sufficient": True,
    }
