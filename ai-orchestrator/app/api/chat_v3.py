"""Chat API v3 using simplified architecture with Gemini 3 function calling.

This module provides the chat endpoints using the new v3 architecture:
- Native image generation
- Sub-agents via function calling
- Simplified graph flow

Requirements: Architecture v3.0
"""

import json
from typing import Any

import structlog
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from langchain_core.messages import AIMessage, HumanMessage
from pydantic import BaseModel, Field

from app.core.graph_v3 import get_agent_graph_v3, run_agent_v3, stream_agent_v3
from app.core.orchestrator import get_orchestrator

logger = structlog.get_logger(__name__)

router = APIRouter()


class ChatMessageV3(BaseModel):
    """Chat message request model."""
    content: str = Field(..., min_length=1, max_length=10000, description="Message content")
    user_id: str = Field(..., description="User identifier")
    session_id: str = Field(..., description="Session identifier")
    history: list[dict[str, Any]] | None = Field(
        default=None,
        description="Optional conversation history",
    )


class ChatResponseV3(BaseModel):
    """Chat response model."""
    response: str = Field(..., description="AI response text")
    success: bool = Field(default=True, description="Whether request succeeded")
    session_id: str = Field(..., description="Session identifier")
    error: str | None = Field(default=None, description="Error message if failed")
    tool_results: list[dict[str, Any]] | None = Field(
        default=None,
        description="Results from sub-agent tool calls",
    )


@router.post("/chat/v3", response_model=ChatResponseV3)
async def chat_v3(request: ChatMessageV3) -> ChatResponseV3:
    """Process a chat message using v3 architecture.

    This endpoint uses the simplified v3 architecture with:
    - Gemini 3 Pro for understanding and reasoning
    - Native image generation
    - Sub-agents via function calling

    Args:
        request: Chat message request

    Returns:
        ChatResponseV3 with AI response
    """
    log = logger.bind(
        user_id=request.user_id,
        session_id=request.session_id,
    )
    log.info("chat_v3_request", message_preview=request.content[:100])

    try:
        orchestrator = get_orchestrator()

        result = await orchestrator.process_message(
            user_id=request.user_id,
            session_id=request.session_id,
            message=request.content,
            conversation_history=request.history,
        )

        log.info("chat_v3_response", success=result.get("success"))

        return ChatResponseV3(
            response=result.get("response", ""),
            success=result.get("success", True),
            session_id=request.session_id,
            error=result.get("error"),
        )

    except Exception as e:
        log.error("chat_v3_error", error=str(e), exc_info=True)
        return ChatResponseV3(
            response=f"抱歉，处理请求时出错：{e}",
            success=False,
            session_id=request.session_id,
            error=str(e),
        )


@router.post("/chat/v3/stream")
async def chat_v3_stream(request: ChatMessageV3) -> StreamingResponse:
    """Stream chat response using v3 architecture.

    This endpoint streams the response in real-time using Server-Sent Events.

    Args:
        request: Chat message request

    Returns:
        StreamingResponse with SSE events
    """
    log = logger.bind(
        user_id=request.user_id,
        session_id=request.session_id,
    )
    log.info("chat_v3_stream_request", message_preview=request.content[:100])

    async def generate():
        """Generate SSE events."""
        try:
            orchestrator = get_orchestrator()

            async for event in orchestrator.stream_message(
                user_id=request.user_id,
                session_id=request.session_id,
                message=request.content,
                conversation_history=request.history,
            ):
                event_type = event.get("type", "text")
                event_data = json.dumps(event, ensure_ascii=False)
                yield f"data: {event_data}\n\n"

        except Exception as e:
            log.error("chat_v3_stream_error", error=str(e))
            error_event = json.dumps({"type": "error", "error": str(e)})
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


@router.post("/chat/v3/langgraph")
async def chat_v3_langgraph(request: ChatMessageV3) -> ChatResponseV3:
    """Process chat using LangGraph v3.

    This endpoint uses the LangGraph state machine directly
    for more complex workflows.

    Args:
        request: Chat message request

    Returns:
        ChatResponseV3 with AI response
    """
    log = logger.bind(
        user_id=request.user_id,
        session_id=request.session_id,
    )
    log.info("chat_v3_langgraph_request")

    try:
        # Build messages
        messages = []
        if request.history:
            for msg in request.history:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                if role == "assistant":
                    messages.append(AIMessage(content=content))
                else:
                    messages.append(HumanMessage(content=content))

        messages.append(HumanMessage(content=request.content))

        # Run graph
        result = await run_agent_v3(
            user_id=request.user_id,
            session_id=request.session_id,
            messages=messages,
        )

        # Extract response from messages
        response_messages = result.get("messages", [])
        response_text = ""
        for msg in reversed(response_messages):
            if isinstance(msg, AIMessage):
                response_text = msg.content
                break

        log.info("chat_v3_langgraph_response", success=True)

        return ChatResponseV3(
            response=response_text,
            success=True,
            session_id=request.session_id,
        )

    except Exception as e:
        log.error("chat_v3_langgraph_error", error=str(e), exc_info=True)
        return ChatResponseV3(
            response=f"抱歉，处理请求时出错：{e}",
            success=False,
            session_id=request.session_id,
            error=str(e),
        )


@router.get("/chat/v3/agents")
async def list_agents() -> dict[str, Any]:
    """List available sub-agents.

    Returns information about all registered sub-agents
    that can be called via function calling.

    Returns:
        Dict with agent information
    """
    from app.agents.registry import get_agent_registry

    registry = get_agent_registry()
    agents = registry.list_agents()

    return {
        "agents": [
            {
                "name": agent.name,
                "description": agent.description,
            }
            for agent in agents
        ],
        "count": len(agents),
    }
