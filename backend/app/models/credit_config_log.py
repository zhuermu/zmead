"""Credit Config Change Log database model."""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class CreditConfigLog(Base):
    """Credit Config Change Log model for tracking configuration changes."""

    __tablename__ = "credit_config_logs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    # Change metadata
    config_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    field_name: Mapped[str] = mapped_column(String(100), nullable=False)
    old_value: Mapped[str] = mapped_column(Text, nullable=True)
    new_value: Mapped[str] = mapped_column(Text, nullable=False)

    # Admin info
    changed_by: Mapped[str] = mapped_column(String(255), nullable=False)
    changed_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    # Optional notes
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
