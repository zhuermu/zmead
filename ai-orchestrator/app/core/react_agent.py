"""ReAct Agent implementation for AAE.

This module provides the ReActAgent class that implements the ReAct
(Reasoning + Acting) pattern for autonomous task execution.

The agent follows this loop:
1. Perceive: Understand user intent and current state
2. Plan: Decide what action to take next
3. Act: Execute the selected tool
4. Observe: Process the tool result
5. Evaluate: Determine if task is complete

The agent supports:
- Dynamic tool loading based on user intent
- Human-in-the-loop for confirmations
- State persistence via Redis
- Error handling and retry logic
"""

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

import structlog

from app.core.evaluator import Evaluator
from app.core.human_in_loop import HumanInLoopHandler, UserInputResponse
from app.core.i18n import get_message
from app.core.memory import AgentMemory
from app.core.planner import PlanAction, Planner
from app.core.redis_client import get_redis
from app.services.gemini_client import GeminiClient, GeminiError
from app.tools.base import AgentTool, ToolExecutionError
from app.tools.registry import ToolRegistry

logger = structlog.get_logger(__name__)


class AgentStatus(str, Enum):
    """Agent execution status."""

    IDLE = "idle"
    THINKING = "thinking"
    ACTING = "acting"
    WAITING_FOR_USER = "waiting_for_user"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class ToolCall:
    """Represents a tool call in the execution history."""

    tool_name: str
    parameters: dict[str, Any]
    result: dict[str, Any] | None = None
    error: str | None = None
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class AgentStep:
    """Represents a single step in the agent's execution."""

    step_number: int
    thought: str  # Agent's reasoning
    action: str | None = None  # Tool name to call
    action_input: dict[str, Any] | None = None  # Tool parameters
    observation: str | None = None  # Tool result
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class AgentState:
    """Agent execution state.

    This state is persisted to Redis and tracks the entire
    execution history of a conversation.
    """

    # Identifiers
    session_id: str
    user_id: str
    conversation_id: str | None = None

    # Current request
    user_message: str = ""
    user_intent: str | None = None

    # File attachments (with Gemini File URIs from backend processing)
    attachments: list[dict[str, Any]] = field(default_factory=list)

    # Execution state
    status: AgentStatus = AgentStatus.IDLE
    current_step: int = 0
    max_steps: int = 10

    # Execution history
    steps: list[AgentStep] = field(default_factory=list)
    tool_calls: list[ToolCall] = field(default_factory=list)

    # Conversation messages (LangChain BaseMessage objects)
    messages: list[Any] = field(default_factory=list)

    # Loaded tools
    loaded_tool_names: list[str] = field(default_factory=list)

    # Human-in-the-loop
    waiting_for_user_input: bool = False
    user_input_request: dict[str, Any] | None = None

    # Results
    final_response: str | None = None
    error_message: str | None = None

    # Metadata
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict[str, Any]:
        """Convert state to dictionary for serialization."""
        # Serialize messages to simple dict format
        serialized_messages = []
        for msg in self.messages:
            msg_dict = {
                "type": getattr(msg, "type", "unknown"),
                "content": getattr(msg, "content", ""),
            }
            if hasattr(msg, "additional_kwargs") and msg.additional_kwargs:
                msg_dict["additional_kwargs"] = msg.additional_kwargs
            serialized_messages.append(msg_dict)

        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "conversation_id": self.conversation_id,
            "user_message": self.user_message,
            "user_intent": self.user_intent,
            "attachments": self.attachments,
            "status": self.status.value,
            "current_step": self.current_step,
            "max_steps": self.max_steps,
            "steps": [
                {
                    "step_number": step.step_number,
                    "thought": step.thought,
                    "action": step.action,
                    "action_input": step.action_input,
                    "observation": step.observation,
                    "timestamp": step.timestamp.isoformat(),
                }
                for step in self.steps
            ],
            "tool_calls": [
                {
                    "tool_name": call.tool_name,
                    "parameters": call.parameters,
                    "result": call.result,
                    "error": call.error,
                    "timestamp": call.timestamp.isoformat(),
                }
                for call in self.tool_calls
            ],
            "messages": serialized_messages,
            "loaded_tool_names": self.loaded_tool_names,
            "waiting_for_user_input": self.waiting_for_user_input,
            "user_input_request": self.user_input_request,
            "final_response": self.final_response,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AgentState":
        """Create state from dictionary."""
        from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

        # Parse steps
        steps = []
        for step_data in data.get("steps", []):
            steps.append(
                AgentStep(
                    step_number=step_data["step_number"],
                    thought=step_data["thought"],
                    action=step_data.get("action"),
                    action_input=step_data.get("action_input"),
                    observation=step_data.get("observation"),
                    timestamp=datetime.fromisoformat(step_data["timestamp"]),
                )
            )

        # Parse tool calls
        tool_calls = []
        for call_data in data.get("tool_calls", []):
            tool_calls.append(
                ToolCall(
                    tool_name=call_data["tool_name"],
                    parameters=call_data["parameters"],
                    result=call_data.get("result"),
                    error=call_data.get("error"),
                    timestamp=datetime.fromisoformat(call_data["timestamp"]),
                )
            )

        # Parse messages
        messages = []
        for msg_data in data.get("messages", []):
            msg_type = msg_data.get("type", "human")
            content = msg_data.get("content", "")
            additional_kwargs = msg_data.get("additional_kwargs", {})

            if msg_type == "human":
                messages.append(HumanMessage(content=content, additional_kwargs=additional_kwargs))
            elif msg_type == "ai":
                messages.append(AIMessage(content=content, additional_kwargs=additional_kwargs))
            elif msg_type == "system":
                messages.append(SystemMessage(content=content, additional_kwargs=additional_kwargs))
            else:
                # Default to HumanMessage for unknown types
                messages.append(HumanMessage(content=content, additional_kwargs=additional_kwargs))

        return cls(
            session_id=data["session_id"],
            user_id=data["user_id"],
            conversation_id=data.get("conversation_id"),
            user_message=data.get("user_message", ""),
            user_intent=data.get("user_intent"),
            attachments=data.get("attachments", []),
            status=AgentStatus(data.get("status", "idle")),
            current_step=data.get("current_step", 0),
            max_steps=data.get("max_steps", 10),
            steps=steps,
            tool_calls=tool_calls,
            messages=messages,
            loaded_tool_names=data.get("loaded_tool_names", []),
            waiting_for_user_input=data.get("waiting_for_user_input", False),
            user_input_request=data.get("user_input_request"),
            final_response=data.get("final_response"),
            error_message=data.get("error_message"),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
        )


@dataclass
class AgentResponse:
    """Response from the agent."""

    status: AgentStatus
    message: str | None = None
    data: dict[str, Any] | None = None
    requires_user_input: bool = False
    user_input_request: dict[str, Any] | None = None
    error: str | None = None


class ReActAgent:
    """ReAct Agent for autonomous task execution.

    The agent implements the ReAct (Reasoning + Acting) pattern:
    - Perceive: Understand user intent
    - Plan: Decide what to do next
    - Act: Execute tools
    - Observe: Process results
    - Evaluate: Check if complete

    Example:
        agent = ReActAgent(
            gemini_client=gemini_client,
            tool_registry=tool_registry,
        )

        response = await agent.process_message(
            user_message="Generate an ad image for my product",
            user_id="user123",
            session_id="session456",
        )

        if response.requires_user_input:
            # Handle user input request
            pass
        elif response.status == AgentStatus.COMPLETED:
            # Task completed
            print(response.message)
    """

    def __init__(
        self,
        gemini_client: GeminiClient | None = None,
        tool_registry: ToolRegistry | None = None,
        planner: Planner | None = None,
        memory: AgentMemory | None = None,
        evaluator: Evaluator | None = None,
        human_in_loop_handler: HumanInLoopHandler | None = None,
        max_steps: int = 10,
        state_ttl: int = 3600,  # 1 hour
    ):
        """Initialize the ReAct Agent.

        Args:
            gemini_client: Gemini client for LLM calls
            tool_registry: Tool registry for tool lookup
            planner: Planner for action planning
            memory: Memory component for state persistence
            evaluator: Evaluator for human-in-the-loop decisions
            human_in_loop_handler: Handler for user input requests
            max_steps: Maximum execution steps before stopping
            state_ttl: State TTL in Redis (seconds)
        """
        self.gemini_client = gemini_client or GeminiClient()
        self.tool_registry = tool_registry
        self.planner = planner or Planner(gemini_client=self.gemini_client)
        self.memory = memory or AgentMemory(state_ttl=state_ttl)
        self.evaluator = evaluator or Evaluator(gemini_client=self.gemini_client)
        self.human_in_loop_handler = human_in_loop_handler or HumanInLoopHandler()
        self.max_steps = max_steps
        self.state_ttl = state_ttl

        logger.info(
            "react_agent_initialized",
            max_steps=max_steps,
            state_ttl=state_ttl,
        )

    async def process_message(
        self,
        user_message: str,
        user_id: str,
        session_id: str,
        conversation_id: str | None = None,
        loaded_tools: list[AgentTool] | None = None,
    ) -> AgentResponse:
        """Process a user message and execute the ReAct loop.

        Args:
            user_message: User's message
            user_id: User ID
            session_id: Session ID
            conversation_id: Optional conversation ID
            loaded_tools: Optional pre-loaded tools (if None, will load all)

        Returns:
            AgentResponse with execution result
        """
        log = logger.bind(
            user_id=user_id,
            session_id=session_id,
            conversation_id=conversation_id,
        )
        log.info("process_message_start", message_length=len(user_message))

        try:
            # Initialize or load state
            state = await self._get_or_create_state(
                user_message=user_message,
                user_id=user_id,
                session_id=session_id,
                conversation_id=conversation_id,
            )

            # Store loaded tools
            if loaded_tools:
                state.loaded_tool_names = [tool.name for tool in loaded_tools]

            # Add user message to conversation history
            await self.memory.add_message(
                session_id=session_id,
                role="user",
                content=user_message,
            )

            # Execute ReAct loop
            response = await self._react_loop(state, loaded_tools)

            # Add assistant response to conversation history
            if response.message:
                await self.memory.add_message(
                    session_id=session_id,
                    role="assistant",
                    content=response.message,
                    metadata={"status": response.status.value},
                )

            # Save state
            await self._save_state(state)

            log.info(
                "process_message_complete",
                status=response.status.value,
                steps=state.current_step,
            )

            return response

        except Exception as e:
            log.error("process_message_error", error=str(e), exc_info=True)
            return AgentResponse(
                status=AgentStatus.ERROR,
                error=str(e),
                message="An error occurred while processing your request",
            )

    async def process_message_stream(
        self,
        user_message: str,
        user_id: str,
        session_id: str,
        conversation_id: str | None = None,
        loaded_tools: list[AgentTool] | None = None,
        attachments: list[dict] | None = None,
    ):
        """Process a user message and stream the response in real-time.

        Args:
            user_message: User's message
            user_id: User ID
            session_id: Session ID
            conversation_id: Optional conversation ID
            loaded_tools: Optional pre-loaded tools (if None, will load all)
            attachments: Optional file attachments with S3 URLs

        Yields:
            dict: Events with type and content:
                - {"type": "text", "content": str} - Text chunk
                - {"type": "user_input_request", "data": dict} - Needs user input
                - {"type": "error", "error": str} - Error occurred
        """
        log = logger.bind(
            user_id=user_id,
            session_id=session_id,
            conversation_id=conversation_id,
        )
        log.info("process_message_stream_start", message_length=len(user_message))

        try:
            # Initialize or load state
            state = await self._get_or_create_state(
                user_message=user_message,
                user_id=user_id,
                session_id=session_id,
                conversation_id=conversation_id,
            )

            # Store loaded tools
            if loaded_tools:
                state.loaded_tool_names = [tool.name for tool in loaded_tools]

            # Process and store attachments with Gemini File URIs
            gemini_attachments = []
            if attachments:
                # Keep attachments that have Gemini File URI
                for att in attachments:
                    if att.get("geminiFileUri"):
                        gemini_attachments.append({
                            "filename": att.get("filename", "unknown"),
                            "contentType": att.get("contentType", "application/octet-stream"),
                            "geminiFileUri": att.get("geminiFileUri"),
                            "geminiFileName": att.get("geminiFileName"),
                            "type": att.get("type", "file"),
                        })

            # Store attachments in state for passing to planner
            if gemini_attachments:
                state.attachments = gemini_attachments
                log.info("attachments_stored_in_state", count=len(gemini_attachments))

            # Add user message to conversation history with attachments in metadata
            message_metadata = {}
            if gemini_attachments:
                message_metadata["attachments"] = gemini_attachments

            await self.memory.add_message(
                session_id=session_id,
                role="user",
                content=user_message,
                metadata=message_metadata,
            )

            # Execute ReAct loop with streaming
            full_response = ""
            async for event in self._react_loop_stream(state, loaded_tools):
                if event.get("type") == "text":
                    full_response += event.get("content", "")
                yield event

            # Add assistant response to conversation history
            if full_response:
                await self.memory.add_message(
                    session_id=session_id,
                    role="assistant",
                    content=full_response,
                    metadata={"status": "completed"},
                )

            # Save state
            await self._save_state(state)

            log.info("process_message_stream_complete", response_length=len(full_response))

        except Exception as e:
            log.error("process_message_stream_error", error=str(e), exc_info=True)
            yield {"type": "error", "error": str(e)}

    async def continue_with_user_input(
        self,
        session_id: str,
        user_input: str | dict[str, Any],
    ) -> AgentResponse:
        """Continue execution after receiving user input.

        Args:
            session_id: Session ID
            user_input: User's input (text or structured data)

        Returns:
            AgentResponse with execution result
        """
        log = logger.bind(session_id=session_id)
        log.info("continue_with_user_input")

        try:
            # Load state
            state = await self._load_state(session_id)
            if not state:
                return AgentResponse(
                    status=AgentStatus.ERROR,
                    error="Session not found",
                    message="Session expired or not found",
                )

            # Get the original request
            if not state.user_input_request:
                return AgentResponse(
                    status=AgentStatus.ERROR,
                    error="No pending input request",
                    message="No input request found for this session",
                )

            # Process user response
            from app.core.human_in_loop import UserInputRequest

            original_request = UserInputRequest(
                type=state.user_input_request["type"],
                question=state.user_input_request["question"],
                options=state.user_input_request.get("options"),
                default_value=state.user_input_request.get("default_value"),
                metadata=state.user_input_request.get("metadata"),
            )

            # Convert user_input to dict if it's a string
            if isinstance(user_input, str):
                user_input_dict = {"value": user_input}
            else:
                user_input_dict = user_input

            user_response = self.human_in_loop_handler.process_user_response(
                request=original_request,
                user_input=user_input_dict,
            )

            log.info(
                "user_response_processed",
                cancelled=user_response.cancelled,
                has_value=user_response.value is not None,
            )

            # Check if user cancelled
            if user_response.cancelled:
                state.status = AgentStatus.COMPLETED
                # TODO: Get user's preferred language from user profile
                # For now, default to English
                cancelled_message = get_message("operation_cancelled", language="en")
                state.final_response = cancelled_message
                state.waiting_for_user_input = False
                state.user_input_request = None

                await self._save_state(state)

                return AgentResponse(
                    status=AgentStatus.COMPLETED,
                    message=cancelled_message,
                )

            # Update state with user input
            state.waiting_for_user_input = False
            state.user_input_request = None

            # Process user input and update last step
            user_confirmed_action = False
            if state.steps:
                last_step = state.steps[-1]

                # If user confirmed, update action_input with confirmed values
                if original_request.metadata and "suggested_action" in original_request.metadata:
                    suggested_action = original_request.metadata["suggested_action"]
                    if user_response.value is True or user_response.value == "yes":
                        # User confirmed, use suggested action
                        last_step.action = suggested_action.get("action")
                        last_step.action_input = suggested_action.get("parameters")
                        user_confirmed_action = True
                        # DON'T set observation yet - let the action execute first
                        log.info(
                            "user_confirmed_action",
                            action=last_step.action,
                            action_input=str(last_step.action_input)[:200] if last_step.action_input else None,
                            observation=last_step.observation,
                            step_number=last_step.step_number,
                        )
                    else:
                        # User provided custom value, update action_input
                        if last_step.action_input:
                            # Update the parameter that was being requested
                            reason = original_request.metadata.get("reason", "")
                            if ":" in reason:
                                param_name = reason.split(":")[1]
                                last_step.action_input[param_name] = user_response.value

                # Only set observation if user didn't confirm an action to execute
                # (for confirmed actions, observation will be set after execution)
                if not user_confirmed_action:
                    if user_response.selected_option:
                        observation = f"User selected: {user_response.selected_option['label']} ({user_response.value})"
                    else:
                        observation = f"User input: {user_response.value}"
                    last_step.observation = observation

            # Add user input to conversation history
            await self.memory.add_message(
                session_id=session_id,
                role="user",
                content=str(user_response.value),
                metadata={"type": "user_input_response"},
            )

            # Debug: Log state before continuing ReAct loop
            if state.steps:
                last_step_before_loop = state.steps[-1]
                log.info(
                    "debug_before_react_loop",
                    step_number=last_step_before_loop.step_number,
                    action=last_step_before_loop.action,
                    has_action_input=last_step_before_loop.action_input is not None,
                    has_observation=last_step_before_loop.observation is not None,
                )

            # Continue ReAct loop
            response = await self._react_loop(state, None)

            # Save state
            await self._save_state(state)

            return response

        except Exception as e:
            log.error("continue_with_user_input_error", error=str(e), exc_info=True)
            return AgentResponse(
                status=AgentStatus.ERROR,
                error=str(e),
                message="An error occurred while processing your input",
            )

    async def _react_loop(
        self,
        state: AgentState,
        loaded_tools: list[AgentTool] | None,
    ) -> AgentResponse:
        """Execute the ReAct loop.

        Args:
            state: Agent state
            loaded_tools: Loaded tools

        Returns:
            AgentResponse
        """
        log = logger.bind(session_id=state.session_id)

        # Get tools
        if loaded_tools is None:
            if self.tool_registry:
                loaded_tools = self.tool_registry.get_all_tools()
            else:
                loaded_tools = []

        # Main loop
        while state.current_step < state.max_steps:
            state.current_step += 1
            state.status = AgentStatus.THINKING

            log.info("react_step_start", step=state.current_step)
            log.info("DEBUG_MARKER_AFTER_REACT_STEP_START")  # Marker to verify code execution

            try:
                # Debug logging to diagnose confirmed action check
                log.info(
                    "debug_state_check",
                    has_steps=bool(state.steps),
                    steps_count=len(state.steps) if state.steps else 0,
                )

                if state.steps:
                    last_step = state.steps[-1]
                    log.info(
                        "debug_last_step",
                        step_number=last_step.step_number,
                        has_action=bool(last_step.action),
                        action_value=last_step.action,
                        has_action_input=last_step.action_input is not None,
                        action_input_value=str(last_step.action_input)[:200] if last_step.action_input else None,
                        has_observation=last_step.observation is not None,
                        observation_value=str(last_step.observation)[:100] if last_step.observation else None,
                    )

                # Check if the last step has a confirmed action awaiting execution
                # (action and action_input set, but no observation)
                pending_action_step = None
                if state.steps:
                    last_step = state.steps[-1]
                    log.info(
                        "CHECKING_CONFIRMED_ACTION",
                        has_action=bool(last_step.action),
                        action=last_step.action,
                        has_action_input=last_step.action_input is not None,
                        action_input_empty=not bool(last_step.action_input) if last_step.action_input is not None else None,
                        has_observation=last_step.observation is not None,
                    )

                if state.steps and state.steps[-1].action and state.steps[-1].action_input is not None:
                    last_step = state.steps[-1]
                    if last_step.observation is None:
                        # Last step has a confirmed action that hasn't been executed yet
                        pending_action_step = last_step
                        log.info(
                            "executing_confirmed_action",
                            step=last_step.step_number,
                            action=last_step.action,
                        )

                # Plan next action using Planner (unless we have a pending confirmed action)
                if pending_action_step:
                    # Use the confirmed action from the last step
                    step = pending_action_step
                    # Don't increment current_step since we're executing the last step's action
                    state.current_step -= 1
                    log.info("using_confirmed_action_from_last_step", action=step.action)
                else:
                    # Plan a new action
                    execution_history = [
                        {
                            "thought": step.thought,
                            "action": step.action,
                            "action_input": step.action_input,
                            "observation": step.observation,
                        }
                        for step in state.steps
                    ]

                    plan = await self.planner.plan_next_action(
                        user_message=state.user_message,
                        available_tools=loaded_tools,
                        execution_history=execution_history,
                        user_id=state.user_id,
                    )

                    # Create step with plan
                    step = AgentStep(
                        step_number=state.current_step,
                        thought=plan.thought,
                        action=plan.action,
                        action_input=plan.action_input,
                    )

                    state.steps.append(step)

                # If this is a pending confirmed action, skip evaluation and execute directly
                if pending_action_step:
                    log.info("skipping_evaluation_for_confirmed_action")
                else:
                    log.info(
                        "plan_generated",
                        step=state.current_step,
                        has_action=plan.action is not None,
                        is_complete=plan.is_complete,
                    )

                    # Check if task is complete
                    if plan.is_complete:
                        state.status = AgentStatus.COMPLETED
                        state.final_response = plan.final_answer or "Task completed successfully"
                        break

                    # If no action, something went wrong
                    if not plan.action:
                        state.status = AgentStatus.COMPLETED
                        state.final_response = plan.thought
                        break

                    # Evaluate if human input is needed
                    evaluation = await self.evaluator.evaluate_plan(
                        plan=plan,
                        user_message=state.user_message,
                        execution_history=execution_history,
                        user_id=state.user_id,
                    )

                    log.info(
                        "evaluation_complete",
                        needs_human_input=evaluation.needs_human_input,
                        confirmation_type=evaluation.confirmation_type.value if evaluation.needs_human_input else None,
                    )

                    # If human input is needed, pause and wait
                    if evaluation.needs_human_input:
                        state.status = AgentStatus.WAITING_FOR_USER
                        state.waiting_for_user_input = True

                        # Create user input request
                        user_input_request = self.human_in_loop_handler.create_request_from_evaluation(
                            evaluation=evaluation
                        )
                        state.user_input_request = user_input_request.to_dict()

                        # Save state and return
                        await self._save_state(state)

                        log.info(
                            "waiting_for_user_input",
                            request_type=user_input_request.type.value,
                        )

                        return AgentResponse(
                            status=AgentStatus.WAITING_FOR_USER,
                            message=user_input_request.question,
                            requires_user_input=True,
                            user_input_request=user_input_request.to_dict(),
                        )

                # Execute action
                state.status = AgentStatus.ACTING

                try:
                    # Convert messages to dict format for tool context
                    conversation_history = self._messages_to_history(state.messages)

                    tool_result = await self._execute_tool(
                        tool_name=step.action,
                        parameters=step.action_input or {},
                        available_tools=loaded_tools,
                        user_id=state.user_id,
                        conversation_history=conversation_history,
                    )

                    # Record tool call
                    tool_call = ToolCall(
                        tool_name=step.action,
                        parameters=step.action_input or {},
                        result=tool_result,
                    )
                    state.tool_calls.append(tool_call)

                    # Save tool result to memory
                    await self.memory.save_tool_result(
                        session_id=state.session_id,
                        tool_name=step.action,
                        parameters=step.action_input or {},
                        result=tool_result,
                    )

                    # Add observation
                    step.observation = self._format_tool_result(tool_result)

                    log.info(
                        "tool_executed",
                        tool_name=step.action,
                        success=tool_result.get("success", False),
                    )

                except ToolExecutionError as e:
                    # Record failed tool call
                    tool_call = ToolCall(
                        tool_name=plan.action,
                        parameters=plan.action_input or {},
                        error=str(e),
                    )
                    state.tool_calls.append(tool_call)

                    # Save error to memory
                    await self.memory.save_tool_result(
                        session_id=state.session_id,
                        tool_name=plan.action,
                        parameters=plan.action_input or {},
                        error=str(e),
                    )

                    # Add error observation
                    step.observation = f"Tool execution failed: {e.message}"

                    log.error(
                        "tool_execution_failed",
                        tool_name=plan.action,
                        error=str(e),
                    )

                except Exception as e:
                    # Unexpected error
                    step.observation = f"Unexpected error: {str(e)}"
                    log.error(
                        "tool_execution_error",
                        tool_name=plan.action,
                        error=str(e),
                        exc_info=True,
                    )

                # Check if we should stop
                if state.current_step >= state.max_steps:
                    state.status = AgentStatus.COMPLETED
                    state.final_response = "Maximum steps reached. Task may be incomplete."
                    break

            except GeminiError as e:
                log.error("planning_error", error=str(e), step=state.current_step)
                state.status = AgentStatus.ERROR
                state.error_message = f"Planning failed: {e.message}"
                break

            except Exception as e:
                log.error(
                    "react_step_error",
                    error=str(e),
                    step=state.current_step,
                    exc_info=True,
                )
                state.status = AgentStatus.ERROR
                state.error_message = f"Execution error: {str(e)}"
                break

        return AgentResponse(
            status=state.status,
            message=state.final_response or state.error_message,
            data={"steps": len(state.steps)},
            error=state.error_message,
        )

    async def _react_loop_stream(
        self,
        state: AgentState,
        loaded_tools: list[AgentTool] | None,
    ):
        """Execute the ReAct loop with streaming response.

        Streams the agent's thinking process and final response in real-time.

        Event types emitted:
        - thought: Agent's reasoning process (streaming)
        - action: Tool being executed
        - observation: Tool execution result
        - text: Final response text (streaming for long responses)
        - user_input_request: Needs user confirmation
        - error: Error occurred

        Args:
            state: Agent state
            loaded_tools: Loaded tools

        Yields:
            dict: Events with streaming content
        """
        log = logger.bind(session_id=state.session_id)

        # Get tools
        if loaded_tools is None:
            if self.tool_registry:
                loaded_tools = self.tool_registry.get_all_tools()
            else:
                loaded_tools = []

        # Main loop
        while state.current_step < state.max_steps:
            state.current_step += 1
            state.status = AgentStatus.THINKING

            log.info("react_step_start", step=state.current_step)

            try:
                # Check if the last step has a confirmed action awaiting execution
                # (action and action_input set, but no observation)
                pending_action_step = None
                if state.steps:
                    last_step = state.steps[-1]
                    log.info(
                        "STREAM_CHECKING_CONFIRMED_ACTION",
                        has_action=bool(last_step.action),
                        action=last_step.action,
                        has_action_input=last_step.action_input is not None,
                        has_observation=last_step.observation is not None,
                    )

                if state.steps and state.steps[-1].action and state.steps[-1].action_input is not None:
                    last_step = state.steps[-1]
                    if last_step.observation is None:
                        # Last step has a confirmed action that hasn't been executed yet
                        pending_action_step = last_step
                        log.info(
                            "stream_executing_confirmed_action",
                            step=last_step.step_number,
                            action=last_step.action,
                        )

                # Build execution history
                execution_history = [
                    {
                        "thought": step.thought,
                        "action": step.action,
                        "action_input": step.action_input,
                        "observation": step.observation,
                    }
                    for step in state.steps
                ]

                # Plan next action with streaming (unless we have a pending confirmed action)
                plan = None
                thought_content = ""
                step = None

                if pending_action_step:
                    # Use the confirmed action from the last step
                    step = pending_action_step
                    # Don't increment current_step since we're executing the last step's action
                    state.current_step -= 1
                    log.info("stream_using_confirmed_action_from_last_step", action=step.action)

                    # Create a minimal plan object for the confirmed action
                    plan = PlanAction(
                        thought=step.thought or "Executing confirmed action",
                        action=step.action,
                        action_input=step.action_input,
                        is_complete=False,
                    )
                else:
                    async for event in self.planner.plan_next_action_stream(
                    user_message=state.user_message,
                    available_tools=loaded_tools,
                    execution_history=execution_history,
                    user_id=state.user_id,
                    attachments=state.attachments if state.attachments else None,
                ):
                        if event["type"] == "thought":
                            chunk = event["content"]
                            thought_content += chunk
                            # Always stream thought events - frontend will handle display
                            yield {"type": "thought", "content": chunk}

                        elif event["type"] == "plan":
                            plan = event["data"]

                    if not plan:
                        log.error("no_plan_received")
                        yield {"type": "error", "error": "Failed to generate plan"}
                        break

                    # Create step with plan
                    step = AgentStep(
                        step_number=state.current_step,
                        thought=plan.thought or thought_content[:500],
                        action=plan.action,
                        action_input=plan.action_input,
                    )

                    state.steps.append(step)

                log.info(
                    "plan_generated",
                    step=state.current_step,
                    has_action=plan.action is not None,
                    is_complete=plan.is_complete,
                )

                # Check if task is complete
                if plan.is_complete:
                    state.status = AgentStatus.COMPLETED

                    # Use final_answer directly (don't stream again)
                    if plan.final_answer:
                        yield {"type": "text", "content": plan.final_answer}
                        state.final_response = plan.final_answer
                    else:
                        # Fallback - extract clean response from thought
                        clean_response = self._extract_clean_response(thought_content)
                        state.final_response = clean_response or "Task completed."
                        yield {"type": "text", "content": state.final_response}
                    break

                # If no action but not complete, use final_answer or clean thought
                if not plan.action:
                    state.status = AgentStatus.COMPLETED
                    if plan.final_answer:
                        state.final_response = plan.final_answer
                    else:
                        state.final_response = self._extract_clean_response(thought_content) or "I couldn't determine what to do."
                    yield {"type": "text", "content": state.final_response}
                    break

                # Evaluate if human input is needed (skip evaluation for confirmed actions)
                if pending_action_step:
                    log.info("stream_skipping_evaluation_for_confirmed_action")
                else:
                    evaluation = await self.evaluator.evaluate_plan(
                        plan=plan,
                        user_message=state.user_message,
                        execution_history=execution_history,
                        user_id=state.user_id,
                    )

                    log.info(
                        "evaluation_complete",
                        needs_human_input=evaluation.needs_human_input,
                    )

                    # If human input is needed, yield request and stop
                    if evaluation.needs_human_input:
                        state.status = AgentStatus.WAITING_FOR_USER
                        state.waiting_for_user_input = True

                        user_input_request = self.human_in_loop_handler.create_request_from_evaluation(
                            evaluation=evaluation
                        )
                        state.user_input_request = user_input_request.to_dict()

                        await self._save_state(state)

                        yield {
                            "type": "user_input_request",
                            "data": user_input_request.to_dict(),
                            "message": user_input_request.question,
                        }
                        return

                # Notify user about tool execution
                yield {
                    "type": "action",
                    "tool": plan.action,
                    "parameters": plan.action_input,
                }

                # Execute action
                state.status = AgentStatus.ACTING

                try:
                    # Convert messages to dict format for tool context
                    conversation_history = self._messages_to_history(state.messages)
                    
                    tool_result = await self._execute_tool(
                        tool_name=plan.action,
                        parameters=plan.action_input or {},
                        available_tools=loaded_tools,
                        user_id=state.user_id,
                        conversation_history=conversation_history,
                    )

                    tool_call = ToolCall(
                        tool_name=plan.action,
                        parameters=plan.action_input or {},
                        result=tool_result,
                    )
                    state.tool_calls.append(tool_call)

                    await self.memory.save_tool_result(
                        session_id=state.session_id,
                        tool_name=plan.action,
                        parameters=plan.action_input or {},
                        result=tool_result,
                    )

                    observation = self._format_tool_result(tool_result)
                    step.observation = observation

                    # Notify user about tool result
                    # Include full data for media-generating tools
                    observation_event = {
                        "type": "observation",
                        "tool": plan.action,
                        "result": observation,
                        "success": tool_result.get("success", False),
                    }

                    # Include generated images/videos in the event
                    if plan.action == "generate_image_tool" and tool_result.get("images"):
                        observation_event["images"] = tool_result["images"]
                    elif plan.action == "generate_video_tool":
                        # Priority: GCS object name > base64 > direct URL
                        if tool_result.get("video_object_name"):
                            # GCS object name for signed URL generation
                            observation_event["video_object_name"] = tool_result["video_object_name"]
                            observation_event["video_bucket"] = tool_result.get("video_bucket")
                        elif tool_result.get("video_data_b64"):
                            # Fallback to base64 data
                            observation_event["video_data_b64"] = tool_result["video_data_b64"]
                            observation_event["video_format"] = tool_result.get("video_format", "mp4")
                        elif tool_result.get("video_url"):
                            # Legacy fallback to direct URL
                            observation_event["video_url"] = tool_result["video_url"]

                    yield observation_event

                    log.info("tool_executed", tool_name=plan.action)

                except ToolExecutionError as e:
                    tool_call = ToolCall(
                        tool_name=plan.action,
                        parameters=plan.action_input or {},
                        error=str(e),
                    )
                    state.tool_calls.append(tool_call)

                    step.observation = f"Tool execution failed: {e.message}"

                    yield {
                        "type": "observation",
                        "tool": plan.action,
                        "result": step.observation,
                        "success": False,
                    }

                    log.error("tool_execution_failed", tool_name=plan.action, error=str(e))

                except Exception as e:
                    step.observation = f"Unexpected error: {str(e)}"

                    yield {
                        "type": "observation",
                        "tool": plan.action,
                        "result": step.observation,
                        "success": False,
                    }

                    log.error("tool_execution_error", error=str(e), exc_info=True)

                # Check if we should stop due to max steps
                if state.current_step >= state.max_steps:
                    state.status = AgentStatus.COMPLETED
                    error_msg = "Maximum steps reached. Task may be incomplete."
                    state.final_response = error_msg
                    yield {"type": "text", "content": error_msg}
                    break

            except GeminiError as e:
                log.error("planning_error", error=str(e))
                state.status = AgentStatus.ERROR
                error_msg = f"Planning failed: {e.message}"
                state.error_message = error_msg
                yield {"type": "error", "error": error_msg}
                break

            except Exception as e:
                log.error("react_step_error", error=str(e), exc_info=True)
                state.status = AgentStatus.ERROR
                error_msg = f"Execution error: {str(e)}"
                state.error_message = error_msg
                yield {"type": "error", "error": error_msg}
                break

    async def _get_or_create_state(
        self,
        user_message: str,
        user_id: str,
        session_id: str,
        conversation_id: str | None,
    ) -> AgentState:
        """Get existing state or create new one.

        If there's an existing state waiting for user input, load it
        and continue from where we left off. Otherwise create fresh state.

        Args:
            user_message: User message
            user_id: User ID
            session_id: Session ID
            conversation_id: Conversation ID

        Returns:
            AgentState
        """
        # Check if there's an existing state waiting for user input
        existing_state = await self._load_state(session_id)
        if existing_state and existing_state.waiting_for_user_input:
            logger.info(
                "resuming_from_waiting_state",
                session_id=session_id,
                original_message=existing_state.user_message[:50] if existing_state.user_message else "",
            )

            # Update the last step with user's response
            user_confirmed_action = False
            if existing_state.steps:
                last_step = existing_state.steps[-1]

                # Check if user is confirming a suggested action
                if existing_state.user_input_request:
                    metadata = existing_state.user_input_request.get("metadata", {})
                    suggested_action = metadata.get("suggested_action")

                    if suggested_action:
                        # User is responding to a confirmation request
                        # Check if they confirmed (true/yes) or rejected
                        user_message_str = str(user_message).strip()
                        user_message_lower = user_message_str.lower()
                        # Match various confirmation formats from frontend
                        is_confirmed = (
                            user_message_lower in ["true", "yes", "确认", "✅"]
                            or user_message_str == "✅ 确认"  # Exact match with emoji
                            or "确认" in user_message_str  # Contains confirmation text
                        )
                        if is_confirmed:
                            # User confirmed, set the action to execute
                            last_step.action = suggested_action.get("action")
                            last_step.action_input = suggested_action.get("parameters")
                            user_confirmed_action = True
                            # DON'T set observation yet - let execution set it
                            logger.info(
                                "user_confirmed_action_in_process_message",
                                action=last_step.action,
                                action_input=str(last_step.action_input)[:200] if last_step.action_input else None,
                            )
                        else:
                            # User rejected or provided alternative
                            last_step.observation = f"User rejected: {user_message}"
                    else:
                        # Not a confirmation, check if updating action_input parameter
                        reason = metadata.get("reason", "")
                        if ":" in reason:
                            param_name = reason.split(":")[1]
                            if last_step.action_input:
                                last_step.action_input[param_name] = user_message
                        last_step.observation = f"User input: {user_message}"

                # Only set observation if user didn't confirm an action to execute
                if not user_confirmed_action and not existing_state.user_input_request:
                    last_step.observation = f"User selected: {user_message}"

            # Reset waiting state
            existing_state.waiting_for_user_input = False
            existing_state.user_input_request = None

            return existing_state

        # Create fresh state for new messages (using dataclass, not TypedDict)
        from langchain_core.messages import HumanMessage
        
        state = AgentState(
            session_id=session_id,
            user_id=user_id,
            conversation_id=conversation_id,
            user_message=user_message,
            max_steps=self.max_steps,
            messages=[HumanMessage(content=user_message)],
        )
        
        return state

    async def _load_state(self, session_id: str) -> AgentState | None:
        """Load state from Redis.

        Args:
            session_id: Session ID

        Returns:
            AgentState or None if not found
        """
        try:
            redis = await get_redis()
            key = f"agent:state:{session_id}"

            data = await redis.get(key)
            if not data:
                return None

            import json

            state_dict = json.loads(data)
            return AgentState.from_dict(state_dict)

        except Exception as e:
            logger.error("load_state_error", session_id=session_id, error=str(e))
            return None

    async def _save_state(self, state: AgentState) -> None:
        """Save state to Redis.

        Args:
            state: Agent state
        """
        try:
            redis = await get_redis()
            key = f"agent:state:{state.session_id}"

            state.updated_at = datetime.utcnow()

            import json

            data = json.dumps(state.to_dict(), ensure_ascii=False)
            await redis.set(key, data, ex=self.state_ttl)

            logger.debug("state_saved", session_id=state.session_id)

        except Exception as e:
            logger.error(
                "save_state_error",
                session_id=state.session_id,
                error=str(e),
            )

    async def get_state(self, session_id: str) -> AgentState | None:
        """Get current agent state for a session.

        Args:
            session_id: Session ID

        Returns:
            AgentState or None if not found
        """
        return await self._load_state(session_id)

    async def clear_state(self, session_id: str) -> bool:
        """Clear agent state for a session.

        Args:
            session_id: Session ID

        Returns:
            True if cleared successfully
        """
        try:
            redis = await get_redis()
            key = f"agent:state:{session_id}"
            await redis.delete(key)
            logger.info("state_cleared", session_id=session_id)
            return True
        except Exception as e:
            logger.error("clear_state_error", session_id=session_id, error=str(e))
            return False

    async def _execute_tool(
        self,
        tool_name: str,
        parameters: dict[str, Any],
        available_tools: list[AgentTool],
        user_id: str,
        conversation_history: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Execute a tool.

        Args:
            tool_name: Name of the tool to execute
            parameters: Tool parameters
            available_tools: List of available tools
            user_id: User ID for context
            conversation_history: Optional conversation history for context-aware tools

        Returns:
            Tool execution result

        Raises:
            ToolExecutionError: If tool execution fails
        """
        log = logger.bind(tool_name=tool_name, user_id=user_id)
        log.info("execute_tool_start")

        # Find tool
        tool = None
        for t in available_tools:
            if t.name == tool_name:
                tool = t
                break

        if not tool:
            raise ToolExecutionError(
                message=f"Tool '{tool_name}' not found",
                tool_name=tool_name,
                error_code="TOOL_NOT_FOUND",
            )

        # Execute tool
        try:
            context = {
                "user_id": user_id,
                "conversation_history": conversation_history or [],
            }
            result = await tool.execute(parameters=parameters, context=context)

            log.info("execute_tool_complete", success=result.get("success", False))

            return result

        except ToolExecutionError:
            raise

        except Exception as e:
            log.error("execute_tool_error", error=str(e), exc_info=True)
            raise ToolExecutionError(
                message=f"Tool execution failed: {str(e)}",
                tool_name=tool_name,
                error_code="EXECUTION_ERROR",
            )

    def _messages_to_history(self, messages: list | None) -> list[dict[str, Any]]:
        """Convert LangChain messages to simple dict format for tool context.

        Args:
            messages: List of LangChain BaseMessage objects or None

        Returns:
            List of message dicts with role, content, and metadata
        """
        if not messages:
            return []
            
        history = []
        for msg in messages:
            msg_dict = {
                "role": getattr(msg, "type", "unknown"),
                "content": getattr(msg, "content", ""),
            }
            
            # Extract any image data from message metadata
            if hasattr(msg, "additional_kwargs"):
                kwargs = msg.additional_kwargs
                if "generated_images" in kwargs:
                    msg_dict["generated_images"] = kwargs["generated_images"]
                if "attachments" in kwargs:
                    msg_dict["attachments"] = kwargs["attachments"]
            
            history.append(msg_dict)
        
        return history

    def _format_tool_result(self, result: dict[str, Any]) -> str:
        """Format tool result as observation text.

        Args:
            result: Tool result dictionary

        Returns:
            Formatted observation text
        """
        if not result:
            return "Tool returned no result"

        # Check for success
        success = result.get("success", False)
        message = result.get("message", "")

        if success:
            observation = f"Success: {message}"

            # Add summary if present (e.g., from google_search)
            if "summary" in result and result["summary"]:
                summary = result["summary"]
                # Truncate if too long but keep useful info
                if len(summary) > 3000:
                    summary = summary[:3000] + "..."
                observation += f"\n\nSearch Results:\n{summary}"

            # Add sources if present
            if "sources" in result and result["sources"]:
                sources = result["sources"]
                if sources:
                    source_list = []
                    for src in sources[:5]:  # Max 5 sources
                        title = src.get("title", "")
                        url = src.get("url", "")
                        if title or url:
                            source_list.append(f"- {title}: {url}")
                    if source_list:
                        observation += f"\n\nSources:\n" + "\n".join(source_list)

            # Add key data points
            if "data" in result:
                data = result["data"]
                if isinstance(data, dict):
                    key_points = []
                    for key, value in list(data.items())[:5]:  # First 5 items
                        key_points.append(f"{key}: {value}")
                    if key_points:
                        observation += f"\nData: {', '.join(key_points)}"

            return observation
        else:
            error = result.get("error", "Unknown error")
            return f"Failed: {message or error}"

    def _extract_clean_response(self, thought_content: str) -> str:
        """Extract clean response text from thought content.

        Removes JSON blocks and technical formatting.

        Args:
            thought_content: Raw thought content from planner

        Returns:
            Clean text suitable for user display
        """
        if not thought_content:
            return ""

        # Remove JSON blocks
        clean = thought_content
        if "```json" in clean:
            clean = clean.split("```json")[0]
        if "```" in clean:
            clean = clean.split("```")[0]

        # Remove common headers
        for header in ["## Thinking", "## Decision", "## Response"]:
            clean = clean.replace(header, "")

        # Remove leading/trailing whitespace
        clean = clean.strip()

        return clean
