"""File processing service for chat attachments.

Handles async file operations:
- Upload files to Gemini Files API
- Generate signed URLs for file access
"""

import logging
from typing import Any

from app.core.config import settings
from app.core.gemini_files import gemini_files_service
from app.core.storage import GCSStorage

logger = logging.getLogger(__name__)

# Storage instance
uploads_storage = GCSStorage(settings.gcs_bucket_uploads)


class ProcessedAttachment:
    """Processed attachment result."""

    def __init__(
        self,
        file_id: str,
        filename: str,
        content_type: str,
        size: int,
        permanent_key: str,
        permanent_url: str,
        cdn_url: str,
        gemini_file_uri: str | None = None,
        gemini_file_name: str | None = None,
    ):
        self.file_id = file_id
        self.filename = filename
        self.content_type = content_type
        self.size = size
        self.permanent_key = permanent_key
        self.permanent_url = permanent_url
        self.cdn_url = cdn_url
        self.gemini_file_uri = gemini_file_uri
        self.gemini_file_name = gemini_file_name

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "fileId": self.file_id,
            "filename": self.filename,
            "contentType": self.content_type,
            "size": self.size,
            "permanentKey": self.permanent_key,
            "permanentUrl": self.permanent_url,
            "cdnUrl": self.cdn_url,
            "geminiFileUri": self.gemini_file_uri,
            "geminiFileName": self.gemini_file_name,
        }


async def process_attachment(
    gcs_path: str,
    file_id: str,
    user_id: str,
    filename: str,
) -> ProcessedAttachment | None:
    """
    Process a file attachment that's already in permanent storage.

    Steps:
    1. Download file from storage
    2. Upload to Gemini Files API
    3. Generate signed URLs
    4. Return processed attachment info

    Args:
        gcs_path: GCS file path (e.g., "{user_id}/chat-attachments/{session_id}/{file_id}.ext")
        file_id: Unique file ID
        user_id: User ID (for permission check)
        filename: Original filename

    Returns:
        ProcessedAttachment if successful, None if failed
    """
    try:
        # Verify file belongs to user
        if not gcs_path.startswith(f"{user_id}/"):
            logger.error(
                f"Permission denied: file {gcs_path} does not belong to user {user_id}"
            )
            return None

        # Check if file exists
        if not uploads_storage.file_exists(gcs_path):
            logger.error(f"File not found: {gcs_path}")
            return None

        # Download from storage
        file_blob = uploads_storage.bucket.blob(gcs_path)
        file_data = file_blob.download_as_bytes()
        content_type = file_blob.content_type or "application/octet-stream"
        file_size = len(file_data)

        # Upload to Gemini Files API
        gemini_file_uri = None
        gemini_file_name = None

        gemini_result = gemini_files_service.upload_file(
            data=file_data,
            mime_type=content_type,
            display_name=filename,
        )

        if gemini_result:
            gemini_file_uri = gemini_result.get("uri")
            gemini_file_name = gemini_result.get("name")
            logger.info(
                f"File uploaded to Gemini: {filename} -> {gemini_file_name}"
            )
        else:
            logger.warning(f"Failed to upload file to Gemini: {filename}")

        # Generate signed URL (valid for 1 hour)
        permanent_url = uploads_storage.generate_presigned_download_url(
            key=gcs_path,
            expires_in=3600,
        )

        # Get CDN URL
        cdn_url = uploads_storage.get_cdn_url(gcs_path)

        return ProcessedAttachment(
            file_id=file_id,
            filename=filename,
            content_type=content_type,
            size=file_size,
            permanent_key=gcs_path,
            permanent_url=permanent_url,
            cdn_url=cdn_url,
            gemini_file_uri=gemini_file_uri,
            gemini_file_name=gemini_file_name,
        )

    except Exception as e:
        logger.error(f"Error processing attachment {gcs_path}: {e}", exc_info=True)
        return None


async def process_attachments(
    attachments: list[dict[str, Any]],
    user_id: str,
) -> list[ProcessedAttachment]:
    """
    Process multiple file attachments.

    Args:
        attachments: List of attachment dicts with gcsPath, fileId, filename
        user_id: User ID for permission check

    Returns:
        List of successfully processed attachments
    """
    processed = []

    for attachment in attachments:
        gcs_path = attachment.get("gcsPath")
        file_id = attachment.get("fileId")
        filename = attachment.get("filename")

        if not gcs_path or not file_id or not filename:
            logger.warning(f"Invalid attachment: {attachment}")
            continue

        result = await process_attachment(
            gcs_path=gcs_path,
            file_id=file_id,
            user_id=user_id,
            filename=filename,
        )

        if result:
            processed.append(result)
            logger.info(
                f"Successfully processed attachment: {filename} ({file_id})"
            )
        else:
            logger.error(f"Failed to process attachment: {filename} ({file_id})")

    return processed


async def process_temp_attachments(
    temp_files: list[dict[str, Any]],
    user_id: str,
) -> list[ProcessedAttachment]:
    """
    Process legacy temporary file attachments (DEPRECATED).

    Args:
        temp_files: List of temp file dicts with fileKey, fileId, filename, contentType, size
        user_id: User ID for permission check

    Returns:
        List of successfully processed attachments
    """
    processed = []

    for temp_file in temp_files:
        file_key = temp_file.get("fileKey")
        file_id = temp_file.get("fileId")
        filename = temp_file.get("filename")

        if not file_key or not file_id or not filename:
            logger.warning(f"Invalid temp attachment: {temp_file}")
            continue

        # Use fileKey as gcs_path for legacy format
        result = await process_attachment(
            gcs_path=file_key,
            file_id=file_id,
            user_id=user_id,
            filename=filename,
        )

        if result:
            processed.append(result)
            logger.info(
                f"Successfully processed temp attachment: {filename} ({file_id})"
            )
        else:
            logger.error(f"Failed to process temp attachment: {filename} ({file_id})")

    return processed
