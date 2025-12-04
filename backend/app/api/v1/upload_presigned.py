"""Presigned URL generation for direct upload to GCS."""

import uuid
from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.api.deps import CurrentUser
from app.core.config import settings
from app.core.storage import GCSStorage

router = APIRouter(prefix="/uploads/presigned", tags=["uploads"])

# Temporary uploads storage (36 hour expiry)
temp_uploads_storage = GCSStorage(settings.gcs_bucket_uploads_temp)
# Permanent uploads storage
perm_uploads_storage = GCSStorage(settings.gcs_bucket_uploads)


class PresignedUploadRequest(BaseModel):
    """Request for presigned upload URL."""

    filename: str
    contentType: str
    size: int = Field(gt=0, le=50 * 1024 * 1024)  # Max 50MB


class PresignedUploadResponse(BaseModel):
    """Presigned upload URL response."""

    uploadUrl: str  # Presigned URL for PUT request
    fileKey: str  # GCS object key
    fileId: str  # UUID for this file
    expiresAt: str  # ISO 8601 timestamp
    cdnUrl: str  # CDN URL for preview (after upload)


class ConfirmUploadRequest(BaseModel):
    """Confirm upload and make permanent."""

    fileKey: str
    fileId: str


class ConfirmUploadResponse(BaseModel):
    """Upload confirmation response."""

    fileKey: str
    fileId: str
    permanentUrl: str
    cdnUrl: str
    geminiFileUri: str | None = None
    geminiFileName: str | None = None


@router.post("/generate", response_model=PresignedUploadResponse)
async def generate_presigned_url(
    current_user: CurrentUser,
    request: PresignedUploadRequest,
) -> PresignedUploadResponse:
    """
    Generate presigned URL for direct upload to GCS.

    The file will be stored temporarily (36 hours) until confirmed.

    Args:
        current_user: Authenticated user
        request: Upload request with file metadata

    Returns:
        Presigned URL and file metadata
    """
    # Generate unique file ID
    file_id = str(uuid.uuid4())

    # Extract file extension
    ext = ""
    if "." in request.filename:
        ext = "." + request.filename.split(".")[-1]

    # Generate object key: temp/{user_id}/{file_id}.ext
    object_key = f"temp/{current_user.id}/{file_id}{ext}"

    # Generate presigned URL (valid for 1 hour)
    presigned_data = temp_uploads_storage.generate_presigned_upload_url(
        key=object_key,
        content_type=request.contentType,
        expires_in=3600,  # 1 hour to complete upload
    )

    # Calculate expiry time
    expires_at = datetime.utcnow() + timedelta(seconds=3600)

    # Get CDN URL for preview (will be valid after upload completes)
    cdn_url = temp_uploads_storage.get_cdn_url(object_key)

    return PresignedUploadResponse(
        uploadUrl=presigned_data["url"],
        fileKey=object_key,
        fileId=file_id,
        expiresAt=expires_at.isoformat() + "Z",
        cdnUrl=cdn_url,
    )


@router.post("/confirm", response_model=ConfirmUploadResponse)
async def confirm_upload(
    current_user: CurrentUser,
    request: ConfirmUploadRequest,
) -> ConfirmUploadResponse:
    """
    Confirm upload and move file from temporary to permanent storage.

    Also uploads to Gemini Files API for AI processing.

    Args:
        current_user: Authenticated user
        request: Confirmation request with file key

    Returns:
        Permanent file URLs and Gemini file info
    """
    from app.core.gemini_files import gemini_files_service

    # Verify file exists in temp storage
    if not temp_uploads_storage.file_exists(request.fileKey):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Temporary file not found or expired",
        )

    # Verify file belongs to current user
    if not request.fileKey.startswith(f"temp/{current_user.id}/"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    # Download from temp storage
    temp_blob = temp_uploads_storage.bucket.blob(request.fileKey)
    file_data = temp_blob.download_as_bytes()
    content_type = temp_blob.content_type or "application/octet-stream"

    # Generate permanent key
    ext = ""
    if "." in request.fileKey:
        ext = "." + request.fileKey.split(".")[-1]
    perm_key = f"chat-attachments/{current_user.id}/{request.fileId}{ext}"

    # Upload to permanent storage
    perm_url = perm_uploads_storage.upload_file(
        key=perm_key,
        data=file_data,
        content_type=content_type,
    )

    # Get CDN URL
    cdn_url = perm_uploads_storage.get_cdn_url(perm_key)

    # Upload to Gemini Files API
    gemini_file_uri = None
    gemini_file_name = None
    filename = request.fileKey.split("/")[-1]  # Extract filename

    gemini_result = gemini_files_service.upload_file(
        data=file_data,
        mime_type=content_type,
        display_name=filename,
    )

    if gemini_result:
        gemini_file_uri = gemini_result.get("uri")
        gemini_file_name = gemini_result.get("name")

    # Delete temporary file
    try:
        temp_blob.delete()
    except Exception:
        pass  # Ignore deletion errors, temp files will expire anyway

    return ConfirmUploadResponse(
        fileKey=perm_key,
        fileId=request.fileId,
        permanentUrl=perm_url,
        cdnUrl=cdn_url,
        geminiFileUri=gemini_file_uri,
        geminiFileName=gemini_file_name,
    )
