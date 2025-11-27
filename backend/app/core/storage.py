"""AWS S3 storage utilities."""

from typing import Any

import boto3
from botocore.config import Config

from app.core.config import settings


def get_s3_client() -> Any:
    """Get S3 client instance."""
    return boto3.client(
        "s3",
        aws_access_key_id=settings.aws_access_key_id,
        aws_secret_access_key=settings.aws_secret_access_key,
        region_name=settings.aws_region,
        config=Config(signature_version="s3v4"),
    )


class S3Storage:
    """S3 storage utility class."""

    def __init__(self, bucket: str) -> None:
        self.bucket = bucket
        self.client = get_s3_client()

    def generate_presigned_upload_url(
        self,
        key: str,
        content_type: str,
        expires_in: int = 3600,
    ) -> dict[str, Any]:
        """Generate presigned URL for file upload."""
        return self.client.generate_presigned_post(
            Bucket=self.bucket,
            Key=key,
            Fields={"Content-Type": content_type},
            Conditions=[
                {"Content-Type": content_type},
                ["content-length-range", 1, 100 * 1024 * 1024],  # Max 100MB
            ],
            ExpiresIn=expires_in,
        )

    def generate_presigned_download_url(
        self,
        key: str,
        expires_in: int = 3600,
    ) -> str:
        """Generate presigned URL for file download."""
        return self.client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": key},
            ExpiresIn=expires_in,
        )


    def upload_file(
        self,
        key: str,
        data: bytes,
        content_type: str,
    ) -> str:
        """Upload file to S3."""
        self.client.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=data,
            ContentType=content_type,
        )
        return f"s3://{self.bucket}/{key}"

    def delete_file(self, key: str) -> None:
        """Delete file from S3."""
        self.client.delete_object(Bucket=self.bucket, Key=key)

    def get_cdn_url(self, key: str) -> str:
        """Get CloudFront CDN URL for a file."""
        if settings.cloudfront_domain:
            return f"https://{settings.cloudfront_domain}/{key}"
        return f"https://{self.bucket}.s3.{settings.aws_region}.amazonaws.com/{key}"

    def file_exists(self, key: str) -> bool:
        """Check if file exists in S3."""
        try:
            self.client.head_object(Bucket=self.bucket, Key=key)
            return True
        except self.client.exceptions.ClientError:
            return False


# Pre-configured storage instances
creatives_storage = S3Storage(settings.s3_bucket_creatives)
landing_pages_storage = S3Storage(settings.s3_bucket_landing_pages)
exports_storage = S3Storage(settings.s3_bucket_exports)


def get_presigned_upload_url(key: str, expires_in: int = 3600) -> str:
    """
    Generate presigned URL for file upload.
    
    This is a convenience function for simple uploads.
    For more complex uploads, use S3Storage.generate_presigned_upload_url().
    """
    s3_client = get_s3_client()
    return s3_client.generate_presigned_url(
        'put_object',
        Params={'Bucket': settings.s3_bucket_creatives, 'Key': key},
        ExpiresIn=expires_in
    )
