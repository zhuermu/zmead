"""Google Cloud Storage client for image/video uploads.

Uses the Google Cloud Storage SDK for proper signed URL generation.
Uploads use the JSON API with API key, signed URLs use service account credentials.

Requirements: 生成的图片/视频使用 Google 对象存储保存，通过签名URL访问
"""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import quote

import httpx
import structlog
from google.cloud import storage
from google.oauth2 import service_account

from app.core.config import get_settings

logger = structlog.get_logger(__name__)


class GCSError(Exception):
    """Google Cloud Storage error."""

    def __init__(self, message: str, code: str | None = None, retryable: bool = False):
        self.message = message
        self.code = code
        self.retryable = retryable
        super().__init__(message)


class GCSClient:
    """Client for Google Cloud Storage uploads.

    Uses:
    - GCS JSON API with API key for uploads
    - GCS SDK with service account for signed URLs
    """

    def __init__(
        self,
        bucket_name: str | None = None,
        api_key: str | None = None,
        credentials_path: str | None = None,
    ):
        """Initialize GCS client.

        Args:
            bucket_name: GCS bucket name
            api_key: Google API key (uses Gemini API key by default)
            credentials_path: Path to service account JSON file for signed URLs
        """
        settings = get_settings()
        self.api_key = api_key or settings.gemini_api_key
        self.bucket_name = bucket_name or getattr(settings, 'gcs_bucket_name', 'zmead-creatives')
        self.base_url = "https://storage.googleapis.com"

        # Service account credentials for signed URLs
        self._credentials_path = credentials_path or getattr(
            settings, 'gcs_credentials_path', None
        )
        self._storage_client: storage.Client | None = None
        self._credentials: service_account.Credentials | None = None

    def _generate_object_name(
        self,
        user_id: str,
        filename: str,
        prefix: str = "creatives",
    ) -> str:
        """Generate a unique object name for the upload.

        Args:
            user_id: User ID
            filename: Original filename
            prefix: Path prefix (creatives, temp, etc.)

        Returns:
            Unique object name with path
        """
        date_str = datetime.now(timezone.utc).strftime("%Y/%m/%d")
        unique_id = uuid.uuid4().hex[:12]
        # Sanitize filename
        safe_filename = filename.replace(" ", "_").replace("/", "_")
        return f"{prefix}/{user_id}/{date_str}/{unique_id}_{safe_filename}"

    async def upload_image(
        self,
        image_bytes: bytes,
        filename: str,
        user_id: str,
        content_type: str = "image/png",
        prefix: str = "creatives",
        metadata: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Upload an image to GCS.

        Args:
            image_bytes: Image binary data
            filename: Original filename
            user_id: User ID for path organization
            content_type: MIME type of the image
            prefix: Path prefix (creatives, temp, etc.)
            metadata: Optional custom metadata

        Returns:
            Dict with gcs_url and public_url

        Raises:
            GCSError: If upload fails
        """
        object_name = self._generate_object_name(user_id, filename, prefix)

        # Use the simple upload endpoint
        # URL-encode the object name to handle non-ASCII characters (e.g., Chinese)
        encoded_object_name = quote(object_name, safe='')
        upload_url = (
            f"{self.base_url}/upload/storage/v1/b/{self.bucket_name}/o"
            f"?uploadType=media&name={encoded_object_name}&key={self.api_key}"
        )

        headers = {
            "Content-Type": content_type,
            "Content-Length": str(len(image_bytes)),
        }

        # Add custom metadata if provided
        # URL-encode metadata values to handle non-ASCII characters (e.g., Chinese)
        if metadata:
            for key, value in metadata.items():
                # Encode non-ASCII characters in header values
                encoded_value = quote(str(value), safe='')
                headers[f"x-goog-meta-{key}"] = encoded_value

        async with httpx.AsyncClient(timeout=120.0) as client:
            try:
                response = await client.post(
                    upload_url,
                    content=image_bytes,
                    headers=headers,
                )

                if response.status_code == 401:
                    raise GCSError(
                        "Authentication failed. Check API key.",
                        code="AUTH_FAILED",
                        retryable=False,
                    )

                if response.status_code == 403:
                    raise GCSError(
                        "Permission denied. Check bucket permissions.",
                        code="PERMISSION_DENIED",
                        retryable=False,
                    )

                if response.status_code == 429:
                    raise GCSError(
                        "Rate limit exceeded",
                        code="RATE_LIMIT",
                        retryable=True,
                    )

                if response.status_code >= 500:
                    raise GCSError(
                        f"Server error: {response.status_code}",
                        code="SERVER_ERROR",
                        retryable=True,
                    )

                if response.status_code not in (200, 201):
                    error_msg = response.text
                    try:
                        error_data = response.json()
                        error_msg = error_data.get("error", {}).get("message", response.text)
                    except Exception:
                        pass
                    raise GCSError(f"Upload failed: {error_msg}", code="UPLOAD_FAILED")

                result = response.json()

                # Build URLs
                gcs_url = f"gs://{self.bucket_name}/{object_name}"
                # Public URL (if bucket is public)
                public_url = f"https://storage.googleapis.com/{self.bucket_name}/{object_name}"
                # Authenticated URL (for private buckets)
                auth_url = f"https://storage.googleapis.com/{self.bucket_name}/{object_name}?key={self.api_key}"

                logger.info(
                    "gcs_image_uploaded",
                    bucket=self.bucket_name,
                    object_name=object_name,
                    size=len(image_bytes),
                    content_type=content_type,
                )

                return {
                    "gcs_url": gcs_url,
                    "public_url": public_url,
                    "object_name": object_name,
                    "bucket": self.bucket_name,
                    "size": len(image_bytes),
                    "content_type": content_type,
                    "generation": result.get("generation"),
                    "md5_hash": result.get("md5Hash"),
                }

            except httpx.TimeoutException:
                raise GCSError("Upload timed out", code="TIMEOUT", retryable=True)
            except httpx.HTTPError as e:
                raise GCSError(f"HTTP error: {e}", code="HTTP_ERROR", retryable=True)

    async def upload_for_chat_display(
        self,
        image_bytes: bytes,
        filename: str,
        user_id: str,
        session_id: str,
        style: str | None = None,
        score: int | None = None,
    ) -> dict[str, Any]:
        """Upload image specifically for chat display.

        This creates a temporary upload that can be viewed in chat history.
        The image is stored with metadata for later reference.

        Args:
            image_bytes: Image binary data
            filename: Original filename
            user_id: User ID
            session_id: Chat session ID
            style: Creative style
            score: Quality score

        Returns:
            Dict with URLs and metadata
        """
        metadata = {
            "user-id": user_id,
            "session-id": session_id,
            "purpose": "chat-display",
        }
        if style:
            metadata["style"] = style
        if score is not None:
            metadata["score"] = str(score)

        return await self.upload_image(
            image_bytes=image_bytes,
            filename=filename,
            user_id=user_id,
            content_type="image/png",
            prefix="chat-creatives",
            metadata=metadata,
        )

    async def upload_video(
        self,
        video_bytes: bytes,
        filename: str,
        user_id: str,
        content_type: str = "video/mp4",
        prefix: str = "videos",
        metadata: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Upload a video to GCS.

        Args:
            video_bytes: Video binary data
            filename: Original filename
            user_id: User ID for path organization
            content_type: MIME type of the video
            prefix: Path prefix (videos, chat-videos, etc.)
            metadata: Optional custom metadata

        Returns:
            Dict with gcs_url and public_url

        Raises:
            GCSError: If upload fails
        """
        object_name = self._generate_object_name(user_id, filename, prefix)

        # Use the simple upload endpoint
        encoded_object_name = quote(object_name, safe='')
        upload_url = (
            f"{self.base_url}/upload/storage/v1/b/{self.bucket_name}/o"
            f"?uploadType=media&name={encoded_object_name}&key={self.api_key}"
        )

        headers = {
            "Content-Type": content_type,
            "Content-Length": str(len(video_bytes)),
        }

        if metadata:
            for key, value in metadata.items():
                encoded_value = quote(str(value), safe='')
                headers[f"x-goog-meta-{key}"] = encoded_value

        async with httpx.AsyncClient(timeout=300.0) as client:  # Longer timeout for videos
            try:
                response = await client.post(
                    upload_url,
                    content=video_bytes,
                    headers=headers,
                )

                if response.status_code == 401:
                    raise GCSError(
                        "Authentication failed. Check API key.",
                        code="AUTH_FAILED",
                        retryable=False,
                    )

                if response.status_code == 403:
                    raise GCSError(
                        "Permission denied. Check bucket permissions.",
                        code="PERMISSION_DENIED",
                        retryable=False,
                    )

                if response.status_code == 429:
                    raise GCSError(
                        "Rate limit exceeded",
                        code="RATE_LIMIT",
                        retryable=True,
                    )

                if response.status_code >= 500:
                    raise GCSError(
                        f"Server error: {response.status_code}",
                        code="SERVER_ERROR",
                        retryable=True,
                    )

                if response.status_code not in (200, 201):
                    error_msg = response.text
                    try:
                        error_data = response.json()
                        error_msg = error_data.get("error", {}).get("message", response.text)
                    except Exception:
                        pass
                    raise GCSError(f"Upload failed: {error_msg}", code="UPLOAD_FAILED")

                result = response.json()

                # Build URLs
                gcs_url = f"gs://{self.bucket_name}/{object_name}"
                public_url = f"https://storage.googleapis.com/{self.bucket_name}/{object_name}"

                logger.info(
                    "gcs_video_uploaded",
                    bucket=self.bucket_name,
                    object_name=object_name,
                    size=len(video_bytes),
                    content_type=content_type,
                )

                return {
                    "gcs_url": gcs_url,
                    "public_url": public_url,
                    "object_name": object_name,
                    "bucket": self.bucket_name,
                    "size": len(video_bytes),
                    "content_type": content_type,
                    "generation": result.get("generation"),
                    "md5_hash": result.get("md5Hash"),
                }

            except httpx.TimeoutException:
                raise GCSError("Video upload timed out", code="TIMEOUT", retryable=True)
            except httpx.HTTPError as e:
                raise GCSError(f"HTTP error: {e}", code="HTTP_ERROR", retryable=True)

    async def delete_object(self, object_name: str) -> bool:
        """Delete an object from GCS.

        Args:
            object_name: Full object path

        Returns:
            True if deleted, False if not found
        """
        delete_url = (
            f"{self.base_url}/storage/v1/b/{self.bucket_name}/o/{object_name.replace('/', '%2F')}"
            f"?key={self.api_key}"
        )

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.delete(delete_url)

                if response.status_code == 204:
                    logger.info("gcs_object_deleted", object_name=object_name)
                    return True
                elif response.status_code == 404:
                    logger.debug("gcs_object_not_found", object_name=object_name)
                    return False
                else:
                    logger.warning(
                        "gcs_delete_failed",
                        object_name=object_name,
                        status=response.status_code,
                    )
                    return False

            except httpx.HTTPError as e:
                logger.error("gcs_delete_error", object_name=object_name, error=str(e))
                return False

    def _get_storage_client(self) -> storage.Client:
        """Get or create the GCS storage client with service account credentials."""
        if self._storage_client is None:
            if self._credentials_path:
                self._credentials = service_account.Credentials.from_service_account_file(
                    self._credentials_path
                )
                self._storage_client = storage.Client(credentials=self._credentials)
                logger.info(
                    "gcs_storage_client_initialized",
                    credentials_path=self._credentials_path,
                )
            else:
                # Use default credentials (ADC)
                self._storage_client = storage.Client()
                logger.info("gcs_storage_client_initialized_with_adc")
        return self._storage_client

    def get_signed_url(
        self,
        object_name: str,
        expiration_minutes: int = 60,
        method: str = "GET",
    ) -> str:
        """Get a signed URL for temporary access.

        Uses service account credentials to generate a V4 signed URL.

        Args:
            object_name: Object path in the bucket
            expiration_minutes: URL expiration time in minutes (default 60)
            method: HTTP method (GET, PUT, etc.)

        Returns:
            Signed URL for temporary access

        Raises:
            GCSError: If signing fails
        """
        try:
            client = self._get_storage_client()
            bucket = client.bucket(self.bucket_name)
            blob = bucket.blob(object_name)

            url = blob.generate_signed_url(
                version="v4",
                expiration=timedelta(minutes=expiration_minutes),
                method=method,
            )

            logger.info(
                "gcs_signed_url_generated",
                object_name=object_name,
                expiration_minutes=expiration_minutes,
            )

            return url

        except Exception as e:
            logger.error(
                "gcs_signed_url_error",
                object_name=object_name,
                error=str(e),
            )
            raise GCSError(
                f"Failed to generate signed URL: {e}",
                code="SIGNED_URL_ERROR",
            )


# Global client instance
_gcs_client: GCSClient | None = None


def get_gcs_client() -> GCSClient:
    """Get or create GCS client singleton.

    Returns:
        GCSClient instance
    """
    global _gcs_client
    if _gcs_client is None:
        _gcs_client = GCSClient()
    return _gcs_client
