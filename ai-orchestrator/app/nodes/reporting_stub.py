"""Reporting stub module node.

This module implements a stub for the Ad Performance functionality.
Phase 1: Returns mock data but exercises full credit check/deduct flow.

Requirements: 需求 8 (Ad Performance), 需求 12.4 (Error Recovery)
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
CREDIT_GET_REPORT = 1.0
CREDIT_ANALYZE = 2.0


def estimate_reporting_cost(action_type: str) -> float:
    """Estimate credit cost for reporting action."""
    if action_type == "analyze_performance":
        return CREDIT_ANALYZE
    return CREDIT_GET_REPORT


def generate_mock_report(date_range: str) -> dict[str, Any]:
    """Generate mock report data.

    Args:
        date_range: Time range for the report

    Returns:
        Mock report data
    """
    # Generate realistic-looking metrics
    spend = round(random.uniform(500, 2000), 2)
    impressions = random.randint(50000, 200000)
    clicks = random.randint(1000, 5000)
    conversions = random.randint(50, 200)

    ctr = round((clicks / impressions) * 100, 2)
    cpc = round(spend / clicks, 2)
    cpa = round(spend / conversions, 2)
    roas = round(random.uniform(1.5, 4.0), 2)

    return {
        "date_range": date_range,
        "summary": {
            "spend": spend,
            "impressions": impressions,
            "clicks": clicks,
            "conversions": conversions,
            "ctr": ctr,
            "cpc": cpc,
            "cpa": cpa,
            "roas": roas,
        },
        "trends": {
            "spend_change": round(random.uniform(-20, 30), 1),
            "roas_change": round(random.uniform(-10, 20), 1),
            "ctr_change": round(random.uniform(-5, 15), 1),
        },
        "top_campaigns": [
            {
                "id": f"campaign_{i}",
                "name": f"Campaign {i}",
                "spend": round(spend * random.uniform(0.1, 0.3), 2),
                "roas": round(random.uniform(2.0, 5.0), 2),
            }
            for i in range(1, 4)
        ],
        "insights": [
            "📈 ROAS 较上周提升 15%，表现良好",
            "💡 建议增加表现最好的 Campaign 1 的预算",
            "⚠️ Campaign 3 的 CTR 偏低，建议优化素材",
        ],
    }


async def reporting_stub_node(state: AgentState) -> dict[str, Any]:
    """Ad Performance stub node with credit check.

    This stub:
    1. Estimates credit cost
    2. Checks credit via MCP
    3. Simulates data fetching (1s delay)
    4. Deducts credit via MCP
    5. Returns mock report data

    Args:
        state: Current agent state

    Returns:
        State updates with completed results

    Requirements: 需求 8.1-8.5
    """
    log = logger.bind(
        user_id=state.get("user_id"),
        session_id=state.get("session_id"),
        module="reporting_stub",
    )
    log.info("reporting_stub_start")

    # Get action parameters
    pending_actions = state.get("pending_actions", [])
    report_actions = [a for a in pending_actions if a.get("module") == "reporting"]

    if not report_actions:
        log.warning("reporting_stub_no_actions")
        return {"completed_results": []}

    action = report_actions[0]
    action_type = action.get("type", "get_report")
    params = action.get("params", {})
    date_range = params.get("date_range", "last_7_days")

    # Step 1: Estimate cost
    estimated_cost = estimate_reporting_cost(action_type)
    operation_id = f"report_{uuid.uuid4().hex[:12]}"

    log.info(
        "reporting_stub_cost_estimated",
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
                    context="reporting_credit_check",
                )
                log.info("reporting_stub_credit_check_passed")

            except InsufficientCreditsError as e:
                log.warning("reporting_stub_insufficient_credits")
                error_state = ErrorHandler.create_node_error_state(
                    error=e,
                    node_name="reporting_stub",
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
                        "mock": True,
                    }
                ]
                return error_state

            except MCPError as e:
                log.error("reporting_stub_credit_check_failed", error=str(e))
                error_state = ErrorHandler.create_node_error_state(
                    error=e,
                    node_name="reporting_stub",
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
                        "mock": True,
                    }
                ]
                return error_state

            # Step 3: Simulate data fetching
            log.info("reporting_stub_fetching", date_range=date_range)
            await asyncio.sleep(1)

            # Step 4: Generate mock data
            mock_report = generate_mock_report(date_range)

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
                    context="reporting_credit_deduct",
                )
                log.info("reporting_stub_credit_deducted", credits=estimated_cost)

            except MCPError as e:
                log.error("reporting_stub_credit_deduct_failed", error=str(e))

    except Exception as e:
        log.error(
            "reporting_stub_unexpected_error",
            error=str(e),
            exc_info=True,
        )
        error_state = ErrorHandler.create_node_error_state(
            error=e,
            node_name="reporting_stub",
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
                "mock": True,
            }
        ]
        return error_state

    # Step 6: Return result
    result = {
        "action_type": action_type,
        "module": "reporting",
        "status": "success",
        "data": mock_report,
        "error": None,
        "cost": estimated_cost,
        "mock": True,
    }

    log.info("reporting_stub_complete", date_range=date_range)

    return {
        "completed_results": [result],
        "credit_checked": True,
        "credit_sufficient": True,
    }
