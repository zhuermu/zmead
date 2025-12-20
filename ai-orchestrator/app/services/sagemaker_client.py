"""SageMaker client for creative generation.

This module provides high-level interfaces for using SageMaker endpoints
for image and video generation in the AI orchestrator.
"""

import os
from typing import Any

import structlog

from app.services.model_factory import ModelConfig, ModelProviderFactory
from app.services.sagemaker_provider import SageMakerProvider

logger = structlog.get_logger(__name__)


class SageMakerClient:
    """Client for SageMaker creative generation models.

    This class provides convenient methods for image and video generation
    using deployed SageMaker endpoints.

    Example:
        client = SageMakerClient()

        # Generate image
        image_bytes = await client.generate_image(
            prompt="A beautiful sunset",
            width=512,
            height=512
        )

        # Generate video
        video_result = await client.generate_video(
            prompt="A cat playing",
            duration=3
        )
    """

    def __init__(
        self,
        qwen_image_endpoint: str | None = None,
        wan_video_endpoint: str | None = None,
        region: str | None = None,
        aws_access_key_id: str | None = None,
        aws_secret_access_key: str | None = None,
        aws_session_token: str | None = None,
    ):
        """Initialize SageMaker client.

        Args:
            qwen_image_endpoint: Qwen-Image endpoint name (defaults to env var)
            wan_video_endpoint: Wan2.2 video endpoint name (defaults to env var)
            region: AWS region (defaults to env var)
            aws_access_key_id: AWS access key (optional)
            aws_secret_access_key: AWS secret key (optional)
            aws_session_token: AWS session token (optional)
        """
        self.qwen_image_endpoint = qwen_image_endpoint or os.getenv(
            "SAGEMAKER_QWEN_IMAGE_ENDPOINT", ""
        )
        self.wan_video_endpoint = wan_video_endpoint or os.getenv(
            "SAGEMAKER_WAN_VIDEO_ENDPOINT", ""
        )
        self.region = region or os.getenv("SAGEMAKER_REGION", "us-west-2")

        # Store credentials
        self.aws_access_key_id = aws_access_key_id
        self.aws_secret_access_key = aws_secret_access_key
        self.aws_session_token = aws_session_token

        logger.info(
            "sagemaker_client_initialized",
            qwen_image_endpoint=self.qwen_image_endpoint or "not configured",
            wan_video_endpoint=self.wan_video_endpoint or "not configured",
            region=self.region,
        )

    def _get_image_provider(self) -> SageMakerProvider:
        """Get SageMaker provider for image generation.

        Returns:
            Configured SageMakerProvider instance

        Raises:
            ValueError: If endpoint is not configured
        """
        if not self.qwen_image_endpoint:
            raise ValueError(
                "Qwen-Image endpoint not configured. "
                "Set SAGEMAKER_QWEN_IMAGE_ENDPOINT environment variable."
            )

        return SageMakerProvider(
            endpoint_name=self.qwen_image_endpoint,
            region_name=self.region,
            aws_access_key_id=self.aws_access_key_id,
            aws_secret_access_key=self.aws_secret_access_key,
            aws_session_token=self.aws_session_token,
            timeout=120.0,  # Image generation timeout
        )

    def _get_video_provider(self) -> SageMakerProvider:
        """Get SageMaker provider for video generation.

        Returns:
            Configured SageMakerProvider instance

        Raises:
            ValueError: If endpoint is not configured
        """
        if not self.wan_video_endpoint:
            raise ValueError(
                "Wan2.2 video endpoint not configured. "
                "Set SAGEMAKER_WAN_VIDEO_ENDPOINT environment variable."
            )

        return SageMakerProvider(
            endpoint_name=self.wan_video_endpoint,
            region_name=self.region,
            aws_access_key_id=self.aws_access_key_id,
            aws_secret_access_key=self.aws_secret_access_key,
            aws_session_token=self.aws_session_token,
            timeout=300.0,  # Video generation timeout (longer)
        )

    async def generate_image(
        self,
        prompt: str,
        width: int = 512,
        height: int = 512,
        num_inference_steps: int = 20,
        guidance_scale: float = 7.5,
        **kwargs: Any,
    ) -> bytes:
        """Generate image using Qwen-Image model.

        Args:
            prompt: Text description of the image
            width: Image width in pixels
            height: Image height in pixels
            num_inference_steps: Number of denoising steps
            guidance_scale: Guidance scale for generation
            **kwargs: Additional model-specific parameters

        Returns:
            Generated image as bytes

        Raises:
            ValueError: If endpoint is not configured
            ModelProviderError: If generation fails
        """
        log = logger.bind(
            operation="generate_image",
            prompt=prompt[:50],
            width=width,
            height=height,
        )
        log.info("generate_image_start")

        provider = self._get_image_provider()

        try:
            image_bytes = await provider.generate_image(
                prompt=prompt,
                width=width,
                height=height,
                num_inference_steps=num_inference_steps,
                guidance_scale=guidance_scale,
                **kwargs,
            )

            log.info("generate_image_complete", size=len(image_bytes))
            return image_bytes

        except Exception as e:
            log.error("generate_image_failed", error=str(e))
            raise

    async def generate_video(
        self,
        prompt: str,
        duration: int = 3,
        fps: int = 24,
        resolution: str = "512x512",
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Generate video using Wan2.2 model.

        Args:
            prompt: Text description of the video
            duration: Video duration in seconds
            fps: Frames per second
            resolution: Video resolution (e.g., "512x512", "1024x576")
            **kwargs: Additional model-specific parameters

        Returns:
            Video generation result (format depends on model)

        Raises:
            ValueError: If endpoint is not configured
            ModelProviderError: If generation fails
        """
        log = logger.bind(
            operation="generate_video",
            prompt=prompt[:50],
            duration=duration,
            fps=fps,
            resolution=resolution,
        )
        log.info("generate_video_start")

        provider = self._get_video_provider()

        try:
            result = await provider.generate_video(
                prompt=prompt,
                duration=duration,
                fps=fps,
                resolution=resolution,
                **kwargs,
            )

            log.info("generate_video_complete")
            return result

        except Exception as e:
            log.error("generate_video_failed", error=str(e))
            raise

    def is_image_generation_available(self) -> bool:
        """Check if image generation is available.

        Returns:
            True if Qwen-Image endpoint is configured
        """
        return bool(self.qwen_image_endpoint)

    def is_video_generation_available(self) -> bool:
        """Check if video generation is available.

        Returns:
            True if Wan2.2 video endpoint is configured
        """
        return bool(self.wan_video_endpoint)

    def get_status(self) -> dict[str, Any]:
        """Get SageMaker client status.

        Returns:
            Dictionary with configuration and availability status
        """
        return {
            "image_generation": {
                "available": self.is_image_generation_available(),
                "endpoint": self.qwen_image_endpoint or None,
            },
            "video_generation": {
                "available": self.is_video_generation_available(),
                "endpoint": self.wan_video_endpoint or None,
            },
            "region": self.region,
        }


# Global client instance
_sagemaker_client: SageMakerClient | None = None


def get_sagemaker_client() -> SageMakerClient:
    """Get global SageMaker client instance.

    Returns:
        SageMakerClient instance
    """
    global _sagemaker_client

    if _sagemaker_client is None:
        _sagemaker_client = SageMakerClient()

    return _sagemaker_client
