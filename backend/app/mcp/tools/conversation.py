"""MCP tools for conversation management.

Implements tools for managing AI chat conversations:
- save_conversation: Save messages to a conversation
- get_conversation_history: Get conversation history by session_id
- list_conversations: List user's conversations
- delete_conversation: Delete a conversation
"""

from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.mcp.registry import tool
from app.mcp.types import MCPToolParameter
from app.models.conversation import Conversation
from app.models.message import Message


@tool(
    name="save_conversation",
    description="Save messages to a conversation. Creates a new conversation if session_id doesn't exist.",
    parameters=[
        MCPToolParameter(
            name="session_id",
            type="string",
            description="Unique session identifier for the conversation",
            required=True,
        ),
        MCPToolParameter(
            name="messages",
            type="array",
            description="Array of message objects with role, content, and optional metadata",
            required=True,
        ),
        MCPToolParameter(
            name="title",
            type="string",
            description="Optional title for the conversation",
            required=False,
        ),
        MCPToolParameter(
            name="current_intent",
            type="string",
            description="Current recognized intent",
            required=False,
        ),
        MCPToolParameter(
            name="context_data",
            type="object",
            description="Additional context data to store",
            required=False,
        ),
    ],
    category="conversation",
)
async def save_conversation(
    user_id: int,
    db: AsyncSession,
    session_id: str,
    messages: list[dict[str, Any]],
    title: str | None = None,
    current_intent: str | None = None,
    context_data: dict | None = None,
) -> dict[str, Any]:
    """Save messages to a conversation."""
    # Find or create conversation
    result = await db.execute(
        select(Conversation).where(
            Conversation.session_id == session_id,
            Conversation.user_id == user_id,
        )
    )
    conversation = result.scalar_one_or_none()

    now = datetime.utcnow()

    if not conversation:
        # Create new conversation
        conversation = Conversation(
            user_id=user_id,
            session_id=session_id,
            title=title,
            current_intent=current_intent,
            context_data=context_data or {},
            created_at=now,
            last_message_at=now,
        )
        db.add(conversation)
        await db.flush()  # Get the ID
    else:
        # Update existing conversation
        if title:
            conversation.title = title
        if current_intent:
            conversation.current_intent = current_intent
        if context_data:
            conversation.context_data = context_data
        conversation.last_message_at = now

    # Add new messages
    saved_messages = []
    for msg_data in messages:
        message = Message(
            conversation_id=conversation.id,
            role=msg_data.get("role", "user"),
            content=msg_data.get("content", ""),
            tool_calls=msg_data.get("tool_calls"),
            tool_call_id=msg_data.get("tool_call_id"),
            metadata=msg_data.get("metadata", {}),
            input_tokens=msg_data.get("input_tokens"),
            output_tokens=msg_data.get("output_tokens"),
            created_at=datetime.fromisoformat(msg_data["timestamp"])
            if msg_data.get("timestamp")
            else now,
        )
        db.add(message)
        saved_messages.append(message)

    await db.commit()

    return {
        "conversation_id": conversation.id,
        "session_id": conversation.session_id,
        "messages_saved": len(saved_messages),
        "total_messages": len(conversation.messages) if conversation.messages else len(saved_messages),
    }


@tool(
    name="get_conversation_history",
    description="Get conversation history by session_id with pagination.",
    parameters=[
        MCPToolParameter(
            name="session_id",
            type="string",
            description="Session identifier for the conversation",
            required=True,
        ),
        MCPToolParameter(
            name="limit",
            type="integer",
            description="Maximum number of messages to return (default 50, max 200)",
            required=False,
            default=50,
        ),
        MCPToolParameter(
            name="before_id",
            type="integer",
            description="Get messages before this message ID (for pagination)",
            required=False,
        ),
    ],
    category="conversation",
)
async def get_conversation_history(
    user_id: int,
    db: AsyncSession,
    session_id: str,
    limit: int = 50,
    before_id: int | None = None,
) -> dict[str, Any]:
    """Get conversation history by session_id."""
    # Validate limit
    limit = min(limit, 200)

    # Find conversation
    result = await db.execute(
        select(Conversation).where(
            Conversation.session_id == session_id,
            Conversation.user_id == user_id,
        )
    )
    conversation = result.scalar_one_or_none()

    if not conversation:
        return {
            "conversation_id": None,
            "session_id": session_id,
            "messages": [],
            "total": 0,
            "has_more": False,
        }

    # Build message query
    query = select(Message).where(Message.conversation_id == conversation.id)

    if before_id:
        query = query.where(Message.id < before_id)

    query = query.order_by(Message.created_at.desc()).limit(limit + 1)

    result = await db.execute(query)
    messages = list(result.scalars().all())

    # Check if there are more messages
    has_more = len(messages) > limit
    if has_more:
        messages = messages[:limit]

    # Reverse to get chronological order
    messages.reverse()

    # Format messages
    formatted_messages = [
        {
            "id": msg.id,
            "role": msg.role,
            "content": msg.content,
            "tool_calls": msg.tool_calls,
            "tool_call_id": msg.tool_call_id,
            "metadata": msg.metadata or {},
            "input_tokens": msg.input_tokens,
            "output_tokens": msg.output_tokens,
            "created_at": msg.created_at.isoformat() if msg.created_at else None,
        }
        for msg in messages
    ]

    return {
        "conversation_id": conversation.id,
        "session_id": conversation.session_id,
        "title": conversation.title,
        "current_intent": conversation.current_intent,
        "context_data": conversation.context_data or {},
        "messages": formatted_messages,
        "total": len(formatted_messages),
        "has_more": has_more,
        "created_at": conversation.created_at.isoformat() if conversation.created_at else None,
        "last_message_at": conversation.last_message_at.isoformat()
        if conversation.last_message_at
        else None,
    }


@tool(
    name="list_conversations",
    description="List user's conversations with pagination.",
    parameters=[
        MCPToolParameter(
            name="page",
            type="integer",
            description="Page number (1-indexed)",
            required=False,
            default=1,
        ),
        MCPToolParameter(
            name="page_size",
            type="integer",
            description="Number of items per page (max 50)",
            required=False,
            default=20,
        ),
    ],
    category="conversation",
)
async def list_conversations(
    user_id: int,
    db: AsyncSession,
    page: int = 1,
    page_size: int = 20,
) -> dict[str, Any]:
    """List user's conversations."""
    # Validate page_size
    page_size = min(page_size, 50)
    offset = (page - 1) * page_size

    # Count total
    from sqlalchemy import func

    count_result = await db.execute(
        select(func.count(Conversation.id)).where(Conversation.user_id == user_id)
    )
    total = count_result.scalar() or 0

    # Get conversations
    result = await db.execute(
        select(Conversation)
        .where(Conversation.user_id == user_id)
        .order_by(Conversation.last_message_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    conversations = result.scalars().all()

    # Format conversations
    formatted = [
        {
            "id": conv.id,
            "session_id": conv.session_id,
            "title": conv.title,
            "current_intent": conv.current_intent,
            "created_at": conv.created_at.isoformat() if conv.created_at else None,
            "last_message_at": conv.last_message_at.isoformat()
            if conv.last_message_at
            else None,
        }
        for conv in conversations
    ]

    return {
        "conversations": formatted,
        "total": total,
        "page": page,
        "page_size": page_size,
        "has_more": offset + len(conversations) < total,
    }


@tool(
    name="delete_conversation",
    description="Delete a conversation and all its messages.",
    parameters=[
        MCPToolParameter(
            name="session_id",
            type="string",
            description="Session identifier for the conversation to delete",
            required=True,
        ),
    ],
    category="conversation",
)
async def delete_conversation(
    user_id: int,
    db: AsyncSession,
    session_id: str,
) -> dict[str, Any]:
    """Delete a conversation."""
    # Find conversation
    result = await db.execute(
        select(Conversation).where(
            Conversation.session_id == session_id,
            Conversation.user_id == user_id,
        )
    )
    conversation = result.scalar_one_or_none()

    if not conversation:
        return {
            "deleted": False,
            "message": "Conversation not found",
        }

    # Delete conversation (messages will be cascade deleted)
    await db.delete(conversation)
    await db.commit()

    return {
        "deleted": True,
        "session_id": session_id,
        "message": "Conversation deleted successfully",
    }
