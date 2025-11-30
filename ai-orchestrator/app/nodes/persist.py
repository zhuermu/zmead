"""Conversation persistence node.

This module implements the persist_conversation_node that saves
conversation history to the Web Platform via MCP.

Requirements: 需求 5.1 (Conversation Persistence), 需求 12.4 (Error Recovery)
"""

from datetime import UTC, datetime
from typing import Any

import structlog

from app.core.retry import retry_async
from app.core.state import AgentState
from app.services.mcp_client import MCPClient

logger = structlog.get_logger(__name__)


def format_messages_for_storage(
    messages: list,
    max_messages: int = 100,
) -> list[dict[str, Any]]:
    """Format messages for storage in Web Platform.

    Args:
        messages: List of BaseMessage objects
        max_messages: Maximum messages to store

    Returns:
        List of message dicts with role, content, timestamp
    """
    formatted = []

    # Take the most recent messages
    recent_messages = messages[-max_messages:] if len(messages) > max_messages else messages

    for msg in recent_messages:
        # Determine role from message type
        if hasattr(msg, "type"):
            if msg.type == "human":
                role = "user"
            elif msg.type == "ai":
                role = "assistant"
            elif msg.type == "system":
                role = "system"
            else:
                role = "user"
        else:
            role = "user"

        # Get content
        content = msg.content if hasattr(msg, "content") else str(msg)

        # Get or generate timestamp
        timestamp = datetime.now(UTC).isoformat()
        if hasattr(msg, "additional_kwargs"):
            timestamp = msg.additional_kwargs.get("timestamp", timestamp)

        formatted.append(
            {
                "role": role,
                "content": content,
                "timestamp": timestamp,
            }
        )

    return formatted


def generate_conversation_title(messages: list) -> str:
    """Generate a title for the conversation based on first user message.

    Args:
        messages: List of messages

    Returns:
        Generated title string
    """
    for msg in messages:
        if hasattr(msg, "type") and msg.type == "human":
            content = msg.content if hasattr(msg, "content") else str(msg)
            # Take first 50 chars as title
            title = content[:50]
            if len(content) > 50:
                title += "..."
            return title

    return "新对话"


async def persist_conversation_node(state: AgentState) -> dict[str, Any]:
    """Conversation persistence node.

    This node:
    1. Formats messages for storage
    2. Calls MCP save_conversation tool
    3. Handles failures gracefully (logs but doesn't fail)
    4. Includes retry logic for transient failures

    Args:
        state: Current agent state

    Returns:
        Empty dict (no state changes needed)

    Requirements: 需求 5.1
    """
    log = logger.bind(
        user_id=state.get("user_id"),
        session_id=state.get("session_id"),
    )
    log.info("persist_conversation_start")

    # Get messages
    messages = state.get("messages", [])

    if not messages:
        log.info("persist_conversation_no_messages")
        return {}

    # Format messages for storage
    formatted_messages = format_messages_for_storage(messages)

    # Generate title from first user message
    title = generate_conversation_title(messages)

    # Get current intent for context
    current_intent = state.get("current_intent")

    # Build context data
    context_data = {}
    if state.get("extracted_params"):
        context_data["last_params"] = state.get("extracted_params")
    if state.get("completed_results"):
        # Store summary of results, not full data
        context_data["last_results"] = [
            {
                "module": r.get("module"),
                "action": r.get("action_type"),
                "status": r.get("status"),
            }
            for r in state.get("completed_results", [])
        ]

    log.info(
        "persist_conversation_saving",
        message_count=len(formatted_messages),
        title=title,
    )

    # Save via MCP client with retry
    try:
        async with MCPClient() as mcp:
            result = await retry_async(
                lambda: mcp.save_conversation(
                    user_id=state.get("user_id", ""),
                    session_id=state.get("session_id", ""),
                    messages=formatted_messages,
                    title=title,
                    current_intent=current_intent,
                    context_data=context_data if context_data else None,
                ),
                max_retries=3,
                context="persist_conversation",
            )

            if result:
                log.info(
                    "persist_conversation_complete",
                    conversation_id=result.get("conversation_id"),
                    messages_saved=result.get("messages_saved"),
                )
            else:
                log.warning("persist_conversation_failed_gracefully")

    except Exception as e:
        # Log but don't fail - persistence is fire-and-forget
        log.error(
            "persist_conversation_error",
            error=str(e),
            exc_info=True,
        )

    # Don't update state - persistence is fire-and-forget
    return {}
