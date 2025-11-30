"""Creative stub module node.

This module implements a stub for the Ad Creative functionality.
Phase 1: Returns mock data but exercises full credit check/deduct flow.

Requirements: 需求 6 (Ad Creative), 需求 12.4 (Error Recovery)
"""

import asyncio
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


# Credit cost per creative
CREDIT_PER_CREATIVE = 0.5


def estimate_creative_cost(params: dict[str, Any]) -> float:
    """Estimate credit cost for creative generation.

    Args:
        params: Action parameters

    Returns:
        Estimated credit cost
    """
    count = params.get("count", 10)
    return count * CREDIT_PER_CREATIVE


def generate_mock_creatives(count: int) -> list[dict[str, Any]]:
    """Generate mock creative data.

    Args:
        count: Number of creatives to generate

    Returns:
        List of mock creative dicts
    """
    styles = ["简约风格", "现代风格", "活力风格", "商务风格", "时尚风格"]

    creatives = []
    for i in range(count):
        style = styles[i % len(styles)]
        creatives.append(
            {
                "id": f"mock_creative_{uuid.uuid4().hex[:8]}",
                "name": f"{style}-{i + 1:02d}.jpg",
                "url": f"https://mock.storage.com/creatives/{uuid.uuid4().hex}.jpg",
                "score": 85 + (i % 15),  # Scores between 85-99
                "style": style,
                "status": "ready",
            }
        )

    return creatives


async def creative_stub_node(state: AgentState) -> dict[str, Any]:
    """Ad Creative stub node with credit check.

    This stub:
    1. Estimates credit cost
    2. Checks credit via MCP
    3. Simulates processing (2s delay)
    4. Deducts credit via MCP
    5. Returns mock creative data

    Args:
        state: Current agent state

    Returns:
        State updates with completed results

    Requirements: 需求 6.1-6.5
    """
    log = logger.bind(
        user_id=state.get("user_id"),
        session_id=state.get("session_id"),
        module="creative_stub",
    )
    log.info("creative_stub_start")

    # Get action parameters
    pending_actions = state.get("pending_actions", [])
    creative_actions = [a for a in pending_actions if a.get("module") == "creative"]

    if not creative_actions:
        log.warning("creative_stub_no_actions")
        return {"completed_results": []}

    action = creative_actions[0]
    params = action.get("params", {})
    count = params.get("count", 10)

    # Step 1: Estimate cost
    estimated_cost = estimate_creative_cost(params)
    operation_id = f"creative_{uuid.uuid4().hex[:12]}"

    log.info(
        "creative_stub_cost_estimated",
        count=count,
        estimated_cost=estimated_cost,
        operation_id=operation_id,
    )

    try:
        async with MCPClient() as mcp:
            # Step 2: Check credit with retry
            try:
                await retry_async(
                    lambda: mcp.check_credit(
                        user_id=state.get("user_id", ""),
                        estimated_credits=estimated_cost,
                        operation_type="generate_creative",
                    ),
                    max_retries=3,
                    context="creative_credit_check",
                )
                log.info("creative_stub_credit_check_passed")

            except InsufficientCreditsError as e:
                log.warning(
                    "creative_stub_insufficient_credits",
                    required=e.required,
                    available=e.available,
                )
                error_state = ErrorHandler.create_node_error_state(
                    error=e,
                    node_name="creative_stub",
                    user_id=state.get("user_id"),
                    session_id=state.get("session_id"),
                )
                error_state["completed_results"] = [
                    {
                        "action_type": "generate_creative",
                        "module": "creative",
                        "status": "error",
                        "data": {},
                        "error": error_state.get("error"),
                        "cost": 0,
                        "mock": True,
                    }
                ]
                return error_state

            except MCPError as e:
                log.error("creative_stub_credit_check_failed", error=str(e))
                error_state = ErrorHandler.create_node_error_state(
                    error=e,
                    node_name="creative_stub",
                    user_id=state.get("user_id"),
                    session_id=state.get("session_id"),
                )
                error_state["completed_results"] = [
                    {
                        "action_type": "generate_creative",
                        "module": "creative",
                        "status": "error",
                        "data": {},
                        "error": error_state.get("error"),
                        "cost": 0,
                        "mock": True,
                    }
                ]
                return error_state

            # Step 3: Simulate processing
            log.info("creative_stub_processing", count=count)
            await asyncio.sleep(2)  # Simulate generation time

            # Step 4: Generate mock data
            mock_creatives = generate_mock_creatives(count)

            # Step 5: Deduct credit with retry
            try:
                await retry_async(
                    lambda: mcp.deduct_credit(
                        user_id=state.get("user_id", ""),
                        credits=estimated_cost,
                        operation_type="generate_creative",
                        operation_id=operation_id,
                        details={
                            "count": count,
                            "mock": True,
                        },
                    ),
                    max_retries=3,
                    context="creative_credit_deduct",
                )
                log.info(
                    "creative_stub_credit_deducted",
                    credits=estimated_cost,
                    operation_id=operation_id,
                )

            except MCPError as e:
                # Log but don't fail - we already generated the creatives
                log.error(
                    "creative_stub_credit_deduct_failed",
                    error=str(e),
                    operation_id=operation_id,
                )

    except Exception as e:
        # Catch any unexpected errors
        log.error(
            "creative_stub_unexpected_error",
            error=str(e),
            exc_info=True,
        )
        error_state = ErrorHandler.create_node_error_state(
            error=e,
            node_name="creative_stub",
            user_id=state.get("user_id"),
            session_id=state.get("session_id"),
        )
        error_state["completed_results"] = [
            {
                "action_type": "generate_creative",
                "module": "creative",
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
        "action_type": "generate_creative",
        "module": "creative",
        "status": "success",
        "data": {
            "creatives": mock_creatives,
            "creative_ids": [c["id"] for c in mock_creatives],
            "count": count,
            "message": f"✅ 已生成 {count} 张素材（模拟数据）",
        },
        "error": None,
        "cost": estimated_cost,
        "mock": True,
    }

    log.info(
        "creative_stub_complete",
        count=count,
        cost=estimated_cost,
    )

    return {
        "completed_results": [result],
        "credit_checked": True,
        "credit_sufficient": True,
    }
