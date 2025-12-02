"""Agent state schema for LangGraph state machine.

This module defines the AgentState TypedDict that represents the complete
state of the AI Orchestrator during conversation processing. The state
flows through all nodes in the LangGraph and maintains conversation context.

Requirements: 需求 4 (Orchestrator), 需求 5 (Conversation Context)
"""

import operator
from typing import Annotated, Any, TypedDict

from langchain_core.messages import BaseMessage


class ActionItem(TypedDict, total=False):
    """Represents a single action to be executed.

    Attributes:
        type: Action type (e.g., "generate_creative", "create_campaign")
        module: Target module (creative, reporting, market_intel, landing_page, ad_engine)
        params: Action parameters extracted from user message
        depends_on: List of action indices this action depends on
        estimated_cost: Estimated credit cost for this action
    """

    type: str
    module: str
    params: dict[str, Any]
    depends_on: list[int]
    estimated_cost: float


class ActionResult(TypedDict, total=False):
    """Represents the result of an executed action.

    Attributes:
        action_type: Type of action that was executed
        module: Module that executed the action
        status: Execution status ("success", "error", "partial")
        data: Result data from the action
        error: Error information if action failed
        cost: Actual credit cost incurred
        mock: Whether this is mock data (Phase 1)
    """

    action_type: str
    module: str
    status: str
    data: dict[str, Any]
    error: dict[str, Any] | None
    cost: float
    mock: bool


class ErrorInfo(TypedDict, total=False):
    """Represents error information in the state.

    Attributes:
        code: Error code (e.g., "6011" for insufficient credits)
        type: Error type (e.g., "INSUFFICIENT_CREDITS")
        message: User-friendly error message
        details: Additional error details
        retryable: Whether the operation can be retried
    """

    code: str
    type: str
    message: str
    details: dict[str, Any]
    retryable: bool


class AgentState(TypedDict, total=False):
    """Complete state for the AI Orchestrator LangGraph.

    This TypedDict defines all fields that flow through the state machine.
    The state is passed between nodes and updated as the conversation progresses.

    Message Handling:
        The `messages` field uses `operator.add` annotation, which means
        new messages are automatically appended to the existing list when
        a node returns {"messages": [new_message]}.

    Conversation Flow:
        1. User message arrives → router_node identifies intent
        2. Credit check → functional module executes
        3. Confirmation check → respond_node generates response
        4. persist_node saves conversation

    Requirements:
        - 需求 4: Orchestrator state management
        - 需求 5: Conversation context management
    """

    # =========================================================================
    # Conversation Messages
    # =========================================================================

    messages: Annotated[list[BaseMessage], operator.add]
    """Conversation message history.
    
    Uses operator.add for automatic message appending. When a node returns
    {"messages": [AIMessage(content="...")]}, the message is appended to
    the existing list rather than replacing it.
    
    Message types:
    - HumanMessage: User input
    - AIMessage: Assistant responses
    - SystemMessage: System prompts (typically at start)
    """

    # =========================================================================
    # User and Session Information
    # =========================================================================

    user_id: str
    """Unique identifier for the user.
    
    Used for:
    - Credit operations (check, deduct, refund)
    - Conversation persistence
    - User-specific context retrieval
    """

    session_id: str
    """Unique identifier for the conversation session.
    
    Used for:
    - LangGraph checkpointing (thread_id)
    - Conversation persistence
    - Context continuity across messages
    """

    # =========================================================================
    # Intent Recognition Results
    # =========================================================================

    current_intent: str | None
    """Primary intent identified from user message.
    
    Possible values:
    - "generate_creative": Ad creative generation
    - "analyze_report": Performance reporting
    - "market_analysis": Market intelligence
    - "create_landing_page": Landing page creation
    - "create_campaign": Campaign automation
    - "multi_step": Multiple intents detected
    - "general_query": General conversation
    - "clarification_needed": Intent unclear, need more info
    
    Requirements: 需求 2.1-2.5
    """

    extracted_params: dict[str, Any] | None
    """Parameters extracted from user message.
    
    Examples:
    - {"product_url": "https://...", "count": 10} for creative generation
    - {"campaign_id": "123", "budget": 100} for budget changes
    - {"date_range": "last_7_days"} for reporting
    
    Requirements: 需求 14.1 (Smart information extraction)
    """

    # =========================================================================
    # Action Management
    # =========================================================================

    pending_actions: list[ActionItem]
    """List of actions waiting to be executed.
    
    Populated by router_node based on intent recognition.
    Actions are executed in order, respecting dependencies.
    
    Requirements: 需求 3 (Multi-intent), 需求 4 (Orchestrator)
    """

    completed_results: list[ActionResult]
    """Results from executed actions.
    
    Each functional module appends its result here.
    Used by respond_node to generate final response.
    
    Requirements: 需求 4.5 (Result aggregation)
    """

    # =========================================================================
    # Confirmation State
    # =========================================================================

    requires_confirmation: bool
    """Whether current operation requires user confirmation.
    
    Set to True for high-risk operations:
    - pause_all: Pausing all campaigns
    - delete_campaign: Deleting campaigns
    - budget_change > 50%: Large budget modifications
    
    Requirements: 需求 14.5 (Safety confirmation)
    """

    user_confirmed: bool | None
    """User's confirmation response.
    
    - None: Waiting for confirmation
    - True: User confirmed, proceed with operation
    - False: User cancelled, abort operation
    
    Requirements: 需求 14.5.4, 14.5.5
    """

    confirmation_message: str | None
    """Message shown to user for confirmation.
    
    Contains operation details and potential impact.
    Generated by human_confirmation_node.
    """

    # =========================================================================
    # Credit Management
    # =========================================================================

    credit_checked: bool
    """Whether credit has been checked for current operation."""

    credit_sufficient: bool
    """Whether user has sufficient credits."""

    estimated_cost: float | None
    """Estimated credit cost for pending actions.
    
    Calculated by router_node based on action types.
    Used for credit pre-check before execution.
    """

    # =========================================================================
    # Error Handling
    # =========================================================================

    error: ErrorInfo | None
    """Error information if something went wrong.
    
    Set by any node that encounters an error.
    Used by respond_node to generate error response.
    
    Requirements: 需求 12 (Error handling)
    """

    retry_count: int
    """Number of retry attempts for current operation.
    
    Incremented on each retry. Max 3 retries before giving up.
    Reset when operation succeeds or user sends new message.
    
    Requirements: 需求 11.4 (MCP retry), 需求 12.5 (Resume from failure)
    """

    # =========================================================================
    # Context Management
    # =========================================================================

    context_references: dict[str, Any] | None
    """Resolved context references from user message.

    When user says "use the previous creative" or "add $50 more",
    this contains the resolved entities:
    - {"creative_ids": ["abc123"]}
    - {"budget_base": 100, "budget_delta": 50}

    Requirements: 需求 5.2, 5.3 (Context resolution)
    """

    conversation_compressed: bool
    """Whether conversation history has been compressed.

    Set to True after compress_history is called (after 100 rounds).
    Prevents repeated compression.

    Requirements: 需求 5.4 (Compress after 100 rounds)
    """

    # =========================================================================
    # Execution Plan (v2.0)
    # =========================================================================

    execution_plan: dict[str, Any] | None
    """Current execution plan for multi-step tasks.

    Contains:
    - goal: User's goal
    - complexity: simple/moderate/complex
    - steps: List of ExecutionStep
    - estimated_total_credits: Total estimated cost
    - requires_confirmation: Whether user confirmation is needed

    Generated by planner_node, executed by executor_node.

    Requirements: Architecture v2.0
    """

    current_step_index: int
    """Index of the current step being executed.

    0-indexed, incremented after each step execution.
    """

    step_results: list[dict[str, Any]]
    """Results from executed steps.

    Each entry contains:
    - step_id: The step that was executed
    - tool: Tool that was called
    - success: Whether execution succeeded
    - data: Result data
    - error: Error message if failed
    - credit_consumed: Actual credits consumed
    """

    plan_confirmed: bool
    """Whether the execution plan has been confirmed.

    For complex or high-cost plans, user confirmation is required
    before execution begins.
    """

    execution_complete: bool
    """Whether all steps in the plan have been executed.

    Set to True by executor_node when all steps are done,
    or by analyzer_node when deciding to stop.
    """

    analyzer_decision: str | None
    """Decision from the analyzer node.

    Possible values:
    - "continue": Execute next step
    - "respond": Generate final response
    - "replan": Adjust the execution plan
    """

    replan_suggestion: str | None
    """Suggestion for replanning when analyzer decides to replan."""

    memory_context: dict[str, Any] | None
    """Memory context retrieved from long-term memory.

    Contains relevant past interactions, preferences, etc.
    Passed to tools for context-aware execution.
    """


def create_initial_state(
    user_id: str,
    session_id: str,
    messages: list[BaseMessage] | None = None,
) -> AgentState:
    """Create initial agent state for a new conversation turn.

    Args:
        user_id: User identifier
        session_id: Session identifier
        messages: Optional initial messages (typically user's message)

    Returns:
        AgentState with default values set
    """
    return AgentState(
        messages=messages or [],
        user_id=user_id,
        session_id=session_id,
        current_intent=None,
        extracted_params=None,
        pending_actions=[],
        completed_results=[],
        requires_confirmation=False,
        user_confirmed=None,
        confirmation_message=None,
        credit_checked=False,
        credit_sufficient=False,
        estimated_cost=None,
        error=None,
        retry_count=0,
        context_references=None,
        conversation_compressed=False,
        # v2.0 Execution Plan fields
        execution_plan=None,
        current_step_index=0,
        step_results=[],
        plan_confirmed=False,
        execution_complete=False,
        analyzer_decision=None,
        replan_suggestion=None,
        memory_context=None,
    )
