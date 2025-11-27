"""Credit Transaction database model."""

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Numeric, String
from sqlalchemy.dialects.mysql import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.user import User


class CreditTransaction(Base):
    """Credit Transaction model for tracking credit usage and purchases."""

    __tablename__ = "credit_transactions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Transaction info
    type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # 'deduct', 'refund', 'recharge', 'gift'
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    # Source tracking
    from_gifted: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), default=Decimal("0.00")
    )
    from_purchased: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), default=Decimal("0.00")
    )

    # Balance after transaction
    balance_after: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    # Operation details
    operation_type: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )  # 'generate_creative', 'chat', etc.
    operation_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    details: Mapped[dict] = mapped_column(JSON, default=dict)  # Model, tokens, etc.

    # Metadata
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    # Relationships
    user: Mapped["User"] = relationship("User")

    # Indexes for efficient querying
    __table_args__ = (
        Index("ix_credit_transactions_user_created", "user_id", "created_at"),
        Index("ix_credit_transactions_type", "type"),
    )
