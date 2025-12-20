"""AWS Bedrock Video Generation Client.

Supports multiple video generation models:
- Amazon Nova Reel v1.1 (amazon.nova-reel-v1:1)
- Luma Ray v2 (luma.ray-v2:0)
"""

import asyncio
import base64
import json
import time
from typing import Any

import boto3
import structlog
from botocore.exceptions import BotoCoreError, ClientError

from app.core.config import get_settings

logger = structlog.get_logger(__name__)


class BedrockVideoClient:
    """AWS Bedrock video generation client."""

    def __init__(
        self,
        region: str | None = None,
    ):
        """Initialize Bedrock video client.

        Args:
            region: AWS region (defaults to settings)
        """
        settings = get_settings()
        self.default_region = region or settings.bedrock_region
        self._client = None  # Will be initialized per-request based on model

        logger.info(
            "bedrock_video_client_initialized",
            default_region=self.default_region,
        )

    def _get_client_for_model(self, model_id: str):
        """Get Bedrock client for specific model with appropriate region.

        Args:
            model_id: Model identifier

        Returns:
            Bedrock runtime client
        """
        # Nova Reel models require us-east-1
        if "nova-reel" in model_id:
            region = "us-east-1"
        else:
            # All other models (including Luma Ray v2) use default region (us-west-2)
            region = self.default_region

        try:
            client = boto3.client(
                service_name="bedrock-runtime",
                region_name=region,
            )
            logger.info(
                "bedrock_client_created",
                model_id=model_id,
                region=region,
            )
            return client
        except Exception as e:
            logger.error("bedrock_client_creation_failed", model_id=model_id, region=region, error=str(e))
            raise RuntimeError(f"Failed to create Bedrock client: {e}")

    async def generate_video(
        self,
        prompt: str,
        model_id: str = "amazon.nova-reel-v1:1",
        duration: int = 6,
        aspect_ratio: str = "16:9",
        first_frame: bytes | None = None,
        last_frame: bytes | None = None,
        negative_prompt: str | None = None,
        user_id: str = "default",
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Generate video using Bedrock async API.

        Both Nova Reel and Luma use async invoke (StartAsyncInvoke).
        Video generation takes 2-8 minutes, output is saved to S3.

        Args:
            prompt: Text prompt for video generation
            model_id: Bedrock model ID
            duration: Video duration in seconds
            aspect_ratio: Video aspect ratio
            first_frame: Optional first frame image bytes
            last_frame: Optional last frame image bytes
            negative_prompt: Things to avoid
            user_id: User ID for S3 output path
            **kwargs: Additional model-specific parameters

        Returns:
            Dictionary with invocation_arn and status="processing"

        Raises:
            RuntimeError: If generation fails
        """
        log = logger.bind(
            model_id=model_id,
            prompt_preview=prompt[:100],
            duration=duration,
            aspect_ratio=aspect_ratio,
            has_first_frame=first_frame is not None,
        )
        log.info("bedrock_video_generation_start")

        try:
            # Get appropriate client for this model
            client = self._get_client_for_model(model_id)
            settings = get_settings()

            # Build model input based on model type
            if "nova-reel" in model_id:
                model_input = self._build_nova_reel_request(
                    prompt, duration, aspect_ratio, first_frame, last_frame, negative_prompt, **kwargs
                )
            elif "luma" in model_id:
                model_input = self._build_luma_request(
                    prompt, duration, aspect_ratio, first_frame, negative_prompt, **kwargs
                )
            else:
                raise ValueError(f"Unsupported model: {model_id}")

            # S3 output configuration (trailing slash indicates directory)
            s3_output_uri = f"s3://{settings.s3_bucket_uploads}/video-outputs/{user_id}/"

            # Start async invocation
            response = client.start_async_invoke(
                modelId=model_id,
                modelInput=model_input,
                outputDataConfig={
                    "s3OutputDataConfig": {
                        "s3Uri": s3_output_uri,
                    }
                },
            )

            invocation_arn = response["invocationArn"]
            log.info(
                "bedrock_video_async_started",
                invocation_arn=invocation_arn,
                s3_output=s3_output_uri,
            )

            return {
                "status": "processing",
                "invocation_arn": invocation_arn,
                "model_id": model_id,
                "s3_output_uri": s3_output_uri,
                "message": "Video generation started. This will take 2-8 minutes.",
            }

        except (BotoCoreError, ClientError) as e:
            log.error("bedrock_video_generation_failed", error=str(e))
            raise RuntimeError(f"Bedrock video generation failed: {e}")
        except Exception as e:
            log.error("bedrock_video_unexpected_error", error=str(e))
            raise RuntimeError(f"Unexpected error: {e}")

    async def poll_video_operation(
        self,
        invocation_arn: str,
        model_id: str = "amazon.nova-reel-v1:1",
    ) -> dict[str, Any]:
        """Poll video generation status using GetAsyncInvoke.

        Args:
            invocation_arn: Invocation ARN from generate_video
            model_id: Model ID used for generation

        Returns:
            Dictionary with status, progress, and S3 output location
        """
        log = logger.bind(invocation_arn=invocation_arn, model_id=model_id)

        try:
            client = self._get_client_for_model(model_id)

            # Get async invocation status
            response = client.get_async_invoke(
                invocationArn=invocation_arn,
            )

            status = response["status"]
            log.info("bedrock_video_poll", status=status)

            # Map Bedrock status to our status
            status_map = {
                "InProgress": "processing",
                "Completed": "completed",
                "Failed": "failed",
                "PartiallyCompleted": "completed",
            }

            result = {
                "status": status_map.get(status, "unknown"),
                "bedrock_status": status,
            }

            # Add output location if completed
            if status == "Completed" and "outputDataConfig" in response:
                output_config = response["outputDataConfig"]
                if "s3OutputDataConfig" in output_config:
                    result["s3_uri"] = output_config["s3OutputDataConfig"]["s3Uri"]

            # Add failure message if failed
            if status == "Failed" and "failureMessage" in response:
                result["error"] = response["failureMessage"]

            # Add submit time
            if "submitTime" in response:
                result["submit_time"] = response["submitTime"].isoformat()

            # Add end time if completed
            if "endTime" in response:
                result["end_time"] = response["endTime"].isoformat()

            return result

        except (BotoCoreError, ClientError) as e:
            log.error("bedrock_video_poll_failed", error=str(e))
            return {
                "status": "error",
                "error": str(e),
            }
        except Exception as e:
            log.error("bedrock_video_poll_unexpected_error", error=str(e))
            return {
                "status": "error",
                "error": str(e),
            }

    def _build_nova_reel_request(
        self,
        prompt: str,
        duration: int,
        aspect_ratio: str,
        first_frame: bytes | None,
        last_frame: bytes | None,
        negative_prompt: str | None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Build request for Amazon Nova Reel.

        Args:
            prompt: Generation prompt
            duration: Video duration
            aspect_ratio: Aspect ratio
            first_frame: First frame image
            last_frame: Last frame image
            negative_prompt: Negative prompt
            **kwargs: Additional parameters

        Returns:
            Request body
        """
        # Map aspect ratio to pixel dimensions
        dimension_map = {
            "16:9": "1280x720",
            "9:16": "720x1280",
            "1:1": "720x720",
            "4:3": "960x720",
            "3:4": "720x960",
        }
        dimension = dimension_map.get(aspect_ratio, "1280x720")

        body = {
            "taskType": "TEXT_VIDEO",
            "textToVideoParams": {
                "text": prompt,
            },
            "videoGenerationConfig": {
                "durationSeconds": duration,
                "fps": 24,
                "dimension": dimension,
            },
        }

        if negative_prompt:
            body["textToVideoParams"]["negativeText"] = negative_prompt

        # Add image-to-video if first frame provided
        if first_frame:
            body["taskType"] = "IMAGE_VIDEO"
            body["imageToVideoParams"] = {
                "image": base64.b64encode(first_frame).decode("utf-8"),
            }
            if prompt:
                body["imageToVideoParams"]["text"] = prompt

        return body

    def _build_luma_request(
        self,
        prompt: str,
        duration: int,
        aspect_ratio: str,
        first_frame: bytes | None,
        negative_prompt: str | None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Build request for Luma Ray v2.

        Reference: https://docs.aws.amazon.com/bedrock/latest/userguide/model-parameters-luma.html

        Args:
            prompt: Generation prompt
            duration: Video duration (1-5 seconds for Ray v2)
            aspect_ratio: Aspect ratio ("16:9", "9:16", "1:1", "4:3", "3:4", "21:9", "9:21")
            first_frame: First frame image
            negative_prompt: Negative prompt
            **kwargs: Additional parameters

        Returns:
            Request body
        """
        # Luma Ray v2 duration is 1-5 seconds, ensure valid range
        duration = max(1, min(5, duration))

        body = {
            "prompt": prompt,
            "aspect_ratio": aspect_ratio,
            "loop": kwargs.get("loop", False),
        }

        if negative_prompt:
            body["negative_prompt"] = negative_prompt

        if first_frame:
            # Image-to-video mode
            body["image"] = base64.b64encode(first_frame).decode("utf-8")

        return body


__all__ = ["BedrockVideoClient"]
