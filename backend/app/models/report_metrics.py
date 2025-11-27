"""Report Metrics database model."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, DateTime, Float, Index, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ReportMetrics(Base):
    """Report Metrics model for storing advertising performance data."""

    __tablename__ = "report_metrics"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    ad_account_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)

    # Entity info
    entity_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # 'campaign', 'adset', 'ad'
    entity_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    entity_name: Mapped[str] = mapped_column(String(255), nullable=False)

    # Metrics
    impressions: Mapped[int] = mapped_column(Integer, default=0)
    clicks: Mapped[int] = mapped_column(Integer, default=0)
    spend: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0.00"))
    conversions: Mapped[int] = mapped_column(Integer, default=0)
    revenue: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0.00"))

    # Calculated metrics
    ctr: Mapped[float] = mapped_column(Float, default=0.0)  # Click-through rate
    cpc: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), default=Decimal("0.00")
    )  # Cost per click
    cpa: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), default=Decimal("0.00")
    )  # Cost per acquisition
    roas: Mapped[float] = mapped_column(Float, default=0.0)  # Return on ad spend

    # Metadata
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    # Composite indexes for efficient querying
    __table_args__ = (
        Index("ix_report_metrics_user_timestamp", "user_id", "timestamp"),
        Index("ix_report_metrics_account_timestamp", "ad_account_id", "timestamp"),
        Index("ix_report_metrics_entity", "entity_type", "entity_id", "timestamp"),
    )
