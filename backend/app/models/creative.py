"""Creative database model."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.dialects.mysql import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.user import User


class Creative(Base):
    """Creative model for managing advertising assets (images/videos)."""

    __tablename__ = "creatives"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # File info
    file_url: Mapped[str] = mapped_column(String(1024), nullable=False)  # S3 URL
    cdn_url: Mapped[str] = mapped_column(String(1024), nullable=False)  # CloudFront URL
    file_type: Mapped[str] = mapped_column(String(50), nullable=False)  # 'image', 'video'
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)  # bytes

    # Metadata
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    product_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    style: Mapped[str | None] = mapped_column(String(100), nullable=True)
    score: Mapped[float | None] = mapped_column(Float, nullable=True)  # AI quality score
    tags: Mapped[list] = mapped_column(JSON, default=list)

    # Status
    status: Mapped[str] = mapped_column(
        String(50), default="active"
    )  # 'active', 'deleted'

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime, onupdate=datetime.utcnow, nullable=True
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="creatives")
