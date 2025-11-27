"""Report metrics service for managing advertising performance data."""

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import and_, delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.report_metrics import ReportMetrics
from app.schemas.report import (
    AggregatedMetrics,
    EntityType,
    MetricsCreate,
    MetricsFilter,
    TrendDataPoint,
)


class ReportMetricsNotFoundError(Exception):
    """Raised when report metrics are not found."""

    def __init__(self, metrics_id: int):
        self.metrics_id = metrics_id
        super().__init__(f"Report metrics {metrics_id} not found")


class ReportService:
    """Service for report metrics operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    def _calculate_derived_metrics(
        self,
        impressions: int,
        clicks: int,
        spend: Decimal,
        conversions: int,
        revenue: Decimal,
    ) -> dict[str, Any]:
        """Calculate derived metrics (CTR, CPC, CPA, ROAS).

        Args:
            impressions: Number of impressions
            clicks: Number of clicks
            spend: Total spend amount
            conversions: Number of conversions
            revenue: Total revenue

        Returns:
            Dictionary with ctr, cpc, cpa, roas
        """
        # CTR = clicks / impressions * 100
        ctr = (clicks / impressions * 100) if impressions > 0 else 0.0

        # CPC = spend / clicks
        cpc = Decimal(str(spend / clicks)) if clicks > 0 else Decimal("0.00")

        # CPA = spend / conversions
        cpa = Decimal(str(spend / conversions)) if conversions > 0 else Decimal("0.00")

        # ROAS = revenue / spend
        roas = float(revenue / spend) if spend > 0 else 0.0

        return {
            "ctr": round(ctr, 2),
            "cpc": round(cpc, 2),
            "cpa": round(cpa, 2),
            "roas": round(roas, 2),
        }

    async def save_metrics(
        self,
        user_id: int,
        data: MetricsCreate,
    ) -> ReportMetrics:
        """Save a single metrics record.

        Args:
            user_id: Owner user ID
            data: Metrics data to save

        Returns:
            Created ReportMetrics instance
        """
        # Calculate derived metrics
        derived = self._calculate_derived_metrics(
            impressions=data.impressions,
            clicks=data.clicks,
            spend=data.spend,
            conversions=data.conversions,
            revenue=data.revenue,
        )

        metrics = ReportMetrics(
            timestamp=data.timestamp,
            user_id=user_id,
            ad_account_id=data.ad_account_id,
            entity_type=data.entity_type.value,
            entity_id=data.entity_id,
            entity_name=data.entity_name,
            impressions=data.impressions,
            clicks=data.clicks,
            spend=data.spend,
            conversions=data.conversions,
            revenue=data.revenue,
            ctr=derived["ctr"],
            cpc=derived["cpc"],
            cpa=derived["cpa"],
            roas=derived["roas"],
        )

        self.db.add(metrics)
        await self.db.flush()
        await self.db.refresh(metrics)

        return metrics

    async def save_metrics_batch(
        self,
        user_id: int,
        metrics_list: list[MetricsCreate],
    ) -> list[ReportMetrics]:
        """Save multiple metrics records in batch.

        Args:
            user_id: Owner user ID
            metrics_list: List of metrics data to save

        Returns:
            List of created ReportMetrics instances
        """
        results = []
        for data in metrics_list:
            metrics = await self.save_metrics(user_id, data)
            results.append(metrics)
        return results


    async def get_metrics(
        self,
        user_id: int,
        filters: MetricsFilter | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        """Get paginated list of metrics with optional filters.

        Args:
            user_id: Owner user ID
            filters: Optional filter criteria
            page: Page number (1-indexed)
            page_size: Number of items per page

        Returns:
            Dictionary with metrics, total, page, page_size, has_more
        """
        # Base query
        query = select(ReportMetrics).where(ReportMetrics.user_id == user_id)

        # Apply filters
        if filters:
            if filters.ad_account_id is not None:
                query = query.where(
                    ReportMetrics.ad_account_id == filters.ad_account_id
                )
            if filters.entity_type is not None:
                query = query.where(
                    ReportMetrics.entity_type == filters.entity_type.value
                )
            if filters.entity_id is not None:
                query = query.where(ReportMetrics.entity_id == filters.entity_id)
            if filters.start_date is not None:
                query = query.where(ReportMetrics.timestamp >= filters.start_date)
            if filters.end_date is not None:
                query = query.where(ReportMetrics.timestamp <= filters.end_date)

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        count_result = await self.db.execute(count_query)
        total = count_result.scalar() or 0

        # Apply pagination and ordering
        offset = (page - 1) * page_size
        query = (
            query.order_by(ReportMetrics.timestamp.desc())
            .offset(offset)
            .limit(page_size)
        )

        result = await self.db.execute(query)
        metrics = list(result.scalars().all())

        return {
            "metrics": metrics,
            "total": total,
            "page": page,
            "page_size": page_size,
            "has_more": offset + len(metrics) < total,
        }

    async def get_aggregated_metrics(
        self,
        user_id: int,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        ad_account_id: int | None = None,
        entity_type: EntityType | None = None,
    ) -> AggregatedMetrics:
        """Get aggregated metrics for a time period.

        Args:
            user_id: Owner user ID
            start_date: Start of period (defaults to 7 days ago)
            end_date: End of period (defaults to now)
            ad_account_id: Optional ad account filter
            entity_type: Optional entity type filter

        Returns:
            AggregatedMetrics with totals and averages
        """
        # Default to last 7 days
        if end_date is None:
            end_date = datetime.utcnow()
        if start_date is None:
            start_date = end_date - timedelta(days=7)

        # Build query conditions
        conditions = [
            ReportMetrics.user_id == user_id,
            ReportMetrics.timestamp >= start_date,
            ReportMetrics.timestamp <= end_date,
        ]

        if ad_account_id is not None:
            conditions.append(ReportMetrics.ad_account_id == ad_account_id)
        if entity_type is not None:
            conditions.append(ReportMetrics.entity_type == entity_type.value)


        # Aggregation query
        query = select(
            func.sum(ReportMetrics.impressions).label("total_impressions"),
            func.sum(ReportMetrics.clicks).label("total_clicks"),
            func.sum(ReportMetrics.spend).label("total_spend"),
            func.sum(ReportMetrics.conversions).label("total_conversions"),
            func.sum(ReportMetrics.revenue).label("total_revenue"),
            func.avg(ReportMetrics.ctr).label("avg_ctr"),
            func.avg(ReportMetrics.cpc).label("avg_cpc"),
            func.avg(ReportMetrics.cpa).label("avg_cpa"),
            func.avg(ReportMetrics.roas).label("avg_roas"),
        ).where(and_(*conditions))

        result = await self.db.execute(query)
        row = result.one()

        return AggregatedMetrics(
            total_impressions=row.total_impressions or 0,
            total_clicks=row.total_clicks or 0,
            total_spend=row.total_spend or Decimal("0.00"),
            total_conversions=row.total_conversions or 0,
            total_revenue=row.total_revenue or Decimal("0.00"),
            avg_ctr=round(float(row.avg_ctr or 0), 2),
            avg_cpc=round(Decimal(str(row.avg_cpc or 0)), 2),
            avg_cpa=round(Decimal(str(row.avg_cpa or 0)), 2),
            avg_roas=round(float(row.avg_roas or 0), 2),
            period_start=start_date,
            period_end=end_date,
        )

    async def get_trend_data(
        self,
        user_id: int,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        ad_account_id: int | None = None,
        granularity: str = "daily",
    ) -> list[TrendDataPoint]:
        """Get trend data aggregated by time period.

        Args:
            user_id: Owner user ID
            start_date: Start of period (defaults to 7 days ago)
            end_date: End of period (defaults to now)
            ad_account_id: Optional ad account filter
            granularity: 'daily', 'weekly', or 'monthly'

        Returns:
            List of TrendDataPoint for each period
        """
        # Default to last 7 days
        if end_date is None:
            end_date = datetime.utcnow()
        if start_date is None:
            start_date = end_date - timedelta(days=7)

        # Build query conditions
        conditions = [
            ReportMetrics.user_id == user_id,
            ReportMetrics.timestamp >= start_date,
            ReportMetrics.timestamp <= end_date,
        ]

        if ad_account_id is not None:
            conditions.append(ReportMetrics.ad_account_id == ad_account_id)

        # Group by date based on granularity
        if granularity == "daily":
            date_trunc = func.date(ReportMetrics.timestamp)
        elif granularity == "weekly":
            # MySQL week function
            date_trunc = func.date(
                func.date_sub(
                    ReportMetrics.timestamp,
                    func.weekday(ReportMetrics.timestamp)
                )
            )
        else:  # monthly
            date_trunc = func.date_format(ReportMetrics.timestamp, "%Y-%m-01")

        # Aggregation query grouped by date
        query = (
            select(
                date_trunc.label("date"),
                func.sum(ReportMetrics.impressions).label("impressions"),
                func.sum(ReportMetrics.clicks).label("clicks"),
                func.sum(ReportMetrics.spend).label("spend"),
                func.sum(ReportMetrics.conversions).label("conversions"),
                func.sum(ReportMetrics.revenue).label("revenue"),
            )
            .where(and_(*conditions))
            .group_by(date_trunc)
            .order_by(date_trunc)
        )

        result = await self.db.execute(query)
        rows = result.all()

        trend_data = []
        for row in rows:
            # Calculate derived metrics for each period
            derived = self._calculate_derived_metrics(
                impressions=row.impressions or 0,
                clicks=row.clicks or 0,
                spend=row.spend or Decimal("0.00"),
                conversions=row.conversions or 0,
                revenue=row.revenue or Decimal("0.00"),
            )

            # Handle date conversion
            date_value = row.date
            if isinstance(date_value, str):
                date_value = datetime.strptime(date_value, "%Y-%m-%d")

            trend_data.append(
                TrendDataPoint(
                    date=date_value,
                    impressions=row.impressions or 0,
                    clicks=row.clicks or 0,
                    spend=row.spend or Decimal("0.00"),
                    conversions=row.conversions or 0,
                    revenue=row.revenue or Decimal("0.00"),
                    ctr=derived["ctr"],
                    cpc=derived["cpc"],
                    cpa=derived["cpa"],
                    roas=derived["roas"],
                )
            )

        return trend_data


    async def archive_old_metrics(
        self,
        days_threshold: int = 90,
    ) -> dict[str, Any]:
        """Archive metrics older than threshold.

        This method deletes detailed metrics older than the threshold.
        In a production system, you would first aggregate and store
        summary data before deletion.

        Args:
            days_threshold: Number of days after which to archive (default 90)

        Returns:
            Dictionary with archived_count and archived_before timestamp
        """
        archive_before = datetime.utcnow() - timedelta(days=days_threshold)

        # Count records to be archived
        count_query = select(func.count()).where(
            ReportMetrics.timestamp < archive_before
        )
        count_result = await self.db.execute(count_query)
        archived_count = count_result.scalar() or 0

        if archived_count > 0:
            # Delete old records
            # In production, you would first create summary records
            delete_query = delete(ReportMetrics).where(
                ReportMetrics.timestamp < archive_before
            )
            await self.db.execute(delete_query)
            await self.db.flush()

        return {
            "archived_count": archived_count,
            "archived_before": archive_before,
            "summary_created": False,  # Would be True if we created summary records
        }

    async def get_by_id(
        self,
        metrics_id: int,
        user_id: int | None = None,
    ) -> ReportMetrics | None:
        """Get metrics by ID.

        Args:
            metrics_id: Metrics record ID
            user_id: Optional user ID to filter by owner

        Returns:
            ReportMetrics instance or None if not found
        """
        query = select(ReportMetrics).where(ReportMetrics.id == metrics_id)

        if user_id is not None:
            query = query.where(ReportMetrics.user_id == user_id)

        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def delete_metrics(
        self,
        user_id: int,
        ad_account_id: int | None = None,
        entity_type: EntityType | None = None,
        entity_id: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> int:
        """Delete metrics matching criteria.

        Args:
            user_id: Owner user ID
            ad_account_id: Optional ad account filter
            entity_type: Optional entity type filter
            entity_id: Optional entity ID filter
            start_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            Number of deleted records
        """
        conditions = [ReportMetrics.user_id == user_id]

        if ad_account_id is not None:
            conditions.append(ReportMetrics.ad_account_id == ad_account_id)
        if entity_type is not None:
            conditions.append(ReportMetrics.entity_type == entity_type.value)
        if entity_id is not None:
            conditions.append(ReportMetrics.entity_id == entity_id)
        if start_date is not None:
            conditions.append(ReportMetrics.timestamp >= start_date)
        if end_date is not None:
            conditions.append(ReportMetrics.timestamp <= end_date)

        # Count before delete
        count_query = select(func.count()).select_from(
            select(ReportMetrics).where(and_(*conditions)).subquery()
        )
        count_result = await self.db.execute(count_query)
        delete_count = count_result.scalar() or 0

        if delete_count > 0:
            delete_query = delete(ReportMetrics).where(and_(*conditions))
            await self.db.execute(delete_query)
            await self.db.flush()

        return delete_count
