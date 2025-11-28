"""Report metrics API endpoints."""

from datetime import datetime

from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import CurrentUser, DbSession
from app.schemas.report import (
    AggregatedMetrics,
    ArchivalResult,
    EntityType,
    MetricsBatchCreate,
    MetricsCreate,
    MetricsFilter,
    MetricsListResponse,
    MetricsResponse,
    TrendResponse,
)
from app.services.report import ReportService

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/metrics", response_model=MetricsListResponse)
async def list_metrics(
    db: DbSession,
    current_user: CurrentUser,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    ad_account_id: int | None = Query(None, description="Filter by ad account"),
    entity_type: EntityType | None = Query(None, description="Filter by entity type"),
    entity_id: str | None = Query(None, description="Filter by entity ID"),
    start_date: datetime | None = Query(None, description="Filter by start date"),
    end_date: datetime | None = Query(None, description="Filter by end date"),
) -> MetricsListResponse:
    """List metrics with optional filters and pagination."""
    service = ReportService(db)

    filters = MetricsFilter(
        ad_account_id=ad_account_id,
        entity_type=entity_type,
        entity_id=entity_id,
        start_date=start_date,
        end_date=end_date,
    )

    result = await service.get_metrics(
        user_id=current_user.id,
        filters=filters,
        page=page,
        page_size=page_size,
    )

    return MetricsListResponse(
        items=[MetricsResponse.model_validate(m) for m in result["metrics"]],
        total=result["total"],
        page=result["page"],
        page_size=result["page_size"],
        has_more=result["has_more"],
    )



@router.post("/metrics", response_model=MetricsResponse, status_code=status.HTTP_201_CREATED)
async def save_metrics(
    db: DbSession,
    current_user: CurrentUser,
    data: MetricsCreate,
) -> MetricsResponse:
    """Save a single metrics record.

    This endpoint is used by the Ad Performance module to store
    metrics data fetched from ad platforms.
    """
    service = ReportService(db)

    metrics = await service.save_metrics(
        user_id=current_user.id,
        data=data,
    )

    await db.commit()

    return MetricsResponse.model_validate(metrics)


@router.post(
    "/metrics/batch",
    response_model=list[MetricsResponse],
    status_code=status.HTTP_201_CREATED,
)
async def save_metrics_batch(
    db: DbSession,
    current_user: CurrentUser,
    data: MetricsBatchCreate,
) -> list[MetricsResponse]:
    """Save multiple metrics records in batch.

    This endpoint is used for bulk importing metrics data.
    Maximum 1000 records per request.
    """
    service = ReportService(db)

    metrics_list = await service.save_metrics_batch(
        user_id=current_user.id,
        metrics_list=data.metrics,
    )

    await db.commit()

    return [MetricsResponse.model_validate(m) for m in metrics_list]


@router.get("/metrics/{metrics_id}", response_model=MetricsResponse)
async def get_metrics_by_id(
    db: DbSession,
    current_user: CurrentUser,
    metrics_id: int,
) -> MetricsResponse:
    """Get a specific metrics record by ID."""
    service = ReportService(db)

    metrics = await service.get_by_id(
        metrics_id=metrics_id,
        user_id=current_user.id,
    )

    if not metrics:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Metrics {metrics_id} not found",
        )

    return MetricsResponse.model_validate(metrics)


@router.get("/summary", response_model=AggregatedMetrics)
async def get_aggregated_metrics(
    db: DbSession,
    current_user: CurrentUser,
    start_date: datetime | None = Query(None, description="Start of period"),
    end_date: datetime | None = Query(None, description="End of period"),
    ad_account_id: int | None = Query(None, description="Filter by ad account"),
    entity_type: EntityType | None = Query(None, description="Filter by entity type"),
) -> AggregatedMetrics:
    """Get aggregated metrics for a time period.

    Returns totals and averages for impressions, clicks, spend,
    conversions, revenue, CTR, CPC, CPA, and ROAS.
    """
    service = ReportService(db)

    return await service.get_aggregated_metrics(
        user_id=current_user.id,
        start_date=start_date,
        end_date=end_date,
        ad_account_id=ad_account_id,
        entity_type=entity_type,
    )


@router.get("/trend", response_model=TrendResponse)
async def get_trend_data(
    db: DbSession,
    current_user: CurrentUser,
    start_date: datetime | None = Query(None, description="Start of period"),
    end_date: datetime | None = Query(None, description="End of period"),
    ad_account_id: int | None = Query(None, description="Filter by ad account"),
    granularity: str = Query("daily", description="Granularity: daily, weekly, monthly"),
) -> TrendResponse:
    """Get trend data aggregated by time period.

    Returns time series data for visualizing performance trends.
    """
    if granularity not in ["daily", "weekly", "monthly"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Granularity must be 'daily', 'weekly', or 'monthly'",
        )

    service = ReportService(db)

    # Set defaults for date range
    from datetime import timedelta

    if end_date is None:
        end_date = datetime.utcnow()
    if start_date is None:
        start_date = end_date - timedelta(days=7)

    data = await service.get_trend_data(
        user_id=current_user.id,
        start_date=start_date,
        end_date=end_date,
        ad_account_id=ad_account_id,
        granularity=granularity,
    )

    return TrendResponse(
        data=data,
        period_start=start_date,
        period_end=end_date,
        granularity=granularity,
    )


@router.post("/archive", response_model=ArchivalResult)
async def archive_old_metrics(
    db: DbSession,
    current_user: CurrentUser,
    days_threshold: int = Query(90, ge=30, le=365, description="Days threshold"),
) -> ArchivalResult:
    """Archive metrics older than threshold.

    This endpoint archives (deletes) detailed metrics older than
    the specified number of days. Default is 90 days.

    Note: In production, summary data would be preserved before deletion.
    """
    service = ReportService(db)

    result = await service.archive_old_metrics(days_threshold=days_threshold)

    await db.commit()

    return ArchivalResult(
        archived_count=result["archived_count"],
        archived_before=result["archived_before"],
        summary_created=result["summary_created"],
    )


@router.delete("/metrics", status_code=status.HTTP_200_OK)
async def delete_metrics(
    db: DbSession,
    current_user: CurrentUser,
    ad_account_id: int | None = Query(None, description="Filter by ad account"),
    entity_type: EntityType | None = Query(None, description="Filter by entity type"),
    entity_id: str | None = Query(None, description="Filter by entity ID"),
    start_date: datetime | None = Query(None, description="Filter by start date"),
    end_date: datetime | None = Query(None, description="Filter by end date"),
) -> dict[str, int]:
    """Delete metrics matching criteria.

    At least one filter must be provided to prevent accidental deletion
    of all metrics.
    """
    # Require at least one filter
    if all(
        v is None
        for v in [ad_account_id, entity_type, entity_id, start_date, end_date]
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one filter must be provided",
        )

    service = ReportService(db)

    deleted_count = await service.delete_metrics(
        user_id=current_user.id,
        ad_account_id=ad_account_id,
        entity_type=entity_type,
        entity_id=entity_id,
        start_date=start_date,
        end_date=end_date,
    )

    await db.commit()

    return {"deleted_count": deleted_count}
