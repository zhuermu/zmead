"""Presigned URL generation for direct upload to S3."""

import uuid
from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.api.deps import CurrentUser
from app.core.config import settings
from app.core.storage import S3Storage

router = APIRouter(prefix="/uploads/presigned", tags=["uploads"])

# Permanent uploads storage (S3)
uploads_storage = S3Storage(settings.s3_bucket_uploads)


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


class ChatAttachmentUploadRequest(BaseModel):
    """Request for chat attachment upload."""

    filename: str = Field(..., description="Original filename")
    content_type: str = Field(..., description="MIME type")
    file_size: int = Field(gt=0, le=200 * 1024 * 1024, description="File size in bytes (max 200MB)")
    session_id: str = Field(..., description="Chat session ID")


class ChatAttachmentUploadResponse(BaseModel):
    """Chat attachment upload response."""

    upload_url: str = Field(..., description="Presigned URL for uploading file")
    gcs_path: str = Field(..., description="GCS object path")
    download_url: str = Field(..., description="Signed download URL (valid for 1 hour)")
    expires_in: int = Field(..., description="Upload URL expiration in seconds")
    file_id: str = Field(..., description="Unique file identifier")


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


@router.post("/chat-attachment", response_model=ChatAttachmentUploadResponse)
async def generate_chat_attachment_upload_url(
    current_user: CurrentUser,
    request: ChatAttachmentUploadRequest,
) -> ChatAttachmentUploadResponse:
    """
    Generate presigned URL for chat attachment upload.

    Files are stored permanently in: {user_id}/chat-attachments/{session_id}/{filename}

    Supported file types:
    - Images: PNG, JPG, JPEG, WEBP, HEIC, HEIF (max 20MB)
    - Videos: MP4, MPEG, MOV, AVI, FLV, MPG, WEBM, WMV, 3GPP (max 200MB)
    - Documents: PDF, TXT, HTML, CSS, JS, TS, PY, MD, CSV, XML, RTF (max 50MB)

    Args:
        current_user: Authenticated user
        request: Upload request with file metadata

    Returns:
        Presigned upload URL and download URL

    Raises:
        HTTPException 400: Invalid file type or size
        HTTPException 402: Insufficient credits
    """
    # Validate file type and size limits
    allowed_types = {
        # Images (max 20MB)
        "image/png": 20 * 1024 * 1024,
        "image/jpeg": 20 * 1024 * 1024,
        "image/webp": 20 * 1024 * 1024,
        "image/heic": 20 * 1024 * 1024,
        "image/heif": 20 * 1024 * 1024,
        # Videos (max 200MB)
        "video/mp4": 200 * 1024 * 1024,
        "video/mpeg": 200 * 1024 * 1024,
        "video/quicktime": 200 * 1024 * 1024,  # .mov
        "video/x-msvideo": 200 * 1024 * 1024,  # .avi
        "video/x-flv": 200 * 1024 * 1024,
        "video/webm": 200 * 1024 * 1024,
        "video/x-ms-wmv": 200 * 1024 * 1024,
        "video/3gpp": 200 * 1024 * 1024,
        # Documents (max 50MB)
        "application/pdf": 50 * 1024 * 1024,
        "text/plain": 50 * 1024 * 1024,
        "text/html": 50 * 1024 * 1024,
        "text/css": 50 * 1024 * 1024,
        "application/javascript": 50 * 1024 * 1024,
        "application/typescript": 50 * 1024 * 1024,
        "text/x-python": 50 * 1024 * 1024,
        "text/markdown": 50 * 1024 * 1024,
        "text/csv": 50 * 1024 * 1024,
        "application/xml": 50 * 1024 * 1024,
        "text/rtf": 50 * 1024 * 1024,
    }

    if request.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type: {request.content_type}. Please upload images, videos, or documents.",
        )

    max_size = allowed_types[request.content_type]
    if request.file_size > max_size:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large. Maximum size for {request.content_type} is {max_size / 1024 / 1024}MB",
        )

    # Generate unique file ID
    file_id = str(uuid.uuid4())

    # Extract file extension
    ext = ""
    if "." in request.filename:
        ext = "." + request.filename.split(".")[-1]

    # Generate GCS path: {user_id}/chat-attachments/{session_id}/{file_id}.ext
    gcs_path = f"{current_user.id}/chat-attachments/{request.session_id}/{file_id}{ext}"

    # Generate presigned upload URL (valid for 15 minutes)
    presigned_data = uploads_storage.generate_presigned_upload_url(
        key=gcs_path,
        content_type=request.content_type,
        expires_in=900,  # 15 minutes to complete upload
    )

    # Generate signed download URL (valid for 1 hour)
    download_url = uploads_storage.generate_presigned_download_url(
        key=gcs_path,
        expires_in=3600,  # 1 hour
    )

    return ChatAttachmentUploadResponse(
        upload_url=presigned_data["url"],
        gcs_path=gcs_path,
        download_url=download_url,
        expires_in=900,
        file_id=file_id,
    )


@router.post("/generate", response_model=PresignedUploadResponse)
async def generate_presigned_url(
    current_user: CurrentUser,
    request: PresignedUploadRequest,
) -> PresignedUploadResponse:
    """
    Generate presigned URL for direct upload to GCS.

    DEPRECATED: Use /chat-attachment endpoint for chat attachments.

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

    # Generate object key: uploads/{user_id}/{file_id}.ext
    object_key = f"uploads/{current_user.id}/{file_id}{ext}"

    # Generate presigned URL (valid for 1 hour)
    presigned_data = uploads_storage.generate_presigned_upload_url(
        key=object_key,
        content_type=request.contentType,
        expires_in=3600,  # 1 hour to complete upload
    )

    # Calculate expiry time
    expires_at = datetime.utcnow() + timedelta(seconds=3600)

    # Get CDN URL for preview (will be valid after upload completes)
    cdn_url = uploads_storage.get_cdn_url(object_key)

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
    Confirm upload and get file URLs.

    DEPRECATED: Files are now directly uploaded to permanent storage.
    This endpoint is kept for backward compatibility.

    Args:
        current_user: Authenticated user
        request: Confirmation request with file key

    Returns:
        File URLs and Gemini file info

    Raises:
        HTTPException 404: File not found
        HTTPException 403: Access denied
    """
    from app.core.gemini_files import gemini_files_service

    # Verify file exists in uploads storage
    if not uploads_storage.file_exists(request.fileKey):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found",
        )

    # Verify file belongs to current user
    if not request.fileKey.startswith(f"uploads/{current_user.id}/") and not request.fileKey.startswith(f"{current_user.id}/"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    # Download file
    file_blob = uploads_storage.bucket.blob(request.fileKey)
    file_data = file_blob.download_as_bytes()
    content_type = file_blob.content_type or "application/octet-stream"

    # Get CDN URL
    cdn_url = uploads_storage.get_cdn_url(request.fileKey)

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

    # Generate signed download URL
    perm_url = uploads_storage.generate_presigned_download_url(
        key=request.fileKey,
        expires_in=3600,
    )

    return ConfirmUploadResponse(
        fileKey=request.fileKey,
        fileId=request.fileId,
        permanentUrl=perm_url,
        cdnUrl=cdn_url,
        geminiFileUri=gemini_file_uri,
        geminiFileName=gemini_file_name,
    )
