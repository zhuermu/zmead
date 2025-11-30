"""Gemini Client wrapper for AI model interactions.

This module provides the GeminiClient class for interacting with Google's
Gemini AI models via langchain-google-genai and google-genai SDK. It includes:
- Chat completion (Gemini 3 Pro)
- Structured output with Pydantic schemas
- Fast completion (Gemini 2.5 Flash)
- Image generation (Gemini 3 Pro Image)
- Image-to-image generation (with reference images)
- Error handling for API errors, rate limiting, quota exceeded
- Retry logic with exponential backoff
"""

import asyncio
import base64
import httpx
from typing import Any, TypeVar

import structlog
from google import genai
from google.genai import types
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel

from app.core.config import get_settings

logger = structlog.get_logger(__name__)

# Type variable for structured output
T = TypeVar("T", bound=BaseModel)


class GeminiError(Exception):
    """Base exception for Gemini errors."""

    def __init__(
        self,
        message: str,
        code: str | None = None,
        retryable: bool = False,
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.retryable = retryable


class GeminiRateLimitError(GeminiError):
    """Raised when rate limit is exceeded."""

    def __init__(self, message: str = "Rate limit exceeded"):
        super().__init__(message, code="RATE_LIMIT", retryable=True)


class GeminiQuotaExceededError(GeminiError):
    """Raised when quota is exceeded."""

    def __init__(self, message: str = "Quota exceeded"):
        super().__init__(message, code="QUOTA_EXCEEDED", retryable=False)


class GeminiAPIError(GeminiError):
    """Raised for general API errors."""

    def __init__(self, message: str, retryable: bool = False):
        super().__init__(message, code="API_ERROR", retryable=retryable)


class GeminiTimeoutError(GeminiError):
    """Raised when request times out."""

    def __init__(self, message: str = "Request timed out"):
        super().__init__(message, code="TIMEOUT", retryable=True)


class GeminiImageGenerationError(GeminiError):
    """Raised when image generation fails."""

    def __init__(self, message: str, retryable: bool = True):
        super().__init__(message, code="IMAGE_GENERATION_ERROR", retryable=retryable)


class GeminiClient:
    """Client for interacting with Google Gemini AI models.

    Uses google-genai SDK for Gemini 3 integration with:
    - Chat completion using Gemini 3 Pro
    - Structured output with Pydantic schemas
    - Fast completion using Gemini 2.5 Flash
    - Image generation using Gemini 3 Pro Image
    - Automatic retry with exponential backoff

    Example:
        client = GeminiClient()
        response = await client.chat_completion([
            {"role": "user", "content": "Hello!"}
        ])

        # Generate image
        image_bytes = await client.generate_image(
            prompt="A beautiful sunset",
            aspect_ratio="16:9"
        )
    """

    # Gemini API base URL
    GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta"

    def __init__(
        self,
        api_key: str | None = None,
        chat_model: str | None = None,
        fast_model: str | None = None,
        imagen_model: str | None = None,
        imagen_pro_model: str | None = None,
        max_retries: int = 3,
        backoff_base: float = 1.0,
        backoff_factor: float = 2.0,
        timeout: float = 60.0,
    ):
        """Initialize Gemini Client.

        Args:
            api_key: Gemini API key. Defaults to settings value
            chat_model: Model for chat completion. Defaults to gemini-3-pro-preview
            fast_model: Model for fast completion. Defaults to gemini-2.5-flash
            imagen_model: Model for image generation. Defaults to gemini-3-pro-image-preview
            imagen_pro_model: Pro model for high-quality image generation
            max_retries: Maximum retry attempts (default 3)
            backoff_base: Base wait time for retries in seconds (default 1s)
            backoff_factor: Multiplier for exponential backoff (default 2.0)
            timeout: Request timeout in seconds (default 60s)
        """
        settings = get_settings()

        self.api_key = api_key or settings.gemini_api_key
        self.chat_model_name = chat_model or settings.gemini_model_chat
        self.fast_model_name = fast_model or settings.gemini_model_fast
        self.imagen_model_name = imagen_model or settings.gemini_model_imagen
        self.imagen_pro_model_name = imagen_pro_model or settings.gemini_model_imagen_pro
        self.max_retries = max_retries
        self.backoff_base = backoff_base
        self.backoff_factor = backoff_factor
        self.timeout = timeout

        # Initialize google-genai client for Gemini 3
        self._genai_client: genai.Client | None = None

        # Initialize LLM instances (for backward compatibility with langchain)
        self._chat_llm: ChatGoogleGenerativeAI | None = None
        self._fast_llm: ChatGoogleGenerativeAI | None = None
        self._http_client: httpx.AsyncClient | None = None

    def _get_genai_client(self) -> genai.Client:
        """Get or create google-genai client."""
        if self._genai_client is None:
            self._genai_client = genai.Client(api_key=self.api_key)
        return self._genai_client

    def _get_chat_llm(self) -> ChatGoogleGenerativeAI:
        """Get or create chat LLM instance (Gemini 2.5 Pro)."""
        if self._chat_llm is None:
            self._chat_llm = ChatGoogleGenerativeAI(
                model=self.chat_model_name,
                google_api_key=self.api_key,
                temperature=0.1,
                max_retries=0,  # We handle retries ourselves
                timeout=self.timeout,
            )
        return self._chat_llm

    def _get_fast_llm(self) -> ChatGoogleGenerativeAI:
        """Get or create fast LLM instance (Gemini 2.5 Flash)."""
        if self._fast_llm is None:
            self._fast_llm = ChatGoogleGenerativeAI(
                model=self.fast_model_name,
                google_api_key=self.api_key,
                temperature=0.3,
                max_retries=0,  # We handle retries ourselves
                timeout=self.timeout,
            )
        return self._fast_llm

    def _convert_messages(
        self,
        messages: list[dict[str, str]],
    ) -> list[BaseMessage]:
        """Convert dict messages to LangChain message objects.

        Args:
            messages: List of message dicts with 'role' and 'content'

        Returns:
            List of LangChain BaseMessage objects
        """
        result: list[BaseMessage] = []

        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")

            if role == "system":
                result.append(SystemMessage(content=content))
            elif role == "assistant":
                result.append(AIMessage(content=content))
            else:  # user or default
                result.append(HumanMessage(content=content))

        return result

    def _handle_error(self, error: Exception) -> GeminiError:
        """Convert exception to appropriate GeminiError.

        Args:
            error: Original exception

        Returns:
            Appropriate GeminiError subclass
        """
        error_str = str(error).lower()

        # Check for rate limiting
        if "rate" in error_str and "limit" in error_str:
            return GeminiRateLimitError(str(error))

        # Check for quota exceeded
        if "quota" in error_str or "exceeded" in error_str:
            return GeminiQuotaExceededError(str(error))

        # Check for timeout
        if "timeout" in error_str or "timed out" in error_str:
            return GeminiTimeoutError(str(error))

        # Check for retryable errors
        retryable = any(
            keyword in error_str for keyword in ["503", "500", "unavailable", "internal"]
        )

        return GeminiAPIError(str(error), retryable=retryable)

    async def _execute_with_retry(
        self,
        func,
        log: Any,
        operation: str,
    ) -> Any:
        """Execute function with retry logic.

        Args:
            func: Async function to execute
            log: Bound logger
            operation: Operation name for logging

        Returns:
            Function result

        Raises:
            GeminiError: If all retries fail
        """
        last_error: GeminiError | None = None

        for attempt in range(self.max_retries):
            try:
                return await func()

            except Exception as e:
                gemini_error = self._handle_error(e)
                last_error = gemini_error

                if not gemini_error.retryable:
                    log.error(
                        f"{operation}_failed",
                        error=str(e),
                        code=gemini_error.code,
                        retryable=False,
                    )
                    raise gemini_error

                if attempt < self.max_retries - 1:
                    wait_time = self.backoff_base * (self.backoff_factor**attempt)
                    log.warning(
                        f"{operation}_retry",
                        attempt=attempt + 1,
                        max_retries=self.max_retries,
                        wait_seconds=wait_time,
                        error=str(e),
                    )
                    await asyncio.sleep(wait_time)
                else:
                    log.error(
                        f"{operation}_failed",
                        attempt=attempt + 1,
                        error=str(e),
                        code=gemini_error.code,
                    )
                    raise gemini_error

        # Should not reach here
        if last_error:
            raise last_error
        raise GeminiAPIError("Unknown error")

    async def chat_completion(
        self,
        messages: list[dict[str, str]],
        temperature: float | None = None,
    ) -> str:
        """Generate chat completion using Gemini 3 Pro.

        Args:
            messages: List of message dicts with 'role' and 'content'
            temperature: Optional temperature override (default 1.0 for Gemini 3)

        Returns:
            Generated response text

        Raises:
            GeminiError: If generation fails
        """
        log = logger.bind(
            model=self.chat_model_name,
            message_count=len(messages),
        )
        log.info("chat_completion_start")

        client = self._get_genai_client()

        # Convert messages to google-genai format
        contents = self._convert_messages_to_genai(messages)

        async def _invoke():
            # Use google-genai SDK for Gemini 3
            response = await asyncio.to_thread(
                client.models.generate_content,
                model=self.chat_model_name,
                contents=contents,
                config=types.GenerateContentConfig(
                    temperature=temperature or 1.0,  # Gemini 3 default
                ),
            )
            return response.text

        result = await self._execute_with_retry(_invoke, log, "chat_completion")

        log.info(
            "chat_completion_complete",
            response_length=len(result) if result else 0,
        )

        return result

    def _convert_messages_to_genai(
        self,
        messages: list[dict[str, str]],
    ) -> list[types.Content]:
        """Convert dict messages to google-genai Content objects.

        Args:
            messages: List of message dicts with 'role' and 'content'

        Returns:
            List of google-genai Content objects
        """
        contents = []
        system_instruction = None

        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")

            if role == "system":
                # System messages are handled as system_instruction
                system_instruction = content
                continue
            elif role == "assistant":
                contents.append(types.Content(
                    role="model",
                    parts=[types.Part.from_text(text=content)],
                ))
            else:  # user
                contents.append(types.Content(
                    role="user",
                    parts=[types.Part.from_text(text=content)],
                ))

        # If there's a system instruction, prepend it to the first user message
        if system_instruction and contents:
            first_content = contents[0]
            if first_content.role == "user":
                combined_text = f"{system_instruction}\n\n{first_content.parts[0].text}"
                contents[0] = types.Content(
                    role="user",
                    parts=[types.Part.from_text(text=combined_text)],
                )

        return contents

    async def structured_output(
        self,
        messages: list[dict[str, str]],
        schema: type[T],
        temperature: float | None = None,
    ) -> T:
        """Generate structured output using Gemini 2.5 Pro.

        Uses Pydantic schema for structured output parsing.

        Args:
            messages: List of message dicts with 'role' and 'content'
            schema: Pydantic model class for output structure
            temperature: Optional temperature override (0.0-1.0)

        Returns:
            Parsed Pydantic model instance

        Raises:
            GeminiError: If generation fails
        """
        log = logger.bind(
            model=self.chat_model_name,
            schema=schema.__name__,
            message_count=len(messages),
        )
        log.info("structured_output_start")

        llm = self._get_chat_llm()

        if temperature is not None:
            llm = llm.bind(temperature=temperature)

        # Use with_structured_output for reliable parsing
        structured_llm = llm.with_structured_output(schema)

        langchain_messages = self._convert_messages(messages)

        async def _invoke():
            return await structured_llm.ainvoke(langchain_messages)

        result = await self._execute_with_retry(_invoke, log, "structured_output")

        log.info("structured_output_complete")

        return result

    async def fast_completion(
        self,
        messages: list[dict[str, str]],
        temperature: float | None = None,
    ) -> str:
        """Generate fast completion using Gemini 2.5 Flash.

        Use this for quick responses where speed is more important
        than reasoning depth.

        Args:
            messages: List of message dicts with 'role' and 'content'
            temperature: Optional temperature override (0.0-1.0)

        Returns:
            Generated response text

        Raises:
            GeminiError: If generation fails
        """
        log = logger.bind(
            model=self.fast_model_name,
            message_count=len(messages),
        )
        log.info("fast_completion_start")

        llm = self._get_fast_llm()

        if temperature is not None:
            llm = llm.bind(temperature=temperature)

        langchain_messages = self._convert_messages(messages)

        async def _invoke():
            response = await llm.ainvoke(langchain_messages)
            return response.content

        result = await self._execute_with_retry(_invoke, log, "fast_completion")

        log.info(
            "fast_completion_complete",
            response_length=len(result) if result else 0,
        )

        return result

    async def fast_structured_output(
        self,
        messages: list[dict[str, str]],
        schema: type[T],
        temperature: float | None = None,
    ) -> T:
        """Generate fast structured output using Gemini 2.5 Flash.

        Args:
            messages: List of message dicts with 'role' and 'content'
            schema: Pydantic model class for output structure
            temperature: Optional temperature override (0.0-1.0)

        Returns:
            Parsed Pydantic model instance

        Raises:
            GeminiError: If generation fails
        """
        log = logger.bind(
            model=self.fast_model_name,
            schema=schema.__name__,
            message_count=len(messages),
        )
        log.info("fast_structured_output_start")

        llm = self._get_fast_llm()

        if temperature is not None:
            llm = llm.bind(temperature=temperature)

        structured_llm = llm.with_structured_output(schema)

        langchain_messages = self._convert_messages(messages)

        async def _invoke():
            return await structured_llm.ainvoke(langchain_messages)

        result = await self._execute_with_retry(_invoke, log, "fast_structured_output")

        log.info("fast_structured_output_complete")

        return result

    async def _get_http_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client for direct API calls."""
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.timeout),
                headers={"Content-Type": "application/json"},
            )
        return self._http_client

    async def generate_image(
        self,
        prompt: str,
        aspect_ratio: str = "1:1",
        use_pro_model: bool = False,
        reference_images: list[bytes] | None = None,
    ) -> bytes:
        """Generate an image using Gemini's native image generation.

        Uses the Gemini API with response_modalities=["IMAGE"] to generate images.
        Supports text-to-image and image-to-image (with reference images).

        Args:
            prompt: Text description of the image to generate
            aspect_ratio: Aspect ratio (1:1, 16:9, 9:16, 4:3, 3:4)
            use_pro_model: Use the Pro model for higher quality (slower)
            reference_images: Optional list of reference image bytes for image-to-image

        Returns:
            Generated image as bytes (PNG format)

        Raises:
            GeminiImageGenerationError: If image generation fails
        """
        log = logger.bind(
            model=self.imagen_pro_model_name if use_pro_model else self.imagen_model_name,
            aspect_ratio=aspect_ratio,
            has_reference=reference_images is not None,
        )
        log.info("generate_image_start")

        model_name = self.imagen_pro_model_name if use_pro_model else self.imagen_model_name

        async def _generate():
            return await self._call_gemini_image_api(
                prompt=prompt,
                model=model_name,
                aspect_ratio=aspect_ratio,
                reference_images=reference_images,
            )

        try:
            result = await self._execute_with_retry(_generate, log, "generate_image")
            log.info("generate_image_complete", image_size=len(result))
            return result
        except GeminiError:
            raise
        except Exception as e:
            log.error("generate_image_failed", error=str(e))
            raise GeminiImageGenerationError(f"Image generation failed: {e}")

    async def generate_images(
        self,
        prompt: str,
        count: int = 1,
        aspect_ratio: str = "1:1",
        use_pro_model: bool = False,
        reference_images: list[bytes] | None = None,
    ) -> list[bytes]:
        """Generate multiple images in parallel.

        Args:
            prompt: Text description of the images to generate
            count: Number of images to generate (1-4)
            aspect_ratio: Aspect ratio (1:1, 16:9, 9:16, 4:3, 3:4)
            use_pro_model: Use the Pro model for higher quality
            reference_images: Optional reference images for image-to-image

        Returns:
            List of generated image bytes

        Raises:
            GeminiImageGenerationError: If all image generations fail
        """
        log = logger.bind(count=count, aspect_ratio=aspect_ratio)
        log.info("generate_images_start")

        # Generate images in parallel
        tasks = [
            self.generate_image(
                prompt=prompt,
                aspect_ratio=aspect_ratio,
                use_pro_model=use_pro_model,
                reference_images=reference_images,
            )
            for _ in range(count)
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Collect successful results
        images: list[bytes] = []
        errors: list[Exception] = []

        for result in results:
            if isinstance(result, Exception):
                errors.append(result)
            else:
                images.append(result)

        if not images:
            error_msgs = [str(e) for e in errors[:3]]  # First 3 errors
            raise GeminiImageGenerationError(
                f"All {count} image generations failed: {error_msgs}",
                retryable=True,
            )

        log.info(
            "generate_images_complete",
            generated=len(images),
            failed=len(errors),
        )

        return images

    async def _call_gemini_image_api(
        self,
        prompt: str,
        model: str,
        aspect_ratio: str,
        reference_images: list[bytes] | None = None,
    ) -> bytes:
        """Call Gemini API for image generation using google-genai SDK.

        Uses Gemini 3 Pro Image model with image_config for image generation.

        Args:
            prompt: Generation prompt
            model: Model name (gemini-3-pro-image-preview)
            aspect_ratio: Aspect ratio (1:1, 16:9, 9:16, 4:3, 3:4)
            reference_images: Optional reference images for image-to-image

        Returns:
            Generated image bytes
        """
        client = self._get_genai_client()

        # Build content parts
        contents = []

        # Add reference images if provided (for image-to-image)
        if reference_images:
            for img_bytes in reference_images:
                contents.append(types.Part.from_bytes(
                    data=img_bytes,
                    mime_type="image/png",
                ))

        # Add text prompt
        contents.append(prompt)

        try:
            # Use google-genai SDK with image_config
            response = await asyncio.to_thread(
                client.models.generate_content,
                model=model,
                contents=contents,
                config=types.GenerateContentConfig(
                    response_modalities=["IMAGE"],
                    image_config=types.ImageConfig(
                        aspect_ratio=aspect_ratio,
                    ),
                ),
            )

            # Extract image from response
            if response.candidates:
                for part in response.candidates[0].content.parts:
                    if hasattr(part, "inline_data") and part.inline_data:
                        return part.inline_data.data

            raise GeminiImageGenerationError(
                "No image data in response",
                retryable=True,
            )

        except Exception as e:
            error_str = str(e).lower()
            if "timeout" in error_str:
                raise GeminiTimeoutError("Image generation request timed out")
            elif "rate" in error_str and "limit" in error_str:
                raise GeminiRateLimitError(str(e))
            elif "quota" in error_str:
                raise GeminiQuotaExceededError(str(e))
            else:
                logger.error("gemini_image_api_error", error=str(e))
                raise GeminiImageGenerationError(
                    f"Image generation failed: {e}",
                    retryable=True,
                )

    async def generate_video(
        self,
        prompt: str,
        duration: int = 4,
        aspect_ratio: str = "16:9",
        first_frame: bytes | None = None,
        last_frame: bytes | None = None,
        reference_images: list[bytes] | None = None,
        use_fast_model: bool = False,
        negative_prompt: str | None = None,
    ) -> dict:
        """Generate a video using Veo model.

        Supports text-to-video, image-to-video (with first frame), and interpolation.

        Args:
            prompt: Text description of the video
            duration: Video duration in seconds (4, 6, or 8)
            aspect_ratio: Video aspect ratio (16:9 or 9:16)
            first_frame: Optional starting frame image bytes
            last_frame: Optional ending frame image bytes (for interpolation)
            reference_images: Optional reference images (up to 3)
            use_fast_model: Use fast model for quicker generation
            negative_prompt: Things to avoid in the video

        Returns:
            dict with operation_id for polling, or video data if completed

        Raises:
            GeminiError: If video generation fails
        """
        settings = get_settings()
        model = settings.gemini_model_veo_fast if use_fast_model else settings.gemini_model_veo

        log = logger.bind(
            model=model,
            duration=duration,
            aspect_ratio=aspect_ratio,
            has_first_frame=first_frame is not None,
            has_last_frame=last_frame is not None,
        )
        log.info("generate_video_start")

        client = await self._get_http_client()

        # Build request for predictLongRunning
        url = f"{self.GEMINI_API_BASE}/models/{model}:predictLongRunning"

        # Build instances (input)
        instance = {"prompt": prompt}

        if first_frame:
            instance["image"] = {
                "bytesBase64Encoded": base64.b64encode(first_frame).decode("utf-8"),
                "mimeType": "image/png",
            }

        if last_frame:
            instance["lastFrame"] = {
                "bytesBase64Encoded": base64.b64encode(last_frame).decode("utf-8"),
                "mimeType": "image/png",
            }

        if reference_images:
            instance["referenceImages"] = [
                {
                    "referenceImage": {
                        "bytesBase64Encoded": base64.b64encode(img).decode("utf-8"),
                        "mimeType": "image/png",
                    },
                    "referenceType": "asset",
                }
                for img in reference_images[:3]  # Max 3 reference images
            ]

        # Build parameters
        parameters = {
            "aspectRatio": aspect_ratio,
            "durationSeconds": duration,
        }

        if negative_prompt:
            parameters["negativePrompt"] = negative_prompt

        request_body = {
            "instances": [instance],
            "parameters": parameters,
        }

        try:
            response = await client.post(
                url,
                json=request_body,
                params={"key": self.api_key},
                timeout=120.0,  # Longer timeout for video generation
            )

            if response.status_code != 200:
                error_text = response.text
                log.error(
                    "veo_api_error",
                    status_code=response.status_code,
                    error=error_text[:500],
                )
                raise GeminiAPIError(
                    f"Veo API returned {response.status_code}: {error_text[:200]}",
                    retryable=response.status_code >= 500,
                )

            data = response.json()

            # Return operation info for async polling
            operation_name = data.get("name")
            if operation_name:
                log.info("generate_video_operation_started", operation=operation_name)
                return {
                    "status": "processing",
                    "operation_id": operation_name,
                    "message": "Video generation started, poll for completion",
                }

            # If immediate response (unlikely for video)
            return data

        except httpx.TimeoutException:
            raise GeminiTimeoutError("Video generation request timed out")
        except httpx.RequestError as e:
            raise GeminiAPIError(f"Request failed: {e}", retryable=True)

    async def poll_video_operation(self, operation_id: str) -> dict:
        """Poll for video generation completion.

        Args:
            operation_id: The operation ID from generate_video

        Returns:
            dict with status and video URL if completed
        """
        log = logger.bind(operation_id=operation_id)
        log.info("poll_video_operation")

        client = await self._get_http_client()

        # Poll the operation
        url = f"{self.GEMINI_API_BASE}/{operation_id}"

        try:
            response = await client.get(
                url,
                params={"key": self.api_key},
            )

            if response.status_code != 200:
                raise GeminiAPIError(f"Failed to poll operation: {response.text[:200]}")

            data = response.json()

            if data.get("done"):
                # Check for error
                if "error" in data:
                    error = data["error"]
                    raise GeminiAPIError(f"Video generation failed: {error.get('message', 'Unknown error')}")

                # Extract video from response
                response_data = data.get("response", {})
                generated_samples = response_data.get("generateVideoResponse", {}).get("generatedSamples", [])

                if generated_samples:
                    video_info = generated_samples[0].get("video", {})
                    return {
                        "status": "completed",
                        "video_uri": video_info.get("uri"),
                        "video_state": video_info.get("state"),
                    }

                return {"status": "completed", "data": response_data}

            # Still processing
            metadata = data.get("metadata", {})
            return {
                "status": "processing",
                "progress": metadata.get("progress", 0),
            }

        except httpx.RequestError as e:
            raise GeminiAPIError(f"Failed to poll operation: {e}", retryable=True)

    async def analyze_video(
        self,
        video_url: str | None = None,
        video_bytes: bytes | None = None,
        prompt: str = "Describe this video in detail, including the main subjects, actions, style, colors, and mood.",
    ) -> str:
        """Analyze a video and extract understanding.

        Args:
            video_url: URL of the video to analyze
            video_bytes: Video bytes (alternative to URL)
            prompt: Question or instruction for analysis

        Returns:
            Text description/analysis of the video
        """
        log = logger.bind(
            has_url=video_url is not None,
            has_bytes=video_bytes is not None,
        )
        log.info("analyze_video_start")

        client = await self._get_http_client()

        # Use Gemini Flash for video understanding
        url = f"{self.GEMINI_API_BASE}/models/{self.fast_model_name}:generateContent"

        parts = []

        if video_bytes:
            parts.append({
                "inline_data": {
                    "mime_type": "video/mp4",
                    "data": base64.b64encode(video_bytes).decode("utf-8"),
                }
            })
        elif video_url:
            parts.append({
                "file_data": {
                    "mime_type": "video/mp4",
                    "file_uri": video_url,
                }
            })
        else:
            raise GeminiAPIError("Either video_url or video_bytes is required")

        parts.append({"text": prompt})

        request_body = {
            "contents": [{"parts": parts}],
            "generationConfig": {
                "temperature": 0.4,
                "maxOutputTokens": 2048,
            },
        }

        try:
            response = await client.post(
                url,
                json=request_body,
                params={"key": self.api_key},
                timeout=180.0,  # Video analysis can take time
            )

            if response.status_code != 200:
                raise GeminiAPIError(f"Video analysis failed: {response.text[:200]}")

            data = response.json()
            candidates = data.get("candidates", [])

            if candidates:
                content = candidates[0].get("content", {})
                parts = content.get("parts", [])
                for part in parts:
                    if "text" in part:
                        log.info("analyze_video_complete")
                        return part["text"]

            raise GeminiAPIError("No analysis result in response")

        except httpx.TimeoutException:
            raise GeminiTimeoutError("Video analysis request timed out")
        except httpx.RequestError as e:
            raise GeminiAPIError(f"Request failed: {e}", retryable=True)

    async def extract_video_frames(
        self,
        video_bytes: bytes,
        frame_count: int = 5,
    ) -> list[bytes]:
        """Extract key frames from a video.

        Uses Gemini to analyze video and extract representative frames.

        Args:
            video_bytes: Video file bytes
            frame_count: Number of frames to extract

        Returns:
            List of frame image bytes

        Note:
            This is a simplified implementation. For production,
            consider using ffmpeg or opencv for frame extraction.
        """
        log = logger.bind(frame_count=frame_count)
        log.info("extract_video_frames_start")

        # For now, we'll ask Gemini to describe key moments
        # In production, use ffmpeg: ffmpeg -i video.mp4 -vf "select=eq(ptype\,I)" -vsync vfr frame_%d.png
        # Or use cv2 to extract frames at intervals

        # Placeholder: Return empty list, actual implementation needs video processing library
        log.warning("extract_video_frames_not_implemented")
        return []

    async def close(self):
        """Close HTTP client and cleanup resources."""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None
