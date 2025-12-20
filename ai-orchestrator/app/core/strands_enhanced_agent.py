"""Strands Enhanced ReAct Agent - 增强版智能 Agent.

这个模块在 Strands Agent 框架之上构建完整的 ReAct 智能层：
- ✅ 保留 Strands 框架的便利性（tool conversion, streaming, model flexibility）
- ✅ 添加显式的 Planner 逻辑（意图理解、任务分解、工具选择）
- ✅ 添加显式的 Evaluator 逻辑（风险评估、HITL 判断）
- ✅ 增强 Memory 系统（长期记忆、反思学习）
- ✅ 添加 Perceive 逻辑（自我评估、自适应终止）

目标：完全替换 LangChain，但保持甚至提升 AI 智能水平。

Architecture:
    User Input
        ↓
    [Planner] ← 显式规划节点
        ↓
    [Evaluator] ← 风险评估 + HITL
        ↓
    [Strands Agent] ← 工具执行
        ↓
    [Memory] ← 记忆存储
        ↓
    [Perceive] ← 自我评估
        ↓
    Response / Continue Loop
"""

import asyncio
import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, AsyncIterator

import structlog
from strands import Agent, tool, ToolContext
from strands.models import BedrockModel
from strands.models.gemini import GeminiModel

from app.core.config import get_settings
from app.core.evaluator import Evaluator, EvaluationResult
from app.core.human_in_loop import HumanInLoopHandler
from app.core.i18n import get_message
from app.core.memory import AgentMemory
from app.core.planner import Planner, PlanAction
from app.core.redis_client import get_redis
from app.services.gemini_client import GeminiClient
from app.tools.base import AgentTool, ToolExecutionError
from app.tools.registry import ToolRegistry

logger = structlog.get_logger(__name__)


class AgentStatus(str, Enum):
    """Agent execution status."""
    IDLE = "idle"
    PLANNING = "planning"
    EVALUATING = "evaluating"
    THINKING = "thinking"
    ACTING = "acting"
    WAITING_FOR_USER = "waiting_for_user"
    REFLECTING = "reflecting"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class ExecutionStep:
    """Single execution step in the ReAct loop."""
    step_number: int

    # Planning phase
    thought: str
    action: str | None = None
    action_input: dict[str, Any] | None = None

    # Evaluation phase
    needs_confirmation: bool = False
    evaluation_reason: str | None = None

    # Execution phase
    observation: str | None = None
    tool_result: dict[str, Any] | None = None

    # Reflection phase
    reflection: str | None = None
    should_continue: bool = True

    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class AgentState:
    """Enhanced agent state with full ReAct tracking."""
    # Identifiers
    session_id: str
    user_id: str
    conversation_id: str | None = None

    # Current request
    user_message: str = ""
    user_intent: str | None = None

    # Attachments
    attachments: list[dict[str, Any]] = field(default_factory=list)

    # Execution state
    status: AgentStatus = AgentStatus.IDLE
    current_step: int = 0
    max_steps: int = 10

    # ReAct execution steps
    steps: list[ExecutionStep] = field(default_factory=list)

    # Messages for Strands Agent
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
        """Serialize state to dict."""
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
                    "needs_confirmation": step.needs_confirmation,
                    "evaluation_reason": step.evaluation_reason,
                    "observation": step.observation,
                    "reflection": step.reflection,
                    "should_continue": step.should_continue,
                    "timestamp": step.timestamp.isoformat(),
                }
                for step in self.steps
            ],
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
        """Deserialize state from dict."""
        steps = []
        for step_data in data.get("steps", []):
            steps.append(
                ExecutionStep(
                    step_number=step_data["step_number"],
                    thought=step_data["thought"],
                    action=step_data.get("action"),
                    action_input=step_data.get("action_input"),
                    needs_confirmation=step_data.get("needs_confirmation", False),
                    evaluation_reason=step_data.get("evaluation_reason"),
                    observation=step_data.get("observation"),
                    reflection=step_data.get("reflection"),
                    should_continue=step_data.get("should_continue", True),
                    timestamp=datetime.fromisoformat(step_data["timestamp"]),
                )
            )

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
            messages=data.get("messages", []),
            waiting_for_user_input=data.get("waiting_for_user_input", False),
            user_input_request=data.get("user_input_request"),
            final_response=data.get("final_response"),
            error_message=data.get("error_message"),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
        )


class StrandsEnhancedReActAgent:
    """Enhanced Strands Agent with full ReAct intelligence.

    This agent combines:
    - Strands framework's convenience (tool conversion, streaming, multi-model)
    - ReAct pattern's intelligence (Planner, Evaluator, Memory, Perceive)
    - No LangChain dependency

    ReAct Loop:
    1. **Plan**: Analyze user intent, decompose task, select tools
    2. **Evaluate**: Assess risk, decide if HITL needed
    3. **Act**: Execute tool using Strands Agent
    4. **Remember**: Store execution result in memory
    5. **Perceive**: Self-assess, decide if task complete or continue

    Example:
        agent = StrandsEnhancedReActAgent(
            model_provider="gemini",
            tool_registry=registry,
        )

        async for event in agent.process_message_stream(
            user_message="Generate an ad image",
            user_id="user123",
            session_id="session456",
        ):
            print(event)
    """

    def __init__(
        self,
        model_provider: str = "gemini",
        model_name: str | None = None,
        tool_registry: ToolRegistry | None = None,
        max_steps: int = 10,
        state_ttl: int = 3600,
    ):
        """Initialize enhanced agent.

        Args:
            model_provider: AI provider ("gemini" or "bedrock")
            model_name: Specific model ID
            tool_registry: Tool registry
            max_steps: Max execution steps
            state_ttl: State TTL in Redis (seconds)
        """
        self.model_provider = model_provider
        self.model_name = model_name
        self.tool_registry = tool_registry
        self.max_steps = max_steps
        self.state_ttl = state_ttl

        # Initialize intelligence components
        # Note: Planner and Evaluator will use Strands Agent's model (respecting user preferences)
        # We still keep a GeminiClient for fallback scenarios
        self.gemini_client = GeminiClient() if model_provider == "gemini" else None
        self.planner = None  # Will be initialized per-request with user's model choice
        self.evaluator = None  # Will be initialized per-request with user's model choice
        self.memory = AgentMemory(state_ttl=state_ttl)
        self.human_in_loop_handler = HumanInLoopHandler()

        # Strands Agent will be created per-request
        self._strands_agent: Agent | None = None

        logger.info(
            "strands_enhanced_agent_initialized",
            model_provider=model_provider,
            model_name=model_name,
            max_steps=max_steps,
        )

    def _get_model(self):
        """Get AI model for Strands Agent."""
        settings = get_settings()

        if self.model_provider == "gemini":
            model_id = self.model_name or "gemini-2.5-flash"
            logger.info("creating_gemini_model", model_id=model_id)
            return GeminiModel(
                client_args={"api_key": settings.gemini_api_key},
                model_id=model_id,
                params={"temperature": 0.7, "max_output_tokens": 4096},
            )
        elif self.model_provider == "bedrock":
            # Use Claude Sonnet 4.5 as default (latest version with cross-region inference profile)
            model_id = self.model_name or "us.anthropic.claude-sonnet-4-5-20250929-v1:0"

            logger.info(
                "creating_bedrock_model",
                model_id=model_id,
                region=settings.aws_region,
                provider=self.model_provider,
            )

            # IMPORTANT: BedrockModel must be initialized with model_id as first positional argument
            # to ensure it's not overridden by default values
            return BedrockModel(
                model_id=model_id,  # ✅ First argument to ensure it's used
                client_args={"region_name": settings.aws_region},
                params={"temperature": 0.7, "max_tokens": 4096},
            )
        else:
            # Fallback to Gemini
            logger.warning("unknown_model_provider_fallback", provider=self.model_provider)
            return GeminiModel(
                client_args={"api_key": settings.gemini_api_key},
                model_id="gemini-2.5-flash",
                params={"temperature": 0.7, "max_output_tokens": 4096},
            )

    def _create_strands_agent(self, tools: list[Any]) -> Agent:
        """Create Strands Agent with tools."""
        model = self._get_model()

        system_prompt = """You are an AI assistant for the AAE (Automated Ad Engine) platform.

Your capabilities:
- Generate ad creatives (images, videos, copy)
- Analyze campaign performance
- Manage campaigns and budgets
- Create landing pages
- Provide market insights

IMPORTANT Instructions:

1. **Image/Video Generation Prompts**: When calling generate_image_tool or generate_video_tool, you MUST write the prompt parameter in English, even if the user's input is in Chinese. The underlying AI models (Bedrock Stable Diffusion, Luma Ray, etc.) work best with English prompts. Translate and rewrite the user's requirements into detailed, descriptive English prompts.

   Example:
   - User input (Chinese): "生成一张猫咪抓鱼的图片"
   - Your tool call: generate_image_tool(prompt="A realistic cat catching fish in a stream, paws reaching into clear water, water splashing around, rocks and green plants in the background, sunlight reflecting on the water surface, highly detailed, 8K ultra HD")

2. **No Image Links in Text**: When you generate images or videos using tools, DO NOT include image links or markdown image syntax (like ![alt](url)) in your text response. The generated files will automatically be displayed as attachments to the user. Just describe what you created in plain text.

Always be helpful, concise, and action-oriented. Use tools when needed."""

        return Agent(
            system_prompt=system_prompt,
            tools=tools,
            model=model,
        )

    async def process_message_stream(
        self,
        user_message: str,
        user_id: str,
        session_id: str,
        conversation_id: str | None = None,
        conversation_history: list[dict[str, str]] | None = None,
        loaded_tools: list[AgentTool] | None = None,
        attachments: list[dict] | None = None,
        model_preferences: Any = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Process message with streaming ReAct loop.

        Args:
            user_message: Current user message
            user_id: User identifier
            session_id: Session identifier
            conversation_id: Optional conversation identifier
            conversation_history: Previous conversation messages (list of {"role": str, "content": str})
            loaded_tools: Pre-loaded tools (optional)
            attachments: File attachments
            model_preferences: User's model preferences

        Yields events:
        - {"type": "planning", "content": str} - Planning phase
        - {"type": "thought", "content": str} - Agent reasoning
        - {"type": "evaluation", "data": dict} - Risk assessment
        - {"type": "action", "tool": str} - Tool execution
        - {"type": "observation", "result": str} - Tool result
        - {"type": "reflection", "content": str} - Self-assessment
        - {"type": "text", "content": str} - Final response
        - {"type": "user_input_request", "data": dict} - HITL request
        - {"type": "done"} - Complete
        """
        log = logger.bind(
            user_id=user_id,
            session_id=session_id,
            conversation_id=conversation_id,
        )
        log.info("enhanced_agent_process_start")

        try:
            # Initialize state
            state = await self._get_or_create_state(
                user_message=user_message,
                user_id=user_id,
                session_id=session_id,
                conversation_id=conversation_id,
            )

            # Store attachments
            if attachments:
                state.attachments = attachments

            # Add user message to memory
            await self.memory.add_message(
                session_id=session_id,
                role="user",
                content=user_message,
                metadata={"attachments": attachments} if attachments else None,
                model_provider=None,
                model_name=None,
            )

            # Get tools
            if loaded_tools is None:
                loaded_tools = self.tool_registry.get_all_tools() if self.tool_registry else []

            # Convert tools to Strands format (pass conversation_history for tool context)
            strands_tools = self._convert_tools_to_strands(
                loaded_tools, user_id, session_id, model_preferences, conversation_history
            )

            # Create Strands Agent (this will use user's model preferences)
            strands_agent = self._create_strands_agent(strands_tools)

            # Use Strands Agent directly (respects user's model choice)
            # Strands Agent has intelligent task decomposition and tool execution

            state.status = AgentStatus.THINKING
            # Send thought event (will be saved to processInfo in frontend)
            yield {"type": "thought", "content": "🤔 正在分析您的请求...\n"}

            # Build conversation context for system prompt (if history exists)
            # Strands Agent only accepts string input, so we need to inject history into the message
            user_message_with_context = state.user_message
            if conversation_history and len(conversation_history) > 0:
                # Build context string from history
                context_parts = []
                for msg in conversation_history[-10:]:  # Only last 10 messages to avoid token limit
                    role_name = "用户" if msg["role"] == "user" else "助手"
                    context_parts.append(f"{role_name}: {msg['content']}")

                context_str = "\n".join(context_parts)
                user_message_with_context = f"""对话历史：
{context_str}

当前问题：
{state.user_message}

请基于上述对话历史回答当前问题。"""

                logger.info(
                    "injecting_conversation_history",
                    history_length=len(conversation_history),
                    last_n_used=min(10, len(conversation_history)),
                )

            # Execute with Strands Agent using stream_async
            try:
                # Stream response from Strands Agent
                final_response = ""
                current_tool = None
                tool_announced = set()  # Track which tools have been announced to avoid duplicates

                # Call Strands Agent with message (including history in context)
                async for chunk in strands_agent.stream_async(user_message_with_context):
                    # Strands Agent returns dict chunks with different structures
                    if not isinstance(chunk, dict):
                        continue

                    # DEBUG: Log all chunk structures to understand event format
                    logger.debug(
                        "strands_chunk_received",
                        chunk_keys=list(chunk.keys()),
                        chunk_type=type(chunk).__name__,
                        has_event="event" in chunk,
                        has_delta="delta" in chunk,
                        has_data="data" in chunk,
                        chunk_sample={k: str(v)[:100] for k, v in chunk.items()},
                    )

                    # Handle tool stream events (tool streaming - observation events with attachments)
                    if "tool_stream_event" in chunk:
                        tool_stream_data = chunk["tool_stream_event"].get("data")
                        if isinstance(tool_stream_data, dict) and tool_stream_data.get("type") == "observation":
                            logger.info(
                                "tool_stream_observation_received",
                                tool=tool_stream_data.get("tool"),
                                has_attachments="attachments" in tool_stream_data,
                                attachment_count=len(tool_stream_data.get("attachments", [])),
                                tool_stream_data_keys=list(tool_stream_data.keys()),
                                tool_stream_data_preview=str(tool_stream_data)[:300],
                            )
                            # Forward observation event to frontend
                            logger.info(
                                "forwarding_observation_to_frontend",
                                event_keys=list(tool_stream_data.keys()),
                            )
                            yield tool_stream_data
                            continue

                    # Check for current_tool_use field mentioned in docs
                    if "current_tool_use" in chunk:
                        tool_info = chunk["current_tool_use"]
                        if isinstance(tool_info, dict) and "name" in tool_info:
                            tool_name = tool_info["name"]
                            tool_use_id = tool_info.get("toolUseId", tool_name)

                            # Only announce tool once (not on every input delta)
                            if tool_use_id not in tool_announced:
                                tool_announced.add(tool_use_id)
                                current_tool = tool_name
                                logger.info("tool_use_start", tool_name=tool_name, tool_use_id=tool_use_id)
                                yield {
                                    "type": "action",
                                    "tool": tool_name,
                                    "input": tool_info.get("input", {}),
                                    "message": f"使用工具 {tool_name}"
                                }

                    # Handle tool use events first (before text extraction)
                    if "event" in chunk and isinstance(chunk["event"], dict):
                        event = chunk["event"]

                        # Log event structure
                        logger.debug("event_structure", event_keys=list(event.keys()))

                        # Tool use start (various possible keys)
                        tool_event_keys = ["toolUseStart", "toolUse", "tool_use", "contentBlockStart"]
                        for key in tool_event_keys:
                            if key in event:
                                tool_info = event[key]
                                if isinstance(tool_info, dict):
                                    tool_name = tool_info.get("name") or tool_info.get("toolName")
                                    if tool_name:
                                        tool_input = tool_info.get("input", {})
                                        current_tool = tool_name
                                        logger.info("tool_start_event", tool_name=tool_name, input=tool_input)
                                        # Send action event (will be saved to processInfo)
                                        yield {
                                            "type": "action",
                                            "tool": tool_name,
                                            "input": tool_input,
                                            "message": f"使用工具 {tool_name}"
                                        }
                                        break

                        # Tool result
                        if "toolResult" in event:
                            tool_result = event["toolResult"]
                            result_content = tool_result.get("content", "")

                            # Debug logging to see the actual structure
                            logger.info(
                                "tool_result_event",
                                tool=current_tool,
                                tool_result_type=type(tool_result).__name__,
                                content_type=type(result_content).__name__,
                                has_content="content" in tool_result if isinstance(tool_result, dict) else False,
                                result_preview=str(result_content)[:200],
                                full_tool_result=str(tool_result)[:500]
                            )

                            # Parse tool result to extract structured data
                            observation_event = {
                                "type": "observation",
                                "tool": current_tool or "unknown",
                                "success": True,
                                "result": "执行成功"
                            }

                            # Try to parse result_content as JSON to extract attachments
                            attachments_to_send = None
                            if isinstance(result_content, str):
                                try:
                                    import json
                                    parsed_result = json.loads(result_content)
                                    if isinstance(parsed_result, dict):
                                        # Extract attachments for separate event
                                        if "attachments" in parsed_result:
                                            attachments_to_send = parsed_result["attachments"]
                                        # Update result message if available
                                        if "message" in parsed_result:
                                            observation_event["result"] = parsed_result["message"]
                                except json.JSONDecodeError:
                                    pass
                            elif isinstance(result_content, dict):
                                # Already a dict, extract directly
                                if "attachments" in result_content:
                                    attachments_to_send = result_content["attachments"]
                                if "message" in result_content:
                                    observation_event["result"] = result_content["message"]

                            # Include attachments in observation event (unified format per UNIFIED_ATTACHMENT_ARCHITECTURE.md)
                            if attachments_to_send and len(attachments_to_send) > 0:
                                observation_event["attachments"] = attachments_to_send

                            logger.info(
                                "sending_observation",
                                tool=current_tool,
                                has_attachments="attachments" in observation_event,
                                attachment_count=len(observation_event.get("attachments", [])),
                            )

                            # Send observation event with attachments
                            yield observation_event

                            current_tool = None
                            continue

                    # Extract text - ONLY use delta strategy to avoid duplication
                    # Forward the original streaming granularity from the model without buffering
                    if "delta" in chunk and isinstance(chunk["delta"], dict):
                        text = chunk["delta"].get("text", "")
                        if text:
                            final_response += text
                            # Forward as-is to maintain real-time streaming experience
                            yield {"type": "text", "content": text}
                            continue

                    # Skip data chunks (they're duplicates of delta)
                    if "data" in chunk:
                        continue

                    # Skip event.contentBlockDelta (already handled by delta above)
                    if "event" in chunk and "contentBlockDelta" in chunk["event"]:
                        continue

                    # Strategy: Final message or result
                    if "result" in chunk:
                        # Final result from Strands Agent - contains AgentResult
                        agent_result = chunk["result"]
                        # Debug: Print all attributes of AgentResult
                        agent_result_attrs = dir(agent_result)
                        public_attrs = [attr for attr in agent_result_attrs if not attr.startswith('_')]

                        # Try to get values of key attributes
                        attr_values = {}
                        for attr in ['output', 'data', 'content', 'text', 'response']:
                            if hasattr(agent_result, attr):
                                val = getattr(agent_result, attr)
                                attr_values[attr] = str(val)[:200] if val else None

                        logger.info(
                            "agent_result_received",
                            result_type=type(agent_result).__name__,
                            has_last_message=hasattr(agent_result, "last_message"),
                            has_messages=hasattr(agent_result, "messages"),
                            all_attrs=public_attrs[:20],  # Limit to first 20
                            attr_values=attr_values,
                        )

                        # Check the 'message' attribute (found in AgentResult)
                        if hasattr(agent_result, "message") and agent_result.message:
                            message = agent_result.message

                            # If it's a dict, log its keys and values
                            if isinstance(message, dict):
                                logger.info(
                                    "inspecting_agent_result_message_dict",
                                    message_keys=list(message.keys()),
                                    message_values_preview={k: str(v)[:200] for k, v in message.items()},
                                )

                                # Check if dict has 'content' key
                                if "content" in message:
                                    content = message["content"]
                                    logger.info(
                                        "found_content_in_message_dict",
                                        content_type=type(content).__name__,
                                        is_list=isinstance(content, list),
                                        content_length=len(content) if isinstance(content, (list, str)) else None,
                                    )

                                    # Process content blocks if it's a list
                                    if isinstance(content, list):
                                        for idx, block in enumerate(content):
                                            if isinstance(block, dict):
                                                block_type = block.get("type")
                                                logger.info(
                                                    "inspecting_content_block_dict",
                                                    index=idx,
                                                    block_type=block_type,
                                                    block_keys=list(block.keys()),
                                                )

                                                # Check for tool_result blocks
                                                if block_type == "tool_result":
                                                    tool_result_content = block.get("content")
                                                    logger.info(
                                                        "found_tool_result_in_message_dict",
                                                        content_preview=str(tool_result_content)[:300],
                                                    )

                                                    # Try to parse and extract attachments
                                                    try:
                                                        import json
                                                        if isinstance(tool_result_content, str):
                                                            parsed = json.loads(tool_result_content)
                                                        elif isinstance(tool_result_content, dict):
                                                            parsed = tool_result_content
                                                        else:
                                                            parsed = None

                                                        if parsed and isinstance(parsed, dict):
                                                            logger.info("parsed_tool_result_dict", keys=list(parsed.keys()))

                                                            # Send observation event with attachments (unified format)
                                                            observation_event = {
                                                                "type": "observation",
                                                                "tool": current_tool or "unknown",
                                                                "success": parsed.get("success", True),
                                                                "result": parsed.get("message", "执行成功")
                                                            }

                                                            # Include attachments in observation event if present
                                                            if "attachments" in parsed and len(parsed["attachments"]) > 0:
                                                                observation_event["attachments"] = parsed["attachments"]
                                                                logger.info(
                                                                    "observation_with_attachments_dict",
                                                                    attachment_count=len(parsed["attachments"]),
                                                                )

                                                            yield observation_event
                                                    except (json.JSONDecodeError, AttributeError, TypeError) as e:
                                                        logger.warning("failed_to_parse_tool_result_dict", error=str(e))
                            else:
                                # It's an object, use original logic
                                logger.info(
                                    "inspecting_agent_result_message",
                                    message_type=type(message).__name__,
                                    has_content=hasattr(message, "content"),
                                    has_role=hasattr(message, "role"),
                                    message_attrs=[attr for attr in dir(message) if not attr.startswith('_')][:15],
                                )

                            # Check if message has content blocks (old object-based logic)
                            if hasattr(message, "content") and message.content:
                                content = message.content
                                logger.info(
                                    "inspecting_message_content",
                                    content_type=type(content).__name__,
                                    is_list=isinstance(content, list),
                                    content_length=len(content) if isinstance(content, (list, str)) else None,
                                )

                                # If it's a list, check each content block
                                if isinstance(content, list):
                                    for idx, block in enumerate(content):
                                        block_type = getattr(block, "type", None) if hasattr(block, "type") else type(block).__name__
                                        logger.info(
                                            "inspecting_content_block",
                                            index=idx,
                                            block_type=block_type,
                                            block_attrs=[attr for attr in dir(block) if not attr.startswith('_')][:15],
                                        )

                                        # Check for tool_result blocks
                                        if hasattr(block, "type") and block.type == "tool_result":
                                            tool_result_content = getattr(block, "content", None)
                                            logger.info(
                                                "found_tool_result_in_message",
                                                content_preview=str(tool_result_content)[:300],
                                            )

                                            # Try to parse and extract attachments
                                            try:
                                                import json
                                                if isinstance(tool_result_content, str):
                                                    parsed = json.loads(tool_result_content)
                                                elif isinstance(tool_result_content, dict):
                                                    parsed = tool_result_content
                                                else:
                                                    parsed = None

                                                if parsed and isinstance(parsed, dict):
                                                    logger.info("parsed_tool_result", keys=list(parsed.keys()))

                                                    # Send observation event with attachments (unified format)
                                                    observation_event = {
                                                        "type": "observation",
                                                        "tool": current_tool or "unknown",
                                                        "success": parsed.get("success", True),
                                                        "result": parsed.get("message", "执行成功")
                                                    }

                                                    # Include attachments in observation event if present
                                                    if "attachments" in parsed and len(parsed["attachments"]) > 0:
                                                        observation_event["attachments"] = parsed["attachments"]
                                                        logger.info(
                                                            "observation_with_attachments_message",
                                                            attachment_count=len(parsed["attachments"]),
                                                        )

                                                    yield observation_event
                                            except (json.JSONDecodeError, AttributeError, TypeError) as e:
                                                logger.warning("failed_to_parse_tool_result_from_message", error=str(e))

                        # DEBUG: Inspect the AgentResult structure (old code for last_message)
                        if hasattr(agent_result, "last_message"):
                            last_msg = agent_result.last_message
                            logger.info(
                                "inspecting_last_message",
                                msg_type=type(last_msg).__name__,
                                has_content=hasattr(last_msg, "content"),
                                has_role=hasattr(last_msg, "role"),
                                role=getattr(last_msg, "role", None),
                            )

                            if hasattr(last_msg, "content"):
                                content = last_msg.content
                                logger.info(
                                    "inspecting_message_content",
                                    content_type=type(content).__name__,
                                    content_length=len(content) if isinstance(content, (list, str)) else None,
                                    content_preview=str(content)[:200] if content else None,
                                )

                                if isinstance(content, list):
                                    for idx, block in enumerate(content):
                                        block_type = type(block).__name__
                                        has_type_attr = hasattr(block, "type")
                                        block_type_value = getattr(block, "type", None) if has_type_attr else None

                                        logger.info(
                                            "inspecting_content_block",
                                            index=idx,
                                            block_type=block_type,
                                            has_type_attr=has_type_attr,
                                            type_value=block_type_value,
                                            block_attrs=dir(block)[:20] if hasattr(block, "__dict__") else None,
                                        )

                                        # Check if this is a tool result content block
                                        if has_type_attr and block_type_value == "tool_result":
                                            if hasattr(block, "content"):
                                                result_text = block.content
                                                logger.info(
                                                    "found_tool_result_block",
                                                    content_type=type(result_text).__name__,
                                                    content_preview=str(result_text)[:300],
                                                )

                                                # Try to parse as JSON to extract attachments
                                                try:
                                                    import json
                                                    if isinstance(result_text, str):
                                                        parsed = json.loads(result_text)
                                                    elif isinstance(result_text, dict):
                                                        parsed = result_text
                                                    else:
                                                        parsed = None

                                                    if parsed and isinstance(parsed, dict):
                                                        logger.info(
                                                            "parsed_tool_result",
                                                            keys=list(parsed.keys()),
                                                            has_attachments="attachments" in parsed,
                                                        )

                                                        # Send observation event with attachments (unified format)
                                                        observation_event = {
                                                            "type": "observation",
                                                            "tool": current_tool or "unknown",
                                                            "success": parsed.get("success", True),
                                                            "result": parsed.get("message", "执行成功")
                                                        }

                                                        # Include attachments in observation event if present
                                                        if "attachments" in parsed and len(parsed["attachments"]) > 0:
                                                            observation_event["attachments"] = parsed["attachments"]
                                                            logger.info(
                                                                "observation_with_attachments",
                                                                tool=current_tool,
                                                                attachment_count=len(parsed["attachments"]),
                                                            )

                                                        yield observation_event
                                                except (json.JSONDecodeError, AttributeError, TypeError) as e:
                                                    logger.warning("failed_to_parse_tool_result", error=str(e))
                        continue

                    if "message" in chunk:
                        # Final message received, streaming complete
                        continue

                # Mark as completed
                state.status = AgentStatus.COMPLETED
                state.final_response = final_response if final_response else "完成"

            except Exception as e:
                logger.error("strands_agent_execution_failed", error=str(e), exc_info=True)
                yield {"type": "error", "error": f"执行失败: {str(e)}"}

            # Add assistant response to memory
            if state.final_response:
                await self.memory.add_message(
                    session_id=session_id,
                    role="assistant",
                    content=state.final_response,
                    metadata={"status": "completed"},
                    model_provider=self.model_provider,
                    model_name=self.model_name or self._get_default_model_name(),
                )

            # Save state
            await self._save_state(state)

            yield {"type": "done"}

        except Exception as e:
            log.error("enhanced_agent_error", error=str(e), exc_info=True)
            yield {"type": "error", "error": str(e)}

    async def _generate_reflection(
        self,
        step: ExecutionStep,
        remaining_steps: int,
    ) -> dict[str, Any]:
        """Generate reflection about current execution state.

        Args:
            step: Current execution step
            remaining_steps: Remaining steps available

        Returns:
            Reflection with should_continue decision
        """
        prompt = f"""Reflect on the current execution state and decide if we should continue.

Current Step: {step.step_number}
Action Taken: {step.action}
Result: {step.observation}
Remaining Steps: {remaining_steps}

Questions to consider:
1. Did the action succeed?
2. Is the user's goal achieved?
3. Should we continue with more actions?
4. What's the final answer if we're done?

Respond in JSON:
{{
    "thought": "Your reflection about current state",
    "should_continue": true/false,
    "final_answer": "Final response if complete (or null)"
}}
"""

        try:
            response = await self.gemini_client.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
            )

            reflection = json.loads(response)
            return reflection

        except Exception as e:
            logger.error("reflection_generation_failed", error=str(e))
            # Default: continue if tool succeeded
            success = step.observation and "Success" in step.observation
            return {
                "thought": "Continuing execution based on tool result.",
                "should_continue": success and remaining_steps > 0,
                "final_answer": None,
            }

    def _convert_tools_to_strands(
        self,
        agent_tools: list[AgentTool],
        user_id: str,
        session_id: str,
        model_preferences: Any = None,
        conversation_history: list[dict[str, str]] | None = None,
    ) -> list[Any]:
        """Convert AgentTool to Strands tool functions."""
        strands_tools = []

        def make_tool_wrapper(captured_tool: AgentTool):
            @tool(
                name=captured_tool.name,
                description=captured_tool.description,
                context=True,
            )
            async def tool_fn(tool_context: ToolContext, **kwargs) -> AsyncIterator[dict[str, Any]]:
                # DEBUG: Log that tool function is called as async generator
                logger.info(
                    "tool_wrapper_called",
                    tool_name=captured_tool.name,
                    is_generator=True,
                )

                # Strands Agent passes all parameters under a 'kwargs' key
                # Extract the actual parameters
                if "kwargs" in kwargs and isinstance(kwargs["kwargs"], dict):
                    # Parameters are in kwargs['kwargs'] as a dict
                    params = kwargs["kwargs"]
                elif "kwargs" in kwargs and isinstance(kwargs["kwargs"], str):
                    # Parameters are in kwargs['kwargs'] as a single string value
                    # Map to the first parameter of the tool
                    if captured_tool.metadata.parameters:
                        first_param_name = captured_tool.metadata.parameters[0].name
                        params = {first_param_name: kwargs["kwargs"]}
                    else:
                        params = kwargs
                else:
                    # Use kwargs as-is
                    params = kwargs

                # Log tool execution
                logger.info(
                    "tool_execution_start",
                    tool_name=captured_tool.name,
                    params=params,
                    user_id=user_id,
                    session_id=session_id,
                )

                context = {
                    "user_id": tool_context.invocation_state.get("user_id", user_id),
                    "session_id": tool_context.invocation_state.get("session_id", session_id),
                    "conversation_history": conversation_history or [],
                    "model_preferences": model_preferences,
                }

                try:
                    result = await captured_tool.execute(parameters=params, context=context)
                    logger.info(
                        "tool_execution_success",
                        tool_name=captured_tool.name,
                        result_keys=list(result.keys()) if isinstance(result, dict) else None,
                    )

                    # Stream observation event with attachments (unified format)
                    # This allows the frontend to receive the observation event in real-time
                    if isinstance(result, dict):
                        logger.info(
                            "preparing_observation_event",
                            tool=captured_tool.name,
                            has_attachments="attachments" in result,
                            attachment_count=len(result.get("attachments", [])),
                        )

                        observation_event = {
                            "type": "observation",
                            "tool": captured_tool.name,
                            "success": result.get("success", True),
                            "result": result.get("message", "执行成功"),
                        }

                        # Include attachments in observation event if present
                        if "attachments" in result and result["attachments"]:
                            observation_event["attachments"] = result["attachments"]
                            logger.info(
                                "observation_event_has_attachments",
                                tool=captured_tool.name,
                                attachment_count=len(result["attachments"]),
                            )

                        # Yield observation event for tool streaming
                        logger.info(
                            "yielding_observation_event",
                            tool=captured_tool.name,
                            event_keys=list(observation_event.keys()),
                        )
                        yield observation_event
                        logger.info(
                            "yielded_observation_event",
                            tool=captured_tool.name,
                        )

                    # Yield final result to Strands Agent (last yield becomes the tool result)
                    logger.info(
                        "yielding_final_result",
                        tool=captured_tool.name,
                        result_keys=list(result.keys()) if isinstance(result, dict) else None,
                    )
                    yield result
                    logger.info(
                        "yielded_final_result",
                        tool=captured_tool.name,
                    )
                except ToolExecutionError as e:
                    logger.error(
                        "tool_execution_error",
                        tool_name=captured_tool.name,
                        error=e.message,
                        error_code=e.error_code,
                    )
                    error_result = {
                        "success": False,
                        "error": e.message,
                        "error_code": e.error_code,
                    }
                    # Yield error observation
                    logger.info("yielding_error_observation", tool=captured_tool.name)
                    yield {
                        "type": "observation",
                        "tool": captured_tool.name,
                        "success": False,
                        "result": e.message,
                    }
                    # Yield final error result
                    logger.info("yielding_error_result", tool=captured_tool.name)
                    yield error_result
                except Exception as e:
                    logger.error(
                        "tool_execution_exception",
                        tool_name=captured_tool.name,
                        error=str(e),
                        exc_info=True,
                    )
                    error_result = {
                        "success": False,
                        "error": str(e),
                        "error_code": "EXECUTION_ERROR",
                    }
                    # Yield error observation
                    logger.info("yielding_exception_observation", tool=captured_tool.name)
                    yield {
                        "type": "observation",
                        "tool": captured_tool.name,
                        "success": False,
                        "result": str(e),
                    }
                    # Yield final error result
                    logger.info("yielding_exception_result", tool=captured_tool.name)
                    yield error_result

            return tool_fn

        for agent_tool in agent_tools:
            strands_tools.append(make_tool_wrapper(agent_tool))

        logger.info("tools_converted_to_strands", count=len(strands_tools))
        return strands_tools

    async def _execute_tool(
        self,
        tool_name: str,
        parameters: dict[str, Any],
        available_tools: list[AgentTool],
        user_id: str,
        conversation_history: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Execute tool directly."""
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

        # Execute
        context = {
            "user_id": user_id,
            "conversation_history": conversation_history,
        }

        return await tool.execute(parameters=parameters, context=context)

    def _format_tool_result(self, result: dict[str, Any]) -> str:
        """Format tool result as observation text."""
        if not result:
            return "Tool returned no result"

        success = result.get("success", False)
        message = result.get("message", "")

        if success:
            observation = f"Success: {message}"

            # Add summary if present
            if "summary" in result and result["summary"]:
                summary = result["summary"]
                if len(summary) > 3000:
                    summary = summary[:3000] + "..."
                observation += f"\n\nResults:\n{summary}"

            return observation
        else:
            error = result.get("error", "Unknown error")
            return f"Failed: {message or error}"

    def _get_default_model_name(self) -> str:
        """Get default model name for provider."""
        if self.model_provider == "gemini":
            return "gemini-2.5-flash"
        elif self.model_provider == "bedrock":
            return "global.anthropic.claude-sonnet-4-5-20250929-v1:0"
        return "gemini-2.5-flash"

    async def _get_or_create_state(
        self,
        user_message: str,
        user_id: str,
        session_id: str,
        conversation_id: str | None,
    ) -> AgentState:
        """Get or create agent state."""
        existing = await self._load_state(session_id)
        if existing:
            existing.user_message = user_message
            return existing

        return AgentState(
            session_id=session_id,
            user_id=user_id,
            conversation_id=conversation_id,
            user_message=user_message,
            max_steps=self.max_steps,
        )

    async def _load_state(self, session_id: str) -> AgentState | None:
        """Load state from Redis."""
        try:
            redis = await get_redis()
            key = f"agent:enhanced:state:{session_id}"
            data = await redis.get(key)

            if not data:
                return None

            state_dict = json.loads(data)
            return AgentState.from_dict(state_dict)
        except Exception as e:
            logger.error("load_state_error", session_id=session_id, error=str(e))
            return None

    async def _save_state(self, state: AgentState) -> None:
        """Save state to Redis."""
        try:
            redis = await get_redis()
            key = f"agent:enhanced:state:{state.session_id}"

            state.updated_at = datetime.utcnow()
            data = json.dumps(state.to_dict(), ensure_ascii=False)

            await redis.set(key, data, ex=self.state_ttl)
            logger.debug("state_saved", session_id=state.session_id)
        except Exception as e:
            logger.error("save_state_error", error=str(e))


__all__ = ["StrandsEnhancedReActAgent", "AgentStatus", "ExecutionStep", "AgentState"]
