"""Chat API using ReAct Agent architecture.

This module provides the unified chat endpoint using the ReAct Agent:
- Single agent with dynamic tool loading
- Human-in-the-loop for confirmations
- State persistence via Redis
- SSE streaming for real-time responses

Requirements: ReAct Agent v2
"""

import asyncio
import json

import structlog
from fastapi import APIRouter, Header
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.core.i18n import detect_language, get_message
from app.core.react_agent import ReActAgent
from app.tools.registry import ToolRegistry
from app.tools.langchain_tools import create_langchain_tools

logger = structlog.get_logger(__name__)


def _create_agent_with_tools() -> ReActAgent:
    """Create ReActAgent with default tools loaded."""
    registry = ToolRegistry()

    # Register LangChain built-in tools
    langchain_tools = create_langchain_tools()
    registry.register_batch(langchain_tools)

    return ReActAgent(tool_registry=registry)

router = APIRouter()


class ChatMessage(BaseModel):
    """Single chat message."""
    role: str = Field(..., description="Message role: user, assistant, or system")
    content: str = Field(..., description="Message content")


class ChatRequest(BaseModel):
    """Unified chat request model compatible with Vercel AI SDK."""
    messages: list[ChatMessage] = Field(..., description="Conversation messages")
    user_id: str = Field(..., description="User identifier")
    session_id: str = Field(..., description="Session identifier")


@router.post("/chat")
async def chat_stream(
    request: ChatRequest,
    accept_language: str | None = Header(default=None, alias="Accept-Language"),
) -> StreamingResponse:
    """
    Unified chat endpoint with Server-Sent Events streaming.

    This is the main chat endpoint that:
    - Accepts messages array from frontend/backend
    - Uses ReAct Agent for intelligent task processing
    - Streams responses in real-time via SSE
    - Supports human-in-the-loop interactions
    - Supports i18n via Accept-Language header

    Args:
        request: Chat request with messages array, user_id, and session_id
        accept_language: Accept-Language header for i18n (e.g., "zh-CN", "en-US")

    Returns:
        StreamingResponse with SSE events:
        - type: "thinking" - Agent started processing
        - type: "thought" - Agent's reasoning process (streaming)
        - type: "action" - Agent executing a tool
        - type: "observation" - Tool execution result
        - type: "text" - Final response text
        - type: "user_input_request" - Needs user confirmation/input
        - type: "done" - Response complete
        - type: "error" - Error occurred
    """
    language = detect_language(accept_language)
    log = logger.bind(
        user_id=request.user_id,
        session_id=request.session_id,
        language=language,
    )

    # Extract last user message
    last_message = request.messages[-1].content if request.messages else ""

    log.info("chat_stream_request", message_preview=last_message[:100])

    async def generate():
        """Generate SSE events."""
        try:
            agent = _create_agent_with_tools()

            # Send initial thinking event
            thinking_msg = get_message("thinking", language)
            yield f"data: {json.dumps({'type': 'thinking', 'message': thinking_msg}, ensure_ascii=False)}\n\n"

            # Process message with ReAct Agent in streaming mode
            async for event in agent.process_message_stream(
                user_message=last_message,
                user_id=request.user_id,
                session_id=request.session_id,
            ):
                event_type = event.get("type")

                # Stream events to frontend
                if event_type == "thought":
                    # Agent's reasoning process - keep as thought type
                    # Frontend will display with different styling (collapsible)
                    yield f"data: {json.dumps({'type': 'thought', 'content': event.get('content', '')}, ensure_ascii=False)}\n\n"

                elif event_type == "action":
                    # Tool execution starting
                    tool_name = event.get("tool", "unknown")
                    status_msg = get_message("tool_executing", language).format(tool=tool_name)
                    yield f"data: {json.dumps({'type': 'action', 'tool': tool_name, 'message': status_msg}, ensure_ascii=False)}\n\n"

                elif event_type == "observation":
                    # Tool execution result
                    tool_name = event.get("tool", "unknown")
                    success = event.get("success", False)
                    result = event.get("result", "")
                    yield f"data: {json.dumps({'type': 'observation', 'tool': tool_name, 'success': success, 'result': result}, ensure_ascii=False)}\n\n"

                elif event_type == "text":
                    # Final response text
                    yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

                elif event_type == "user_input_request":
                    # Human-in-the-loop request
                    yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

                elif event_type == "error":
                    # Error occurred
                    yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
                    return

            # Send done event
            yield f"data: {json.dumps({'type': 'done'}, ensure_ascii=False)}\n\n"

        except Exception as e:
            log.error("chat_stream_error", error=str(e), exc_info=True)
            error_event = json.dumps({"type": "error", "error": str(e)}, ensure_ascii=False)
            yield f"data: {error_event}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )









