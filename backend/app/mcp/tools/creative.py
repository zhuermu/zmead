"""MCP tools for creative management.

Implements tools for managing advertising creatives:
- get_creatives: List creatives with filtering
- get_creative: Get single creative details
- create_creative: Create a new creative
- update_creative: Update creative metadata
- delete_creative: Delete a creative
- get_upload_url: Get presigned URL for file upload
"""

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.mcp.registry import tool
from app.mcp.types import MCPToolParameter
from app.schemas.creative import (
    CreativeCreate,
    CreativeFilter,
    CreativeStatus,
    CreativeUpdate,
    FileType,
)
from app.services.creative import CreativeNotFoundError, CreativeService


@tool(
    name="get_creatives",
    description="Get a paginated list of creatives for the current user. Supports filtering by file type, style, status, and tags.",
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
            name="file_type",
            type="string",
            description="Filter by file type",
            required=False,
            enum=["image", "video"],
        ),
        MCPToolParameter(
            name="style",
            type="string",
            description="Filter by creative style",
            required=False,
        ),
        MCPToolParameter(
            name="status",
            type="string",
            description="Filter by status",
            required=False,
            default="active",
            enum=["active", "deleted"],
        ),
        MCPToolParameter(
            name="tags",
            type="array",
            description="Filter by tags (creatives must have all specified tags)",
            required=False,
        ),
    ],
    category="creative",
)
async def get_creatives(
    user_id: int,
    db: AsyncSession,
    page: int = 1,
    page_size: int = 20,
    file_type: str | None = None,
    style: str | None = None,
    status: str = "active",
    tags: list[str] | None = None,
) -> dict[str, Any]:
    """Get list of creatives."""
    # Validate page_size
    page_size = min(page_size, 100)

    # Build filter
    filters = CreativeFilter(
        file_type=FileType(file_type) if file_type else None,
        style=style,
        status=CreativeStatus(status),
        tags=tags,
    )

    service = CreativeService(db)
    result = await service.get_list(
        user_id=user_id,
        filters=filters,
        page=page,
        page_size=page_size,
    )

    # Convert to serializable format
    creatives = [
        {
            "id": c.id,
            "file_url": c.file_url,
            "cdn_url": c.cdn_url,
            "file_type": c.file_type,
            "file_size": c.file_size,
            "name": c.name,
            "product_url": c.product_url,
            "style": c.style,
            "score": c.score,
            "tags": c.tags or [],
            "status": c.status,
            "created_at": c.created_at.isoformat() if c.created_at else None,
            "updated_at": c.updated_at.isoformat() if c.updated_at else None,
        }
        for c in result["creatives"]
    ]

    return {
        "creatives": creatives,
        "total": result["total"],
        "page": result["page"],
        "page_size": result["page_size"],
        "has_more": result["has_more"],
    }


@tool(
    name="get_creative",
    description="Get details of a specific creative by ID.",
    parameters=[
        MCPToolParameter(
            name="creative_id",
            type="integer",
            description="ID of the creative to retrieve",
            required=True,
        ),
    ],
    category="creative",
)
async def get_creative(
    user_id: int,
    db: AsyncSession,
    creative_id: int,
) -> dict[str, Any]:
    """Get a single creative by ID."""
    service = CreativeService(db)
    creative = await service.get_by_id(creative_id, user_id)

    if not creative:
        raise ValueError(f"Creative {creative_id} not found")

    return {
        "id": creative.id,
        "user_id": creative.user_id,
        "file_url": creative.file_url,
        "cdn_url": creative.cdn_url,
        "file_type": creative.file_type,
        "file_size": creative.file_size,
        "name": creative.name,
        "product_url": creative.product_url,
        "style": creative.style,
        "score": creative.score,
        "tags": creative.tags or [],
        "status": creative.status,
        "created_at": creative.created_at.isoformat() if creative.created_at else None,
        "updated_at": creative.updated_at.isoformat() if creative.updated_at else None,
    }


@tool(
    name="create_creative",
    description="Create a new creative with the provided metadata. Use get_upload_url first to upload the file to S3.",
    parameters=[
        MCPToolParameter(
            name="file_url",
            type="string",
            description="S3 URL of the uploaded file",
            required=True,
        ),
        MCPToolParameter(
            name="cdn_url",
            type="string",
            description="CloudFront CDN URL of the file",
            required=True,
        ),
        MCPToolParameter(
            name="file_type",
            type="string",
            description="Type of file",
            required=True,
            enum=["image", "video"],
        ),
        MCPToolParameter(
            name="file_size",
            type="integer",
            description="File size in bytes",
            required=True,
        ),
        MCPToolParameter(
            name="name",
            type="string",
            description="Name/title of the creative",
            required=False,
        ),
        MCPToolParameter(
            name="product_url",
            type="string",
            description="URL of the product this creative is for",
            required=False,
        ),
        MCPToolParameter(
            name="style",
            type="string",
            description="Style/category of the creative",
            required=False,
        ),
        MCPToolParameter(
            name="score",
            type="number",
            description="AI quality score (0-100)",
            required=False,
        ),
        MCPToolParameter(
            name="tags",
            type="array",
            description="Tags for categorizing the creative",
            required=False,
        ),
    ],
    category="creative",
)
async def create_creative(
    user_id: int,
    db: AsyncSession,
    file_url: str,
    cdn_url: str,
    file_type: str,
    file_size: int,
    name: str | None = None,
    product_url: str | None = None,
    style: str | None = None,
    score: float | None = None,
    tags: list[str] | None = None,
) -> dict[str, Any]:
    """Create a new creative."""
    data = CreativeCreate(
        file_url=file_url,
        cdn_url=cdn_url,
        file_type=FileType(file_type),
        file_size=file_size,
        name=name,
        product_url=product_url,
        style=style,
        score=score,
        tags=tags or [],
    )

    service = CreativeService(db)
    creative = await service.create(user_id, data)

    return {
        "id": creative.id,
        "user_id": creative.user_id,
        "file_url": creative.file_url,
        "cdn_url": creative.cdn_url,
        "file_type": creative.file_type,
        "file_size": creative.file_size,
        "name": creative.name,
        "product_url": creative.product_url,
        "style": creative.style,
        "score": creative.score,
        "tags": creative.tags or [],
        "status": creative.status,
        "created_at": creative.created_at.isoformat() if creative.created_at else None,
    }


@tool(
    name="update_creative",
    description="Update metadata of an existing creative.",
    parameters=[
        MCPToolParameter(
            name="creative_id",
            type="integer",
            description="ID of the creative to update",
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
            name="style",
            type="string",
            description="New style/category",
            required=False,
        ),
        MCPToolParameter(
            name="score",
            type="number",
            description="New AI quality score (0-100)",
            required=False,
        ),
        MCPToolParameter(
            name="tags",
            type="array",
            description="New tags (replaces existing)",
            required=False,
        ),
    ],
    category="creative",
)
async def update_creative(
    user_id: int,
    db: AsyncSession,
    creative_id: int,
    name: str | None = None,
    product_url: str | None = None,
    style: str | None = None,
    score: float | None = None,
    tags: list[str] | None = None,
) -> dict[str, Any]:
    """Update a creative."""
    # Build update data with only provided fields
    update_data = {}
    if name is not None:
        update_data["name"] = name
    if product_url is not None:
        update_data["product_url"] = product_url
    if style is not None:
        update_data["style"] = style
    if score is not None:
        update_data["score"] = score
    if tags is not None:
        update_data["tags"] = tags

    if not update_data:
        raise ValueError("No fields to update")

    data = CreativeUpdate(**update_data)

    service = CreativeService(db)
    try:
        creative = await service.update(creative_id, user_id, data)
    except CreativeNotFoundError:
        raise ValueError(f"Creative {creative_id} not found")

    return {
        "id": creative.id,
        "user_id": creative.user_id,
        "file_url": creative.file_url,
        "cdn_url": creative.cdn_url,
        "file_type": creative.file_type,
        "file_size": creative.file_size,
        "name": creative.name,
        "product_url": creative.product_url,
        "style": creative.style,
        "score": creative.score,
        "tags": creative.tags or [],
        "status": creative.status,
        "created_at": creative.created_at.isoformat() if creative.created_at else None,
        "updated_at": creative.updated_at.isoformat() if creative.updated_at else None,
    }


@tool(
    name="delete_creative",
    description="Delete a creative. By default performs a soft delete (marks as deleted). Use hard_delete=true to permanently remove.",
    parameters=[
        MCPToolParameter(
            name="creative_id",
            type="integer",
            description="ID of the creative to delete",
            required=True,
        ),
        MCPToolParameter(
            name="hard_delete",
            type="boolean",
            description="If true, permanently delete including S3 file",
            required=False,
            default=False,
        ),
    ],
    category="creative",
)
async def delete_creative(
    user_id: int,
    db: AsyncSession,
    creative_id: int,
    hard_delete: bool = False,
) -> dict[str, Any]:
    """Delete a creative."""
    service = CreativeService(db)
    try:
        await service.delete(creative_id, user_id, hard_delete=hard_delete)
    except CreativeNotFoundError:
        raise ValueError(f"Creative {creative_id} not found")

    return {
        "deleted": True,
        "creative_id": creative_id,
        "hard_delete": hard_delete,
    }


@tool(
    name="get_upload_url",
    description="Generate a presigned URL for uploading a creative file to S3. Use this before create_creative.",
    parameters=[
        MCPToolParameter(
            name="filename",
            type="string",
            description="Original filename (used for extension)",
            required=True,
        ),
        MCPToolParameter(
            name="content_type",
            type="string",
            description="MIME type of the file (e.g., image/jpeg, video/mp4)",
            required=True,
        ),
        MCPToolParameter(
            name="expires_in",
            type="integer",
            description="URL expiration time in seconds",
            required=False,
            default=3600,
        ),
    ],
    category="creative",
)
async def get_upload_url(
    user_id: int,
    db: AsyncSession,
    filename: str,
    content_type: str,
    expires_in: int = 3600,
) -> dict[str, Any]:
    """Generate presigned upload URL."""
    service = CreativeService(db)
    result = service.generate_presigned_upload_url(
        user_id=user_id,
        filename=filename,
        content_type=content_type,
        expires_in=expires_in,
    )

    return result
