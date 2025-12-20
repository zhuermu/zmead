"""AWS S3 client for file storage."""
import io
from typing import Any

import boto3
import structlog
from botocore.exceptions import ClientError

from app.core.config import get_settings

logger = structlog.get_logger(__name__)


class S3Error(Exception):
    """S3 operation error."""

    def __init__(self, message: str, code: str = "S3_ERROR"):
        self.message = message
        self.code = code
        super().__init__(self.message)


class S3Client:
    """AWS S3 client for file uploads."""

    def __init__(self):
        """Initialize S3 client."""
        settings = get_settings()
        self.s3 = boto3.client("s3", region_name=settings.aws_region)
        self.bucket_uploads = settings.s3_bucket_uploads
        logger.info(
            "s3_client_initialized",
            bucket=self.bucket_uploads,
            region=settings.aws_region,
        )

    async def upload_for_chat_display(
        self,
        image_bytes: bytes,
        filename: str,
        user_id: str,
        session_id: str,
        style: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Upload image for chat display.

        Args:
            image_bytes: Image data
            filename: File name
            user_id: User ID
            session_id: Session ID
            style: Image style
            **kwargs: Additional metadata

        Returns:
            Upload result with object_name, bucket, s3_url
        """
        object_name = f"chat-images/{user_id}/{session_id}/{filename}"

        try:
            # Upload to S3
            self.s3.put_object(
                Bucket=self.bucket_uploads,
                Key=object_name,
                Body=image_bytes,
                ContentType="image/png",
                Metadata={
                    "user_id": user_id,
                    "session_id": session_id,
                    "style": style or "",
                },
            )

            s3_url = f"s3://{self.bucket_uploads}/{object_name}"

            logger.info(
                "s3_upload_success",
                object_name=object_name,
                size=len(image_bytes),
            )

            return {
                "object_name": object_name,
                "bucket": self.bucket_uploads,
                "s3_url": s3_url,
                "size": len(image_bytes),
            }

        except ClientError as e:
            error_msg = f"Upload failed: {str(e)}"
            logger.error("s3_upload_failed", error=error_msg, object_name=object_name)
            raise S3Error(error_msg)

    async def upload_video(
        self,
        video_bytes: bytes,
        filename: str,
        user_id: str,
        content_type: str = "video/mp4",
        prefix: str = "chat-videos",
        metadata: dict | None = None,
    ) -> dict[str, Any]:
        """Upload video to S3.

        Args:
            video_bytes: Video data
            filename: File name
            user_id: User ID
            content_type: Content type
            prefix: S3 prefix
            metadata: Additional metadata

        Returns:
            Upload result
        """
        object_name = f"{prefix}/{user_id}/{filename}"

        try:
            # Upload to S3
            self.s3.put_object(
                Bucket=self.bucket_uploads,
                Key=object_name,
                Body=video_bytes,
                ContentType=content_type,
                Metadata=metadata or {},
            )

            s3_url = f"s3://{self.bucket_uploads}/{object_name}"

            logger.info(
                "s3_video_upload_success",
                object_name=object_name,
                size=len(video_bytes),
            )

            return {
                "object_name": object_name,
                "bucket": self.bucket_uploads,
                "s3_url": s3_url,
                "size": len(video_bytes),
            }

        except ClientError as e:
            error_msg = f"Video upload failed: {str(e)}"
            logger.error("s3_video_upload_failed", error=error_msg)
            raise S3Error(error_msg)

    def generate_presigned_url(
        self,
        object_name: str,
        expiration: int = 3600,
    ) -> str:
        """Generate presigned URL for S3 object.

        Args:
            object_name: S3 object key
            expiration: URL expiration time in seconds (default 1 hour)

        Returns:
            Presigned URL

        Raises:
            S3Error: If URL generation fails
        """
        try:
            url = self.s3.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket_uploads, "Key": object_name},
                ExpiresIn=expiration,
            )
            logger.info(
                "presigned_url_generated",
                object_name=object_name,
                expiration=expiration,
            )
            return url
        except ClientError as e:
            error_msg = f"Failed to generate presigned URL: {str(e)}"
            logger.error("presigned_url_failed", error=error_msg)
            raise S3Error(error_msg)


# Singleton instance
_s3_client: S3Client | None = None


def get_s3_client() -> S3Client:
    """Get S3 client singleton."""
    global _s3_client
    if _s3_client is None:
        _s3_client = S3Client()
    return _s3_client


__all__ = ["S3Client", "S3Error", "get_s3_client"]
