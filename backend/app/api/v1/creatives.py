"""Creative management API endpoints."""

import logging

from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import CurrentUser, DbSession
from app.schemas.creative import (
    BucketFileInfo,
    BucketListResponse,
    BucketSyncRequest,
    BucketSyncResponse,
    BucketSyncResult,
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

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/creatives", tags=["creatives"])


def _add_signed_url(creative, service: CreativeService) -> CreativeResponse:
    """Create CreativeResponse with signed URL."""
    response = CreativeResponse.model_validate(creative)
    # Generate signed URL for secure access (1 hour expiry)
    response.signed_url = service.generate_signed_url(creative.file_url, expires_in=3600)
    return response


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
        items=[_add_signed_url(c, service) for c in result["creatives"]],
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

    return _add_signed_url(creative, service)


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

    return _add_signed_url(creative, service)


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
        return _add_signed_url(creative, service)
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


@router.get("/bucket/files", response_model=BucketListResponse)
async def list_bucket_files(
    db: DbSession,
    current_user: CurrentUser,
    file_type: str | None = Query(
        None,
        description="Filter by file type prefix: 'image/', 'video/', 'audio/'",
    ),
) -> BucketListResponse:
    """List files in user's uploads bucket that can be synced to creatives.

    Returns files from the GCS uploads bucket that the user has uploaded
    via AI Agent. Use the sync endpoint to import these files into the
    creatives database.
    """
    service = CreativeService(db)

    # Determine file type filters
    file_types = None
    if file_type:
        file_types = [file_type]
    else:
        # Default: all media types
        file_types = ["image/", "video/", "audio/"]

    # List files from bucket
    bucket_files = service.list_bucket_files(
        user_id=current_user.id,
        file_types=file_types,
    )

    # Get already synced URLs
    synced_urls = await service.get_synced_file_urls(current_user.id)

    # Mark synced status
    files = []
    for f in bucket_files:
        files.append(
            BucketFileInfo(
                name=f["name"],
                size=f.get("size", 0),
                content_type=f.get("content_type"),
                updated=f.get("updated"),
                url=f["url"],
                synced=f["url"] in synced_urls,
            )
        )

    logger.info(
        f"Listed {len(files)} bucket files for user {current_user.id}, "
        f"{sum(1 for f in files if f.synced)} already synced"
    )

    return BucketListResponse(
        files=files,
        total=len(files),
        prefix=f"{current_user.id}/",
    )


@router.post("/bucket/sync", response_model=BucketSyncResponse)
async def sync_bucket_files(
    db: DbSession,
    current_user: CurrentUser,
    data: BucketSyncRequest,
) -> BucketSyncResponse:
    """Sync files from uploads bucket to creatives database.

    Import files that were uploaded via AI Agent into the creatives
    management system. Files must belong to the current user's folder.
    """
    service = CreativeService(db)

    results = []
    synced_count = 0
    failed_count = 0

    for file_key in data.file_keys:
        result = await service.sync_file_from_bucket(
            user_id=current_user.id,
            file_key=file_key,
        )

        results.append(
            BucketSyncResult(
                file_key=file_key,
                success=result["success"],
                creative_id=result.get("creative_id"),
                error=result.get("error"),
            )
        )

        if result["success"]:
            synced_count += 1
        else:
            failed_count += 1

    # Commit all successful syncs
    if synced_count > 0:
        await db.commit()

    logger.info(
        f"Synced {synced_count} files for user {current_user.id}, "
        f"{failed_count} failed"
    )

    return BucketSyncResponse(
        synced_count=synced_count,
        failed_count=failed_count,
        results=results,
    )
