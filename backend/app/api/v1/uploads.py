"""File upload API endpoints."""

import uuid
from typing import Any

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from pydantic import BaseModel

from app.api.deps import CurrentUser
from app.core.storage import creatives_storage
from app.core.config import settings
from app.core.gemini_files import gemini_files_service

router = APIRouter(prefix="/uploads", tags=["uploads"])


class UploadedFileResponse(BaseModel):
    """Uploaded file response model."""

    id: str
    filename: str
    contentType: str
    size: int
    s3Url: str  # GCS URL (gs://bucket/path)
    cdnUrl: str | None = None  # CDN URL for viewing
    geminiFileUri: str | None = None  # Gemini file URI for AI processing
    geminiFileName: str | None = None  # Gemini file name


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
        Upload results with GCS URLs and Gemini file URIs
    """
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

            # Upload to S3 creatives bucket for persistent storage
            s3_url = creatives_storage.upload_file(
                key=object_name,
                data=content,
                content_type=file.content_type or "application/octet-stream",
            )

            # Get CDN URL for viewing
            cdn_url = creatives_storage.get_cdn_url(object_name)

            # Upload to Gemini Files API for AI processing
            gemini_file_uri = None
            gemini_file_name = None
            gemini_result = gemini_files_service.upload_file(
                data=content,
                mime_type=file.content_type or "application/octet-stream",
                display_name=file.filename,
            )
            if gemini_result:
                gemini_file_uri = gemini_result.get("uri")
                gemini_file_name = gemini_result.get("name")

            uploaded.append(
                UploadedFileResponse(
                    id=file_id,
                    filename=file.filename,
                    contentType=file.content_type or "application/octet-stream",
                    size=len(content),
                    s3Url=s3_url,
                    cdnUrl=cdn_url,
                    geminiFileUri=gemini_file_uri,
                    geminiFileName=gemini_file_name,
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
