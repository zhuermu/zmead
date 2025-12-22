"""Media API endpoints for signed URL generation.

This module provides endpoints for accessing S3 media files
through signed URLs for secure, time-limited access.

Requirements: 视频/图片使用签名URL访问，不暴露存储桶公开访问
"""

from typing import Any

import structlog
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.core.config import get_settings
from app.services.s3_client import S3Error, get_s3_client

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/media", tags=["media"])


class SignedUrlRequest(BaseModel):
    """Request body for signed URL generation."""

    object_name: str
    expiration_minutes: int | None = None


class SignedUrlResponse(BaseModel):
    """Response with signed URL."""

    signed_url: str
    expires_in_minutes: int
    object_name: str


@router.post("/signed-url", response_model=SignedUrlResponse)
async def get_signed_url(request: SignedUrlRequest) -> dict[str, Any]:
    """Generate a signed URL for accessing an S3 object.

    Args:
        request: Request with object_name and optional expiration

    Returns:
        SignedUrlResponse with the signed URL

    Raises:
        HTTPException: If signed URL generation fails
    """
    settings = get_settings()
    expiration = request.expiration_minutes or 60  # Default 1 hour

    log = logger.bind(
        object_name=request.object_name,
        expiration_minutes=expiration,
    )
    log.info("signed_url_request")

    try:
        s3_client = get_s3_client()
        signed_url = s3_client.generate_presigned_url(
            object_name=request.object_name,
            expiration=expiration * 60,  # Convert minutes to seconds
        )

        log.info("signed_url_generated")

        return {
            "signed_url": signed_url,
            "expires_in_minutes": expiration,
            "object_name": request.object_name,
        }

    except S3Error as e:
        log.error("signed_url_error", error=str(e), code=e.code)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate signed URL: {e.message}",
        )

    except Exception as e:
        log.error("signed_url_unexpected_error", error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Internal server error",
        )


@router.get("/signed-url/{object_path:path}", response_model=SignedUrlResponse)
async def get_signed_url_by_path(
    object_path: str,
    expiration: int = Query(default=60, ge=1, le=1440, description="Expiration in minutes"),
) -> dict[str, Any]:
    """Generate a signed URL for an S3 object by path.

    Args:
        object_path: Full object path in the bucket
        expiration: URL expiration time in minutes (1-1440)

    Returns:
        SignedUrlResponse with the signed URL

    Raises:
        HTTPException: If signed URL generation fails
    """
    log = logger.bind(
        object_path=object_path,
        expiration_minutes=expiration,
    )
    log.info("signed_url_request_by_path")

    try:
        s3_client = get_s3_client()
        signed_url = s3_client.generate_presigned_url(
            object_name=object_path,
            expiration=expiration * 60,  # Convert minutes to seconds
        )

        log.info("signed_url_generated")

        return {
            "signed_url": signed_url,
            "expires_in_minutes": expiration,
            "object_name": object_path,
        }

    except S3Error as e:
        log.error("signed_url_error", error=str(e), code=e.code)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate signed URL: {e.message}",
        )

    except Exception as e:
        log.error("signed_url_unexpected_error", error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Internal server error",
        )
