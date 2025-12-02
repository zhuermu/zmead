"""Gemini 3 unified client with native image/video generation.

This module provides a unified client for Gemini 3 Pro, supporting:
- Multi-turn conversation
- Native image generation (gemini-2.5-flash-image, gemini-3-pro-image-preview)
- Video generation (Veo 3.1)
- Function calling for sub-agents
- Thinking mode for complex reasoning

Reference: https://ai.google.dev/gemini-api/docs/gemini-3

Requirements: Architecture v3.0 - Simplified Agent Architecture
"""

import asyncio
import base64
import json
from typing import Any, Callable, AsyncGenerator
from enum import Enum

import httpx
import structlog
from pydantic import BaseModel, Field

from app.core.config import get_settings

logger = structlog.get_logger(__name__)


class ThinkingLevel(str, Enum):
    """Thinking level for Gemini 3 reasoning."""
    LOW = "low"  # Faster, lower cost
    HIGH = "high"  # Maximum reasoning (default)


class MediaResolution(str, Enum):
    """Media resolution for multimodal processing."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ImageSize(str, Enum):
    """Image output size."""
    SIZE_1K = "1K"
    SIZE_2K = "2K"
    SIZE_4K = "4K"


class AspectRatio(str, Enum):
    """Aspect ratio for image/video generation."""
    SQUARE = "1:1"
    LANDSCAPE = "16:9"
    PORTRAIT = "9:16"
    STANDARD = "4:3"
    STANDARD_PORTRAIT = "3:4"


class Gemini3Error(Exception):
    """Base error for Gemini 3 client."""
    def __init__(self, message: str, code: str = "UNKNOWN", retryable: bool = False):
        super().__init__(message)
        self.code = code
        self.retryable = retryable


class Gemini3RateLimitError(Gemini3Error):
    """Rate limit exceeded."""
    def __init__(self, message: str = "Rate limit exceeded"):
        super().__init__(message, code="RATE_LIMIT", retryable=True)


class Gemini3TimeoutError(Gemini3Error):
    """Request timeout."""
    def __init__(self, message: str = "Request timed out"):
        super().__init__(message, code="TIMEOUT", retryable=True)


class Gemini3ImageGenerationError(Gemini3Error):
    """Image generation failed."""
    def __init__(self, message: str, retryable: bool = True):
        super().__init__(message, code="IMAGE_GENERATION_FAILED", retryable=retryable)


class Gemini3VideoGenerationError(Gemini3Error):
    """Video generation failed."""
    def __init__(self, message: str, retryable: bool = True):
        super().__init__(message, code="VIDEO_GENERATION_FAILED", retryable=retryable)


class FunctionDeclaration(BaseModel):
    """Function declaration for Gemini function calling."""
    name: str
    description: str
    parameters: dict[str, Any] = Field(default_factory=dict)


class GenerationConfig(BaseModel):
    """Configuration for content generation."""
    temperature: float = 1.0
    top_p: float | None = None
    top_k: int | None = None
    max_output_tokens: int | None = None
    thinking_level: ThinkingLevel | None = None
    media_resolution: MediaResolution | None = None
    response_modalities: list[str] | None = None  # ["TEXT", "IMAGE"]
    response_mime_type: str | None = None


class ImageConfig(BaseModel):
    """Configuration for image generation."""
    aspect_ratio: AspectRatio = AspectRatio.SQUARE
    image_size: ImageSize = ImageSize.SIZE_2K


class Gemini3Client:
    """Unified Gemini 3 client with native multimodal capabilities.

    Supports:
    - Text generation with thinking mode
    - Native image generation
    - Video generation with Veo 3.1
    - Function calling for sub-agents
    - Streaming responses

    Usage:
        client = Gemini3Client()

        # Text chat
        response = await client.chat([
            {"role": "user", "content": "Hello!"}
        ])

        # Generate image
        image_bytes = await client.generate_image(
            "A professional ad for headphones",
            aspect_ratio=AspectRatio.SQUARE,
        )

        # Generate video
        video_result = await client.generate_video(
            "A product showcase video",
            duration=4,
        )

        # Function calling
        response = await client.chat_with_tools(
            messages=[...],
            tools=[creative_agent, performance_agent, ...],
        )
    """

    GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta"

    # Model names
    MODEL_CHAT = "gemini-3-pro-preview"  # Main chat model
    MODEL_IMAGE = "gemini-2.5-flash-image"  # Fast image generation
    MODEL_IMAGE_PRO = "gemini-3-pro-image-preview"  # High quality image
    MODEL_VEO = "veo-3.1-generate-preview"  # Video generation
    MODEL_VEO_FAST = "veo-3.1-fast-generate-preview"  # Fast video generation

    def __init__(
        self,
        api_key: str | None = None,
        chat_model: str | None = None,
        image_model: str | None = None,
        video_model: str | None = None,
    ):
        """Initialize Gemini 3 client.

        Args:
            api_key: Gemini API key (uses env if not provided)
            chat_model: Override chat model name
            image_model: Override image model name
            video_model: Override video model name
        """
        settings = get_settings()
        self.api_key = api_key or settings.gemini_api_key

        self.chat_model = chat_model or settings.gemini_model_chat or self.MODEL_CHAT
        self.image_model = image_model or settings.gemini_model_imagen or self.MODEL_IMAGE
        self.video_model = video_model or settings.gemini_model_veo or self.MODEL_VEO

        self._http_client: httpx.AsyncClient | None = None

    async def _get_http_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient(
                timeout=httpx.Timeout(120.0, connect=10.0),
                headers={"x-goog-api-key": self.api_key},
            )
        return self._http_client

    async def close(self):
        """Close the HTTP client."""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None

    # =========================================================================
    # Text Generation
    # =========================================================================

    async def chat(
        self,
        messages: list[dict[str, Any]],
        config: GenerationConfig | None = None,
        system_instruction: str | None = None,
    ) -> str:
        """Generate text response from messages.

        Args:
            messages: List of messages [{"role": "user", "content": "..."}]
            config: Generation configuration
            system_instruction: System prompt

        Returns:
            Generated text response
        """
        client = await self._get_http_client()
        url = f"{self.GEMINI_API_BASE}/models/{self.chat_model}:generateContent"

        # Build request body
        body = self._build_chat_request(messages, config, system_instruction)

        try:
            response = await client.post(url, json=body)
            return self._parse_text_response(response)
        except httpx.TimeoutException:
            raise Gemini3TimeoutError()
        except httpx.HTTPError as e:
            raise Gemini3Error(f"HTTP error: {e}", retryable=True)

    async def chat_stream(
        self,
        messages: list[dict[str, Any]],
        config: GenerationConfig | None = None,
        system_instruction: str | None = None,
    ) -> AsyncGenerator[str, None]:
        """Stream text response from messages.

        Args:
            messages: List of messages
            config: Generation configuration
            system_instruction: System prompt

        Yields:
            Text chunks as they are generated
        """
        client = await self._get_http_client()
        # Use alt=sse for Server-Sent Events format
        url = f"{self.GEMINI_API_BASE}/models/{self.chat_model}:streamGenerateContent?alt=sse"

        body = self._build_chat_request(messages, config, system_instruction)
        body["generationConfig"] = body.get("generationConfig", {})

        try:
            async with client.stream("POST", url, json=body) as response:
                # Check for HTTP errors
                if response.status_code != 200:
                    error_body = await response.aread()
                    raise Gemini3Error(f"API error {response.status_code}: {error_body.decode()[:500]}")

                buffer = ""
                async for chunk in response.aiter_text():
                    buffer += chunk
                    # Process complete SSE messages
                    while "\n\n" in buffer:
                        message, buffer = buffer.split("\n\n", 1)
                        for line in message.split("\n"):
                            if line.startswith("data: "):
                                try:
                                    data = json.loads(line[6:])
                                    if "candidates" in data:
                                        for candidate in data["candidates"]:
                                            for part in candidate.get("content", {}).get("parts", []):
                                                if "text" in part:
                                                    yield part["text"]
                                except json.JSONDecodeError:
                                    continue
        except httpx.TimeoutException:
            raise Gemini3TimeoutError()

    # =========================================================================
    # Function Calling (Agents as Tools)
    # =========================================================================

    async def chat_with_tools(
        self,
        messages: list[dict[str, Any]],
        tools: list[FunctionDeclaration],
        tool_handlers: dict[str, Callable],
        config: GenerationConfig | None = None,
        system_instruction: str | None = None,
        max_iterations: int = 10,
    ) -> dict[str, Any]:
        """Chat with function calling support.

        This enables the Agents-as-Tools pattern where sub-agents are
        exposed as callable functions to the main orchestrator.

        Args:
            messages: Conversation messages
            tools: List of function declarations
            tool_handlers: Dict mapping function names to async handlers
            config: Generation configuration
            system_instruction: System prompt
            max_iterations: Maximum tool call iterations

        Returns:
            Final response with tool results
        """
        client = await self._get_http_client()
        url = f"{self.GEMINI_API_BASE}/models/{self.chat_model}:generateContent"

        # Build tools spec
        tools_spec = [{
            "functionDeclarations": [t.model_dump() for t in tools]
        }]

        current_messages = list(messages)
        iteration = 0

        while iteration < max_iterations:
            iteration += 1

            body = self._build_chat_request(current_messages, config, system_instruction)
            body["tools"] = tools_spec

            response = await client.post(url, json=body)
            result = self._parse_response(response)

            # Check for function calls (returns full parts with thoughtSignature)
            function_call_parts = self._extract_function_calls(result)

            if not function_call_parts:
                # No more function calls, return final response
                return {
                    "response": self._extract_text(result),
                    "messages": current_messages,
                    "iterations": iteration,
                }

            # Get all model parts to preserve thoughtSignature
            model_parts = self._extract_model_parts(result)

            # Add model response with all parts (preserves thoughtSignature)
            current_messages.append({
                "role": "model",
                "parts": model_parts
            })

            # Execute function calls and build responses
            function_response_parts = []
            for part in function_call_parts:
                func_call = part["functionCall"]
                func_name = func_call["name"]
                func_args = func_call.get("args", {})

                logger.info(
                    "executing_function_call",
                    function=func_name,
                    args=func_args,
                )

                if func_name in tool_handlers:
                    try:
                        func_result = await tool_handlers[func_name](**func_args)
                    except Exception as e:
                        func_result = {"error": str(e)}
                else:
                    func_result = {"error": f"Unknown function: {func_name}"}

                function_response_parts.append({
                    "functionResponse": {
                        "name": func_name,
                        "response": func_result,
                    }
                })

            # Add all function responses in a single message
            current_messages.append({
                "role": "function",
                "parts": function_response_parts
            })

        raise Gemini3Error(
            f"Exceeded max iterations ({max_iterations})",
            code="MAX_ITERATIONS",
        )

    # =========================================================================
    # Native Image Generation
    # =========================================================================

    async def generate_image(
        self,
        prompt: str,
        aspect_ratio: AspectRatio = AspectRatio.SQUARE,
        image_size: ImageSize = ImageSize.SIZE_2K,
        use_pro_model: bool = False,
        reference_images: list[bytes] | None = None,
    ) -> bytes:
        """Generate an image using Gemini native image generation.

        Uses responseModalities=["TEXT", "IMAGE"] as per official docs.

        Args:
            prompt: Text description of the image to generate
            aspect_ratio: Image aspect ratio
            image_size: Output image size (1K, 2K, 4K)
            use_pro_model: Use pro model for higher quality
            reference_images: Optional reference images for image-to-image

        Returns:
            Generated image as PNG bytes
        """
        client = await self._get_http_client()
        model = self.MODEL_IMAGE_PRO if use_pro_model else self.image_model
        url = f"{self.GEMINI_API_BASE}/models/{model}:generateContent"

        # Build content parts
        parts = []

        # Add reference images if provided
        if reference_images:
            for img_bytes in reference_images:
                parts.append({
                    "inlineData": {
                        "mimeType": "image/png",
                        "data": base64.b64encode(img_bytes).decode("utf-8"),
                    }
                })

        # Add text prompt
        parts.append({"text": prompt})

        body = {
            "contents": [{"parts": parts}],
            "generationConfig": {
                "responseModalities": ["TEXT", "IMAGE"],
                # Note: imageConfig (aspectRatio, imageSize) is not supported by
                # gemini-2.5-flash-image model - causes 500 error
            },
        }

        logger.info(
            "generate_image_request",
            model=model,
            aspect_ratio=aspect_ratio.value,
            image_size=image_size.value,
        )

        try:
            response = await client.post(url, json=body)

            if response.status_code == 429:
                raise Gemini3RateLimitError()

            if response.status_code >= 500:
                raise Gemini3ImageGenerationError(
                    f"Server error: {response.status_code}",
                    retryable=True,
                )

            if response.status_code != 200:
                error_text = response.text[:500]
                raise Gemini3ImageGenerationError(f"API error: {error_text}")

            data = response.json()

            # Extract image from response
            candidates = data.get("candidates", [])
            if not candidates:
                raise Gemini3ImageGenerationError("No candidates in response")

            for part in candidates[0].get("content", {}).get("parts", []):
                inline_data = part.get("inlineData", {})
                if inline_data and inline_data.get("mimeType", "").startswith("image/"):
                    image_data = inline_data.get("data")
                    if image_data:
                        logger.info("generate_image_success")
                        return base64.b64decode(image_data)

            raise Gemini3ImageGenerationError("No image data in response")

        except httpx.TimeoutException:
            raise Gemini3TimeoutError("Image generation timed out")

    async def generate_images(
        self,
        prompt: str,
        count: int = 4,
        aspect_ratio: AspectRatio = AspectRatio.SQUARE,
        image_size: ImageSize = ImageSize.SIZE_2K,
        use_pro_model: bool = False,
    ) -> list[bytes]:
        """Generate multiple images in parallel.

        Args:
            prompt: Text description
            count: Number of images to generate (1-10)
            aspect_ratio: Image aspect ratio
            image_size: Output size
            use_pro_model: Use pro model

        Returns:
            List of generated image bytes
        """
        count = min(max(count, 1), 10)

        tasks = [
            self.generate_image(
                prompt=prompt,
                aspect_ratio=aspect_ratio,
                image_size=image_size,
                use_pro_model=use_pro_model,
            )
            for _ in range(count)
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        images = []
        errors = []

        for result in results:
            if isinstance(result, Exception):
                errors.append(result)
            else:
                images.append(result)

        if not images:
            raise Gemini3ImageGenerationError(
                f"All {count} image generations failed: {errors[:3]}"
            )

        logger.info(
            "generate_images_complete",
            requested=count,
            generated=len(images),
            failed=len(errors),
        )

        return images

    # =========================================================================
    # Video Generation (Veo 3.1)
    # =========================================================================

    async def generate_video(
        self,
        prompt: str,
        duration: int = 4,
        aspect_ratio: AspectRatio = AspectRatio.LANDSCAPE,
        first_frame: bytes | None = None,
        last_frame: bytes | None = None,
        negative_prompt: str | None = None,
        use_fast_model: bool = False,
    ) -> dict[str, Any]:
        """Generate a video using Veo 3.1.

        This is a long-running operation. Returns operation_id for polling.

        Args:
            prompt: Text description of the video
            duration: Video duration in seconds (4, 6, or 8)
            aspect_ratio: Video aspect ratio (16:9 or 9:16)
            first_frame: Optional starting frame image
            last_frame: Optional ending frame (for interpolation)
            negative_prompt: Things to avoid in the video
            use_fast_model: Use fast model for quicker generation

        Returns:
            Dict with operation_id for polling, or video data if completed
        """
        client = await self._get_http_client()
        model = self.MODEL_VEO_FAST if use_fast_model else self.video_model
        url = f"{self.GEMINI_API_BASE}/models/{model}:predictLongRunning"

        # Validate duration
        if duration not in [4, 6, 8]:
            duration = 4

        # Build instance
        instance: dict[str, Any] = {"prompt": prompt}

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

        # Build parameters
        parameters = {
            "aspectRatio": aspect_ratio.value,
            "durationSeconds": duration,
        }

        if negative_prompt:
            parameters["negativePrompt"] = negative_prompt

        body = {
            "instances": [instance],
            "parameters": parameters,
        }

        logger.info(
            "generate_video_request",
            model=model,
            duration=duration,
            aspect_ratio=aspect_ratio.value,
        )

        try:
            response = await client.post(url, json=body)

            if response.status_code == 429:
                raise Gemini3RateLimitError()

            if response.status_code >= 400:
                error_text = response.text[:500]
                raise Gemini3VideoGenerationError(f"API error: {error_text}")

            data = response.json()

            # Return operation info for polling
            return {
                "operation_id": data.get("name"),
                "status": "pending",
                "model": model,
            }

        except httpx.TimeoutException:
            raise Gemini3TimeoutError("Video generation request timed out")

    async def poll_video_operation(
        self,
        operation_id: str,
        poll_interval: float = 10.0,
        max_wait: float = 300.0,
    ) -> dict[str, Any]:
        """Poll for video generation completion.

        Args:
            operation_id: Operation ID from generate_video
            poll_interval: Seconds between polls
            max_wait: Maximum wait time in seconds

        Returns:
            Dict with video URL and metadata
        """
        client = await self._get_http_client()
        url = f"{self.GEMINI_API_BASE}/{operation_id}"

        elapsed = 0.0

        while elapsed < max_wait:
            response = await client.get(url)
            data = response.json()

            if data.get("done"):
                # Video is ready
                if "error" in data:
                    raise Gemini3VideoGenerationError(
                        f"Video generation failed: {data['error']}"
                    )

                # Extract video URL
                result = data.get("response", {})
                videos = result.get("videos", [])

                if videos:
                    return {
                        "status": "completed",
                        "video_url": videos[0].get("uri"),
                        "duration": videos[0].get("durationSeconds"),
                    }

                raise Gemini3VideoGenerationError("No video in response")

            await asyncio.sleep(poll_interval)
            elapsed += poll_interval

        raise Gemini3TimeoutError(f"Video generation timed out after {max_wait}s")

    # =========================================================================
    # Helper Methods
    # =========================================================================

    def _build_chat_request(
        self,
        messages: list[dict[str, Any]],
        config: GenerationConfig | None,
        system_instruction: str | None,
    ) -> dict[str, Any]:
        """Build request body for chat endpoints."""
        # Convert messages to Gemini format
        contents = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            parts = msg.get("parts")

            if role == "system":
                # System messages handled separately
                continue

            gemini_role = "model" if role == "assistant" else role

            if parts:
                contents.append({"role": gemini_role, "parts": parts})
            else:
                contents.append({
                    "role": gemini_role,
                    "parts": [{"text": content}]
                })

        body: dict[str, Any] = {"contents": contents}

        # Add system instruction
        if system_instruction:
            body["systemInstruction"] = {"parts": [{"text": system_instruction}]}

        # Add generation config
        if config:
            gen_config: dict[str, Any] = {}

            if config.temperature is not None:
                gen_config["temperature"] = config.temperature
            if config.top_p is not None:
                gen_config["topP"] = config.top_p
            if config.top_k is not None:
                gen_config["topK"] = config.top_k
            if config.max_output_tokens is not None:
                gen_config["maxOutputTokens"] = config.max_output_tokens
            # Note: thinkingLevel is not supported in current Gemini API
            # if config.thinking_level is not None:
            #     gen_config["thinkingLevel"] = config.thinking_level.value
            if config.media_resolution is not None:
                gen_config["mediaResolution"] = config.media_resolution.value
            if config.response_modalities:
                gen_config["responseModalities"] = config.response_modalities

            if gen_config:
                body["generationConfig"] = gen_config

        return body

    def _parse_text_response(self, response: httpx.Response) -> str:
        """Parse text from API response."""
        if response.status_code == 429:
            raise Gemini3RateLimitError()

        if response.status_code != 200:
            raise Gemini3Error(
                f"API error {response.status_code}: {response.text[:500]}",
                retryable=response.status_code >= 500,
            )

        data = response.json()
        return self._extract_text(data)

    def _parse_response(self, response: httpx.Response) -> dict[str, Any]:
        """Parse full API response."""
        if response.status_code == 429:
            raise Gemini3RateLimitError()

        if response.status_code != 200:
            raise Gemini3Error(
                f"API error {response.status_code}: {response.text[:500]}",
                retryable=response.status_code >= 500,
            )

        return response.json()

    def _extract_text(self, data: dict[str, Any]) -> str:
        """Extract text from response data."""
        candidates = data.get("candidates", [])
        if not candidates:
            return ""

        parts = candidates[0].get("content", {}).get("parts", [])
        texts = [p.get("text", "") for p in parts if "text" in p]
        return "".join(texts)

    def _extract_function_calls(self, data: dict[str, Any]) -> list[dict[str, Any]]:
        """Extract function calls from response data.

        Returns the full part objects (including thoughtSignature) for Gemini 3.
        """
        candidates = data.get("candidates", [])
        if not candidates:
            return []

        parts = candidates[0].get("content", {}).get("parts", [])
        calls = []

        for part in parts:
            if "functionCall" in part:
                # Return the full part to preserve thoughtSignature
                calls.append(part)

        return calls

    def _extract_model_parts(self, data: dict[str, Any]) -> list[dict[str, Any]]:
        """Extract all parts from model response, preserving thoughtSignature."""
        candidates = data.get("candidates", [])
        if not candidates:
            return []

        return candidates[0].get("content", {}).get("parts", [])


# Singleton instance
_client: Gemini3Client | None = None


def get_gemini3_client() -> Gemini3Client:
    """Get or create Gemini 3 client singleton."""
    global _client
    if _client is None:
        _client = Gemini3Client()
    return _client


async def reset_gemini3_client():
    """Reset the Gemini 3 client (for testing)."""
    global _client
    if _client:
        await _client.close()
        _client = None
