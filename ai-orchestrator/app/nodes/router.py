"""Intent recognition router node.

This module implements the router_node that identifies user intent
and routes to appropriate functional modules.

Requirements: 需求 2.1-2.5 (Intent Recognition), 需求 14.1 (Smart Extraction)
"""

from typing import Any, Literal

import structlog
from langchain_core.messages import AIMessage
from pydantic import BaseModel, Field

from app.core.errors import ErrorHandler
from app.core.state import AgentState
from app.prompts.intent_recognition import (
    INTENT_RECOGNITION_SYSTEM_PROMPT,
    INTENT_RECOGNITION_USER_PROMPT,
    format_conversation_history,
)
from app.services.gemini_client import GeminiClient, GeminiError

logger = structlog.get_logger(__name__)


# Intent types
IntentType = Literal[
    "generate_creative",
    "analyze_report",
    "market_analysis",
    "create_landing_page",
    "create_campaign",
    "multi_step",
    "general_query",
    "clarification_needed",
]


class ActionSchema(BaseModel):
    """Schema for a single action to execute."""

    type: str = Field(description="Action type (e.g., generate_creative, get_report)")
    module: str = Field(
        description="Target module (creative, reporting, market_intel, landing_page, ad_engine)"
    )
    params: dict[str, Any] = Field(default_factory=dict, description="Action parameters")
    depends_on: list[int] = Field(
        default_factory=list, description="Indices of actions this depends on"
    )
    estimated_cost: float = Field(default=0.0, description="Estimated credit cost for this action")


class IntentSchema(BaseModel):
    """Structured output schema for intent recognition.

    This schema is used with Gemini's structured output feature
    to ensure reliable parsing of intent recognition results.
    """

    intent: IntentType = Field(description="Primary intent identified from user message")

    confidence: float = Field(
        ge=0.0, le=1.0, description="Confidence score for the intent (0.0-1.0)"
    )

    parameters: dict[str, Any] = Field(
        default_factory=dict, description="Parameters extracted from user message"
    )

    actions: list[ActionSchema] = Field(
        default_factory=list, description="List of actions to execute"
    )

    estimated_cost: float = Field(default=0.0, description="Total estimated credit cost")

    requires_confirmation: bool = Field(
        default=False, description="Whether operation requires user confirmation"
    )

    clarification_question: str | None = Field(
        default=None, description="Question to ask if clarification is needed"
    )


# Credit cost estimates per action type
CREDIT_COSTS = {
    "generate_creative": 5.0,
    "analyze_creative": 1.0,
    "get_report": 1.0,
    "analyze_performance": 2.0,
    "analyze_competitor": 2.0,
    "get_trends": 1.5,
    "generate_strategy": 3.0,
    "create_landing_page": 3.0,
    "translate_page": 1.0,
    "create_campaign": 2.0,
    "update_budget": 0.5,
    "pause_campaign": 0.5,
    "pause_all": 0.5,
    "delete_campaign": 0.5,
}


def estimate_action_cost(action_type: str, params: dict[str, Any]) -> float:
    """Estimate credit cost for an action.

    Args:
        action_type: Type of action
        params: Action parameters

    Returns:
        Estimated credit cost
    """
    base_cost = CREDIT_COSTS.get(action_type, 1.0)

    # Adjust for quantity parameters
    if action_type == "generate_creative":
        count = params.get("count", 10)
        return base_cost * (count / 10)  # 5 credits per 10 images

    return base_cost


def is_high_risk_operation(actions: list[ActionSchema]) -> bool:
    """Check if any action is high-risk and requires confirmation.

    High-risk operations:
    - pause_all: Pausing all campaigns
    - delete_campaign: Deleting campaigns
    - budget_change > 50%

    Args:
        actions: List of actions to check

    Returns:
        True if any action is high-risk
    """
    high_risk_types = {"pause_all", "delete_campaign", "delete"}

    for action in actions:
        if action.type in high_risk_types:
            return True

        # Check for large budget changes
        if action.type == "update_budget":
            budget_change = action.params.get("budget_change_percent", 0)
            if abs(budget_change) > 50:
                return True

    return False


async def router_node(state: AgentState) -> dict[str, Any]:
    """Intent recognition and routing node.

    This node:
    1. Analyzes the user's message
    2. Identifies the intent using Gemini 2.5 Pro
    3. Extracts relevant parameters
    4. Determines actions to execute
    5. Estimates credit cost

    Args:
        state: Current agent state

    Returns:
        State updates with intent, parameters, and actions

    Requirements: 需求 2.1-2.5, 14.1
    """
    log = logger.bind(
        user_id=state.get("user_id"),
        session_id=state.get("session_id"),
    )
    log.info("router_node_start")

    # Get the last user message
    messages = state.get("messages", [])
    if not messages:
        log.warning("router_node_no_messages")
        return {
            "current_intent": "clarification_needed",
            "error": {
                "code": "4000",
                "type": "NO_MESSAGE",
                "message": "没有收到消息",
            },
        }

    last_message = messages[-1]
    user_message = last_message.content if hasattr(last_message, "content") else str(last_message)

    log.info("router_node_processing", message_preview=user_message[:100])

    try:
        # Initialize Gemini client
        gemini = GeminiClient()

        # Format conversation history for context
        history = format_conversation_history(messages[:-1])  # Exclude current message

        # Build prompt
        prompt_messages = [
            {"role": "system", "content": INTENT_RECOGNITION_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": INTENT_RECOGNITION_USER_PROMPT.format(
                    user_message=user_message,
                    conversation_history=history,
                ),
            },
        ]

        # Get structured output from Gemini
        result = await gemini.structured_output(
            messages=prompt_messages,
            schema=IntentSchema,
            temperature=0.1,  # Low temperature for consistent results
        )

        log.info(
            "router_node_intent_recognized",
            intent=result.intent,
            confidence=result.confidence,
            action_count=len(result.actions),
        )

        # Handle low confidence
        if result.confidence < 0.6:
            log.info("router_node_low_confidence", confidence=result.confidence)

            clarification = (
                result.clarification_question or "请问您想要做什么？能告诉我更多细节吗？"
            )

            return {
                "current_intent": "clarification_needed",
                "extracted_params": result.parameters,
                "pending_actions": [],
                "estimated_cost": 0,
                "requires_confirmation": False,
                "messages": [AIMessage(content=f"🤔 {clarification}")],
            }

        # Convert actions to dict format
        actions = [
            {
                "type": action.type,
                "module": action.module,
                "params": action.params,
                "depends_on": action.depends_on,
                "estimated_cost": action.estimated_cost
                or estimate_action_cost(action.type, action.params),
            }
            for action in result.actions
        ]

        # Calculate total estimated cost
        total_cost = sum(a.get("estimated_cost", 0) for a in actions)
        if result.estimated_cost > 0:
            total_cost = result.estimated_cost

        # Check for high-risk operations
        requires_confirmation = result.requires_confirmation or is_high_risk_operation(
            result.actions
        )

        log.info(
            "router_node_complete",
            intent=result.intent,
            action_count=len(actions),
            estimated_cost=total_cost,
            requires_confirmation=requires_confirmation,
        )

        return {
            "current_intent": result.intent,
            "extracted_params": result.parameters,
            "pending_actions": actions,
            "estimated_cost": total_cost,
            "requires_confirmation": requires_confirmation,
            "credit_checked": False,
            "credit_sufficient": False,
        }

    except GeminiError as e:
        log.error(
            "router_node_gemini_error",
            error=str(e),
            code=e.code,
        )

        # Use ErrorHandler for consistent error state
        error_state = ErrorHandler.create_node_error_state(
            error=e,
            node_name="router",
            user_id=state.get("user_id"),
            session_id=state.get("session_id"),
        )
        error_state["current_intent"] = None
        return error_state

    except Exception as e:
        log.error(
            "router_node_unexpected_error",
            error=str(e),
            exc_info=True,
        )

        # Use ErrorHandler for consistent error state
        error_state = ErrorHandler.create_node_error_state(
            error=e,
            node_name="router",
            user_id=state.get("user_id"),
            session_id=state.get("session_id"),
        )
        error_state["current_intent"] = None
        return error_state
