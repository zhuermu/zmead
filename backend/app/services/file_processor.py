"""File processing service for chat attachments.

Handles async file operations:
- Move files from temp to permanent storage
- Upload files to Gemini Files API
"""

import logging
from typing import Any

from app.core.config import settings
from app.core.gemini_files import gemini_files_service
from app.core.storage import GCSStorage

logger = logging.getLogger(__name__)

# Storage instances
temp_uploads_storage = GCSStorage(settings.gcs_bucket_uploads_temp)
perm_uploads_storage = GCSStorage(settings.gcs_bucket_uploads)


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


async def process_temp_attachment(
    file_key: str,
    file_id: str,
    user_id: str,
    filename: str | None = None,
) -> ProcessedAttachment | None:
    """
    Process a temporary file attachment.

    Steps:
    1. Download file from temp storage
    2. Upload to permanent storage
    3. Upload to Gemini Files API
    4. Delete temp file
    5. Return processed attachment info

    Args:
        file_key: Temporary file key in GCS
        file_id: Unique file ID
        user_id: User ID (for permission check)
        filename: Original filename (optional, extracted from file_key if not provided)

    Returns:
        ProcessedAttachment if successful, None if failed
    """
    try:
        # Verify file belongs to user
        if not file_key.startswith(f"temp/{user_id}/"):
            logger.error(
                f"Permission denied: file {file_key} does not belong to user {user_id}"
            )
            return None

        # Check if file exists
        if not temp_uploads_storage.file_exists(file_key):
            logger.error(f"Temp file not found: {file_key}")
            return None

        # Download from temp storage
        temp_blob = temp_uploads_storage.bucket.blob(file_key)
        file_data = temp_blob.download_as_bytes()
        content_type = temp_blob.content_type or "application/octet-stream"
        file_size = len(file_data)

        # Extract filename if not provided
        if not filename:
            filename = file_key.split("/")[-1]

        # Generate permanent key
        ext = ""
        if "." in filename:
            ext = "." + filename.split(".")[-1]
        perm_key = f"chat-attachments/{user_id}/{file_id}{ext}"

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

        # Delete temporary file
        try:
            temp_blob.delete()
            logger.info(f"Deleted temp file: {file_key}")
        except Exception as e:
            logger.warning(f"Failed to delete temp file {file_key}: {e}")

        return ProcessedAttachment(
            file_id=file_id,
            filename=filename,
            content_type=content_type,
            size=file_size,
            permanent_key=perm_key,
            permanent_url=perm_url,
            cdn_url=cdn_url,
            gemini_file_uri=gemini_file_uri,
            gemini_file_name=gemini_file_name,
        )

    except Exception as e:
        logger.error(f"Error processing temp attachment {file_key}: {e}", exc_info=True)
        return None


async def process_temp_attachments(
    temp_attachments: list[dict[str, Any]],
    user_id: str,
) -> list[ProcessedAttachment]:
    """
    Process multiple temporary attachments.

    Args:
        temp_attachments: List of temp attachment dicts with fileKey, fileId, filename
        user_id: User ID for permission check

    Returns:
        List of successfully processed attachments
    """
    processed = []

    for temp_file in temp_attachments:
        file_key = temp_file.get("fileKey")
        file_id = temp_file.get("fileId")
        filename = temp_file.get("filename")

        if not file_key or not file_id:
            logger.warning(f"Invalid temp attachment: {temp_file}")
            continue

        result = await process_temp_attachment(
            file_key=file_key,
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
