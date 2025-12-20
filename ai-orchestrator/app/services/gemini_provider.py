"""Gemini model provider implementation.

This module wraps the existing GeminiClient to conform to the
ModelProvider interface, enabling multi-provider support.
"""

from typing import AsyncIterator, TypeVar

import structlog
from pydantic import BaseModel

from app.core.config import get_settings
from app.services.gemini_client import GeminiClient, GeminiError
from app.services.model_provider import ModelProvider, ModelProviderError

logger = structlog.get_logger(__name__)

# Type variable for structured output
T = TypeVar("T", bound=BaseModel)


class GeminiProvider(ModelProvider):
    """Gemini model provider implementation.

    Wraps the existing GeminiClient to provide a unified interface
    for multi-provider AI model support.

    Example:
        provider = GeminiProvider()
        response = await provider.chat_completion([
            {"role": "user", "content": "Hello!"}
        ])
    """

    def __init__(
        self,
        api_key: str | None = None,
        chat_model: str | None = None,
        fast_model: str | None = None,
        max_retries: int = 3,
        backoff_base: float = 1.0,
        backoff_factor: float = 2.0,
        timeout: float = 60.0,
    ):
        """Initialize Gemini provider.

        Args:
            api_key: Gemini API key (defaults to settings)
            chat_model: Model for chat completion (defaults to gemini-3-pro-preview)
            fast_model: Model for fast completion (defaults to gemini-2.5-flash)
            max_retries: Maximum retry attempts
            backoff_base: Base wait time for retries in seconds
            backoff_factor: Multiplier for exponential backoff
            timeout: Request timeout in seconds
        """
        super().__init__(
            provider_name="gemini",
            max_retries=max_retries,
            backoff_base=backoff_base,
            backoff_factor=backoff_factor,
            timeout=timeout,
        )

        settings = get_settings()
        self.api_key = api_key or settings.gemini_api_key
        self.chat_model = chat_model or settings.gemini_model_chat
        self.fast_model = fast_model or settings.gemini_model_fast

        # Initialize underlying Gemini client
        self.client = GeminiClient(
            api_key=self.api_key,
            chat_model=self.chat_model,
            fast_model=self.fast_model,
            max_retries=max_retries,
            backoff_base=backoff_base,
            backoff_factor=backoff_factor,
            timeout=timeout,
        )

        logger.info(
            "gemini_provider_initialized",
            chat_model=self.chat_model,
            fast_model=self.fast_model,
        )

    async def chat_completion(
        self,
        messages: list[dict[str, str]],
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> str:
        """Generate chat completion using Gemini.

        Args:
            messages: List of message dicts with 'role' and 'content'
            temperature: Optional temperature override (0.0-1.0)
            max_tokens: Optional maximum tokens (not used by Gemini)

        Returns:
            Generated response text

        Raises:
            ModelProviderError: If generation fails
        """
        log = logger.bind(
            provider="gemini",
            model=self.chat_model,
            message_count=len(messages),
        )
        log.info("chat_completion_start")

        try:
            result = await self.client.chat_completion(
                messages=messages,
                temperature=temperature,
            )

            log.info(
                "chat_completion_complete",
                response_length=len(result) if result else 0,
            )

            return result

        except GeminiError as e:
            # Convert GeminiError to ModelProviderError
            raise ModelProviderError(
                message=e.message,
                code=e.code,
                retryable=e.retryable,
                provider="gemini",
            )
        except Exception as e:
            raise self._handle_error(e)

    async def chat_completion_stream(
        self,
        messages: list[dict[str, str]],
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> AsyncIterator[str]:
        """Generate streaming chat completion using Gemini.

        Args:
            messages: List of message dicts with 'role' and 'content'
            temperature: Optional temperature override (0.0-1.0)
            max_tokens: Optional maximum tokens (not used by Gemini)

        Yields:
            str: Text chunks as they are generated

        Raises:
            ModelProviderError: If generation fails
        """
        log = logger.bind(
            provider="gemini",
            model=self.fast_model,
            message_count=len(messages),
        )
        log.info("chat_completion_stream_start")

        try:
            async for chunk in self.client.chat_completion_stream(
                messages=messages,
                temperature=temperature,
            ):
                yield chunk

            log.info("chat_completion_stream_complete")

        except GeminiError as e:
            # Convert GeminiError to ModelProviderError
            raise ModelProviderError(
                message=e.message,
                code=e.code,
                retryable=e.retryable,
                provider="gemini",
            )
        except Exception as e:
            raise self._handle_error(e)

    async def structured_output(
        self,
        messages: list[dict[str, str]],
        schema: type[T],
        temperature: float | None = None,
    ) -> T:
        """Generate structured output using Gemini.

        Args:
            messages: List of message dicts with 'role' and 'content'
            schema: Pydantic model class for output structure
            temperature: Optional temperature override (0.0-1.0)

        Returns:
            Parsed Pydantic model instance

        Raises:
            ModelProviderError: If generation fails
        """
        log = logger.bind(
            provider="gemini",
            model=self.chat_model,
            schema=schema.__name__,
        )
        log.info("structured_output_start")

        try:
            result = await self.client.structured_output(
                messages=messages,
                schema=schema,
                temperature=temperature,
            )

            log.info("structured_output_complete")

            return result

        except GeminiError as e:
            # Convert GeminiError to ModelProviderError
            raise ModelProviderError(
                message=e.message,
                code=e.code,
                retryable=e.retryable,
                provider="gemini",
            )
        except Exception as e:
            raise self._handle_error(e)

    async def fast_completion(
        self,
        messages: list[dict[str, str]],
        temperature: float | None = None,
    ) -> str:
        """Generate fast completion using Gemini Flash.

        This is a Gemini-specific method for quick responses.

        Args:
            messages: List of message dicts with 'role' and 'content'
            temperature: Optional temperature override (0.0-1.0)

        Returns:
            Generated response text

        Raises:
            ModelProviderError: If generation fails
        """
        log = logger.bind(
            provider="gemini",
            model=self.fast_model,
        )
        log.info("fast_completion_start")

        try:
            result = await self.client.fast_completion(
                messages=messages,
                temperature=temperature,
            )

            log.info("fast_completion_complete")

            return result

        except GeminiError as e:
            raise ModelProviderError(
                message=e.message,
                code=e.code,
                retryable=e.retryable,
                provider="gemini",
            )
        except Exception as e:
            raise self._handle_error(e)

    async def generate_image(
        self,
        prompt: str,
        aspect_ratio: str = "1:1",
        use_pro_model: bool = False,
        reference_images: list[bytes] | None = None,
    ) -> bytes:
        """Generate image using Gemini.

        This is a Gemini-specific method for image generation.

        Args:
            prompt: Text description of the image
            aspect_ratio: Aspect ratio (1:1, 16:9, 9:16, 4:3, 3:4)
            use_pro_model: Use Pro model for higher quality
            reference_images: Optional reference images

        Returns:
            Generated image bytes

        Raises:
            ModelProviderError: If generation fails
        """
        try:
            return await self.client.generate_image(
                prompt=prompt,
                aspect_ratio=aspect_ratio,
                use_pro_model=use_pro_model,
                reference_images=reference_images,
            )
        except GeminiError as e:
            raise ModelProviderError(
                message=e.message,
                code=e.code,
                retryable=e.retryable,
                provider="gemini",
            )
        except Exception as e:
            raise self._handle_error(e)
