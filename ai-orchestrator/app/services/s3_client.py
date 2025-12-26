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
        # Use AWS_REGION for S3 (creatives bucket region)
        self.s3 = boto3.client("s3", region_name=settings.aws_region)
        # Use creatives bucket for all creative assets (uploaded + AI-generated)
        self.bucket_creatives = settings.s3_bucket_creatives
        logger.info(
            "s3_client_initialized",
            creatives_bucket=self.bucket_creatives,
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
        """Upload AI-generated image to creatives bucket.

        All creative assets (user-uploaded + AI-generated) are stored in the creatives bucket.
        Path structure: users/{user_id}/generated/{session_id}/{filename}

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
        # Store AI-generated images in creatives bucket under users/{user_id}/generated/
        object_name = f"users/{user_id}/generated/{session_id}/{filename}"

        try:
            # Upload to S3 creatives bucket
            self.s3.put_object(
                Bucket=self.bucket_creatives,
                Key=object_name,
                Body=image_bytes,
                ContentType="image/png",
                Metadata={
                    "user_id": user_id,
                    "session_id": session_id,
                    "style": style or "",
                    "source": "ai-generated",
                },
            )

            s3_url = f"s3://{self.bucket_creatives}/{object_name}"

            logger.info(
                "s3_upload_success",
                bucket=self.bucket_creatives,
                object_name=object_name,
                size=len(image_bytes),
                source="ai-generated",
            )

            return {
                "object_name": object_name,
                "bucket": self.bucket_creatives,
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
        session_id: str | None = None,
        metadata: dict | None = None,
    ) -> dict[str, Any]:
        """Upload AI-generated video to creatives bucket.

        All creative assets (user-uploaded + AI-generated) are stored in the creatives bucket.
        Path structure: users/{user_id}/generated/{session_id}/{filename}

        Args:
            video_bytes: Video data
            filename: File name
            user_id: User ID
            content_type: Content type
            session_id: Session ID (optional, defaults to 'videos')
            metadata: Additional metadata

        Returns:
            Upload result
        """
        # Store AI-generated videos in creatives bucket under users/{user_id}/generated/
        prefix = session_id or "videos"
        object_name = f"users/{user_id}/generated/{prefix}/{filename}"

        # Ensure metadata includes source
        upload_metadata = metadata or {}
        upload_metadata["source"] = "ai-generated"

        try:
            # Upload to S3 creatives bucket
            self.s3.put_object(
                Bucket=self.bucket_creatives,
                Key=object_name,
                Body=video_bytes,
                ContentType=content_type,
                Metadata=upload_metadata,
            )

            s3_url = f"s3://{self.bucket_creatives}/{object_name}"

            logger.info(
                "s3_video_upload_success",
                bucket=self.bucket_creatives,
                object_name=object_name,
                size=len(video_bytes),
                source="ai-generated",
            )

            return {
                "object_name": object_name,
                "bucket": self.bucket_creatives,
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
        bucket: str | None = None,
        expiration: int = 3600,
    ) -> str:
        """Generate presigned URL for S3 object.

        Args:
            object_name: S3 object key
            bucket: S3 bucket name (defaults to creatives bucket)
            expiration: URL expiration time in seconds (default 1 hour)

        Returns:
            Presigned URL

        Raises:
            S3Error: If URL generation fails
        """
        bucket_name = bucket or self.bucket_creatives
        try:
            url = self.s3.generate_presigned_url(
                "get_object",
                Params={"Bucket": bucket_name, "Key": object_name},
                ExpiresIn=expiration,
            )
            logger.info(
                "presigned_url_generated",
                bucket=bucket_name,
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
