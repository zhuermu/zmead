"""Ad Account database model."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.user import User


class AdAccount(Base):
    """Ad Account model for managing advertising platform connections."""

    __tablename__ = "ad_accounts"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Platform info
    platform: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # 'meta', 'tiktok', 'google'
    platform_account_id: Mapped[str] = mapped_column(String(255), nullable=False)
    account_name: Mapped[str] = mapped_column(String(255), nullable=False)

    # OAuth tokens (encrypted)
    access_token_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    refresh_token_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    token_expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Status
    status: Mapped[str] = mapped_column(
        String(50), default="active"
    )  # 'active', 'expired', 'revoked'
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=False
    )  # Currently selected account

    # Metadata
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime, onupdate=datetime.utcnow, nullable=True
    )
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="ad_accounts")
