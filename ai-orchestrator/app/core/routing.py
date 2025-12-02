"""Conditional routing logic for LangGraph.

This module implements routing functions that determine which node
to execute next based on the current state.

Architecture: Planning + Multi-step Execution
"""

from typing import Literal

import structlog

from app.core.state import AgentState

logger = structlog.get_logger(__name__)


# =========================================================================
# Node Names
# =========================================================================

NODE_ROUTER = "router"
NODE_PLANNER = "planner"
NODE_EXECUTOR = "executor"
NODE_ANALYZER = "analyzer"
NODE_RESPOND = "respond"
NODE_PERSIST = "persist"
NODE_END = "__end__"


def route_after_router_v2(
    state: AgentState,
) -> Literal["planner", "respond"]:
    """Route after router node.

    Routes to planner for task decomposition, or directly
    to respond for simple queries/errors.

    Args:
        state: Current agent state

    Returns:
        Next node name
    """
    log = logger.bind(
        user_id=state.get("user_id"),
        session_id=state.get("session_id"),
    )

    # Check for errors
    if state.get("error"):
        log.info("route_after_router_error")
        return "respond"

    intent = state.get("current_intent")

    # Handle clarification needed - respond directly
    if intent == "clarification_needed":
        log.info("route_after_router_clarification")
        return "respond"

    # Handle general query - respond directly
    if intent == "general_query":
        log.info("route_after_router_general")
        return "respond"

    # All other intents go to planner
    log.info("route_after_router_planner", intent=intent)
    return "planner"


def route_after_planner(
    state: AgentState,
) -> Literal["executor", "respond", "__end__"]:
    """Route after planner node.

    Routes to executor if plan is confirmed,
    to __end__ if plan needs confirmation,
    to respond if error occurred.

    Args:
        state: Current agent state

    Returns:
        Next node name
    """
    log = logger.bind(
        user_id=state.get("user_id"),
        session_id=state.get("session_id"),
    )

    # Check for errors
    if state.get("error"):
        log.info("route_after_planner_error")
        return "respond"

    # Check if plan requires confirmation
    plan_confirmed = state.get("plan_confirmed", False)

    if not plan_confirmed:
        # Plan needs confirmation - message already added by planner
        log.info("route_after_planner_needs_confirmation")
        return "__end__"  # End and wait for user confirmation

    # Plan confirmed, start execution
    log.info("route_after_planner_execute")
    return "executor"


def route_after_executor(
    state: AgentState,
) -> Literal["analyzer", "respond"]:
    """Route after executor node.

    Always routes to analyzer for decision making,
    unless critical error occurred.

    Args:
        state: Current agent state

    Returns:
        Next node name
    """
    log = logger.bind(
        user_id=state.get("user_id"),
        session_id=state.get("session_id"),
    )

    # Check for critical errors
    error = state.get("error")
    if error and error.get("type") == "CRITICAL":
        log.info("route_after_executor_critical_error")
        return "respond"

    # Always go to analyzer for decision
    log.info("route_after_executor_analyzer")
    return "analyzer"


def route_after_analyzer(
    state: AgentState,
) -> Literal["executor", "planner", "respond"]:
    """Route after analyzer node.

    Routes based on analyzer's decision:
    - continue: back to executor for next step
    - respond: to respond node (done or error)
    - replan: back to planner

    Args:
        state: Current agent state

    Returns:
        Next node name
    """
    log = logger.bind(
        user_id=state.get("user_id"),
        session_id=state.get("session_id"),
    )

    decision = state.get("analyzer_decision", "respond")
    execution_complete = state.get("execution_complete", False)

    log.info(
        "route_after_analyzer",
        decision=decision,
        execution_complete=execution_complete,
    )

    if execution_complete or decision == "respond":
        return "respond"

    if decision == "continue":
        return "executor"

    if decision == "replan":
        return "planner"

    # Default to respond
    return "respond"


def after_respond(
    state: AgentState,
) -> Literal["persist", "__end__"]:
    """Route after response generation.

    Determines whether to persist the conversation or end.

    Args:
        state: Current agent state

    Returns:
        "persist" to save conversation, "__end__" to finish
    """
    log = logger.bind(
        user_id=state.get("user_id"),
        session_id=state.get("session_id"),
    )

    # Check if waiting for plan confirmation
    plan = state.get("execution_plan")
    if plan and not state.get("plan_confirmed", False):
        log.info("after_respond_waiting_plan_confirmation")
        return "__end__"  # End and wait for user input

    # Persist conversation
    log.info("after_respond_persist")
    return "persist"
