"""Credit Config database model."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, DateTime, Numeric, String
from sqlalchemy.dialects.mysql import JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class CreditConfig(Base):
    """Credit Config model for managing credit pricing and configuration."""

    __tablename__ = "credit_config"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    # Model rates (per 1K tokens)
    gemini_flash_input_rate: Mapped[Decimal] = mapped_column(
        Numeric(10, 4), default=Decimal("0.01")
    )
    gemini_flash_output_rate: Mapped[Decimal] = mapped_column(
        Numeric(10, 4), default=Decimal("0.04")
    )
    gemini_pro_input_rate: Mapped[Decimal] = mapped_column(
        Numeric(10, 4), default=Decimal("0.05")
    )
    gemini_pro_output_rate: Mapped[Decimal] = mapped_column(
        Numeric(10, 4), default=Decimal("0.2")
    )

    # Operation rates (fixed)
    image_generation_rate: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), default=Decimal("0.5")
    )
    video_generation_rate: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), default=Decimal("5")
    )
    landing_page_rate: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), default=Decimal("15")
    )
    competitor_analysis_rate: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), default=Decimal("10")
    )
    optimization_suggestion_rate: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), default=Decimal("20")
    )

    # Registration bonus
    registration_bonus: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), default=Decimal("500")
    )

    # Credit packages (stored as JSON)
    packages: Mapped[dict] = mapped_column(JSON, default=dict)

    # Metadata
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime, onupdate=datetime.utcnow, nullable=True
    )
    updated_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
