"""Gemini Files API utilities for file upload and management."""

import logging
from functools import lru_cache
from typing import Any

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Global flag to track if Gemini is available
_gemini_available: bool | None = None

# GCS client singleton
_gcs_client = None


def get_gcs_client():
    """Get GCS client instance (lazy initialization)."""
    global _gcs_client

    if _gcs_client is not None:
        return _gcs_client

    try:
        from google.cloud import storage

        if settings.gcs_credentials_path:
            _gcs_client = storage.Client.from_service_account_json(settings.gcs_credentials_path)
        elif settings.gcs_project_id:
            _gcs_client = storage.Client(project=settings.gcs_project_id)
        else:
            # Try default credentials
            _gcs_client = storage.Client()

        logger.info("GCS client initialized successfully")
        return _gcs_client
    except Exception as e:
        logger.warning(f"GCS client initialization failed: {e}")
        return None


@lru_cache(maxsize=1)
def get_gemini_client():
    """Get Gemini client instance (lazy initialization).

    Returns None if API key is not available.
    """
    global _gemini_available

    try:
        import google.generativeai as genai

        if not settings.gemini_api_key:
            logger.warning("GEMINI_API_KEY not configured. Gemini file upload will be disabled.")
            _gemini_available = False
            return None

        genai.configure(api_key=settings.gemini_api_key)
        _gemini_available = True
        return genai
    except Exception as e:
        logger.warning(f"Gemini client initialization failed: {e}. Gemini features will be disabled.")
        _gemini_available = False
        return None


def is_gemini_available() -> bool:
    """Check if Gemini is available."""
    if _gemini_available is None:
        get_gemini_client()  # Trigger lazy initialization
    return _gemini_available or False


class GeminiFilesService:
    """Gemini Files API service for uploading files to Gemini."""

    def __init__(self) -> None:
        self._client = None

    @property
    def client(self):
        """Lazy initialization of Gemini client."""
        if self._client is None:
            self._client = get_gemini_client()
        return self._client

    def _check_available(self) -> bool:
        """Check if Gemini is available."""
        if not is_gemini_available():
            logger.warning("Gemini operation skipped: API not available")
            return False
        return True

    def download_from_gcs(self, gcs_uri: str) -> bytes | None:
        """
        Download file from GCS.

        Args:
            gcs_uri: GCS URI in format gs://bucket/path/to/file

        Returns:
            File content as bytes, or None if download fails
        """
        try:
            # Parse GCS URI
            if not gcs_uri.startswith("gs://"):
                logger.error(f"Invalid GCS URI: {gcs_uri}")
                return None

            uri_parts = gcs_uri[5:].split("/", 1)
            if len(uri_parts) != 2:
                logger.error(f"Invalid GCS URI format: {gcs_uri}")
                return None

            bucket_name, blob_path = uri_parts

            # Get GCS client
            gcs_client = get_gcs_client()
            if not gcs_client:
                logger.error("GCS client not available")
                return None

            # Download file
            bucket = gcs_client.bucket(bucket_name)
            blob = bucket.blob(blob_path)

            if not blob.exists():
                logger.error(f"GCS file not found: {gcs_uri}")
                return None

            data = blob.download_as_bytes()
            logger.info(f"Downloaded {len(data)} bytes from GCS: {gcs_uri}")
            return data

        except Exception as e:
            logger.error(f"Failed to download from GCS: {e}")
            return None

    def upload_from_gcs(
        self,
        gcs_uri: str,
        mime_type: str,
        display_name: str | None = None,
    ) -> dict[str, Any] | None:
        """
        Download file from GCS and upload to Gemini Files API.

        Args:
            gcs_uri: GCS URI in format gs://bucket/path/to/file
            mime_type: MIME type of the file
            display_name: Optional display name for the file

        Returns:
            Dictionary with Gemini file info or None if upload fails
        """
        # Download from GCS
        data = self.download_from_gcs(gcs_uri)
        if not data:
            return None

        # Upload to Gemini
        return self.upload_file(data, mime_type, display_name)

    def upload_file(
        self,
        data: bytes,
        mime_type: str,
        display_name: str | None = None,
    ) -> dict[str, Any] | None:
        """
        Upload file to Gemini Files API.

        Args:
            data: File content as bytes
            mime_type: MIME type of the file
            display_name: Optional display name for the file

        Returns:
            Dictionary with file info including:
            - name: The Gemini file name (used as URI in prompts)
            - uri: The file URI for use in prompts
            - display_name: Display name
            - mime_type: MIME type
            - size_bytes: File size
            Returns None if upload fails or Gemini is not available
        """
        if not self._check_available():
            return None

        try:
            import tempfile
            import os

            # Gemini Files API requires a file path, so write to temp file
            with tempfile.NamedTemporaryFile(delete=False, suffix=self._get_extension(mime_type)) as tmp_file:
                tmp_file.write(data)
                tmp_path = tmp_file.name

            try:
                # Upload file to Gemini
                upload_response = self.client.upload_file(
                    path=tmp_path,
                    mime_type=mime_type,
                    display_name=display_name,
                )

                logger.info(f"File uploaded to Gemini: {upload_response.name}")

                return {
                    "name": upload_response.name,
                    "uri": upload_response.uri,
                    "display_name": upload_response.display_name or display_name or "",
                    "mime_type": upload_response.mime_type,
                    "size_bytes": upload_response.size_bytes,
                    "state": upload_response.state.name if hasattr(upload_response, 'state') else "ACTIVE",
                }
            finally:
                # Clean up temp file
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)

        except Exception as e:
            logger.error(f"Failed to upload file to Gemini: {e}")
            return None

    def _get_extension(self, mime_type: str) -> str:
        """Get file extension from MIME type."""
        mime_to_ext = {
            "image/jpeg": ".jpg",
            "image/png": ".png",
            "image/gif": ".gif",
            "image/webp": ".webp",
            "video/mp4": ".mp4",
            "video/quicktime": ".mov",
            "video/x-msvideo": ".avi",
            "application/pdf": ".pdf",
            "text/plain": ".txt",
            "text/html": ".html",
            "application/json": ".json",
        }
        return mime_to_ext.get(mime_type, "")

    def delete_file(self, file_name: str) -> bool:
        """
        Delete file from Gemini Files API.

        Args:
            file_name: The Gemini file name (from upload response)

        Returns:
            True if deletion succeeded, False otherwise
        """
        if not self._check_available():
            return False

        try:
            self.client.delete_file(name=file_name)
            logger.info(f"File deleted from Gemini: {file_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete file from Gemini: {e}")
            return False

    def get_file(self, file_name: str) -> dict[str, Any] | None:
        """
        Get file metadata from Gemini Files API.

        Args:
            file_name: The Gemini file name

        Returns:
            Dictionary with file info or None if not found
        """
        if not self._check_available():
            return None

        try:
            file_info = self.client.get_file(name=file_name)
            return {
                "name": file_info.name,
                "uri": file_info.uri,
                "display_name": file_info.display_name,
                "mime_type": file_info.mime_type,
                "size_bytes": file_info.size_bytes,
                "state": file_info.state.name if hasattr(file_info, 'state') else "ACTIVE",
            }
        except Exception as e:
            logger.error(f"Failed to get file from Gemini: {e}")
            return None


# Singleton instance
gemini_files_service = GeminiFilesService()
