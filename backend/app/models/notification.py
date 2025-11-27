"""Notification database model."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.mysql import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.user import User


class Notification(Base):
    """Notification model for managing user notifications."""

    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Notification info
    type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # 'urgent', 'important', 'general'
    category: Mapped[str] = mapped_column(
        String(100), nullable=False
    )  # 'ad_rejected', 'token_expired', etc.
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)

    # Action
    action_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    action_text: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Status
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    read_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Channels (stored as JSON array)
    sent_via: Mapped[list] = mapped_column(JSON, default=list)  # ['in_app', 'email']

    # Extra data
    extra_data: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    # Relationships
    user: Mapped["User"] = relationship("User")

    # Indexes for efficient querying
    __table_args__ = (
        Index("ix_notifications_user_read", "user_id", "is_read"),
        Index("ix_notifications_user_created", "user_id", "created_at"),
    )
