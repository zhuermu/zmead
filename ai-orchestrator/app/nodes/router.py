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
    "save_creative",  # Save generated creatives to asset library
    "analyze_report",
    "market_analysis",
    "create_landing_page",
    "create_campaign",
    "multi_step",
    "general_query",
    "clarification_needed",
]


class ActionSchema(BaseModel):
    """Schema for a single action to execute.

    Note: All fields must be explicitly defined (not nested dicts) to ensure
    LangChain's structured output parser populates them correctly with Gemini.
    """

    type: str = Field(default="generate_creative", description="Action type (e.g., generate_creative, get_report)")
    module: str = Field(
        default="creative", description="Target module (creative, reporting, market_intel, landing_page, ad_engine)"
    )
    # Flatten params into explicit fields for better LLM extraction
    product_description: str | None = Field(default=None, description="产品描述，用于generate_creative")
    count: int | None = Field(default=None, description="生成数量，用于generate_creative")
    style: str | None = Field(default=None, description="风格，用于generate_creative")
    platform: str | None = Field(default=None, description="广告平台，如meta, tiktok, google")
    date_range: str | None = Field(default=None, description="日期范围，如last_7_days, last_30_days")
    campaign_id: str | None = Field(default=None, description="广告活动ID")
    temp_ids: list[str] = Field(default_factory=list, description="临时素材ID列表，用于save_creative")
    depends_on: list[int] = Field(
        default_factory=list, description="Indices of actions this depends on"
    )
    estimated_cost: float = Field(default=0.5, description="Estimated credit cost for this action")

    def to_params(self) -> dict[str, Any]:
        """Convert flattened fields back to params dict."""
        params: dict[str, Any] = {}
        if self.product_description:
            params["product_description"] = self.product_description
        if self.count:
            params["count"] = self.count
        if self.style:
            params["style"] = self.style
        if self.platform:
            params["platform"] = self.platform
        if self.date_range:
            params["date_range"] = self.date_range
        if self.campaign_id:
            params["campaign_id"] = self.campaign_id
        if self.temp_ids:
            params["temp_ids"] = self.temp_ids
        return params


class IntentSchema(BaseModel):
    """Structured output schema for intent recognition.

    This schema is used with Gemini's structured output feature
    to ensure reliable parsing of intent recognition results.

    Note: All fields have defaults to ensure LLM can populate them correctly.
    """

    intent: str = Field(default="general_query", description="Primary intent: generate_creative, save_creative, analyze_report, market_analysis, create_landing_page, create_campaign, multi_step, general_query, clarification_needed")

    confidence: float = Field(
        default=0.8, ge=0.0, le=1.0, description="Confidence score for the intent (0.0-1.0)"
    )

    # Flatten parameters into explicit fields
    product_description: str | None = Field(default=None, description="产品描述")
    count: int | None = Field(default=None, description="数量")
    style: str | None = Field(default=None, description="风格")
    platform: str | None = Field(default=None, description="广告平台")
    date_range: str | None = Field(default=None, description="日期范围")

    actions: list[ActionSchema] = Field(
        default_factory=list, description="List of actions to execute"
    )

    estimated_cost: float = Field(default=0.5, description="Total estimated credit cost")

    requires_confirmation: bool = Field(
        default=False, description="Whether operation requires user confirmation"
    )

    clarification_question: str | None = Field(
        default=None, description="Question to ask if clarification is needed"
    )

    def to_parameters(self) -> dict[str, Any]:
        """Convert flattened fields to parameters dict."""
        params: dict[str, Any] = {}
        if self.product_description:
            params["product_description"] = self.product_description
        if self.count:
            params["count"] = self.count
        if self.style:
            params["style"] = self.style
        if self.platform:
            params["platform"] = self.platform
        if self.date_range:
            params["date_range"] = self.date_range
        return params


# Credit cost estimates per action type
CREDIT_COSTS = {
    "generate_creative": 5.0,
    "save_creative": 0.0,  # No cost to save (already paid for generation)
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

        # Check for large budget changes - use to_params() for flattened schema
        if action.type == "update_budget":
            params = action.to_params() if hasattr(action, "to_params") else {}
            budget_change = params.get("budget_change_percent", 0)
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

        # Handle None result - LLM failed to parse into schema
        if result is None:
            log.warning("router_node_structured_output_none")
            return {
                "current_intent": "clarification_needed",
                "extracted_params": {},
                "pending_actions": [],
                "estimated_cost": 0,
                "requires_confirmation": False,
                "messages": [AIMessage(content="抱歉，我没有完全理解您的请求。请您更详细地描述一下？")],
            }

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
                "extracted_params": result.to_parameters(),
                "pending_actions": [],
                "estimated_cost": 0,
                "requires_confirmation": False,
                "messages": [AIMessage(content=f"🤔 {clarification}")],
            }

        # Convert actions to dict format - handle both dict (from LLM) and ActionSchema objects
        actions = []
        for action in result.actions:
            if isinstance(action, dict):
                # LLM returned raw dict - convert to ActionSchema first
                action_obj = ActionSchema(**action)
            else:
                action_obj = action

            params = action_obj.to_params()
            actions.append({
                "type": action_obj.type,
                "module": action_obj.module,
                "params": params,
                "depends_on": action_obj.depends_on,
                "estimated_cost": action_obj.estimated_cost
                or estimate_action_cost(action_obj.type, params),
            })

        # Calculate total estimated cost
        total_cost = sum(a.get("estimated_cost", 0) for a in actions)
        if result.estimated_cost > 0:
            total_cost = result.estimated_cost

        # Check for high-risk operations - convert dicts back to ActionSchema for check
        action_schemas = [
            ActionSchema(**a) if isinstance(a, dict) else a
            for a in result.actions
        ]
        requires_confirmation = result.requires_confirmation or is_high_risk_operation(
            action_schemas
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
            "extracted_params": result.to_parameters(),
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
