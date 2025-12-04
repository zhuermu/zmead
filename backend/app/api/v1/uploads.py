"""File upload API endpoints."""

import uuid
from typing import Any

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from pydantic import BaseModel

from app.api.deps import CurrentUser
from app.core.storage import get_gcs_client

router = APIRouter(prefix="/uploads", tags=["uploads"])


class UploadedFileResponse(BaseModel):
    """Uploaded file response model."""

    id: str
    filename: str
    contentType: str
    size: int
    s3Url: str
    cdnUrl: str | None = None


class MultipleUploadResponse(BaseModel):
    """Multiple file upload response."""

    uploaded: list[UploadedFileResponse]
    failed: list[dict[str, str]]


@router.post("", response_model=MultipleUploadResponse)
async def upload_files(
    current_user: CurrentUser,
    files: list[UploadFile] = File(...),
) -> MultipleUploadResponse:
    """
    Upload multiple files to S3.

    Supports images, videos, documents, and other file types.
    Files are stored in user-specific folders for organization.

    Args:
        current_user: Authenticated user
        files: List of files to upload

    Returns:
        Upload results with S3 URLs
    """
    storage = get_gcs_client()
    uploaded = []
    failed = []

    for file in files:
        try:
            # Read file content
            content = await file.read()

            # Generate unique filename
            file_id = str(uuid.uuid4())
            ext = file.filename.split(".")[-1] if "." in file.filename else ""
            object_name = f"chat-attachments/{current_user.id}/{file_id}.{ext}"

            # Upload to GCS
            gcs_url = storage.upload_file(
                key=object_name,
                data=content,
                content_type=file.content_type or "application/octet-stream",
            )
            
            # Get CDN URL
            cdn_url = storage.get_cdn_url(object_name)

            uploaded.append(
                UploadedFileResponse(
                    id=file_id,
                    filename=file.filename,
                    contentType=file.content_type or "application/octet-stream",
                    size=len(content),
                    s3Url=gcs_url,
                    cdnUrl=cdn_url,
                )
            )

        except Exception as e:
            failed.append(
                {
                    "filename": file.filename,
                    "error": str(e),
                }
            )

    if not uploaded and failed:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"All uploads failed: {failed}",
        )

    return MultipleUploadResponse(uploaded=uploaded, failed=failed)
