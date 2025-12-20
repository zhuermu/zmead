"""Strands Agent implementation for AAE.

This module provides the StrandsReActAgent class that replaces the LangGraph
ReActAgent with Strands Agents framework implementation.

The agent follows the "Agents as Tools" pattern where specialized capability
agents are wrapped as tools and provided to a central orchestrator agent.

Key features:
- Multi-provider AI model support (Gemini, Bedrock, SageMaker)
- Dynamic tool loading based on user intent
- Human-in-the-loop for confirmations
- State persistence via Redis
- Streaming responses
"""

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, AsyncIterator

import structlog
from strands import Agent, tool, ToolContext
from strands.models import BedrockModel
from strands.models.gemini import GeminiModel

from app.core.config import get_settings
from app.core.human_in_loop import HumanInLoopHandler, UserInputResponse
from app.core.i18n import get_message
from app.core.memory import AgentMemory
from app.core.redis_client import get_redis
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

    # Conversation messages
    messages: list[dict[str, Any]] = field(default_factory=list)

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
            "messages": self.messages,
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
            messages=data.get("messages", []),
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


class StrandsReActAgent:
    """Strands Agent for autonomous task execution.

    This agent replaces the LangGraph ReActAgent with Strands Agents framework.
    It implements the "Agents as Tools" pattern where specialized capability
    agents are wrapped as tools.

    Example:
        agent = StrandsReActAgent(
            model_provider="gemini",
            model_name="gemini-2.5-flash",
            tool_registry=tool_registry,
        )

        response = await agent.process_message(
            user_message="Generate an ad image for my product",
            user_id="user123",
            session_id="session456",
        )
    """

    def __init__(
        self,
        model_provider: str = "gemini",
        model_name: str | None = None,
        tool_registry: ToolRegistry | None = None,
        memory: AgentMemory | None = None,
        human_in_loop_handler: HumanInLoopHandler | None = None,
        max_steps: int = 10,
        state_ttl: int = 3600,  # 1 hour
    ):
        """Initialize the Strands ReAct Agent.

        Args:
            model_provider: Model provider ("gemini", "bedrock", "sagemaker")
            model_name: Specific model name (optional, uses default for provider)
            tool_registry: Tool registry for tool lookup
            memory: Memory component for state persistence
            human_in_loop_handler: Handler for user input requests
            max_steps: Maximum execution steps before stopping
            state_ttl: State TTL in Redis (seconds)
        """
        self.model_provider = model_provider
        self.model_name = model_name
        self.tool_registry = tool_registry
        self.memory = memory or AgentMemory(state_ttl=state_ttl)
        self.human_in_loop_handler = human_in_loop_handler or HumanInLoopHandler()
        self.max_steps = max_steps
        self.state_ttl = state_ttl

        # Create the orchestrator agent (will be initialized on first use)
        self._agent: Agent | None = None

        logger.info(
            "strands_agent_initialized",
            model_provider=model_provider,
            model_name=model_name,
            max_steps=max_steps,
            state_ttl=state_ttl,
        )

    def _get_default_model_name(self) -> str:
        """Get the default model name for the current provider."""
        if self.model_provider == "gemini":
            return "gemini-2.5-flash"
        elif self.model_provider == "bedrock":
            return "global.anthropic.claude-sonnet-4-5-20250929-v1:0"
        else:
            return "gemini-2.5-flash"

    def _get_model(self):
        """Get the AI model instance based on provider configuration."""
        settings = get_settings()
        
        if self.model_provider == "gemini":
            # Use Gemini model
            model_id = self.model_name or self._get_default_model_name()
            return GeminiModel(
                client_args={
                    "api_key": settings.gemini_api_key,
                },
                model_id=model_id,
                params={
                    "temperature": 0.7,
                    "max_output_tokens": 4096,
                },
            )
        elif self.model_provider == "bedrock":
            # Use AWS Bedrock model
            model_id = self.model_name or self._get_default_model_name()
            return BedrockModel(
                client_args={
                    "region_name": settings.aws_region,
                },
                model_id=model_id,
                params={
                    "temperature": 0.7,
                    "max_tokens": 4096,
                },
            )
        else:
            # Default to Gemini
            return GeminiModel(
                client_args={
                    "api_key": settings.gemini_api_key,
                },
                model_id=self._get_default_model_name(),
                params={
                    "temperature": 0.7,
                    "max_output_tokens": 4096,
                },
            )

    def _create_agent(self, tools: list[Any]) -> Agent:
        """Create a Strands Agent instance with the specified tools.

        Args:
            tools: List of tools (can be functions decorated with @tool or AgentTool instances)

        Returns:
            Configured Strands Agent
        """
        settings = get_settings()

        # Get the model
        model = self._get_model()

        # Create system prompt
        system_prompt = """You are an AI assistant for the AAE (Automated Ad Engine) platform.
You help users manage their advertising campaigns, generate creative content, analyze performance,
and gain market insights.

Your capabilities include:
- Generating ad creatives (images, videos, copy)
- Analyzing campaign performance
- Managing campaigns and budgets
- Creating landing pages
- Providing market insights and competitor analysis

Always be helpful, concise, and action-oriented. When users request actions that require
confirmation (like creating campaigns or changing budgets), explain what you're about to do
and wait for confirmation.

Use the available tools to accomplish user requests. Break down complex requests into steps.

When asked about your identity or who you are, simply introduce yourself as the AI assistant
for the AAE platform. Do not mention specific AI models, training data, or the companies that
created the underlying technology."""

        # Create the agent
        agent = Agent(
            system_prompt=system_prompt,
            tools=tools,
            model=model,
        )

        return agent

    async def process_message(
        self,
        user_message: str,
        user_id: str,
        session_id: str,
        conversation_id: str | None = None,
        loaded_tools: list[AgentTool] | None = None,
    ) -> AgentResponse:
        """Process a user message and execute the agent loop.

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

            # Add user message to conversation history
            await self.memory.add_message(
                session_id=session_id,
                role="user",
                content=user_message,
                model_provider=None,  # User messages don't have a provider
                model_name=None,
            )

            # Get tools
            if loaded_tools is None:
                if self.tool_registry:
                    loaded_tools = self.tool_registry.get_all_tools()
                else:
                    loaded_tools = []

            # Convert AgentTool instances to Strands tool functions
            strands_tools = self._convert_tools_to_strands(
                loaded_tools, user_id, session_id, model_preferences
            )

            # Create agent with tools
            agent = self._create_agent(strands_tools)

            # Prepare invocation state for context
            invocation_state = {
                "user_id": user_id,
                "session_id": session_id,
                "conversation_id": conversation_id,
                "attachments": state.attachments,
            }

            # Execute agent
            response_text = agent(user_message, invocation_state=invocation_state)

            # Update state
            state.status = AgentStatus.COMPLETED
            state.final_response = response_text

            # Add assistant response to conversation history
            await self.memory.add_message(
                session_id=session_id,
                role="assistant",
                content=response_text,
                metadata={"status": "completed"},
                model_provider=self.model_provider,
                model_name=self.model_name or self._get_default_model_name(),
            )

            # Save state
            await self._save_state(state)

            log.info("process_message_complete", status="completed")

            return AgentResponse(
                status=AgentStatus.COMPLETED,
                message=response_text,
            )

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
        model_preferences: Any = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Process a user message and stream the response in real-time.

        Args:
            user_message: User's message
            user_id: User ID
            session_id: Session ID
            conversation_id: Optional conversation ID
            loaded_tools: Optional pre-loaded tools
            attachments: Optional file attachments with S3 URLs
            model_preferences: User's model preferences for image/video generation

        Yields:
            dict: Events with type and content
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

            # Process and store attachments
            gemini_attachments = []
            if attachments:
                for att in attachments:
                    if att.get("geminiFileUri"):
                        gemini_attachments.append({
                            "filename": att.get("filename", "unknown"),
                            "contentType": att.get("contentType", "application/octet-stream"),
                            "geminiFileUri": att.get("geminiFileUri"),
                            "geminiFileName": att.get("geminiFileName"),
                            "type": att.get("type", "file"),
                        })

            if gemini_attachments:
                state.attachments = gemini_attachments
                log.info("attachments_stored_in_state", count=len(gemini_attachments))

            # Add user message to conversation history
            message_metadata = {}
            if gemini_attachments:
                message_metadata["attachments"] = gemini_attachments

            await self.memory.add_message(
                session_id=session_id,
                role="user",
                content=user_message,
                metadata=message_metadata,
                model_provider=None,  # User messages don't have a provider
                model_name=None,
            )

            # Get tools
            if loaded_tools is None:
                if self.tool_registry:
                    loaded_tools = self.tool_registry.get_all_tools()
                else:
                    loaded_tools = []

            # Convert AgentTool instances to Strands tool functions
            strands_tools = self._convert_tools_to_strands(
                loaded_tools, user_id, session_id, model_preferences
            )

            # Create agent with tools
            agent = self._create_agent(strands_tools)

            # Prepare invocation state
            invocation_state = {
                "user_id": user_id,
                "session_id": session_id,
                "conversation_id": conversation_id,
                "attachments": state.attachments,
            }

            # Execute agent with streaming (Strands Agents use stream_async)
            # stream_async yields event dictionaries with keys: data, complete, current_tool_use, etc.
            full_response = ""
            async for event in agent.stream_async(user_message, invocation_state=invocation_state):
                # Extract text content from event
                if isinstance(event, dict):
                    # Text content is in 'data' key
                    if "data" in event and event["data"]:
                        text_chunk = event["data"]
                        full_response += text_chunk
                        yield {"type": "text", "content": text_chunk}

                    # Tool usage information
                    if "current_tool_use" in event and event["current_tool_use"]:
                        tool_info = event["current_tool_use"]
                        logger.info(
                            "tool_execution",
                            tool_name=tool_info.get("name"),
                            session_id=session_id,
                        )
                else:
                    # Fallback: if event is a string directly
                    full_response += str(event)
                    yield {"type": "text", "content": str(event)}

            # Update state
            state.status = AgentStatus.COMPLETED
            state.final_response = full_response

            # Add assistant response to conversation history
            if full_response:
                await self.memory.add_message(
                    session_id=session_id,
                    role="assistant",
                    content=full_response,
                    metadata={"status": "completed"},
                    model_provider=self.model_provider,
                    model_name=self.model_name or self._get_default_model_name(),
                )

            # Save state
            await self._save_state(state)

            log.info("process_message_stream_complete", response_length=len(full_response))

        except Exception as e:
            log.error("process_message_stream_error", error=str(e), exc_info=True)
            yield {"type": "error", "error": str(e)}

    def _convert_tools_to_strands(
        self,
        agent_tools: list[AgentTool],
        user_id: str,
        session_id: str,
        model_preferences: Any = None,
    ) -> list[Any]:
        """Convert AgentTool instances to Strands tool functions.

        Args:
            agent_tools: List of AgentTool instances
            user_id: User ID for context
            session_id: Session ID for context
            model_preferences: User's model preferences for image/video generation

        Returns:
            List of Strands tool functions
        """
        strands_tools = []

        # Use factory function to avoid closure issue
        def make_tool_wrapper(captured_tool: AgentTool):
            """Factory function to capture tool in closure correctly."""
            # Create tool with proper name and description
            @tool(
                name=captured_tool.name,
                description=captured_tool.description,
                context=True,
            )
            async def tool_fn(
                tool_context: ToolContext,
                **kwargs
            ) -> dict[str, Any]:
                """Wrapper function for AgentTool execution."""
                # Prepare context with model preferences for generation tools
                context = {
                    "user_id": tool_context.invocation_state.get("user_id", user_id),
                    "session_id": tool_context.invocation_state.get("session_id", session_id),
                    "conversation_history": [],
                    "model_preferences": model_preferences,  # Pass to tools for multi-model support
                }

                # Execute the tool
                try:
                    result = await captured_tool.execute(parameters=kwargs, context=context)
                    return result
                except ToolExecutionError as e:
                    return {
                        "success": False,
                        "error": e.message,
                        "error_code": e.error_code,
                    }
                except Exception as e:
                    return {
                        "success": False,
                        "error": str(e),
                        "error_code": "EXECUTION_ERROR",
                    }

            return tool_fn

        for agent_tool in agent_tools:
            strands_tools.append(make_tool_wrapper(agent_tool))

        logger.info(
            "tools_converted_to_strands",
            tool_count=len(strands_tools),
            tool_names=[t.__name__ for t in strands_tools],
        )

        return strands_tools

    async def _get_or_create_state(
        self,
        user_message: str,
        user_id: str,
        session_id: str,
        conversation_id: str | None,
    ) -> AgentState:
        """Get existing state or create new one.

        Args:
            user_message: User message
            user_id: User ID
            session_id: Session ID
            conversation_id: Conversation ID

        Returns:
            AgentState
        """
        # Check if there's an existing state
        existing_state = await self._load_state(session_id)
        if existing_state:
            logger.info(
                "resuming_from_existing_state",
                session_id=session_id,
            )
            existing_state.user_message = user_message
            return existing_state

        # Create fresh state
        state = AgentState(
            session_id=session_id,
            user_id=user_id,
            conversation_id=conversation_id,
            user_message=user_message,
            max_steps=self.max_steps,
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
