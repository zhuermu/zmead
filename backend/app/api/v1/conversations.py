"""REST API endpoints for conversation management."""

from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, DbSession
from app.models.conversation import Conversation
from app.models.message import Message

router = APIRouter(prefix="/conversations", tags=["conversations"])


# Request/Response Models
class MessageCreate(BaseModel):
    """Message creation model."""
    id: str = Field(..., description="Client-generated message ID")
    role: str = Field(..., description="Message role: user, assistant, system")
    content: str = Field(..., description="Message content")
    tool_calls: list[dict] | None = Field(None, description="Tool calls if any")
    tool_call_id: str | None = Field(None, description="Tool call ID if this is a tool response")
    metadata: dict | None = Field(None, description="Additional metadata")
    process_info: str | None = Field(None, description="Agent thinking process and steps")
    generated_assets: dict | None = Field(None, description="Generated images, videos, etc.")
    attachments: list[dict] | None = Field(None, description="Uploaded file attachments with S3 URLs")
    created_at: datetime | None = Field(None, description="Message timestamp")


class ConversationCreate(BaseModel):
    """Conversation creation model."""
    session_id: str = Field(..., description="Client-generated session ID")
    title: str = Field(default="新对话", description="Conversation title")
    messages: list[MessageCreate] = Field(default=[], description="Initial messages")


class ConversationUpdate(BaseModel):
    """Conversation update model."""
    title: str | None = Field(None, description="New title")
    messages: list[MessageCreate] | None = Field(None, description="Messages to add")


class MessageResponse(BaseModel):
    """Message response model."""
    id: str
    role: str
    content: str
    tool_calls: list[dict] | None = None
    tool_call_id: str | None = None
    metadata: dict | None = None
    process_info: str | None = None
    generated_assets: dict | None = None
    attachments: list[dict] | None = None
    created_at: datetime | None = None


class ConversationResponse(BaseModel):
    """Conversation response model."""
    id: int
    session_id: str
    title: str | None
    messages: list[MessageResponse]
    created_at: datetime
    updated_at: datetime | None


class ConversationListItem(BaseModel):
    """Conversation list item model."""
    id: int
    session_id: str
    title: str | None
    message_count: int
    created_at: datetime
    updated_at: datetime | None


class ConversationListResponse(BaseModel):
    """Conversation list response model."""
    conversations: list[ConversationListItem]
    total: int
    page: int
    page_size: int
    has_more: bool


@router.get("", response_model=ConversationListResponse)
async def list_conversations(
    current_user: CurrentUser,
    db: DbSession,
    page: int = 1,
    page_size: int = 20,
) -> ConversationListResponse:
    """List user's conversations with pagination."""
    page_size = min(page_size, 50)
    offset = (page - 1) * page_size

    # Count total
    count_result = await db.execute(
        select(func.count(Conversation.id)).where(Conversation.user_id == current_user.id)
    )
    total = count_result.scalar() or 0

    # Get conversations with message count
    result = await db.execute(
        select(
            Conversation,
            func.count(Message.id).label("message_count")
        )
        .outerjoin(Message, Message.conversation_id == Conversation.id)
        .where(Conversation.user_id == current_user.id)
        .group_by(Conversation.id)
        .order_by(
            # MySQL doesn't support NULLS FIRST, use COALESCE instead
            func.coalesce(Conversation.updated_at, Conversation.created_at).desc()
        )
        .offset(offset)
        .limit(page_size)
    )
    rows = result.all()

    conversations = [
        ConversationListItem(
            id=conv.id,
            session_id=conv.session_id,
            title=conv.title,
            message_count=msg_count,
            created_at=conv.created_at,
            updated_at=conv.updated_at,
        )
        for conv, msg_count in rows
    ]

    return ConversationListResponse(
        conversations=conversations,
        total=total,
        page=page,
        page_size=page_size,
        has_more=offset + len(conversations) < total,
    )


@router.post("", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    request: ConversationCreate,
    current_user: CurrentUser,
    db: DbSession,
) -> ConversationResponse:
    """Create a new conversation."""
    # Check if session_id already exists
    existing = await db.execute(
        select(Conversation).where(
            Conversation.session_id == request.session_id,
            Conversation.user_id == current_user.id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Conversation with this session_id already exists",
        )

    now = datetime.utcnow()
    conversation = Conversation(
        user_id=current_user.id,
        session_id=request.session_id,
        title=request.title,
        created_at=now,
        last_message_at=now if request.messages else None,
    )
    db.add(conversation)
    await db.flush()

    # Add initial messages
    messages = []
    for msg_data in request.messages:
        message = Message(
            conversation_id=conversation.id,
            client_message_id=msg_data.id,
            role=msg_data.role,
            content=msg_data.content,
            tool_calls=msg_data.tool_calls,
            tool_call_id=msg_data.tool_call_id,
            message_metadata=msg_data.metadata or {},
            process_info=msg_data.process_info,
            generated_assets=msg_data.generated_assets,
            attachments=msg_data.attachments,
            created_at=msg_data.created_at or now,
        )
        db.add(message)
        messages.append(message)

    await db.commit()
    await db.refresh(conversation)

    return ConversationResponse(
        id=conversation.id,
        session_id=conversation.session_id,
        title=conversation.title,
        messages=[
            MessageResponse(
                id=msg.client_message_id or str(msg.id),
                role=msg.role,
                content=msg.content,
                tool_calls=msg.tool_calls,
                tool_call_id=msg.tool_call_id,
                metadata=msg.message_metadata,
                process_info=msg.process_info,
                generated_assets=msg.generated_assets,
                attachments=msg.attachments,
                created_at=msg.created_at,
            )
            for msg in messages
        ],
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
    )


@router.get("/{session_id}", response_model=ConversationResponse)
async def get_conversation(
    session_id: str,
    current_user: CurrentUser,
    db: DbSession,
) -> ConversationResponse:
    """Get a conversation by session_id."""
    result = await db.execute(
        select(Conversation).where(
            Conversation.session_id == session_id,
            Conversation.user_id == current_user.id,
        )
    )
    conversation = result.scalar_one_or_none()

    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )

    # Get messages
    msg_result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation.id)
        .order_by(Message.created_at.asc())
    )
    messages = msg_result.scalars().all()

    return ConversationResponse(
        id=conversation.id,
        session_id=conversation.session_id,
        title=conversation.title,
        messages=[
            MessageResponse(
                id=msg.client_message_id or str(msg.id),
                role=msg.role,
                content=msg.content,
                tool_calls=msg.tool_calls,
                tool_call_id=msg.tool_call_id,
                metadata=msg.message_metadata,
                process_info=msg.process_info,
                generated_assets=msg.generated_assets,
                attachments=msg.attachments,
                created_at=msg.created_at,
            )
            for msg in messages
        ],
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
    )


@router.patch("/{session_id}", response_model=ConversationResponse)
async def update_conversation(
    session_id: str,
    request: ConversationUpdate,
    current_user: CurrentUser,
    db: DbSession,
) -> ConversationResponse:
    """Update a conversation (title or add messages)."""
    result = await db.execute(
        select(Conversation).where(
            Conversation.session_id == session_id,
            Conversation.user_id == current_user.id,
        )
    )
    conversation = result.scalar_one_or_none()

    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )

    now = datetime.utcnow()

    # Update title if provided
    if request.title is not None:
        conversation.title = request.title

    # Add new messages if provided
    if request.messages:
        for msg_data in request.messages:
            # Check if message already exists (by client_message_id)
            existing_msg = await db.execute(
                select(Message).where(
                    Message.conversation_id == conversation.id,
                    Message.client_message_id == msg_data.id,
                )
            )
            if existing_msg.scalar_one_or_none():
                continue  # Skip duplicate messages

            message = Message(
                conversation_id=conversation.id,
                client_message_id=msg_data.id,
                role=msg_data.role,
                content=msg_data.content,
                tool_calls=msg_data.tool_calls,
                tool_call_id=msg_data.tool_call_id,
                message_metadata=msg_data.metadata or {},
                process_info=msg_data.process_info,
                generated_assets=msg_data.generated_assets,
                attachments=msg_data.attachments,
                created_at=msg_data.created_at or now,
            )
            db.add(message)

        conversation.last_message_at = now

    conversation.updated_at = now
    await db.commit()
    await db.refresh(conversation)

    # Get all messages
    msg_result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation.id)
        .order_by(Message.created_at.asc())
    )
    messages = msg_result.scalars().all()

    return ConversationResponse(
        id=conversation.id,
        session_id=conversation.session_id,
        title=conversation.title,
        messages=[
            MessageResponse(
                id=msg.client_message_id or str(msg.id),
                role=msg.role,
                content=msg.content,
                tool_calls=msg.tool_calls,
                tool_call_id=msg.tool_call_id,
                metadata=msg.message_metadata,
                process_info=msg.process_info,
                generated_assets=msg.generated_assets,
                attachments=msg.attachments,
                created_at=msg.created_at,
            )
            for msg in messages
        ],
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
    )


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    session_id: str,
    current_user: CurrentUser,
    db: DbSession,
) -> None:
    """Delete a conversation and all its messages."""
    result = await db.execute(
        select(Conversation).where(
            Conversation.session_id == session_id,
            Conversation.user_id == current_user.id,
        )
    )
    conversation = result.scalar_one_or_none()

    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )

    await db.delete(conversation)
    await db.commit()
