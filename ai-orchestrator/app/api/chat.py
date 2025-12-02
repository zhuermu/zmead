"""Chat API using ReAct Agent architecture.

This module provides the chat endpoints using the ReAct Agent:
- Single agent with dynamic tool loading
- Human-in-the-loop for confirmations
- State persistence via Redis

Requirements: ReAct Agent v2
"""

import json
from typing import Any

import structlog
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.core.react_agent import ReActAgent

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
    """Process a chat message using ReAct Agent.

    This endpoint uses the ReAct Agent architecture with:
    - Dynamic tool loading based on user intent
    - Human-in-the-loop for confirmations
    - State persistence via Redis

    Args:
        request: Chat message request

    Returns:
        ChatResponseV3 with AI response
    """
    log = logger.bind(
        user_id=request.user_id,
        session_id=request.session_id,
    )
    log.info("chat_react_request", message_preview=request.content[:100])

    try:
        agent = ReActAgent()

        result = await agent.process_message(
            user_message=request.content,
            user_id=request.user_id,
            session_id=request.session_id,
        )

        log.info("chat_react_response", status=result.status.value)

        # Handle user input requests
        if result.requires_user_input:
            return ChatResponseV3(
                response=result.message or "需要您的输入",
                success=True,
                session_id=request.session_id,
                tool_results=[{
                    "type": "user_input_request",
                    "data": result.user_input_request,
                }] if result.user_input_request else None,
            )

        return ChatResponseV3(
            response=result.message or "",
            success=result.status != "error",
            session_id=request.session_id,
            error=result.error,
        )

    except Exception as e:
        log.error("chat_react_error", error=str(e), exc_info=True)
        return ChatResponseV3(
            response=f"抱歉，处理请求时出错：{e}",
            success=False,
            session_id=request.session_id,
            error=str(e),
        )


@router.post("/chat/v3/stream")
async def chat_v3_stream(request: ChatMessageV3) -> StreamingResponse:
    """Stream chat response using ReAct Agent.

    This endpoint streams the response in real-time using Server-Sent Events.
    Note: Currently returns the full response at once. Streaming will be
    implemented in a future update.

    Args:
        request: Chat message request

    Returns:
        StreamingResponse with SSE events
    """
    log = logger.bind(
        user_id=request.user_id,
        session_id=request.session_id,
    )
    log.info("chat_react_stream_request", message_preview=request.content[:100])

    async def generate():
        """Generate SSE events."""
        try:
            agent = ReActAgent()

            # Send thinking event
            yield f"data: {json.dumps({'type': 'thinking', 'message': '正在思考...'}, ensure_ascii=False)}\n\n"

            # Process message
            result = await agent.process_message(
                user_message=request.content,
                user_id=request.user_id,
                session_id=request.session_id,
            )

            # Handle user input requests
            if result.requires_user_input:
                event = {
                    "type": "user_input_request",
                    "data": result.user_input_request,
                    "message": result.message,
                }
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
            else:
                # Send response as text chunks
                if result.message:
                    # Split into chunks for streaming effect
                    chunk_size = 20
                    for i in range(0, len(result.message), chunk_size):
                        chunk = result.message[i:i + chunk_size]
                        yield f"data: {json.dumps({'type': 'text', 'content': chunk}, ensure_ascii=False)}\n\n"

            # Send done event
            yield f"data: {json.dumps({'type': 'done'}, ensure_ascii=False)}\n\n"

        except Exception as e:
            log.error("chat_react_stream_error", error=str(e))
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






