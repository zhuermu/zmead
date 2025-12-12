"""Google Cloud Storage utilities."""

import logging
from datetime import timedelta
from functools import lru_cache
from typing import Any

from app.core.config import settings

logger = logging.getLogger(__name__)

# Global flag to track if GCS is available
_gcs_available: bool | None = None


@lru_cache(maxsize=1)
def get_gcs_client():
    """Get Google Cloud Storage client instance (lazy initialization).

    Returns None if credentials are not available.
    """
    global _gcs_available

    try:
        from google.cloud import storage
        from google.oauth2 import service_account

        if settings.gcs_credentials_path:
            credentials = service_account.Credentials.from_service_account_file(
                settings.gcs_credentials_path
            )
            client = storage.Client(
                project=settings.gcs_project_id,
                credentials=credentials,
            )
        else:
            # Use default credentials (ADC - Application Default Credentials)
            client = storage.Client(project=settings.gcs_project_id)

        _gcs_available = True
        return client
    except Exception as e:
        logger.warning(f"GCS client initialization failed: {e}. Storage features will be disabled.")
        _gcs_available = False
        return None


def is_gcs_available() -> bool:
    """Check if GCS is available."""
    if _gcs_available is None:
        get_gcs_client()  # Trigger lazy initialization
    return _gcs_available or False


class GCSStorage:
    """Google Cloud Storage utility class with lazy initialization."""

    def __init__(self, bucket_name: str, cdn_domain: str | None = None) -> None:
        self.bucket_name = bucket_name
        self.cdn_domain = cdn_domain  # Custom CDN domain for this storage
        self._client = None
        self._bucket = None

    @property
    def client(self):
        """Lazy initialization of GCS client."""
        if self._client is None:
            self._client = get_gcs_client()
        return self._client

    @property
    def bucket(self):
        """Lazy initialization of bucket."""
        if self._bucket is None and self.client is not None:
            self._bucket = self.client.bucket(self.bucket_name)
        return self._bucket

    def _check_available(self) -> bool:
        """Check if GCS is available and raise appropriate error if not."""
        if not is_gcs_available():
            logger.warning(f"GCS operation skipped: storage not available")
            return False
        return True

    def generate_presigned_upload_url(
        self,
        key: str,
        content_type: str,
        expires_in: int = 3600,
    ) -> dict[str, Any]:
        """Generate signed URL for file upload."""
        if not self._check_available():
            return {"url": "", "fields": {"Content-Type": content_type}}
        blob = self.bucket.blob(key)
        url = blob.generate_signed_url(
            version="v4",
            expiration=timedelta(seconds=expires_in),
            method="PUT",
            content_type=content_type,
        )
        return {
            "url": url,
            "fields": {
                "Content-Type": content_type,
            },
        }

    def generate_presigned_download_url(
        self,
        key: str,
        expires_in: int = 3600,
    ) -> str:
        """Generate signed URL for file download."""
        if not self._check_available():
            return ""
        blob = self.bucket.blob(key)
        return blob.generate_signed_url(
            version="v4",
            expiration=timedelta(seconds=expires_in),
            method="GET",
        )

    def upload_file(
        self,
        key: str,
        data: bytes,
        content_type: str,
    ) -> str:
        """Upload file to GCS."""
        if not self._check_available():
            return f"gs://{self.bucket_name}/{key}"  # Return expected format but don't upload
        blob = self.bucket.blob(key)
        blob.upload_from_string(data, content_type=content_type)
        return f"gs://{self.bucket_name}/{key}"

    def delete_file(self, key: str) -> None:
        """Delete file from GCS."""
        if not self._check_available():
            return
        blob = self.bucket.blob(key)
        blob.delete()

    def get_cdn_url(self, key: str) -> str:
        """Get CDN URL for a file."""
        # Use instance-specific CDN domain first, then global setting
        cdn_domain = self.cdn_domain or settings.gcs_cdn_domain
        if cdn_domain:
            return f"https://{cdn_domain}/{key}"
        # Default to storage.googleapis.com URL
        return f"https://storage.googleapis.com/{self.bucket_name}/{key}"

    def get_public_url(self, key: str) -> str:
        """Get public URL for a file (requires bucket to be public or object to be public)."""
        return f"https://storage.googleapis.com/{self.bucket_name}/{key}"

    def file_exists(self, key: str) -> bool:
        """Check if file exists in GCS."""
        if not self._check_available():
            return False
        blob = self.bucket.blob(key)
        return blob.exists()

    def make_public(self, key: str) -> str:
        """Make a file publicly accessible and return its public URL."""
        if not self._check_available():
            return self.get_public_url(key)
        blob = self.bucket.blob(key)
        blob.make_public()
        return blob.public_url

    def list_files(
        self,
        prefix: str | None = None,
        max_results: int | None = None,
    ) -> list[dict]:
        """List files in the bucket with optional prefix filter.

        Args:
            prefix: Filter files by prefix (e.g., 'users/123/')
            max_results: Maximum number of results to return

        Returns:
            List of file info dicts with keys: name, size, content_type, updated, url
        """
        if not self._check_available():
            return []

        try:
            blobs = self.client.list_blobs(
                self.bucket_name,
                prefix=prefix,
                max_results=max_results,
            )

            files = []
            for blob in blobs:
                # Skip "directory" markers (blobs ending with /)
                if blob.name.endswith("/"):
                    continue

                files.append({
                    "name": blob.name,
                    "size": blob.size,
                    "content_type": blob.content_type,
                    "updated": blob.updated.isoformat() if blob.updated else None,
                    "url": self.get_public_url(blob.name),
                })

            return files
        except Exception as e:
            logger.warning(f"Failed to list files in {self.bucket_name}: {e}")
            return []

    def get_file_info(self, key: str) -> dict | None:
        """Get file metadata.

        Args:
            key: File key/path in bucket

        Returns:
            File info dict or None if not found
        """
        if not self._check_available():
            return None

        try:
            blob = self.bucket.blob(key)
            if not blob.exists():
                return None

            blob.reload()  # Load metadata
            return {
                "name": blob.name,
                "size": blob.size,
                "content_type": blob.content_type,
                "updated": blob.updated.isoformat() if blob.updated else None,
                "url": self.get_public_url(blob.name),
            }
        except Exception as e:
            logger.warning(f"Failed to get file info for {key}: {e}")
            return None

    def download_file(self, key: str) -> bytes | None:
        """Download file content from GCS.

        Args:
            key: File key/path in bucket

        Returns:
            File content as bytes or None if not found
        """
        if not self._check_available():
            return None

        try:
            blob = self.bucket.blob(key)
            if not blob.exists():
                return None

            return blob.download_as_bytes()
        except Exception as e:
            logger.warning(f"Failed to download file {key}: {e}")
            return None


# Pre-configured storage instances
creatives_storage = GCSStorage(settings.gcs_bucket_creatives)
landing_pages_storage = GCSStorage(
    settings.gcs_bucket_landing_pages,
    cdn_domain=settings.gcs_landing_pages_cdn_domain or None,
)
exports_storage = GCSStorage(settings.gcs_bucket_exports)
uploads_storage = GCSStorage(settings.gcs_bucket_uploads)  # User uploads bucket


def get_presigned_upload_url(key: str, expires_in: int = 3600) -> str:
    """
    Generate signed URL for file upload.

    This is a convenience function for simple uploads.
    For more complex uploads, use GCSStorage.generate_presigned_upload_url().
    """
    if not is_gcs_available():
        return ""
    blob = creatives_storage.bucket.blob(key)
    return blob.generate_signed_url(
        version="v4",
        expiration=timedelta(seconds=expires_in),
        method="PUT",
    )
