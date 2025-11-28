"""Landing page management API endpoints."""

from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import CurrentUser, DbSession
from app.schemas.landing_page import (
    LandingPageCreate,
    LandingPageFilter,
    LandingPageListResponse,
    LandingPagePublishResponse,
    LandingPageResponse,
    LandingPageStatus,
    LandingPageUpdate,
)
from app.services.landing_page import LandingPageNotFoundError, LandingPageService

router = APIRouter(prefix="/landing-pages", tags=["landing-pages"])


@router.get("", response_model=LandingPageListResponse)
async def list_landing_pages(
    db: DbSession,
    current_user: CurrentUser,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    status: LandingPageStatus | None = Query(None, description="Filter by status"),
    template: str | None = Query(None, description="Filter by template"),
    language: str | None = Query(None, description="Filter by language"),
) -> LandingPageListResponse:
    """List user's landing pages with optional filters and pagination."""
    service = LandingPageService(db)

    filters = LandingPageFilter(
        status=status,
        template=template,
        language=language,
    )

    result = await service.get_list(
        user_id=current_user.id,
        filters=filters,
        page=page,
        page_size=page_size,
    )

    return LandingPageListResponse(
        items=[LandingPageResponse.model_validate(lp) for lp in result["landing_pages"]],
        total=result["total"],
        page=result["page"],
        page_size=result["page_size"],
        has_more=result["has_more"],
    )



@router.post("", response_model=LandingPageResponse, status_code=status.HTTP_201_CREATED)
async def create_landing_page(
    db: DbSession,
    current_user: CurrentUser,
    data: LandingPageCreate,
) -> LandingPageResponse:
    """Create a new landing page.

    Creates a landing page in draft status. Use the publish endpoint
    to upload the HTML to S3 and make it publicly accessible.
    """
    service = LandingPageService(db)

    landing_page = await service.create(
        user_id=current_user.id,
        data=data,
    )

    await db.commit()

    return LandingPageResponse.model_validate(landing_page)


@router.get("/{landing_page_id}", response_model=LandingPageResponse)
async def get_landing_page(
    db: DbSession,
    current_user: CurrentUser,
    landing_page_id: int,
) -> LandingPageResponse:
    """Get landing page details by ID."""
    service = LandingPageService(db)

    landing_page = await service.get_by_id(
        landing_page_id=landing_page_id,
        user_id=current_user.id,
    )

    if not landing_page:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Landing page {landing_page_id} not found",
        )

    return LandingPageResponse.model_validate(landing_page)


@router.put("/{landing_page_id}", response_model=LandingPageResponse)
async def update_landing_page(
    db: DbSession,
    current_user: CurrentUser,
    landing_page_id: int,
    data: LandingPageUpdate,
) -> LandingPageResponse:
    """Update a landing page.

    Note: If the landing page is already published and you update the HTML content,
    you need to call the publish endpoint again to update the S3 file.
    """
    service = LandingPageService(db)

    try:
        landing_page = await service.update(
            landing_page_id=landing_page_id,
            user_id=current_user.id,
            data=data,
        )
        await db.commit()
        return LandingPageResponse.model_validate(landing_page)
    except LandingPageNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Landing page {landing_page_id} not found",
        )


@router.delete("/{landing_page_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_landing_page(
    db: DbSession,
    current_user: CurrentUser,
    landing_page_id: int,
    hard_delete: bool = Query(False, description="Permanently delete including S3 file"),
) -> None:
    """Delete a landing page.

    By default, performs a soft delete (archives the landing page).
    Set hard_delete=true to permanently delete including the S3 file.
    """
    service = LandingPageService(db)

    try:
        await service.delete(
            landing_page_id=landing_page_id,
            user_id=current_user.id,
            hard_delete=hard_delete,
        )
        await db.commit()
    except LandingPageNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Landing page {landing_page_id} not found",
        )


@router.post("/{landing_page_id}/publish", response_model=LandingPagePublishResponse)
async def publish_landing_page(
    db: DbSession,
    current_user: CurrentUser,
    landing_page_id: int,
) -> LandingPagePublishResponse:
    """Publish a landing page to S3 and CloudFront.

    Uploads the HTML content to S3 and makes it accessible via CloudFront CDN.
    The landing page must have HTML content before publishing.
    """
    service = LandingPageService(db)

    try:
        landing_page = await service.publish(
            landing_page_id=landing_page_id,
            user_id=current_user.id,
        )
        await db.commit()

        return LandingPagePublishResponse(
            id=landing_page.id,
            url=landing_page.url,
            cdn_url=landing_page.url,  # URL is already the CDN URL
            status=landing_page.status,
            published_at=landing_page.published_at,
        )
    except LandingPageNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Landing page {landing_page_id} not found",
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
