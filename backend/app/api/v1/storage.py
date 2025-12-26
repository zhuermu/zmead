"""Storage API endpoints for on-demand presigned URL generation."""

import logging
from typing import Literal

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.api.deps import CurrentUser
from app.core.storage import (
    creatives_storage,
    exports_storage,
    landing_pages_storage,
    uploads_storage,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/storage", tags=["storage"])


class PresignedUrlRequest(BaseModel):
    """Request for generating presigned URL."""

    path: str = Field(..., description="Storage path (S3/GCS key)")
    storage_type: Literal["creatives", "landing_pages", "exports", "uploads"] = Field(
        default="creatives",
        description="Storage bucket type",
    )
    expires_in: int = Field(
        default=3600,
        ge=60,
        le=604800,  # Max 7 days
        description="URL expiration time in seconds (60s to 7 days)",
    )


class PresignedUrlResponse(BaseModel):
    """Response with presigned URL."""

    url: str = Field(..., description="Presigned download URL")
    expires_in: int = Field(..., description="URL expiration time in seconds")


@router.post("/presigned-url", response_model=PresignedUrlResponse)
async def generate_presigned_download_url(
    current_user: CurrentUser,
    request: PresignedUrlRequest,
) -> PresignedUrlResponse:
    """
    Generate presigned download URL for a storage path.

    This endpoint generates temporary signed URLs for accessing files stored in S3/GCS.
    URLs expire after the specified time and must be regenerated for continued access.

    Security:
    - Path must belong to the authenticated user
    - Validates user_id prefix in path

    Args:
        current_user: Authenticated user
        request: Presigned URL request with path and settings

    Returns:
        Presigned download URL with expiration time

    Raises:
        HTTPException 400: Invalid path format
        HTTPException 403: Access denied (path doesn't belong to user)
        HTTPException 404: File not found
        HTTPException 500: Failed to generate URL
    """
    # Validate path format
    if not request.path or request.path.startswith("/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid path format. Path should not start with '/'",
        )

    # Get storage backend
    storage_backends = {
        "creatives": creatives_storage,
        "landing_pages": landing_pages_storage,
        "exports": exports_storage,
        "uploads": uploads_storage,
    }
    storage = storage_backends[request.storage_type]

    # Security: Verify path belongs to current user
    # Expected path format: {user_id}/... or users/{user_id}/...
    user_id_str = str(current_user.id)
    is_valid_path = (
        request.path.startswith(f"{user_id_str}/")
        or request.path.startswith(f"users/{user_id_str}/")
        or f"/{user_id_str}/" in request.path
    )

    if not is_valid_path:
        logger.warning(
            f"Access denied: User {current_user.id} attempted to access path: {request.path}"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Path does not belong to your account.",
        )

    # Check if file exists
    if not storage.file_exists(request.path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File not found: {request.path}",
        )

    # Generate presigned URL
    try:
        presigned_url = storage.generate_presigned_download_url(
            key=request.path,
            expires_in=request.expires_in,
        )

        if not presigned_url:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate presigned URL",
            )

        logger.info(
            f"Generated presigned URL for user {current_user.id}, "
            f"path: {request.path}, expires_in: {request.expires_in}s"
        )

        return PresignedUrlResponse(
            url=presigned_url,
            expires_in=request.expires_in,
        )

    except Exception as e:
        logger.error(f"Failed to generate presigned URL: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate presigned URL",
        )
