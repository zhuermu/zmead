"""Media API endpoints for signed URL generation.

This module provides endpoints for generating signed URLs to access
media files (images/videos) stored in S3 or GCS.

Requirements:
- Images/videos stored in S3 or GCS, not base64 in database
- Frontend fetches signed URLs for temporary access
- Signed URLs expire after 1 hour for security
"""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.core.storage import (
    creatives_storage,
    is_gcs_available,
    s3_uploads_storage,
    s3_creatives_storage,
)

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
    """Get a signed URL for accessing a storage object (S3 or GCS).

    This endpoint generates a temporary signed URL that allows
    access to media files stored in S3 or Google Cloud Storage.

    Supports both S3 and GCS storage backends. Tries S3 first (current default),
    then falls back to GCS if S3 is not available.

    Args:
        object_name: Full path of the object in storage bucket

    Returns:
        SignedUrlResponse with the signed URL

    Raises:
        HTTPException: If URL generation fails
    """
    expiration_seconds = 3600  # 1 hour expiration
    expiration_minutes = 60

    # Try S3 first (current storage backend)
    try:
        # Determine which S3 bucket based on object path
        storage = s3_uploads_storage  # Default: user uploads bucket

        if object_name.startswith("creatives/"):
            storage = s3_creatives_storage

        signed_url = storage.generate_presigned_download_url(
            key=object_name,
            expires_in=expiration_seconds,
        )

        if signed_url:
            return SignedUrlResponse(
                signed_url=signed_url,
                object_name=object_name,
                expires_in_minutes=expiration_minutes,
            )
    except Exception as e:
        # Log S3 error but continue to try GCS
        import logging
        logging.warning(f"S3 signed URL generation failed: {e}, trying GCS fallback")

    # Fallback to GCS if S3 fails
    if is_gcs_available():
        try:
            signed_url = creatives_storage.generate_presigned_download_url(
                key=object_name,
                expires_in=expiration_seconds,
            )

            if signed_url:
                return SignedUrlResponse(
                    signed_url=signed_url,
                    object_name=object_name,
                    expires_in_minutes=expiration_minutes,
                )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to generate signed URL (GCS): {str(e)}",
            )

    # Both S3 and GCS failed
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Storage service is not available (neither S3 nor GCS)",
    )
