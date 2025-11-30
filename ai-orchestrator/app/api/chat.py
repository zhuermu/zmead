"""Chat API endpoint with HTTP streaming.

This module implements the /chat POST endpoint that accepts messages
from the Web Platform and returns streaming responses using SSE format.

Requirements: 需求 1.2, 13.1, 13.3
"""

import json
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from langchain_core.messages import AIMessage, HumanMessage
from pydantic import BaseModel, Field

from app.core.auth import validate_service_token
from app.core.graph import get_agent_graph
from app.core.logging import bind_context
from app.core.state import create_initial_state

logger = structlog.get_logger(__name__)

router = APIRouter()


class MessageItem(BaseModel):
    """A single message in the conversation."""

    role: str = Field(
        ...,
        description="Message role: 'user' or 'assistant'",
        examples=["user", "assistant"],
    )
    content: str = Field(
        ...,
        description="Message content",
        examples=["帮我生成 10 张广告图片"],
    )


class ChatRequest(BaseModel):
    """Request schema for the chat endpoint."""

    messages: list[MessageItem] = Field(
        ...,
        description="List of conversation messages",
        min_length=1,
    )
    user_id: str = Field(
        ...,
        description="User identifier",
        min_length=1,
        max_length=50,
    )
    session_id: str = Field(
        ...,
        description="Session identifier for conversation continuity",
        min_length=1,
        max_length=100,
    )


class StreamEvent(BaseModel):
    """Schema for SSE stream events."""

    type: str = Field(
        ...,
        description="Event type: token, tool_start, tool_complete, error, done",
    )
    content: str | None = Field(
        default=None,
        description="Content for token events",
    )
    tool: str | None = Field(
        default=None,
        description="Tool name for tool events",
    )
    result: dict[str, Any] | None = Field(
        default=None,
        description="Result data for tool_complete events",
    )
    error: dict[str, Any] | None = Field(
        default=None,
        description="Error details for error events",
    )


def format_sse_event(event: dict[str, Any]) -> str:
    """Format an event as SSE data.

    Args:
        event: Event dictionary to format

    Returns:
        SSE formatted string: "data: {...}\n\n"
    """
    return f"data: {json.dumps(event, ensure_ascii=False)}\n\n"


async def stream_graph_events(
    agent,
    initial_state: dict,
    config: dict,
) -> AsyncGenerator[str, None]:
    """Stream LangGraph execution events as SSE.

    This async generator yields SSE-formatted events as the LangGraph
    executes. It handles:
    - LLM token streaming
    - Tool call start/complete notifications
    - Error handling
    - Final completion signal

    Args:
        agent: Compiled LangGraph agent
        initial_state: Initial agent state
        config: LangGraph execution config

    Yields:
        SSE formatted event strings

    Requirements: 需求 13.1, 13.3
    """
    log = logger.bind(
        session_id=initial_state.get("session_id"),
        user_id=initial_state.get("user_id"),
    )

    log.info("stream_start")

    try:
        async for event in agent.astream_events(initial_state, config, version="v2"):
            event_kind = event.get("event")

            # Stream LLM tokens
            if event_kind == "on_chat_model_stream":
                chunk = event.get("data", {}).get("chunk")
                if chunk and hasattr(chunk, "content") and chunk.content:
                    yield format_sse_event(
                        {
                            "type": "token",
                            "content": chunk.content,
                        }
                    )

            # Tool call started
            elif event_kind == "on_tool_start":
                tool_name = event.get("name", "unknown")
                log.debug("tool_start", tool=tool_name)
                yield format_sse_event(
                    {
                        "type": "tool_start",
                        "tool": tool_name,
                    }
                )

            # Tool call completed
            elif event_kind == "on_tool_end":
                tool_name = event.get("name", "unknown")
                output = event.get("data", {}).get("output")

                log.debug("tool_complete", tool=tool_name)

                # Serialize output if it's not already a dict
                result = output if isinstance(output, dict) else {"data": output}

                yield format_sse_event(
                    {
                        "type": "tool_complete",
                        "tool": tool_name,
                        "result": result,
                    }
                )

            # Chain/node started (for debugging)
            elif event_kind == "on_chain_start":
                node_name = event.get("name")
                if node_name and node_name not in ["LangGraph", "__start__"]:
                    log.debug("node_start", node=node_name)

            # Chain/node ended
            elif event_kind == "on_chain_end":
                node_name = event.get("name")
                output = event.get("data", {}).get("output", {})

                # Check for final response in output
                if node_name == "respond" and output:
                    messages = output.get("messages", [])
                    for msg in messages:
                        if isinstance(msg, AIMessage) and msg.content:
                            # Stream the final response content
                            yield format_sse_event(
                                {
                                    "type": "token",
                                    "content": msg.content,
                                }
                            )

        # Send completion signal
        yield format_sse_event({"type": "done"})
        log.info("stream_complete")

    except Exception as e:
        log.error("stream_error", error=str(e))

        # Send error event
        yield format_sse_event(
            {
                "type": "error",
                "error": {
                    "code": "STREAM_ERROR",
                    "message": "处理请求时发生错误，请稍后重试",
                    "details": str(e) if logger.isEnabledFor(10) else None,  # DEBUG level
                },
            }
        )

        # Still send done to signal end of stream
        yield format_sse_event({"type": "done"})


@router.post("/chat")
async def chat_endpoint(
    request: Request,
    chat_request: ChatRequest,
    _token: str = Depends(validate_service_token),
) -> StreamingResponse:
    """Chat endpoint with HTTP streaming response.

    Accepts messages from the Web Platform and returns a streaming
    response in SSE (Server-Sent Events) format.

    The endpoint:
    1. Validates the service token
    2. Builds initial AgentState from request
    3. Executes LangGraph with streaming
    4. Returns StreamingResponse with text/event-stream content type

    Args:
        request: FastAPI request object
        chat_request: Validated chat request
        _token: Validated service token (from dependency)

    Returns:
        StreamingResponse with SSE events

    Requirements: 需求 1.2, 13.3
    """
    # Bind context for logging
    bind_context(
        user_id=chat_request.user_id,
        session_id=chat_request.session_id,
    )

    log = logger.bind(
        user_id=chat_request.user_id,
        session_id=chat_request.session_id,
        message_count=len(chat_request.messages),
    )

    log.info("chat_request_received")

    # Convert messages to LangChain format
    langchain_messages = []
    for msg in chat_request.messages:
        if msg.role == "user":
            langchain_messages.append(HumanMessage(content=msg.content))
        elif msg.role == "assistant":
            langchain_messages.append(AIMessage(content=msg.content))
        else:
            log.warning("unknown_message_role", role=msg.role)

    if not langchain_messages:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": {
                    "code": "INVALID_REQUEST",
                    "message": "No valid messages provided",
                }
            },
        )

    # Build initial state
    initial_state = create_initial_state(
        user_id=chat_request.user_id,
        session_id=chat_request.session_id,
        messages=langchain_messages,
    )

    # Build LangGraph config with thread_id for checkpointing
    config = {
        "configurable": {
            "thread_id": chat_request.session_id,
        },
    }

    # Get the compiled agent graph
    agent = get_agent_graph()

    # Return streaming response
    return StreamingResponse(
        stream_graph_events(agent, initial_state, config),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )


@router.post("/chat/sync")
async def chat_sync_endpoint(
    request: Request,
    chat_request: ChatRequest,
    _token: str = Depends(validate_service_token),
) -> dict[str, Any]:
    """Synchronous chat endpoint (non-streaming).

    Alternative endpoint that returns the complete response
    without streaming. Useful for testing and simple integrations.

    Args:
        request: FastAPI request object
        chat_request: Validated chat request
        _token: Validated service token

    Returns:
        Complete response with messages and metadata
    """
    bind_context(
        user_id=chat_request.user_id,
        session_id=chat_request.session_id,
    )

    log = logger.bind(
        user_id=chat_request.user_id,
        session_id=chat_request.session_id,
    )

    log.info("chat_sync_request_received")

    # Convert messages
    langchain_messages = []
    for msg in chat_request.messages:
        if msg.role == "user":
            langchain_messages.append(HumanMessage(content=msg.content))
        elif msg.role == "assistant":
            langchain_messages.append(AIMessage(content=msg.content))

    if not langchain_messages:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": {
                    "code": "INVALID_REQUEST",
                    "message": "No valid messages provided",
                }
            },
        )

    # Build initial state
    initial_state = create_initial_state(
        user_id=chat_request.user_id,
        session_id=chat_request.session_id,
        messages=langchain_messages,
    )

    config = {
        "configurable": {
            "thread_id": chat_request.session_id,
        },
    }

    agent = get_agent_graph()

    try:
        # Execute graph synchronously
        result = await agent.ainvoke(initial_state, config)

        # Extract response messages
        response_messages = []
        for msg in result.get("messages", []):
            if isinstance(msg, AIMessage):
                response_messages.append(
                    {
                        "role": "assistant",
                        "content": msg.content,
                    }
                )
            elif isinstance(msg, HumanMessage):
                response_messages.append(
                    {
                        "role": "user",
                        "content": msg.content,
                    }
                )

        log.info("chat_sync_complete", message_count=len(response_messages))

        return {
            "status": "success",
            "messages": response_messages,
            "metadata": {
                "session_id": chat_request.session_id,
                "intent": result.get("current_intent"),
                "timestamp": datetime.now(UTC).isoformat(),
            },
        }

    except Exception as e:
        log.error("chat_sync_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": {
                    "code": "EXECUTION_ERROR",
                    "message": "处理请求时发生错误",
                }
            },
        )
