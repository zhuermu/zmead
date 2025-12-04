"""Media API endpoints for GCS signed URL generation.

This module provides endpoints for generating signed URLs to access
media files (images/videos) stored in Google Cloud Storage.

Requirements:
- Images/videos stored in GCS, not base64 in database
- Frontend fetches signed URLs for temporary access
- Signed URLs expire after 1 hour for security
"""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.core.storage import creatives_storage, is_gcs_available

router = APIRouter()


class SignedUrlResponse(BaseModel):
    """Response with signed URL for media access."""
    signed_url: str
    object_name: str
    expires_in_minutes: int


@router.get("/signed-url/{object_name:path}", response_model=SignedUrlResponse)
async def get_signed_url(
    object_name: str,
) -> SignedUrlResponse:
    """Get a signed URL for accessing a GCS object.

    This endpoint generates a temporary signed URL that allows
    access to media files stored in Google Cloud Storage.

    Args:
        object_name: Full path of the object in GCS bucket

    Returns:
        SignedUrlResponse with the signed URL

    Raises:
        HTTPException: If URL generation fails
    """
    if not is_gcs_available():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="GCS storage is not available",
        )

    try:
        expiration_seconds = 3600  # 1 hour expiration
        expiration_minutes = 60

        signed_url = creatives_storage.generate_presigned_download_url(
            key=object_name,
            expires_in=expiration_seconds,
        )

        if not signed_url:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate signed URL",
            )

        return SignedUrlResponse(
            signed_url=signed_url,
            object_name=object_name,
            expires_in_minutes=expiration_minutes,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error: {str(e)}",
        )
