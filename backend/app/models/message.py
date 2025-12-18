"""Message database model for AI chat messages."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.mysql import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.conversation import Conversation


class Message(Base):
    """Message model for storing individual chat messages."""

    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    conversation_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    
    # Client-generated message ID for deduplication
    client_message_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)

    # Message content
    role: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # 'user', 'assistant', 'system', 'tool'
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # Tool call tracking (for assistant messages that invoke tools)
    tool_calls: Mapped[list | None] = mapped_column(JSON, nullable=True)
    tool_call_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Message metadata (renamed to avoid SQLAlchemy reserved word)
    message_metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    
    # Agent process info (thinking steps, tool calls, observations) - JSON type in DB
    process_info: Mapped[dict | list | str | None] = mapped_column(JSON, nullable=True)
    
    # Generated assets (images, videos, etc.)
    generated_assets: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    
    # Attachments (uploaded files with S3 URLs)
    attachments: Mapped[list | None] = mapped_column(JSON, nullable=True)

    # Token usage tracking
    input_tokens: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    output_tokens: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    # Relationships
    conversation: Mapped["Conversation"] = relationship(
        "Conversation", back_populates="messages"
    )

    # Indexes for efficient querying
    __table_args__ = (
        Index("ix_messages_conversation_created", "conversation_id", "created_at"),
    )

    @validates('process_info', 'tool_calls', 'generated_assets', 'attachments', 'message_metadata')
    def validate_json_fields(self, key: str, value):
        """Prevent empty strings from being stored in JSON fields."""
        # Convert empty strings to None for nullable JSON fields
        if value == '':
            if key == 'message_metadata':
                return {}  # message_metadata has a default of {}
            return None  # Other JSON fields are nullable
        return value
