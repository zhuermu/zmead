"""User database model."""

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Boolean, DateTime, Numeric, String
from sqlalchemy.dialects.mysql import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.ad_account import AdAccount
    from app.models.campaign import Campaign
    from app.models.conversation import Conversation
    from app.models.creative import Creative
    from app.models.landing_page import LandingPage


class User(Base):
    """User model for authentication and profile management."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(String(512), nullable=True)

    # OAuth (Google/Facebook)
    oauth_provider: Mapped[str] = mapped_column(String(50), default="google")
    oauth_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    # Credits
    gifted_credits: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), default=Decimal("500.00")
    )
    purchased_credits: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), default=Decimal("0.00")
    )

    # Settings
    language: Mapped[str] = mapped_column(String(10), default="en")
    timezone: Mapped[str] = mapped_column(String(50), default="UTC")
    notification_preferences: Mapped[dict] = mapped_column(JSON, default=dict)

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Metadata
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime, onupdate=datetime.utcnow, nullable=True
    )
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Relationships
    ad_accounts: Mapped[list["AdAccount"]] = relationship(
        "AdAccount", back_populates="user", cascade="all, delete-orphan"
    )
    creatives: Mapped[list["Creative"]] = relationship(
        "Creative", back_populates="user", cascade="all, delete-orphan"
    )
    campaigns: Mapped[list["Campaign"]] = relationship(
        "Campaign", back_populates="user", cascade="all, delete-orphan"
    )
    landing_pages: Mapped[list["LandingPage"]] = relationship(
        "LandingPage", back_populates="user", cascade="all, delete-orphan"
    )
    conversations: Mapped[list["Conversation"]] = relationship(
        "Conversation", back_populates="user", cascade="all, delete-orphan"
    )

    @property
    def total_credits(self) -> Decimal:
        """Get total available credits."""
        return self.gifted_credits + self.purchased_credits
