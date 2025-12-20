"""Storage utilities for Google Cloud Storage and Amazon S3."""

import logging
from datetime import datetime, timedelta
from functools import lru_cache
from typing import Any, Protocol

from app.core.config import settings

logger = logging.getLogger(__name__)

# Global flag to track if GCS is available
_gcs_available: bool | None = None


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


# Pre-configured storage instances
creatives_storage = GCSStorage(settings.gcs_bucket_creatives)
landing_pages_storage = GCSStorage(
    settings.gcs_bucket_landing_pages,
    cdn_domain=settings.gcs_landing_pages_cdn_domain or None,
)
exports_storage = GCSStorage(settings.gcs_bucket_exports)
uploads_storage = GCSStorage(settings.gcs_bucket_uploads)  # User uploads bucket


# S3 storage instances
s3_creatives_storage = S3Storage(settings.s3_bucket_creatives)
s3_landing_pages_storage = S3Storage(
    settings.s3_bucket_landing_pages,
    cdn_domain=settings.cloudfront_domain or None,
)
s3_exports_storage = S3Storage(settings.s3_bucket_exports)
s3_uploads_storage = S3Storage(settings.s3_bucket_uploads)


def get_storage_backend(
    storage_type: str = "creatives",
    provider: str = "gcs",
) -> GCSStorage | S3Storage:
    """Get storage backend instance based on provider and type.
    
    Args:
        storage_type: Type of storage ('creatives', 'landing_pages', 'exports', 'uploads')
        provider: Storage provider ('gcs' or 's3')
        
    Returns:
        Storage instance (GCSStorage or S3Storage)
        
    Raises:
        ValueError: If invalid storage_type or provider is specified
    """
    storage_map = {
        "gcs": {
            "creatives": creatives_storage,
            "landing_pages": landing_pages_storage,
            "exports": exports_storage,
            "uploads": uploads_storage,
        },
        "s3": {
            "creatives": s3_creatives_storage,
            "landing_pages": s3_landing_pages_storage,
            "exports": s3_exports_storage,
            "uploads": s3_uploads_storage,
        },
    }
    
    if provider not in storage_map:
        raise ValueError(f"Invalid storage provider: {provider}. Must be 'gcs' or 's3'")
    
    if storage_type not in storage_map[provider]:
        raise ValueError(
            f"Invalid storage type: {storage_type}. "
            f"Must be one of: {', '.join(storage_map[provider].keys())}"
        )
    
    return storage_map[provider][storage_type]


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
