"""
Video generator using Google Veo models.

Supports:
- Text-to-video generation
- Image-to-video (first frame animation)
- Video-to-video (analyze and regenerate)
- Frame interpolation (first + last frame)

Requirements: Video generation capability
"""

import asyncio
import uuid
from datetime import datetime
from typing import Any

import httpx
import structlog

from app.services.gemini_client import GeminiClient, GeminiAPIError

logger = structlog.get_logger(__name__)


class VideoGenerationError(Exception):
    """Error during video generation."""

    def __init__(
        self,
        message: str,
        code: str = "VIDEO_GENERATION_FAILED",
        retryable: bool = True,
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.retryable = retryable


class GeneratedVideo:
    """Generated video result."""

    def __init__(
        self,
        video_url: str | None = None,
        operation_id: str | None = None,
        status: str = "pending",
        duration: int = 0,
        aspect_ratio: str = "16:9",
        prompt: str = "",
    ):
        self.video_url = video_url
        self.operation_id = operation_id
        self.status = status
        self.duration = duration
        self.aspect_ratio = aspect_ratio
        self.prompt = prompt
        self.created_at = datetime.utcnow().isoformat()
        self.id = f"video_{uuid.uuid4().hex[:12]}"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "video_url": self.video_url,
            "operation_id": self.operation_id,
            "status": self.status,
            "duration": self.duration,
            "aspect_ratio": self.aspect_ratio,
            "prompt": self.prompt,
            "created_at": self.created_at,
        }


class VideoGenerator:
    """Generates advertising videos using Google Veo models.

    Features:
    - Text-to-video: Generate video from text description
    - Image-to-video: Animate a static image
    - Video reference: Analyze uploaded video and generate similar
    - First/last frame interpolation
    """

    # Supported durations
    SUPPORTED_DURATIONS = [4, 6, 8]

    # Supported aspect ratios
    SUPPORTED_ASPECT_RATIOS = ["16:9", "9:16"]

    def __init__(
        self,
        gemini_client: GeminiClient | None = None,
    ):
        """Initialize video generator.

        Args:
            gemini_client: Gemini client with video generation support
        """
        self.gemini = gemini_client or GeminiClient()

    async def generate_from_prompt(
        self,
        prompt: str,
        duration: int = 4,
        aspect_ratio: str = "16:9",
        negative_prompt: str | None = None,
        use_fast_model: bool = False,
    ) -> GeneratedVideo:
        """Generate video from text prompt only.

        Args:
            prompt: Text description of the video
            duration: Video duration (4, 6, or 8 seconds)
            aspect_ratio: 16:9 or 9:16
            negative_prompt: Things to avoid
            use_fast_model: Use faster but lower quality model

        Returns:
            GeneratedVideo with operation_id for polling
        """
        log = logger.bind(
            prompt=prompt[:50],
            duration=duration,
            aspect_ratio=aspect_ratio,
        )
        log.info("generate_from_prompt_start")

        # Validate parameters
        duration = self._validate_duration(duration)
        aspect_ratio = self._validate_aspect_ratio(aspect_ratio)

        try:
            result = await self.gemini.generate_video(
                prompt=prompt,
                duration=duration,
                aspect_ratio=aspect_ratio,
                negative_prompt=negative_prompt,
                use_fast_model=use_fast_model,
            )

            video = GeneratedVideo(
                operation_id=result.get("operation_id"),
                status=result.get("status", "processing"),
                duration=duration,
                aspect_ratio=aspect_ratio,
                prompt=prompt,
            )

            log.info("generate_from_prompt_started", operation_id=video.operation_id)
            return video

        except GeminiAPIError as e:
            log.error("generate_from_prompt_failed", error=str(e))
            raise VideoGenerationError(str(e), code="VEO_API_ERROR", retryable=e.retryable)

    async def generate_from_image(
        self,
        prompt: str,
        first_frame_url: str | None = None,
        first_frame_bytes: bytes | None = None,
        duration: int = 4,
        aspect_ratio: str = "16:9",
        negative_prompt: str | None = None,
        use_fast_model: bool = False,
    ) -> GeneratedVideo:
        """Generate video starting from a first frame image.

        Args:
            prompt: Text description of the video motion/action
            first_frame_url: URL of the first frame image
            first_frame_bytes: First frame image bytes (alternative)
            duration: Video duration
            aspect_ratio: Video aspect ratio
            negative_prompt: Things to avoid
            use_fast_model: Use faster model

        Returns:
            GeneratedVideo with operation_id
        """
        log = logger.bind(
            prompt=prompt[:50],
            has_url=first_frame_url is not None,
            has_bytes=first_frame_bytes is not None,
        )
        log.info("generate_from_image_start")

        # Get first frame bytes
        if first_frame_bytes is None and first_frame_url:
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.get(first_frame_url)
                    response.raise_for_status()
                    first_frame_bytes = response.content
            except Exception as e:
                raise VideoGenerationError(
                    f"Failed to download first frame: {e}",
                    code="IMAGE_DOWNLOAD_FAILED",
                )

        if first_frame_bytes is None:
            raise VideoGenerationError(
                "Either first_frame_url or first_frame_bytes is required",
                code="INVALID_PARAMS",
                retryable=False,
            )

        # Validate parameters
        duration = self._validate_duration(duration)
        aspect_ratio = self._validate_aspect_ratio(aspect_ratio)

        try:
            result = await self.gemini.generate_video(
                prompt=prompt,
                duration=duration,
                aspect_ratio=aspect_ratio,
                first_frame=first_frame_bytes,
                negative_prompt=negative_prompt,
                use_fast_model=use_fast_model,
            )

            video = GeneratedVideo(
                operation_id=result.get("operation_id"),
                status=result.get("status", "processing"),
                duration=duration,
                aspect_ratio=aspect_ratio,
                prompt=prompt,
            )

            log.info("generate_from_image_started", operation_id=video.operation_id)
            return video

        except GeminiAPIError as e:
            log.error("generate_from_image_failed", error=str(e))
            raise VideoGenerationError(str(e), code="VEO_API_ERROR", retryable=e.retryable)

    async def generate_from_video_reference(
        self,
        video_url: str | None = None,
        video_bytes: bytes | None = None,
        custom_prompt: str | None = None,
        duration: int = 4,
        aspect_ratio: str = "16:9",
        use_fast_model: bool = False,
    ) -> GeneratedVideo:
        """Generate new video based on a reference video.

        Analyzes the reference video, extracts understanding,
        and generates a new video with similar style/content.

        Args:
            video_url: URL of reference video
            video_bytes: Reference video bytes
            custom_prompt: Additional instructions (combined with analysis)
            duration: Output video duration
            aspect_ratio: Output aspect ratio
            use_fast_model: Use faster model

        Returns:
            GeneratedVideo with operation_id
        """
        log = logger.bind(
            has_url=video_url is not None,
            has_bytes=video_bytes is not None,
            custom_prompt=custom_prompt[:30] if custom_prompt else None,
        )
        log.info("generate_from_video_reference_start")

        # Download video if URL provided
        if video_bytes is None and video_url:
            try:
                async with httpx.AsyncClient(timeout=60.0) as client:
                    response = await client.get(video_url)
                    response.raise_for_status()
                    video_bytes = response.content
            except Exception as e:
                raise VideoGenerationError(
                    f"Failed to download reference video: {e}",
                    code="VIDEO_DOWNLOAD_FAILED",
                )

        if video_bytes is None:
            raise VideoGenerationError(
                "Either video_url or video_bytes is required",
                code="INVALID_PARAMS",
                retryable=False,
            )

        # Step 1: Analyze the reference video
        log.info("analyzing_reference_video")
        try:
            analysis = await self.gemini.analyze_video(
                video_bytes=video_bytes,
                prompt="""Analyze this video for the purpose of recreating a similar advertising video.
Describe in detail:
1. Main subject/product shown
2. Visual style (colors, lighting, mood)
3. Camera movements and transitions
4. Key actions and motion
5. Background and setting
6. Overall tone and message

Provide a concise but complete description that could be used as a prompt to generate a similar video.""",
            )
            log.info("video_analysis_complete", analysis_length=len(analysis))
        except GeminiAPIError as e:
            log.error("video_analysis_failed", error=str(e))
            raise VideoGenerationError(
                f"Failed to analyze reference video: {e}",
                code="VIDEO_ANALYSIS_FAILED",
            )

        # Step 2: Build enhanced prompt from analysis
        enhanced_prompt = f"""Create an advertising video based on this reference:

{analysis}

"""
        if custom_prompt:
            enhanced_prompt += f"\nAdditional requirements: {custom_prompt}"

        enhanced_prompt += """

Generate a high-quality, professional advertising video that captures the essence of the reference while being original."""

        # Step 3: Try to extract first frame for image-to-video
        # Note: In production, use ffmpeg or cv2 for frame extraction
        first_frame = None  # Placeholder - frame extraction not implemented

        # Step 4: Generate the video
        try:
            duration = self._validate_duration(duration)
            aspect_ratio = self._validate_aspect_ratio(aspect_ratio)

            result = await self.gemini.generate_video(
                prompt=enhanced_prompt,
                duration=duration,
                aspect_ratio=aspect_ratio,
                first_frame=first_frame,
                use_fast_model=use_fast_model,
            )

            video = GeneratedVideo(
                operation_id=result.get("operation_id"),
                status=result.get("status", "processing"),
                duration=duration,
                aspect_ratio=aspect_ratio,
                prompt=enhanced_prompt[:500],  # Truncate for storage
            )

            log.info("generate_from_video_reference_started", operation_id=video.operation_id)
            return video

        except GeminiAPIError as e:
            log.error("generate_from_video_reference_failed", error=str(e))
            raise VideoGenerationError(str(e), code="VEO_API_ERROR", retryable=e.retryable)

    async def generate_with_interpolation(
        self,
        prompt: str,
        first_frame_url: str | None = None,
        first_frame_bytes: bytes | None = None,
        last_frame_url: str | None = None,
        last_frame_bytes: bytes | None = None,
        duration: int = 8,  # Interpolation requires 8s
        aspect_ratio: str = "16:9",
        use_fast_model: bool = False,
    ) -> GeneratedVideo:
        """Generate video interpolating between first and last frames.

        Args:
            prompt: Description of the transition/motion
            first_frame_url/bytes: Starting frame
            last_frame_url/bytes: Ending frame
            duration: Must be 8 for interpolation
            aspect_ratio: Video aspect ratio
            use_fast_model: Use faster model

        Returns:
            GeneratedVideo with operation_id
        """
        log = logger.bind(prompt=prompt[:50])
        log.info("generate_with_interpolation_start")

        # Download first frame if needed
        if first_frame_bytes is None and first_frame_url:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(first_frame_url)
                response.raise_for_status()
                first_frame_bytes = response.content

        # Download last frame if needed
        if last_frame_bytes is None and last_frame_url:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(last_frame_url)
                response.raise_for_status()
                last_frame_bytes = response.content

        if not first_frame_bytes or not last_frame_bytes:
            raise VideoGenerationError(
                "Both first and last frames are required for interpolation",
                code="INVALID_PARAMS",
                retryable=False,
            )

        # Interpolation requires 8 second duration
        duration = 8
        aspect_ratio = self._validate_aspect_ratio(aspect_ratio)

        try:
            result = await self.gemini.generate_video(
                prompt=prompt,
                duration=duration,
                aspect_ratio=aspect_ratio,
                first_frame=first_frame_bytes,
                last_frame=last_frame_bytes,
                use_fast_model=use_fast_model,
            )

            video = GeneratedVideo(
                operation_id=result.get("operation_id"),
                status=result.get("status", "processing"),
                duration=duration,
                aspect_ratio=aspect_ratio,
                prompt=prompt,
            )

            log.info("generate_with_interpolation_started", operation_id=video.operation_id)
            return video

        except GeminiAPIError as e:
            log.error("generate_with_interpolation_failed", error=str(e))
            raise VideoGenerationError(str(e), code="VEO_API_ERROR", retryable=e.retryable)

    async def check_status(self, operation_id: str) -> dict:
        """Check the status of a video generation operation.

        Args:
            operation_id: The operation ID from generation

        Returns:
            Status dict with completion info
        """
        try:
            return await self.gemini.poll_video_operation(operation_id)
        except GeminiAPIError as e:
            raise VideoGenerationError(str(e), code="POLL_FAILED", retryable=e.retryable)

    async def wait_for_completion(
        self,
        operation_id: str,
        poll_interval: int = 10,
        max_wait: int = 360,  # 6 minutes max
    ) -> dict:
        """Wait for video generation to complete.

        Args:
            operation_id: The operation ID
            poll_interval: Seconds between polls
            max_wait: Maximum wait time in seconds

        Returns:
            Final status with video URL
        """
        log = logger.bind(operation_id=operation_id)
        log.info("wait_for_completion_start", max_wait=max_wait)

        elapsed = 0
        while elapsed < max_wait:
            result = await self.check_status(operation_id)

            if result.get("status") == "completed":
                log.info("video_generation_completed", video_uri=result.get("video_uri"))
                return result

            if result.get("status") == "failed":
                raise VideoGenerationError(
                    result.get("error", "Video generation failed"),
                    code="GENERATION_FAILED",
                    retryable=False,
                )

            await asyncio.sleep(poll_interval)
            elapsed += poll_interval
            log.info("polling_video_status", elapsed=elapsed, progress=result.get("progress"))

        raise VideoGenerationError(
            f"Video generation timed out after {max_wait} seconds",
            code="TIMEOUT",
            retryable=True,
        )

    def _validate_duration(self, duration: int) -> int:
        """Validate and normalize duration."""
        if duration not in self.SUPPORTED_DURATIONS:
            # Find closest supported duration
            return min(self.SUPPORTED_DURATIONS, key=lambda x: abs(x - duration))
        return duration

    def _validate_aspect_ratio(self, aspect_ratio: str) -> str:
        """Validate aspect ratio."""
        if aspect_ratio not in self.SUPPORTED_ASPECT_RATIOS:
            return "16:9"  # Default to landscape
        return aspect_ratio

    async def close(self):
        """Close resources."""
        if self.gemini:
            await self.gemini.close()
