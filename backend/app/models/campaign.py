"""Campaign database model."""

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, ForeignKey, Numeric, String
from sqlalchemy.dialects.mysql import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.ad_account import AdAccount
    from app.models.landing_page import LandingPage
    from app.models.user import User


class Campaign(Base):
    """Campaign model for managing advertising campaigns."""

    __tablename__ = "campaigns"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    ad_account_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("ad_accounts.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Platform info
    platform: Mapped[str] = mapped_column(String(50), nullable=False)
    platform_campaign_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )  # ID from ad platform

    # Campaign data
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    objective: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(
        String(50), default="draft"
    )  # 'draft', 'active', 'paused', 'deleted'

    # Budget
    budget: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    budget_type: Mapped[str] = mapped_column(
        String(50), default="daily"
    )  # 'daily', 'lifetime'

    # Targeting
    targeting: Mapped[dict] = mapped_column(JSON, default=dict)

    # Creative IDs (stored as JSON array)
    creative_ids: Mapped[list] = mapped_column(JSON, default=list)
    landing_page_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("landing_pages.id", ondelete="SET NULL"), nullable=True
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime, onupdate=datetime.utcnow, nullable=True
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="campaigns")
    ad_account: Mapped["AdAccount"] = relationship("AdAccount")
    landing_page: Mapped["LandingPage | None"] = relationship("LandingPage")
