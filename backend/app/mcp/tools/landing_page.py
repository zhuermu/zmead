"""MCP tools for landing page management.

Implements tools for managing landing pages:
- get_landing_pages: List landing pages with filtering
- get_landing_page: Get single landing page details
- create_landing_page: Create a new landing page
- update_landing_page: Update landing page content
- delete_landing_page: Delete a landing page
- publish_landing_page: Publish landing page to S3/CloudFront
"""

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.mcp.registry import tool
from app.mcp.types import MCPToolParameter
from app.schemas.landing_page import (
    LandingPageCreate,
    LandingPageFilter,
    LandingPageStatus,
    LandingPageUpdate,
)
from app.services.landing_page import LandingPageNotFoundError, LandingPageService


@tool(
    name="get_landing_pages",
    description="Get a paginated list of landing pages for the current user. Supports filtering by status, template, and language.",
    parameters=[
        MCPToolParameter(
            name="page",
            type="integer",
            description="Page number (1-indexed)",
            required=False,
            default=1,
        ),
        MCPToolParameter(
            name="page_size",
            type="integer",
            description="Number of items per page (max 100)",
            required=False,
            default=20,
        ),
        MCPToolParameter(
            name="status",
            type="string",
            description="Filter by status",
            required=False,
            enum=["draft", "published", "archived"],
        ),
        MCPToolParameter(
            name="template",
            type="string",
            description="Filter by template name",
            required=False,
        ),
        MCPToolParameter(
            name="language",
            type="string",
            description="Filter by language code (e.g., 'en', 'zh')",
            required=False,
        ),
    ],
    category="landing_page",
)
async def get_landing_pages(
    user_id: int,
    db: AsyncSession,
    page: int = 1,
    page_size: int = 20,
    status: str | None = None,
    template: str | None = None,
    language: str | None = None,
) -> dict[str, Any]:
    """Get list of landing pages."""
    # Validate page_size
    page_size = min(page_size, 100)

    # Build filter
    filters = LandingPageFilter(
        status=LandingPageStatus(status) if status else None,
        template=template,
        language=language,
    )

    service = LandingPageService(db)
    result = await service.get_list(
        user_id=user_id,
        filters=filters,
        page=page,
        page_size=page_size,
    )

    # Convert to serializable format
    landing_pages = [
        {
            "id": lp.id,
            "name": lp.name,
            "url": lp.url,
            "s3_key": lp.s3_key,
            "product_url": lp.product_url,
            "template": lp.template,
            "language": lp.language,
            "status": lp.status,
            "created_at": lp.created_at.isoformat() if lp.created_at else None,
            "updated_at": lp.updated_at.isoformat() if lp.updated_at else None,
            "published_at": lp.published_at.isoformat() if lp.published_at else None,
        }
        for lp in result["landing_pages"]
    ]

    return {
        "landing_pages": landing_pages,
        "total": result["total"],
        "page": result["page"],
        "page_size": result["page_size"],
        "has_more": result["has_more"],
    }


@tool(
    name="get_landing_page",
    description="Get details of a specific landing page by ID, including HTML content.",
    parameters=[
        MCPToolParameter(
            name="landing_page_id",
            type="integer",
            description="ID of the landing page to retrieve",
            required=True,
        ),
    ],
    category="landing_page",
)
async def get_landing_page(
    user_id: int,
    db: AsyncSession,
    landing_page_id: int,
) -> dict[str, Any]:
    """Get a single landing page by ID."""
    service = LandingPageService(db)
    landing_page = await service.get_by_id(landing_page_id, user_id)

    if not landing_page:
        raise ValueError(f"Landing page {landing_page_id} not found")

    return {
        "id": landing_page.id,
        "user_id": landing_page.user_id,
        "name": landing_page.name,
        "url": landing_page.url,
        "s3_key": landing_page.s3_key,
        "product_url": landing_page.product_url,
        "template": landing_page.template,
        "language": landing_page.language,
        "html_content": landing_page.html_content,
        "status": landing_page.status,
        "created_at": landing_page.created_at.isoformat() if landing_page.created_at else None,
        "updated_at": landing_page.updated_at.isoformat() if landing_page.updated_at else None,
        "published_at": landing_page.published_at.isoformat() if landing_page.published_at else None,
    }


@tool(
    name="create_landing_page",
    description="Create a new landing page with the provided configuration.",
    parameters=[
        MCPToolParameter(
            name="name",
            type="string",
            description="Name/title of the landing page",
            required=True,
        ),
        MCPToolParameter(
            name="product_url",
            type="string",
            description="URL of the product this landing page is for",
            required=True,
        ),
        MCPToolParameter(
            name="template",
            type="string",
            description="Template to use (e.g., 'modern', 'minimal')",
            required=False,
            default="modern",
        ),
        MCPToolParameter(
            name="language",
            type="string",
            description="Language code (e.g., 'en', 'zh')",
            required=False,
            default="en",
        ),
        MCPToolParameter(
            name="html_content",
            type="string",
            description="HTML content of the landing page",
            required=False,
        ),
    ],
    category="landing_page",
)
async def create_landing_page(
    user_id: int,
    db: AsyncSession,
    name: str,
    product_url: str,
    template: str = "modern",
    language: str = "en",
    html_content: str | None = None,
) -> dict[str, Any]:
    """Create a new landing page."""
    data = LandingPageCreate(
        name=name,
        product_url=product_url,
        template=template,
        language=language,
        html_content=html_content,
    )

    service = LandingPageService(db)
    landing_page = await service.create(user_id, data)

    return {
        "id": landing_page.id,
        "user_id": landing_page.user_id,
        "name": landing_page.name,
        "url": landing_page.url,
        "s3_key": landing_page.s3_key,
        "product_url": landing_page.product_url,
        "template": landing_page.template,
        "language": landing_page.language,
        "status": landing_page.status,
        "created_at": landing_page.created_at.isoformat() if landing_page.created_at else None,
    }


@tool(
    name="update_landing_page",
    description="Update an existing landing page's content or configuration.",
    parameters=[
        MCPToolParameter(
            name="landing_page_id",
            type="integer",
            description="ID of the landing page to update",
            required=True,
        ),
        MCPToolParameter(
            name="name",
            type="string",
            description="New name/title",
            required=False,
        ),
        MCPToolParameter(
            name="product_url",
            type="string",
            description="New product URL",
            required=False,
        ),
        MCPToolParameter(
            name="template",
            type="string",
            description="New template",
            required=False,
        ),
        MCPToolParameter(
            name="language",
            type="string",
            description="New language code",
            required=False,
        ),
        MCPToolParameter(
            name="html_content",
            type="string",
            description="New HTML content",
            required=False,
        ),
    ],
    category="landing_page",
)
async def update_landing_page(
    user_id: int,
    db: AsyncSession,
    landing_page_id: int,
    name: str | None = None,
    product_url: str | None = None,
    template: str | None = None,
    language: str | None = None,
    html_content: str | None = None,
) -> dict[str, Any]:
    """Update a landing page."""
    # Build update data with only provided fields
    update_data = {}
    if name is not None:
        update_data["name"] = name
    if product_url is not None:
        update_data["product_url"] = product_url
    if template is not None:
        update_data["template"] = template
    if language is not None:
        update_data["language"] = language
    if html_content is not None:
        update_data["html_content"] = html_content

    if not update_data:
        raise ValueError("No fields to update")

    data = LandingPageUpdate(**update_data)

    service = LandingPageService(db)
    try:
        landing_page = await service.update(landing_page_id, user_id, data)
    except LandingPageNotFoundError:
        raise ValueError(f"Landing page {landing_page_id} not found")

    return {
        "id": landing_page.id,
        "user_id": landing_page.user_id,
        "name": landing_page.name,
        "url": landing_page.url,
        "s3_key": landing_page.s3_key,
        "product_url": landing_page.product_url,
        "template": landing_page.template,
        "language": landing_page.language,
        "status": landing_page.status,
        "created_at": landing_page.created_at.isoformat() if landing_page.created_at else None,
        "updated_at": landing_page.updated_at.isoformat() if landing_page.updated_at else None,
    }


@tool(
    name="delete_landing_page",
    description="Delete a landing page. By default archives it (soft delete). Use hard_delete=true to permanently remove.",
    parameters=[
        MCPToolParameter(
            name="landing_page_id",
            type="integer",
            description="ID of the landing page to delete",
            required=True,
        ),
        MCPToolParameter(
            name="hard_delete",
            type="boolean",
            description="If true, permanently delete including S3 files",
            required=False,
            default=False,
        ),
    ],
    category="landing_page",
)
async def delete_landing_page(
    user_id: int,
    db: AsyncSession,
    landing_page_id: int,
    hard_delete: bool = False,
) -> dict[str, Any]:
    """Delete a landing page."""
    service = LandingPageService(db)
    try:
        await service.delete(landing_page_id, user_id, hard_delete=hard_delete)
    except LandingPageNotFoundError:
        raise ValueError(f"Landing page {landing_page_id} not found")

    return {
        "deleted": True,
        "landing_page_id": landing_page_id,
        "hard_delete": hard_delete,
    }


@tool(
    name="publish_landing_page",
    description="Publish a landing page to S3 and CloudFront. The landing page must have HTML content.",
    parameters=[
        MCPToolParameter(
            name="landing_page_id",
            type="integer",
            description="ID of the landing page to publish",
            required=True,
        ),
    ],
    category="landing_page",
)
async def publish_landing_page(
    user_id: int,
    db: AsyncSession,
    landing_page_id: int,
) -> dict[str, Any]:
    """Publish a landing page."""
    service = LandingPageService(db)
    try:
        landing_page = await service.publish(landing_page_id, user_id)
    except LandingPageNotFoundError:
        raise ValueError(f"Landing page {landing_page_id} not found")
    except ValueError as e:
        raise ValueError(str(e))

    return {
        "id": landing_page.id,
        "url": landing_page.url,
        "status": landing_page.status,
        "published_at": landing_page.published_at.isoformat() if landing_page.published_at else None,
    }
