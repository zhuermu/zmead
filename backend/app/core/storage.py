"""Storage utilities for Amazon S3."""

import logging
from typing import Any, Protocol

from app.core.config import settings

logger = logging.getLogger(__name__)


class StorageInterface(Protocol):
    """Protocol defining the storage interface that all implementations must follow."""

    def generate_presigned_upload_url(
        self,
        key: str,
        content_type: str,
        expires_in: int = 3600,
    ) -> dict[str, Any]:
        """Generate signed URL for file upload."""
        ...

    def generate_presigned_download_url(
        self,
        key: str,
        expires_in: int = 3600,
    ) -> str:
        """Generate signed URL for file download."""
        ...

    def upload_file(
        self,
        key: str,
        data: bytes,
        content_type: str,
    ) -> str:
        """Upload file to storage."""
        ...

    def delete_file(self, key: str) -> None:
        """Delete file from storage."""
        ...

    def get_cdn_url(self, key: str) -> str:
        """Get CDN URL for a file."""
        ...

    def file_exists(self, key: str) -> bool:
        """Check if file exists in storage."""
        ...

    def list_files(
        self,
        prefix: str | None = None,
        max_results: int | None = None,
    ) -> list[dict]:
        """List files in the bucket with optional prefix filter."""
        ...


class S3Storage:
    """Amazon S3 Storage utility class with lazy initialization."""

    def __init__(self, bucket_name: str, cdn_domain: str | None = None) -> None:
        self.bucket_name = bucket_name
        self.cdn_domain = cdn_domain  # CloudFront CDN domain for this storage
        self._client = None

    @property
    def client(self):
        """Lazy initialization of S3 client."""
        if self._client is None:
            from app.core.aws_clients import get_s3_client
            self._client = get_s3_client()
        return self._client

    def _check_available(self) -> bool:
        """Check if S3 is available and raise appropriate error if not."""
        from app.core.aws_clients import is_aws_available
        if not is_aws_available():
            logger.warning("S3 operation skipped: AWS not available")
            return False
        return True

    def generate_presigned_upload_url(
        self,
        key: str,
        content_type: str,
        expires_in: int = 3600,
    ) -> dict[str, Any]:
        """Generate presigned URL for file upload to S3.

        Args:
            key: Object key (path) in the bucket
            content_type: MIME type of the file
            expires_in: URL expiration time in seconds

        Returns:
            Dictionary with 'url' and 'fields' for upload
        """
        if not self._check_available():
            return {"url": "", "fields": {"Content-Type": content_type}}

        try:
            # Generate presigned POST URL for S3
            url = self.client.generate_presigned_url(
                ClientMethod="put_object",
                Params={
                    "Bucket": self.bucket_name,
                    "Key": key,
                    "ContentType": content_type,
                },
                ExpiresIn=expires_in,
            )

            return {
                "url": url,
                "fields": {
                    "Content-Type": content_type,
                },
            }
        except Exception as e:
            logger.error(f"Failed to generate S3 presigned upload URL: {e}")
            return {"url": "", "fields": {"Content-Type": content_type}}

    def generate_presigned_download_url(
        self,
        key: str,
        expires_in: int = 3600,
    ) -> str:
        """Generate presigned URL for file download from S3.

        Args:
            key: Object key (path) in the bucket
            expires_in: URL expiration time in seconds

        Returns:
            Presigned download URL
        """
        if not self._check_available():
            return ""

        try:
            url = self.client.generate_presigned_url(
                ClientMethod="get_object",
                Params={
                    "Bucket": self.bucket_name,
                    "Key": key,
                },
                ExpiresIn=expires_in,
            )
            return url
        except Exception as e:
            logger.error(f"Failed to generate S3 presigned download URL: {e}")
            return ""

    def upload_file(
        self,
        key: str,
        data: bytes,
        content_type: str,
    ) -> str:
        """Upload file to S3.

        Args:
            key: Object key (path) in the bucket
            data: File content as bytes
            content_type: MIME type of the file

        Returns:
            S3 URI of the uploaded file
        """
        if not self._check_available():
            return f"s3://{self.bucket_name}/{key}"  # Return expected format but don't upload

        try:
            self.client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=data,
                ContentType=content_type,
            )
            return f"s3://{self.bucket_name}/{key}"
        except Exception as e:
            logger.error(f"Failed to upload file to S3: {e}")
            return f"s3://{self.bucket_name}/{key}"

    def delete_file(self, key: str) -> None:
        """Delete file from S3.

        Args:
            key: Object key (path) in the bucket
        """
        if not self._check_available():
            return

        try:
            self.client.delete_object(
                Bucket=self.bucket_name,
                Key=key,
            )
        except Exception as e:
            logger.error(f"Failed to delete file from S3: {e}")

    def get_cdn_url(self, key: str) -> str:
        """Get CDN URL for a file.

        Args:
            key: Object key (path) in the bucket

        Returns:
            CloudFront CDN URL if configured, otherwise S3 URL
        """
        # Use instance-specific CDN domain first, then global setting
        cdn_domain = self.cdn_domain or settings.cloudfront_domain
        if cdn_domain:
            return f"https://{cdn_domain}/{key}"
        # Default to S3 URL
        return f"https://{self.bucket_name}.s3.{settings.aws_region}.amazonaws.com/{key}"

    def get_public_url(self, key: str) -> str:
        """Get public S3 URL for a file.

        Args:
            key: Object key (path) in the bucket

        Returns:
            Public S3 URL
        """
        return f"https://{self.bucket_name}.s3.{settings.aws_region}.amazonaws.com/{key}"

    def file_exists(self, key: str) -> bool:
        """Check if file exists in S3.

        Args:
            key: Object key (path) in the bucket

        Returns:
            True if file exists, False otherwise
        """
        if not self._check_available():
            return False

        try:
            self.client.head_object(
                Bucket=self.bucket_name,
                Key=key,
            )
            return True
        except Exception:
            return False

    def make_public(self, key: str) -> str:
        """Make a file publicly accessible and return its public URL.

        Args:
            key: Object key (path) in the bucket

        Returns:
            Public URL of the file
        """
        if not self._check_available():
            return self.get_public_url(key)

        try:
            # Set object ACL to public-read
            self.client.put_object_acl(
                Bucket=self.bucket_name,
                Key=key,
                ACL="public-read",
            )
            return self.get_public_url(key)
        except Exception as e:
            logger.error(f"Failed to make S3 object public: {e}")
            return self.get_public_url(key)

    def list_files(
        self,
        prefix: str | None = None,
        max_results: int | None = None,
    ) -> list[dict]:
        """List files in the S3 bucket with optional prefix filter.

        Args:
            prefix: Filter files by prefix (e.g., 'users/123/')
            max_results: Maximum number of results to return

        Returns:
            List of file info dicts with keys: name, size, content_type, updated, url
        """
        if not self._check_available():
            return []

        try:
            params: dict[str, Any] = {"Bucket": self.bucket_name}
            if prefix:
                params["Prefix"] = prefix
            if max_results:
                params["MaxKeys"] = max_results

            response = self.client.list_objects_v2(**params)

            if "Contents" not in response:
                return []

            files = []
            for obj in response["Contents"]:
                # Skip "directory" markers (keys ending with /)
                if obj["Key"].endswith("/"):
                    continue

                # Get content type by making a head request
                try:
                    head_response = self.client.head_object(
                        Bucket=self.bucket_name,
                        Key=obj["Key"],
                    )
                    content_type = head_response.get("ContentType", "application/octet-stream")
                except Exception:
                    content_type = "application/octet-stream"

                files.append({
                    "name": obj["Key"],
                    "size": obj["Size"],
                    "content_type": content_type,
                    "updated": obj["LastModified"].isoformat() if obj.get("LastModified") else None,
                    "url": self.get_public_url(obj["Key"]),
                })

            return files
        except Exception as e:
            logger.warning(f"Failed to list files in S3 bucket {self.bucket_name}: {e}")
            return []

    def get_file_info(self, key: str) -> dict | None:
        """Get file metadata from S3.

        Args:
            key: Object key (path) in the bucket

        Returns:
            File info dict or None if not found
        """
        if not self._check_available():
            return None

        try:
            response = self.client.head_object(
                Bucket=self.bucket_name,
                Key=key,
            )

            return {
                "name": key,
                "size": response.get("ContentLength", 0),
                "content_type": response.get("ContentType", "application/octet-stream"),
                "updated": response.get("LastModified").isoformat() if response.get("LastModified") else None,
                "url": self.get_public_url(key),
            }
        except Exception as e:
            logger.warning(f"Failed to get file info for {key}: {e}")
            return None

    def download_file(self, key: str) -> bytes | None:
        """Download file content from S3.

        Args:
            key: Object key (path) in the bucket

        Returns:
            File content as bytes or None if not found
        """
        if not self._check_available():
            return None

        try:
            response = self.client.get_object(
                Bucket=self.bucket_name,
                Key=key,
            )
            return response["Body"].read()
        except Exception as e:
            logger.warning(f"Failed to download file {key}: {e}")
            return None


# Pre-configured S3 storage instances
creatives_storage = S3Storage(settings.s3_bucket_creatives)
landing_pages_storage = S3Storage(
    settings.s3_bucket_landing_pages,
    cdn_domain=settings.cloudfront_domain or None,
)
exports_storage = S3Storage(settings.s3_bucket_exports)
uploads_storage = S3Storage(settings.s3_bucket_uploads)

# Aliases for backward compatibility
s3_creatives_storage = creatives_storage
s3_landing_pages_storage = landing_pages_storage
s3_exports_storage = exports_storage
s3_uploads_storage = uploads_storage


def get_storage_backend(storage_type: str = "creatives") -> S3Storage:
    """Get S3 storage backend instance.

    Args:
        storage_type: Type of storage ('creatives', 'landing_pages', 'exports', 'uploads')

    Returns:
        S3Storage instance

    Raises:
        ValueError: If invalid storage_type is specified
    """
    storage_map = {
        "creatives": creatives_storage,
        "landing_pages": landing_pages_storage,
        "exports": exports_storage,
        "uploads": uploads_storage,
    }

    if storage_type not in storage_map:
        raise ValueError(
            f"Invalid storage type: {storage_type}. "
            f"Must be one of: {', '.join(storage_map.keys())}"
        )

    return storage_map[storage_type]


def get_presigned_upload_url(key: str, expires_in: int = 3600, content_type: str = "application/octet-stream") -> dict[str, Any]:
    """
    Generate signed URL for file upload.

    This is a convenience function for simple uploads.
    For more complex uploads, use S3Storage.generate_presigned_upload_url().

    Returns:
        Dictionary with 'url' and 'fields' for upload
    """
    return creatives_storage.generate_presigned_upload_url(
        key=key,
        content_type=content_type,
        expires_in=expires_in,
    )
