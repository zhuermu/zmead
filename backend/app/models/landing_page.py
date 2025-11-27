"""Landing Page database model."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.user import User


class LandingPage(Base):
    """Landing Page model for managing generated landing pages."""

    __tablename__ = "landing_pages"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Page info
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    url: Mapped[str] = mapped_column(String(1024), nullable=False)  # Public URL
    s3_key: Mapped[str] = mapped_column(String(512), nullable=False)  # S3 object key

    # Content
    product_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    template: Mapped[str] = mapped_column(String(100), default="modern")
    language: Mapped[str] = mapped_column(String(10), default="en")
    html_content: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Status
    status: Mapped[str] = mapped_column(
        String(50), default="draft"
    )  # 'draft', 'published', 'archived'

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime, onupdate=datetime.utcnow, nullable=True
    )
    published_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="landing_pages")
