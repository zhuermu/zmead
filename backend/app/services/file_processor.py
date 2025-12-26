"""File processing service for chat attachments.

Handles async file operations:
- Upload files to Gemini Files API
- Generate signed URLs for file access
"""

import logging
from typing import Any

from app.core.config import settings
from app.core.gemini_files import gemini_files_service
from app.core.storage import S3Storage

logger = logging.getLogger(__name__)

# Storage instance - use creatives bucket for all file uploads
uploads_storage = S3Storage(settings.s3_bucket_creatives)


class ProcessedAttachment:
    """Processed attachment result.

    Note: Only stores storage path, not presigned URLs.
    URLs should be generated on-demand via /api/v1/storage/presigned-url endpoint.
    """

    def __init__(
        self,
        file_id: str,
        filename: str,
        content_type: str,
        size: int,
        storage_path: str,
        gemini_file_uri: str | None = None,
        gemini_file_name: str | None = None,
    ):
        self.file_id = file_id
        self.filename = filename
        self.content_type = content_type
        self.size = size
        self.storage_path = storage_path  # S3 object key/path
        self.gemini_file_uri = gemini_file_uri
        self.gemini_file_name = gemini_file_name

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "fileId": self.file_id,
            "filename": self.filename,
            "contentType": self.content_type,
            "size": self.size,
            "storagePath": self.storage_path,
            "geminiFileUri": self.gemini_file_uri,
            "geminiFileName": self.gemini_file_name,
        }


async def process_attachment(
    storage_path: str,
    file_id: str,
    user_id: str,
    filename: str,
) -> ProcessedAttachment | None:
    """
    Process a file attachment that's already in permanent storage.

    Steps:
    1. Verify file exists in S3
    2. Get file metadata
    3. Upload to Gemini Files API (for AI processing)
    4. Return processed attachment info (path only, no URLs)

    Note: Presigned URLs should be generated on-demand via API endpoint.

    Args:
        storage_path: S3 file path (e.g., "{user_id}/chat-attachments/{session_id}/{file_id}.ext")
        file_id: Unique file ID
        user_id: User ID (for permission check)
        filename: Original filename

    Returns:
        ProcessedAttachment if successful, None if failed
    """
    try:
        # Verify file belongs to user
        if not storage_path.startswith(f"{user_id}/"):
            logger.error(
                f"Permission denied: file {storage_path} does not belong to user {user_id}"
            )
            return None

        # Check if file exists
        if not uploads_storage.file_exists(storage_path):
            logger.error(f"File not found: {storage_path}")
            return None

        # Get file info from S3
        file_info = uploads_storage.get_file_info(storage_path)
        if not file_info:
            logger.error(f"Failed to get file info: {storage_path}")
            return None

        content_type = file_info.get("content_type", "application/octet-stream")
        file_size = file_info.get("size", 0)

        # Download file data for Gemini upload
        file_data = uploads_storage.download_file(storage_path)
        if not file_data:
            logger.error(f"Failed to download file: {storage_path}")
            return None

        # Upload to Gemini Files API (for AI processing)
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

        return ProcessedAttachment(
            file_id=file_id,
            filename=filename,
            content_type=content_type,
            size=file_size,
            storage_path=storage_path,
            gemini_file_uri=gemini_file_uri,
            gemini_file_name=gemini_file_name,
        )

    except Exception as e:
        logger.error(f"Error processing attachment {storage_path}: {e}", exc_info=True)
        return None


async def process_attachments(
    attachments: list[dict[str, Any]],
    user_id: str,
) -> list[ProcessedAttachment]:
    """
    Process multiple file attachments.

    Args:
        attachments: List of attachment dicts with gcsPath/storagePath, fileId, filename
        user_id: User ID for permission check

    Returns:
        List of successfully processed attachments
    """
    processed = []

    for attachment in attachments:
        # Support both old (gcsPath) and new (storagePath) field names
        storage_path = attachment.get("storagePath") or attachment.get("gcsPath")
        file_id = attachment.get("fileId")
        filename = attachment.get("filename")

        if not storage_path or not file_id or not filename:
            logger.warning(f"Invalid attachment: {attachment}")
            continue

        result = await process_attachment(
            storage_path=storage_path,
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

        # Use fileKey as storage_path for legacy format
        result = await process_attachment(
            storage_path=file_key,
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
