"""Landing page management API endpoints."""

import asyncio
import base64
import logging
import re
from urllib.parse import urljoin, urlparse

import httpx
from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import HTMLResponse

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

logger = logging.getLogger(__name__)

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


async def _download_image_as_base64(
    client: httpx.AsyncClient,
    url: str,
) -> tuple[str, str] | None:
    """Download image and convert to base64 data URI.

    Args:
        client: HTTP client instance
        url: Image URL to download

    Returns:
        Tuple of (original_url, data_uri) or None if download fails
    """
    try:
        response = await client.get(url, follow_redirects=True)
        response.raise_for_status()

        content_type = response.headers.get("content-type", "image/jpeg")
        # Clean content type (remove charset, etc.)
        if ";" in content_type:
            content_type = content_type.split(";")[0].strip()

        # Ensure valid image content type
        if not content_type.startswith("image/"):
            content_type = "image/jpeg"

        image_base64 = base64.b64encode(response.content).decode("utf-8")
        data_uri = f"data:{content_type};base64,{image_base64}"

        return (url, data_uri)
    except Exception as e:
        logger.warning(f"Failed to download image {url[:100]}: {e}")
        return None


def _extract_image_urls(html: str) -> list[str]:
    """Extract image URLs from HTML content.

    Args:
        html: HTML content

    Returns:
        List of unique image URLs
    """
    urls = set()

    # Match src attributes in img tags
    img_pattern = r'<img[^>]+src=["\']([^"\']+)["\']'
    for match in re.finditer(img_pattern, html, re.IGNORECASE):
        url = match.group(1)
        # Skip data URIs and relative paths that don't start with http
        if url.startswith("data:"):
            continue
        if url.startswith("http://") or url.startswith("https://"):
            urls.add(url)

    # Match url() in CSS (for background images)
    css_url_pattern = r'url\(["\']?(https?://[^"\')\s]+)["\']?\)'
    for match in re.finditer(css_url_pattern, html, re.IGNORECASE):
        urls.add(match.group(1))

    return list(urls)


@router.get("/{landing_page_id}/preview", response_class=HTMLResponse)
async def preview_landing_page(
    db: DbSession,
    current_user: CurrentUser,
    landing_page_id: int,
    embed_images: bool = Query(True, description="Download and embed images as base64"),
) -> HTMLResponse:
    """Preview a landing page with embedded images.

    This endpoint returns the HTML content with all external images
    downloaded and embedded as base64 data URIs. This ensures the
    preview displays correctly without CORS issues.

    Args:
        landing_page_id: Landing page ID
        embed_images: Whether to embed images as base64 (default: True)

    Returns:
        HTMLResponse with the landing page content
    """
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

    html_content = landing_page.html_content
    if not html_content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Landing page has no HTML content",
        )

    # If embed_images is False, return HTML as-is
    if not embed_images:
        return HTMLResponse(content=html_content)

    # Extract image URLs from HTML
    image_urls = _extract_image_urls(html_content)

    if not image_urls:
        return HTMLResponse(content=html_content)

    logger.info(f"Preview: Found {len(image_urls)} images to embed for landing page {landing_page_id}")

    # Download images concurrently and convert to base64
    async with httpx.AsyncClient(
        timeout=30.0,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        },
    ) as client:
        tasks = [_download_image_as_base64(client, url) for url in image_urls]
        results = await asyncio.gather(*tasks)

    # Replace image URLs with base64 data URIs
    for result in results:
        if result:
            original_url, data_uri = result
            # Escape special regex characters in URL
            escaped_url = re.escape(original_url)
            html_content = re.sub(escaped_url, data_uri, html_content)

    logger.info(f"Preview: Embedded {sum(1 for r in results if r)} images for landing page {landing_page_id}")

    return HTMLResponse(content=html_content)
