"""Creative management API endpoints."""


from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import CurrentUser, DbSession
from app.schemas.creative import (
    CreativeCreate,
    CreativeFilter,
    CreativeListResponse,
    CreativeResponse,
    CreativeStatus,
    CreativeUpdate,
    FileType,
    PresignedUploadUrlRequest,
    PresignedUploadUrlResponse,
)
from app.services.creative import CreativeNotFoundError, CreativeService

router = APIRouter(prefix="/creatives", tags=["creatives"])


@router.get("", response_model=CreativeListResponse)
async def list_creatives(
    db: DbSession,
    current_user: CurrentUser,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    file_type: FileType | None = Query(None, description="Filter by file type"),
    style: str | None = Query(None, description="Filter by style"),
    status: CreativeStatus = Query(CreativeStatus.ACTIVE, description="Filter by status"),
    tags: list[str] | None = Query(None, description="Filter by tags"),
) -> CreativeListResponse:
    """List user's creatives with optional filters and pagination."""
    service = CreativeService(db)

    filters = CreativeFilter(
        file_type=file_type,
        style=style,
        status=status,
        tags=tags,
    )

    result = await service.get_list(
        user_id=current_user.id,
        filters=filters,
        page=page,
        page_size=page_size,
    )

    return CreativeListResponse(
        creatives=[CreativeResponse.model_validate(c) for c in result["creatives"]],
        total=result["total"],
        page=result["page"],
        page_size=result["page_size"],
        has_more=result["has_more"],
    )


@router.post("", response_model=CreativeResponse, status_code=status.HTTP_201_CREATED)
async def create_creative(
    db: DbSession,
    current_user: CurrentUser,
    data: CreativeCreate,
) -> CreativeResponse:
    """Create a new creative.

    After uploading a file using the presigned URL from /upload-url,
    use this endpoint to create the creative record.
    """
    service = CreativeService(db)

    creative = await service.create(
        user_id=current_user.id,
        data=data,
    )

    await db.commit()

    return CreativeResponse.model_validate(creative)


@router.get("/{creative_id}", response_model=CreativeResponse)
async def get_creative(
    db: DbSession,
    current_user: CurrentUser,
    creative_id: int,
) -> CreativeResponse:
    """Get creative details by ID."""
    service = CreativeService(db)

    creative = await service.get_by_id(
        creative_id=creative_id,
        user_id=current_user.id,
    )

    if not creative:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Creative {creative_id} not found",
        )

    return CreativeResponse.model_validate(creative)


@router.put("/{creative_id}", response_model=CreativeResponse)
async def update_creative(
    db: DbSession,
    current_user: CurrentUser,
    creative_id: int,
    data: CreativeUpdate,
) -> CreativeResponse:
    """Update a creative's metadata."""
    service = CreativeService(db)

    try:
        creative = await service.update(
            creative_id=creative_id,
            user_id=current_user.id,
            data=data,
        )
        await db.commit()
        return CreativeResponse.model_validate(creative)
    except CreativeNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Creative {creative_id} not found",
        )


@router.delete("/{creative_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_creative(
    db: DbSession,
    current_user: CurrentUser,
    creative_id: int,
    hard_delete: bool = Query(False, description="Permanently delete including S3 file"),
) -> None:
    """Delete a creative.

    By default, performs a soft delete (marks as deleted).
    Set hard_delete=true to permanently delete including the S3 file.
    """
    service = CreativeService(db)

    try:
        await service.delete(
            creative_id=creative_id,
            user_id=current_user.id,
            hard_delete=hard_delete,
        )
        await db.commit()
    except CreativeNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Creative {creative_id} not found",
        )


@router.post("/upload-url", response_model=PresignedUploadUrlResponse)
async def get_upload_url(
    current_user: CurrentUser,
    data: PresignedUploadUrlRequest,
) -> PresignedUploadUrlResponse:
    """Generate a presigned URL for uploading a creative file to S3.

    Use this URL to upload the file directly to S3, then call POST /creatives
    to create the creative record with the returned s3_url and cdn_url.
    """
    # Validate content type
    allowed_types = [
        "image/jpeg",
        "image/png",
        "image/gif",
        "image/webp",
        "video/mp4",
        "video/quicktime",
        "video/webm",
    ]

    if data.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Content type {data.content_type} not allowed. Allowed types: {allowed_types}",
        )

    # Use a temporary db session is not needed for presigned URL generation
    service = CreativeService(None)  # type: ignore

    result = service.generate_presigned_upload_url(
        user_id=current_user.id,
        filename=data.filename,
        content_type=data.content_type,
    )

    return PresignedUploadUrlResponse(
        upload_url=result["upload_url"],
        upload_fields=result["upload_fields"],
        file_key=result["file_key"],
        s3_url=result["s3_url"],
        cdn_url=result["cdn_url"],
        expires_in=result["expires_in"],
    )
