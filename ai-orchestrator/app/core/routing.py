"""Conditional routing logic for LangGraph.

This module implements routing functions that determine which node
to execute next based on the current state.

Requirements: 需求 3.2 (Multi-step), 需求 14.5 (Confirmation)
"""

from typing import Literal

import structlog

from app.core.state import AgentState

logger = structlog.get_logger(__name__)


# Node names for routing
NODE_ROUTER = "router"
NODE_CREATIVE = "creative"  # Real implementation (was creative_stub)
NODE_SAVE_CREATIVE = "save_creative"  # Save generated creatives to asset library
NODE_REPORTING = "reporting"  # Real implementation (was reporting_stub)
NODE_AD_ENGINE = "ad_engine"  # Real implementation (was ad_engine_stub)
NODE_LANDING_PAGE = "landing_page"  # Real implementation (was landing_page_stub)
NODE_MARKET_INSIGHTS = "market_insights"  # Real implementation (was market_intel_stub)
NODE_CONFIRMATION = "human_confirmation"
NODE_RESPOND = "respond"
NODE_PERSIST = "persist"
NODE_ERROR = "error_handler"
NODE_END = "__end__"


# Module to node mapping
MODULE_NODE_MAP = {
    "creative": NODE_CREATIVE,  # Real implementation
    "save_creative": NODE_SAVE_CREATIVE,  # Save creatives to asset library
    "reporting": NODE_REPORTING,  # Real implementation
    "ad_engine": NODE_AD_ENGINE,  # Real implementation
    "landing_page": NODE_LANDING_PAGE,  # Real implementation
    "market_insights": NODE_MARKET_INSIGHTS,  # Real implementation
    "market_intel": NODE_MARKET_INSIGHTS,  # Alias for backward compatibility
}


# High-risk action types
HIGH_RISK_ACTIONS = {"pause_all", "delete_campaign", "delete"}


def route_by_intent(
    state: AgentState,
) -> Literal[
    "creative",
    "creative_stub",
    "save_creative",
    "reporting",
    "reporting_stub",
    "ad_engine",
    "ad_engine_stub",
    "landing_page",
    "landing_page_stub",
    "market_insights",
    "market_intel_stub",
    "respond",
    "error_handler",
]:
    """Route to appropriate module based on recognized intent.

    This function is called after the router node to determine
    which functional module should handle the request.

    Args:
        state: Current agent state

    Returns:
        Name of the next node to execute

    Requirements: 需求 3.2
    """
    log = logger.bind(
        user_id=state.get("user_id"),
        session_id=state.get("session_id"),
    )

    # Check for errors first
    if state.get("error"):
        log.info("route_by_intent_error", error_type=state["error"].get("type"))
        return "respond"  # Go to respond to show error message

    intent = state.get("current_intent")
    pending_actions = state.get("pending_actions", [])

    log.info(
        "route_by_intent",
        intent=intent,
        action_count=len(pending_actions),
    )

    # Handle clarification needed
    if intent == "clarification_needed":
        log.info("route_by_intent_clarification")
        return "respond"

    # Handle general query
    if intent == "general_query":
        log.info("route_by_intent_general")
        return "respond"

    # No actions to execute
    if not pending_actions:
        log.info("route_by_intent_no_actions")
        return "respond"

    # Get the first action's module
    first_action = pending_actions[0]
    module = first_action.get("module", "")

    # Map module to node
    node = MODULE_NODE_MAP.get(module)

    if node:
        log.info("route_by_intent_module", module=module, node=node)
        return node

    # Default to respond if module not found
    log.warning("route_by_intent_unknown_module", module=module)
    return "respond"


def should_confirm(
    state: AgentState,
) -> Literal["confirm", "respond"]:
    """Determine if operation requires user confirmation.

    Called after a functional module executes to check if
    the operation needs user confirmation before proceeding.

    Args:
        state: Current agent state

    Returns:
        "confirm" if confirmation needed, "respond" otherwise

    Requirements: 需求 14.5
    """
    log = logger.bind(
        user_id=state.get("user_id"),
        session_id=state.get("session_id"),
    )

    # Check if confirmation is required
    requires_confirmation = state.get("requires_confirmation", False)

    if requires_confirmation:
        # Check if already confirmed
        user_confirmed = state.get("user_confirmed")

        if user_confirmed is None:
            # Waiting for confirmation
            log.info("should_confirm_waiting")
            return "confirm"
        elif user_confirmed is True:
            # User confirmed, proceed
            log.info("should_confirm_confirmed")
            return "respond"
        else:
            # User cancelled
            log.info("should_confirm_cancelled")
            return "respond"

    log.info("should_confirm_not_required")
    return "respond"


def check_requires_confirmation(state: AgentState) -> bool:
    """Check if any pending action requires confirmation.

    Args:
        state: Current agent state

    Returns:
        True if confirmation is required
    """
    pending_actions = state.get("pending_actions", [])

    for action in pending_actions:
        action_type = action.get("type", "")

        # Check for high-risk actions
        if action_type in HIGH_RISK_ACTIONS:
            return True

        # Check for large budget changes
        if action_type == "update_budget":
            params = action.get("params", {})
            budget_change = params.get("budget_change_percent", 0)
            if abs(budget_change) > 50:
                return True

    return False


def after_module(
    state: AgentState,
) -> Literal[
    "creative",
    "reporting",
    "ad_engine",
    "landing_page",
    "market_insights",
    "respond",
]:
    """Route after a functional module completes.

    Checks if there are more actions to execute (multi-step tasks)
    or if we should proceed to response generation.

    Args:
        state: Current agent state

    Returns:
        Name of the next node

    Requirements: 需求 3.3 (Multi-step execution)
    """
    log = logger.bind(
        user_id=state.get("user_id"),
        session_id=state.get("session_id"),
    )

    # Check for errors
    if state.get("error"):
        log.info("after_module_error")
        return "respond"

    # Get completed and pending actions
    completed_results = state.get("completed_results", [])
    pending_actions = state.get("pending_actions", [])

    # Count completed actions
    completed_count = len(completed_results)

    # Check if there are more actions to execute
    if completed_count < len(pending_actions):
        # Get the next action
        next_action = pending_actions[completed_count]
        module = next_action.get("module", "")

        # Check dependencies
        depends_on = next_action.get("depends_on", [])

        # Verify all dependencies are completed
        dependencies_met = all(dep < completed_count for dep in depends_on)

        if dependencies_met:
            node = MODULE_NODE_MAP.get(module)
            if node:
                log.info(
                    "after_module_next",
                    next_module=module,
                    completed=completed_count,
                    total=len(pending_actions),
                )
                return node

    # All actions completed or no more actions
    log.info(
        "after_module_complete",
        completed=completed_count,
        total=len(pending_actions),
    )
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

    # Check if waiting for confirmation
    if state.get("requires_confirmation") and state.get("user_confirmed") is None:
        log.info("after_respond_waiting_confirmation")
        return "__end__"  # End and wait for user input

    # Persist conversation
    log.info("after_respond_persist")
    return "persist"


def after_confirmation(
    state: AgentState,
) -> Literal[
    "creative",
    "reporting",
    "ad_engine",
    "landing_page",
    "market_insights",
    "respond",
    "__end__",
]:
    """Route after confirmation node.

    If user confirmed, route to the appropriate module.
    If user cancelled or waiting, route to respond or end.

    Args:
        state: Current agent state

    Returns:
        Next node name
    """
    log = logger.bind(
        user_id=state.get("user_id"),
        session_id=state.get("session_id"),
    )

    user_confirmed = state.get("user_confirmed")

    if user_confirmed is None:
        # Waiting for user input
        log.info("after_confirmation_waiting")
        return "__end__"

    if user_confirmed is False:
        # User cancelled
        log.info("after_confirmation_cancelled")
        return "respond"

    # User confirmed - execute the pending action
    pending_actions = state.get("pending_actions", [])

    if pending_actions:
        module = pending_actions[0].get("module", "")
        node = MODULE_NODE_MAP.get(module)

        if node:
            log.info("after_confirmation_execute", module=module)
            return node

    log.info("after_confirmation_respond")
    return "respond"
